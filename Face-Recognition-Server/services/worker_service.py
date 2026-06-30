import time
import threading

from .state_store import RAW_FRAME_BUFFER, CURRENT_FRAME_RESULT, buffer_lock, frame_processed_event
from .prediction_service import predict_face, predict_medicine
from .model_loader import is_svm_model_loaded, is_yolo_model_loaded

def analysis_worker():
    global CURRENT_FRAME_RESULT, RAW_FRAME_BUFFER
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
                        CURRENT_FRAME_RESULT["face_prediction"] = result["prediction"]
                        CURRENT_FRAME_RESULT["object_prediction"] = "Paused"
                        CURRENT_FRAME_RESULT["object_type"] = "Person"

            # 2️⃣ لو مفيش وش، نشغل YOLO للأدوية
            if not face_success and is_yolo_model_loaded():
                success, result = predict_medicine(image_to_process)
                with buffer_lock:
                    if success:
                        CURRENT_FRAME_RESULT["object_prediction"] = result["detection"]["name"]
                        CURRENT_FRAME_RESULT["object_type"] = result["detection"]["type"]
                    else:
                        CURRENT_FRAME_RESULT["object_prediction"] = ""
                        CURRENT_FRAME_RESULT["object_type"] = "None"

                    CURRENT_FRAME_RESULT["face_prediction"] = "Paused"

            # إرسال إشعار إن الصورة دي خلصت
            frame_processed_event.set()

        # استراحة صغيرة جداً لعدم استهلاك الـ CPU بنسبة 100% وهو فارغ
        time.sleep(0.01)


def start_analysis_worker():
    worker_thread = threading.Thread(target=analysis_worker, daemon=True)
    worker_thread.start()
