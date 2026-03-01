import boto3
import os
import cv2
import numpy as np
import random
from keras_facenet import FaceNet
from mtcnn import MTCNN
from sklearn.svm import SVC
import joblib
from sklearn.preprocessing import LabelEncoder
import requests
from PIL import Image
import pickle
from io import BytesIO

#to get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ----------------------
# CONFIG
# ----------------------
S3_BUCKET_NAME = "elasticbeanstalk-eu-north-1-395451633256"
TRAINING_DIR_PREFIX = 'training_data/'
MODEL_FILE_KEY = "models/svm_model.pkl"
CACHE_FILE_KEY = "models/embeddings_cache.pkl"
RELOAD_URL = "http://13.61.141.216:5000/reload_eng_mo"

# Augmentation / quality thresholds
AUGMENT_IF_LT = 10      # If a person has fewer images than this, generate augmentations
NUM_AUG_PER_IMAGE = 8     # Number of augmentations per original image
MIN_FACE_SIZE = 60        # Minimum acceptable face width/height
MIN_CONFIDENCE = 0.9    # Face detection confidence threshold

# ----------------------
# INIT
# ----------------------
print("Initializing FaceNet & MTCNN...")
facenet = FaceNet().model   # facenet model (Keras)
detector = MTCNN()

print("Initializing S3 client...")
s3_client = boto3.client('s3')


# ----------------------
# IMAGE UTILITIES
# ----------------------
def augment_face(face, num_aug=NUM_AUG_PER_IMAGE):
    """Generate augmented versions of a face with controlled variations"""
    augmented_faces = [face.copy()]
    h, w = face.shape[:2]

    for _ in range(num_aug):
        img = face.copy()

        # Rotate ±10 degrees
        angle = random.uniform(-10, 10)
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)

        # Flip sometimes
        if random.random() > 0.5:
            img = cv2.flip(img, 1)

        # Gamma / lighting variation
        gamma = random.uniform(0.9, 1.2)
        invGamma = 1.0 / gamma
        table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(256)]).astype("uint8")
        img = cv2.LUT(img, table)

        # Brightness/contrast slight change
        alpha = random.uniform(0.95, 1.15)
        beta = random.randint(-8, 8)
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

        # Small gaussian noise sometimes
        if random.random() > 0.6:
            noise = np.random.normal(0, 2, img.shape).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Light blur rarely
        if random.random() > 0.85:
            img = cv2.GaussianBlur(img, (3, 3), 0)

        augmented_faces.append(img)

    return augmented_faces


def enhance_face(face):
    """Enhance face image: gamma, denoise, CLAHE, light sharpen, normalization.
       Input/Output: RGB uint8 image shape (160,160,3)"""
    # Gamma correction
    gamma = 1.15
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(256)]).astype("uint8")
    face = cv2.LUT(face, table)

    # Denoise (light)
    face = cv2.fastNlMeansDenoisingColored(face, None, 6, 6, 7, 21)

    # CLAHE on L channel
    lab = cv2.cvtColor(face, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    face = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)

    # Gentle sharpening
    kernel = np.array([[0, -0.4, 0],
                       [-0.4, 2.6, -0.4],
                       [0, -0.4, 0]])
    face = cv2.filter2D(face, -1, kernel)

    # Normalize
    face = cv2.normalize(face, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

    return face


def detect_and_extract_face_from_bgr(img_bgr, min_confidence=MIN_CONFIDENCE):
    """Detect best face and return 160x160 RGB uint8 face or None"""
    try:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        img_rgb = img_bgr.copy()

    faces = detector.detect_faces(img_rgb)
    if not faces:
        return None

    best = max(faces, key=lambda f: f.get('confidence', 0))
    if best.get('confidence', 0) < min_confidence:
        return None

    x, y, w, h = best['box']
    # sanitize coordinates
    x, y = max(0, x), max(0, y)
    w, h = max(0, w), max(0, h)
    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE:
        return None

    face = img_rgb[y:y+h, x:x+w]
    face = cv2.resize(face, (160, 160))
    face = enhance_face(face)
    return face


def face_to_embedding(face_rgb):
    """face_rgb: uint8 (160,160,3) RGB -> returns 1D numpy embedding (float32)"""
    arr = face_rgb.astype('float32') / 255.0
    arr = np.expand_dims(arr, axis=0)
    emb = facenet.predict(arr)[0]
    return emb


# ----------------------
# CACHING UTILITIES
# ----------------------
def load_cache():
    print(f"Loading embeddings cache from S3 ({CACHE_FILE_KEY})...")
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=CACHE_FILE_KEY)
        cache_data = pickle.loads(response['Body'].read())
        print(f"Cache loaded. Found {len(cache_data)} cached items.")
        return cache_data
    except s3_client.exceptions.NoSuchKey:
        print("No cache file found. Starting fresh.")
        return {}
    except Exception as e:
        print(f"Error loading cache: {e}. Starting fresh.")
        return {}


