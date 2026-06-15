import time
import threading

from .state_store import RAW_FRAME_BUFFER, LATEST_RESULTS_CACHE, buffer_lock
from .prediction_service import predict_face, predict_medicine
from .model_loader import is_svm_model_loaded, is_yolo_model_loaded

def analysis_worker():
    global LATEST_RESULTS_CACHE, RAW_FRAME_BUFFER
    print("🚀 Background AI analysis worker is running...")

    while True:
        image_to_process = None

        # سحب أحدث صورة بأمان
        with buffer_lock:
            if RAW_FRAME_BUFFER["new_frame"]:
                image_to_process = RAW_FRAME_BUFFER["image_bytes"]
                RAW_FRAME_BUFFER["new_frame"] = False

        # لو في صورة جديدة، نبدأ المعالجة
        if image_to_process:
            face_success = False

            # 1️⃣ أولوية قصوى للوجوه
            if is_svm_model_loaded():
                success, result = predict_face(image_to_process)
                if success:
                    face_success = True
                    with buffer_lock:
                        LATEST_RESULTS_CACHE["face_prediction"] = result["prediction"]
                        LATEST_RESULTS_CACHE["object_prediction"] = "Paused"
                        LATEST_RESULTS_CACHE["object_type"] = "Person"

            # 2️⃣ لو مفيش وش، نشغل YOLO للأدوية
            if not face_success and is_yolo_model_loaded():
                success, result = predict_medicine(image_to_process)
                with buffer_lock:
                    if success:
                        LATEST_RESULTS_CACHE["object_prediction"] = result["detection"]["name"]
                        LATEST_RESULTS_CACHE["object_type"] = result["detection"]["type"]
                    else:
                        LATEST_RESULTS_CACHE["object_prediction"] = ""
                        LATEST_RESULTS_CACHE["object_type"] = "None"

                    LATEST_RESULTS_CACHE["face_prediction"] = "Paused"

        # استراحة صغيرة جداً لعدم استهلاك الـ CPU بنسبة 100% وهو فارغ
        time.sleep(0.01)


def start_analysis_worker():
    worker_thread = threading.Thread(target=analysis_worker, daemon=True)
    worker_thread.start()
