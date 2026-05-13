import boto3
import os
import cv2
import numpy as np
from keras_facenet import FaceNet
from mtcnn import MTCNN
from sklearn.svm import SVC
import joblib
from sklearn.preprocessing import LabelEncoder
import requests
from PIL import Image

# --- 1. إعدادات المشروع ---

# --- 2. إعدادات AWS S3 ---
# ### انتبه: هذا الباكيت سيُستخدم للقراءة (الصور) والكتابة (الموديل)
S3_BUCKET_NAME = "elasticbeanstalk-eu-north-1-395451633256"
# ### هذا هو المسار الذي ستقوم برفع الصور إليه يدويًا
TRAINING_DIR_PREFIX = 'training_data/'
MODEL_FILE_KEY = "models/svm_model.pkl" # المسار + الاسم على S3

# --- 3. إعدادات سيرفر الإنتاج (Elastic Beanstalk) ---
RELOAD_URL = "http://facenet-env.eba-ss6qgkvu.eu-north-1.elasticbeanstalk.com/your-secret-reload-path-12345" # !! تأكد من رابط السيرفر !!

# --- 4. تهيئة الأدوات ---
print("Initializing models (FaceNet, MTCNN)...")
facenet = FaceNet().model
detector = MTCNN()



print("Initializing AWS S3 client...")
# ### تأكد أن السيرفر عليه صلاحيات AWS (عن طريق aws configure أو IAM Role)
s3_client = boto3.client('s3')

def get_face_embedding(image_bytes):
    """
    ### هذه الدالة لم تتغير إطلاقاً
    لأنها تتعامل مع "bytes" بغض النظر عن مصدرها
    """
    try:
        img_array = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        faces = detector.detect_faces(img)
        if len(faces) == 0:
            return None # لم يتم العثور على وجه

        x, y, w, h = faces[0]['box']
        face = img[y:y+h, x:x+w]
        face_img = Image.fromarray(face).resize((160, 160))
        face_array = np.array(face_img).astype('float32') / 255.0
        face_array = np.expand_dims(face_array, axis=0)

        embedding = facenet.predict(face_array)[0]
        return embedding
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def run_retraining():
    print("--- Starting Retraining Process ---")

    # --- أ. تحميل البيانات من S3 (بدلاً من Firebase) ---
    print(f"Fetching training data from S3 Bucket ({S3_BUCKET_NAME}/{TRAINING_DIR_PREFIX})...")
    embeddings = []
    labels = []

    # ### التغيير الرئيسي: جلب الملفات من S3
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=TRAINING_DIR_PREFIX)

    s3_objects = []
    for page in pages:
        s3_objects.extend(page.get('Contents', []))

    for obj in s3_objects:
        s3_key = obj['Key']
        s3_size = obj['Size']

        # تجاهل المجلدات (التي تنتهي بـ /) والملفات الفارغة
        if not s3_key.endswith('/') and s3_size > 0:
            try:
                # استخراج "الاسم" (Label) من المسار
                # مثال: 'training_data/mohamed/img1.jpg' -> 'mohamed'
                label = s3_key.split('/')[-2]

                print(f"Processing {s3_key} (Label: {label})...")

                # ### التغيير: تحميل بيانات الصورة من S3
                response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                image_data = response['Body'].read()

                embedding = get_face_embedding(image_data)

                if embedding is not None:
                    embeddings.append(embedding)
                    labels.append(label)
                else:
                    print(f"Warning: No face found in {s3_key}. Skipping.")
            except Exception as e:
                print(f"Error downloading/processing {s3_key}: {e}")

    if not labels:
        print("No training data found. Exiting.")
        return

    print(f"Successfully processed {len(labels)} images for {len(set(labels))} unique people.")

    # --- ب. تدريب الموديل ---
    # ### هذا الجزء لم يتغير إطلاقاً
    print("Training new SVM model...")

    encoder = LabelEncoder()
    labels_encoded = encoder.fit_transform(labels)

    new_svm_model = SVC(kernel='linear', probability=True)
    new_svm_model.fit(embeddings, labels_encoded)

    local_model_path = "svm_model_new.pkl"

    joblib.dump((new_svm_model, encoder), local_model_path)
    print(f"New model and encoder saved locally as {local_model_path}.")

    # --- ج. رفع الموديل إلى S3 ---
    # ### هذا الجزء لم يتغير إطلاقاً
    print(f"Uploading new model to S3 Bucket ({S3_BUCKET_NAME}) as {MODEL_FILE_KEY}...")
    try:
        s3_client.upload_file(local_model_path, S3_BUCKET_NAME, MODEL_FILE_KEY)
        print("✅ Model successfully uploaded to S3.")
    except Exception as e:
        print(f"❌ Error uploading to S3: {e}")
        return

    # --- د. إخبار السيرفر بإعادة التحميل ---
    # ### هذا الجزء لم يتغير إطلاقاً
    print(f"Sending reload request to server: {RELOAD_URL}...")
    try:
        response = requests.post(RELOAD_URL)
        if response.status_code == 200:
            print("✅ Server responded: Model reloaded successfully!")
        else:
            print(f"⚠️ Server responded with error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Failed to send reload request: {e}")

    print("--- Retraining Process Finished ---")

if __name__ == "__main__":
    run_retraining()