def save_cache(cache_data):
    print(f"Saving new cache ({len(cache_data)} items) to S3 ({CACHE_FILE_KEY})...")

    # Update: use BASE_DIR to store the temporary file
    local_cache_path = os.path.join(BASE_DIR, "cache.pkl")

    try:
        with open(local_cache_path, "wb") as f:
            pickle.dump(cache_data, f)

        s3_client.upload_file(local_cache_path, S3_BUCKET_NAME, CACHE_FILE_KEY)
        os.remove(local_cache_path) # Remove the temporary file
        print("Cache saved successfully.")
    except Exception as e:
        print(f"Error saving cache: {e}")


# ----------------------
# MAIN RETRAINING PIPELINE
# ----------------------
def run_retraining():
    print("--- Starting Retraining Process ---")
    cached_data = load_cache()

    # list all objects under prefix
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=TRAINING_DIR_PREFIX)

    s3_objects = []
    for page in pages:
        for obj in page.get('Contents', []):
            s3_objects.append(obj)

    # build label counts (how many images per person)
    label_counts = {}
    for obj in s3_objects:
        key = obj['Key']
        if key.endswith('/') or obj.get('Size', 0) == 0:
            continue
        parts = key.split('/')
        if len(parts) < 2:
            continue
        label = parts[-2]
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"Found {len(s3_objects)} S3 objects (including folders). Unique labels: {len(label_counts)}")
    current_embeddings = []
    current_labels = []
    new_cache_data = {}

    processed_count = 0
    cache_hit_count = 0

    for obj in s3_objects:
        s3_key = obj['Key']
        s3_size = obj.get('Size', 0)
        s3_etag = obj.get('ETag', '')
        if s3_key.endswith('/') or s3_size == 0:
            continue

        try:
            label = s3_key.split('/')[-2]

            # If in cache and unchanged -> reuse embedding
            if s3_key in cached_data and cached_data[s3_key].get('etag') == s3_etag:
                emb = cached_data[s3_key]['embedding']
                lbl = cached_data[s3_key]['label']
                current_embeddings.append(emb)
                current_labels.append(lbl)
                new_cache_data[s3_key] = cached_data[s3_key]
                cache_hit_count += 1
                continue

            # Otherwise, download and process
            print(f"Cache miss or changed file: {s3_key} -> downloading")
            resp = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            image_data = resp['Body'].read()
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                print(f"Warning: could not decode image {s3_key}. Skipping.")
                continue

            face = detect_and_extract_face_from_bgr(img, min_confidence=MIN_CONFIDENCE)
            if face is None:
                print(f"Warning: no usable face found in {s3_key}. Skipping.")
                continue

            # Decide whether to augment (if label has few examples)
            count_for_label = label_counts.get(label, 0)
            if count_for_label < AUGMENT_IF_LT:
                aug_faces = augment_face(face, num_aug=NUM_AUG_PER_IMAGE)
                for f in aug_faces:
                    emb = face_to_embedding(f)
                    current_embeddings.append(emb)
                    current_labels.append(label)
                # For cache, store embedding for the original image (not all augmentations)
                stored_emb = face_to_embedding(face)
                new_cache_data[s3_key] = {'etag': s3_etag, 'embedding': stored_emb, 'label': label}
                processed_count += 1
            else:
                emb = face_to_embedding(face)
                current_embeddings.append(emb)
                current_labels.append(label)
                new_cache_data[s3_key] = {'etag': s3_etag, 'embedding': emb, 'label': label}
                processed_count += 1

        except Exception as e:
            print(f"Error processing {s3_key}: {e}")

    if not current_labels:
        print("No training data found or processed. Exiting.")
        return

    print("--- Data Fetching Summary ---")
    print(f"Total training samples (after augmentation): {len(current_labels)}")
    print(f"Cache hits: {cache_hit_count}, Newly processed: {processed_count}")
    print(f"Unique people: {len(set(current_labels))}")

    # Train
    print("Training new SVM model (RBF kernel)...")
    encoder = LabelEncoder()
    labels_encoded = encoder.fit_transform(current_labels)

    # Use RBF which often performs better on embeddings; tune C/gamma as needed
    new_svm_model = SVC(kernel='rbf', probability=True, C=10, gamma='scale')
    new_svm_model.fit(np.array(current_embeddings), labels_encoded)

    # Update: use BASE_DIR to store the temporary file
    local_model_path = os.path.join(BASE_DIR, "svm_model_new.joblib")

    joblib.dump((new_svm_model, encoder), local_model_path)
    print(f"New model + encoder saved locally -> {local_model_path}")

    # Upload model
    try:
        print(f"Uploading new model to S3 ({MODEL_FILE_KEY})...")
        s3_client.upload_file(local_model_path, S3_BUCKET_NAME, MODEL_FILE_KEY)
        print("✅ Model uploaded to S3.")

        # Save cache
        save_cache(new_cache_data)
        print("✅ Cache uploaded to S3.")

    except Exception as e:
        print(f"❌ Error uploading model/cache to S3: {e}")
        return

    # notify server to reload
    try:
        print(f"Requesting server to reload model at {RELOAD_URL} ...")
        resp = requests.post(RELOAD_URL, timeout=10)
        if resp.status_code == 200:
            print("✅ Server reloaded model successfully.")
        else:
            print(f"⚠ Server reload responded with {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"❌ Failed to notify server: {e}")

    print("--- Retraining finished ---")


if __name__ == "__main__":
    run_retraining()