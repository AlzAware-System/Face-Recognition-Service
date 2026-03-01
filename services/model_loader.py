import os
import boto3
import joblib
from ultralytics import YOLO

from . import model_state

S3_BUCKET_NAME = "elasticbeanstalk-eu-north-1-395451633256"
MODEL_FILE_KEY = "models/svm_model.pkl"
LOCAL_MODEL_PATH = "/tmp/svm_model.pkl"
s3_client = boto3.client("s3", region_name="eu-north-1")

YOLO_MEDICINE_MODEL_PATH = "object.pt"
YOLO_GENERAL_MODEL_PATH = "yolov8n.pt"


def load_model_from_s3():
    try:
        print(f"Downloading model {MODEL_FILE_KEY} from S3...")
        s3_client.download_file(S3_BUCKET_NAME, MODEL_FILE_KEY, LOCAL_MODEL_PATH)
        model_state.svm_model, model_state.label_encoder = joblib.load(LOCAL_MODEL_PATH)
        print("✅ Face Recognition Model (SVM) loaded successfully from S3.")
        return True
    except Exception as exc:
        print(f"❌ FATAL ERROR: Failed to load SVM model from S3. {exc}")
        return False


def load_yolo_model():
    try:
        if not os.path.exists(YOLO_MEDICINE_MODEL_PATH):
            print(f"❌ FATAL ERROR: YOLO Medicine model file not found at {YOLO_MEDICINE_MODEL_PATH}")
            return False

        device = "cpu"
        print(f"Loading YOLO Medicine model... (using {device})")
        model_state.yolo_medicine_model = YOLO(YOLO_MEDICINE_MODEL_PATH)
        model_state.yolo_medicine_model.to(device)
        print("✅ Medicine Detection (YOLO Expert) model loaded successfully.")
        return True
    except Exception as exc:
        print(f"❌ FATAL ERROR: Failed to load YOLO Medicine model. {exc}")
        return False


def load_yolo_general_model():
    try:
        if not os.path.exists(YOLO_GENERAL_MODEL_PATH):
            print(f"❌ FATAL ERROR: YOLO General model file not found at {YOLO_GENERAL_MODEL_PATH}")
            return False

        device = "cpu"
        print(f"Loading YOLO General model... (using {device})")
        model_state.yolo_general_model = YOLO(YOLO_GENERAL_MODEL_PATH)
        model_state.yolo_general_model.to(device)
        print("✅ General Object Detection (YOLO General) model loaded successfully.")
        return True
    except Exception as exc:
        print(f"❌ FATAL ERROR: Failed to load YOLO General model. {exc}")
        return False


def is_svm_model_loaded():
    return model_state.svm_model is not None


def is_yolo_model_loaded():
    return model_state.yolo_medicine_model is not None


def is_yolo_general_model_loaded():
    return model_state.yolo_general_model is not None
