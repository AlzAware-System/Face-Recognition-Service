from services import (
    CURRENT_FRAME_RESULT,
    RAW_FRAME_BUFFER,
    buffer_lock,
    frame_processed_event,
)

def process_uploaded_frame(image_file):
    if image_file is None:
        return {"error": "No image file part"}, 400

    image_bytes = image_file.read()
    
    # 1️⃣ وضع أحدث صورة في الـ Buffer وتصفير الإشعار
    with buffer_lock:
        RAW_FRAME_BUFFER["image_bytes"] = image_bytes
        frame_processed_event.clear()
        RAW_FRAME_BUFFER["new_frame"] = True

    # 2️⃣ انتظار الـ Worker يخلص معالجة الصورة دي (بحد أقصى 10 ثواني مثلاً)
    processed = frame_processed_event.wait(timeout=10.0)
    
    if not processed:
        return {"error": "Timeout waiting for background worker"}, 504

    with buffer_lock:
        current_result = CURRENT_FRAME_RESULT.copy()

    # تحديد الاسم والنوع بناءً على الموديل اللي اشتغل
    if current_result.get("face_prediction") not in ["Paused", "Waiting..."]:
        resp_name = current_result.get("face_prediction")
        resp_type = "Person"
        mode = "face"
    else:
        resp_name = current_result.get("object_prediction", "Unknown")
        resp_type = current_result.get("object_type", "None")
        mode = "object"

    # الرد فوري بنتيجة الصورة دي بالظبط (مفيش كاش قديم)
    return {
        "status": "success",
        "mode": mode,
        "name": resp_name,
        "type": resp_type,
        "cached": False 
    }, 200

def get_latest_results():
    with buffer_lock:
        results = CURRENT_FRAME_RESULT.copy()
    results["current_server_mode"] = "auto_sequential"
    return results, 200
