import os
import time
import threading
import requests
from services import (
    load_model_from_s3,
    is_svm_model_loaded,
    is_yolo_model_loaded,
)

TRAINER_IP = "YOUR_INSTANCE_2_IP"
TRAINER_PORT = "5001"
TRAINER_SECRET_ENDPOINT = "trigger_model_training_s9a7g3f4d8j1k"
TRAINER_API_KEY = "My-Super-Secret-Key-For-Training-1a2b3c4d"
TRAINER_URL = f"http://{TRAINER_IP}:{TRAINER_PORT}/{TRAINER_SECRET_ENDPOINT}"


def health_check():
    # فحص الموديلات الأساسية المعتمدة فقط (Face & Medicine) بعد إزالة الموديل العام
    if not is_svm_model_loaded() or not is_yolo_model_loaded():
        return {"status": "error", "message": "One or more models are not loaded"}, 500
    return {"status": "success", "message": "Server is running and core models (Face & Medicine) are loaded"}, 200


def reload_model():
    success = load_model_from_s3()
    if success:
        # إنشاء Thread منفصل لإنهاء الـ Worker الحالي بسلام بعد ثانية واحدة
        # لضمان إرسال استجابة الـ 200 OK للمستخدم أولاً دون انقطاع الاتصال
        def kill_worker():
            time.sleep(1)
            print("🔄 Gracefully exiting current worker to reload models in memory...")
            os._exit(0)

        threading.Thread(target=kill_worker).start()

        return {"status": "success", "message": "Model downloaded successfully. Worker memory is refreshing."}, 200
    return {"status": "error", "message": "Failed to reload model."}, 500


def start_retrain_process():
    try:
        headers = {"X-Auth-Key": TRAINER_API_KEY}
        response = requests.post(TRAINER_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"message": "Retraining process started!"}, 202
        return {"error": "Training server failed"}, 500
    except Exception as exc:
        return {"error": f"Could not connect to training server: {exc}"}, 500
