from services import (
    predict_face,
    predict_medicine,
    is_svm_model_loaded,
    is_yolo_model_loaded,
    LATEST_RESULTS_CACHE,
    buffer_lock,
)

def process_uploaded_frame(image_file):
    if image_file is None:
        return {"error": "No image file part"}, 400

    image_bytes = image_file.read()

    response_name = "Unknown"
    response_type = "None"
    determined_mode = "face" # الوضع الذي نجح في التوقع

    # 1️⃣ أولاً: محاولة التعرف على الوجه (هو الأولوية القصوى للمريض)
    face_success = False
    if is_svm_model_loaded():
        success, result = predict_face(image_bytes)
        if success and result["prediction"] != "Unknown":
            face_success = True
            LATEST_RESULTS_CACHE["face_prediction"] = result["prediction"]
            LATEST_RESULTS_CACHE["object_prediction"] = "Paused"
            response_name = result["prediction"]
            response_type = "Person"
            determined_mode = "face"

    # 2️⃣ ثانياً: لو ملقاش وجوه (أو فشل الموديل)، يدخل تلقائياً على فحص الأدوية
    if not face_success:
        determined_mode = "object"
        if is_yolo_model_loaded():
            success, result = predict_medicine(image_bytes)
            if success:
                LATEST_RESULTS_CACHE["object_prediction"] = result["detection"]["name"]
                LATEST_RESULTS_CACHE["object_type"] = result["detection"]["type"]
                response_name = result["detection"]["name"]
                response_type = result["detection"]["type"]
            else:
                LATEST_RESULTS_CACHE["object_prediction"] = "No Object/Medicine"
                response_name = "No Object/Medicine"

        LATEST_RESULTS_CACHE["face_prediction"] = "Paused"

    return {
        "status": "success",
        "mode": determined_mode, # بنرجع للموبايل هو لقط إيه بالظبط
        "name": response_name,
        "type": response_type,
    }, 200

def get_latest_results():
    with buffer_lock:
        results = LATEST_RESULTS_CACHE.copy()
    # بنعرف الويب سايت بالوضع الحالي الذكي
    results["current_server_mode"] = "auto_sequential"
    return results, 200
