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
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(BASE_DIR, "training.lock")

S3_BUCKET_NAME = "mobile-app2"
TRAINING_DIR_PREFIX = 'training_data/'
MODEL_FILE_KEY = "models/svm_model.pkl"
CACHE_FILE_KEY = "models/embeddings_cache.pkl"
RELOAD_URL = "http://56.228.63.146:5000/reload_eng_mo"

AUGMENT_IF_LT = 10
NUM_AUG_PER_IMAGE = 8
MIN_FACE_SIZE = 60
MIN_CONFIDENCE = 0.9
THE_SECRET_API_KEY = os.getenv("API_KEY", "My-Super-Secret-Key-For-Training-1a2b3c4d")

print("Initializing FaceNet & MTCNN...")
facenet = FaceNet().model
detector = MTCNN()

print("Initializing S3 client...")
s3_client = boto3.client('s3')

def create_lock():
    with open(LOCK_FILE, 'w') as f:
        f.write("Training in progress...")

def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def augment_face(face, num_aug=NUM_AUG_PER_IMAGE):
    augmented_faces = [face.copy()]
    h, w = face.shape[:2]
    for _ in range(num_aug):
        img = face.copy()
        angle = random.uniform(-10, 10)
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1)
        img = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        if random.random() > 0.5:
            img = cv2.flip(img, 1)
        gamma = random.uniform(0.9, 1.2)
        invGamma = 1.0 / gamma
        table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(256)]).astype("uint8")
        img = cv2.LUT(img, table)
        alpha = random.uniform(0.95, 1.15)
        beta = random.randint(-8, 8)
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        if random.random() > 0.6:
            noise = np.random.normal(0, 2, img.shape).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        if random.random() > 0.85:
            img = cv2.GaussianBlur(img, (3, 3), 0)
        augmented_faces.append(img)
    return augmented_faces

