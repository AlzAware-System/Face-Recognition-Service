from services import (
    LATEST_RESULTS_CACHE,
    RAW_FRAME_BUFFER,
    buffer_lock,
)

def process_uploaded_frame(image_file):
    if image_file is None:
        return {"error": "No image file part"}, 400

    image_bytes = image_file.read()

    # 1️⃣ وضع أحدث صورة في الـ Buffer وإسقاط أي صورة قديمة
    with buffer_lock:
        RAW_FRAME_BUFFER["image_bytes"] = image_bytes
        RAW_FRAME_BUFFER["new_frame"] = True

    # 2️⃣ جلب أحدث نتيجة تم حسابها مسبقاً من الـ Cache
    with buffer_lock:
        current_result = LATEST_RESULTS_CACHE.copy()

    # تحديد الاسم والنوع بناءً على الموديل اللي اشتغل
    if current_result.get("face_prediction") not in ["Paused", "Waiting..."]:
        resp_name = current_result.get("face_prediction")
        resp_type = "Person"
        mode = "face"
    else:
        resp_name = current_result.get("object_prediction", "Unknown")
        resp_type = current_result.get("object_type", "None")
        mode = "object"

    # الرد فوري (لن يحدث Timeout أبداً)
    return {
        "status": "success",
        "mode": mode,
        "name": resp_name,
        "type": resp_type,
        "cached": True # مجرد علامة ليك إن دي نتيجة من الكاش
    }, 200

def get_latest_results():
    with buffer_lock:
        results = LATEST_RESULTS_CACHE.copy()
    results["current_server_mode"] = "auto_sequential"
    return results, 200