def enhance_face(face):
    gamma = 1.15
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(256)]).astype("uint8")
    face = cv2.LUT(face, table)
    face = cv2.fastNlMeansDenoisingColored(face, None, 6, 6, 7, 21)
    lab = cv2.cvtColor(face, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    face = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    kernel = np.array([[0, -0.4, 0], [-0.4, 2.6, -0.4], [0, -0.4, 0]])
    face = cv2.filter2D(face, -1, kernel)
    face = cv2.normalize(face, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    return face

def detect_and_extract_face_from_bgr(img_bgr, min_confidence=MIN_CONFIDENCE):
    try:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        img_rgb = img_bgr.copy()
    faces = detector.detect_faces(img_rgb)
    if not faces: return None
    best = max(faces, key=lambda f: f.get('confidence', 0))
    if best.get('confidence', 0) < min_confidence: return None
    x, y, w, h = best['box']
    x, y = max(0, x), max(0, y)
    w, h = max(0, w), max(0, h)
    if w < MIN_FACE_SIZE or h < MIN_FACE_SIZE: return None
    face = img_rgb[y:y+h, x:x+w]
    face = cv2.resize(face, (160, 160))
    face = enhance_face(face)
    return face

def face_to_embedding(face_rgb):
    arr = face_rgb.astype('float32') / 255.0
    arr = np.expand_dims(arr, axis=0)
    emb = facenet.predict(arr)[0]
    return emb

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
    local_cache_path = os.path.join(BASE_DIR, "cache.pkl")
    try:
        with open(local_cache_path, "wb") as f:
            pickle.dump(cache_data, f)
        s3_client.upload_file(local_cache_path, S3_BUCKET_NAME, CACHE_FILE_KEY)
        os.remove(local_cache_path)
        print("Cache saved successfully.")
    except Exception as e:
        print(f"Error saving cache: {e}")

def run_retraining_logic():
    print("--- Starting Retraining Logic (PERSISTENT MEMORY MODE) ---")
    cached_data = load_cache()
    new_cache_data = cached_data.copy()

    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=TRAINING_DIR_PREFIX)
    s3_objects = []
    for page in pages:
        for obj in page.get('Contents', []):
            s3_objects.append(obj)

    label_counts = {}
    for obj in s3_objects:
        key = obj['Key']
        if key.endswith('/') or obj.get('Size', 0) == 0: continue
        parts = key.split('/')
        if len(parts) < 2: continue
        label = parts[-2]
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"Found {len(s3_objects)} CURRENT S3 objects.")
    processed_count = 0
    cache_hit_count = 0

    for obj in s3_objects:
        s3_key = obj['Key']
        s3_size = obj.get('Size', 0)
        s3_etag = obj.get('ETag', '')
        if s3_key.endswith('/') or s3_size == 0: continue

        try:
            if s3_key in new_cache_data and new_cache_data[s3_key].get('etag') == s3_etag:
                cache_hit_count += 1
                continue

            print(f"Processing new/changed file: {s3_key}")
            label = s3_key.split('/')[-2]
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

            if label_counts.get(label, 0) < AUGMENT_IF_LT:
                aug_faces = augment_face(face, num_aug=NUM_AUG_PER_IMAGE)
                for i, f in enumerate(aug_faces):
                    emb = face_to_embedding(f)
                    aug_key = f"{s3_key}_aug_{i}"
                    new_cache_data[aug_key] = {'etag': s3_etag, 'embedding': emb, 'label': label, 'is_aug': True}
            else:
                emb = face_to_embedding(face)
                new_cache_data[s3_key] = {'etag': s3_etag, 'embedding': emb, 'label': label}

            processed_count += 1
        except Exception as e:
            print(f"Error processing {s3_key}: {e}")

    final_embeddings = []
    final_labels = []
    print("Gathering all data (persistent history) for training...")
    for key, data in new_cache_data.items():
        final_embeddings.append(data['embedding'])
        final_labels.append(data['label'])

    if not final_labels:
        print("No training data found at all. Exiting.")
        return

    print("--- Data Summary ---")
    print(f"Total historical samples: {len(final_labels)}")
    print(f"Unique people (historical): {len(set(final_labels))}")

    print("Training new SVM model (RBF kernel)...")
    encoder = LabelEncoder()
    labels_encoded = encoder.fit_transform(final_labels)
    new_svm_model = SVC(kernel='rbf', probability=True, C=10, gamma='scale')
    new_svm_model.fit(np.array(final_embeddings), labels_encoded)

    local_model_path = os.path.join(BASE_DIR, "svm_model_new.joblib")
    joblib.dump((new_svm_model, encoder), local_model_path)
    print(f"New model saved locally -> {local_model_path}")

    try:
        print(f"Uploading new model to S3 ({MODEL_FILE_KEY})...")
        s3_client.upload_file(local_model_path, S3_BUCKET_NAME, MODEL_FILE_KEY)
        print("✅ Model uploaded.")
        save_cache(new_cache_data)
        print("✅ Persistent cache uploaded.")
    except Exception as e:
        print(f"❌ Error uploading: {e}")
        return

    try:
        headers = {"X-Auth-Key": THE_SECRET_API_KEY}
        requests.post(RELOAD_URL, headers=headers, timeout=10)
        print("✅ Server reload requested with X-Auth-Key.")
    except Exception as e:
        print(f"⚠️ Failed to send reload request: {e}")

def main():
    print("--- Retraining Script Started ---")
    if os.path.exists(LOCK_FILE):
        print("⚠️ Lock file exists. Training is already in progress. Exiting.")
        return

    try:
        print("🔒 Creating lock file...")
        create_lock()
        run_retraining_logic()
    except Exception as e:
        print(f"❌ FATAL ERROR during retraining: {e}")
    finally:
        print("🔓 Removing lock file...")
        remove_lock()
    print("--- Retraining Script Finished ---")

if __name__ == "__main__":
    main()