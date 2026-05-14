from services import (
    predict_face,
    predict_medicine,
    is_svm_model_loaded,
    is_yolo_model_loaded,
    is_yolo_general_model_loaded,
    LATEST_RESULTS_CACHE,
    buffer_lock,
)
from .mode_controller import get_active_mode


def process_uploaded_frame(image_file):
    if image_file is None:
        return {"error": "No image file part"}, 400

    image_bytes = image_file.read()

    response_name = "Unknown"
    response_type = "None"
    current_mode = get_active_mode()

    if current_mode == "face":
        if is_svm_model_loaded():
            success, result = predict_face(image_bytes)
            if success:
                LATEST_RESULTS_CACHE["face_prediction"] = result["prediction"]
                response_name = result["prediction"]
                response_type = "Person"
            else:
                LATEST_RESULTS_CACHE["face_prediction"] = "Unknown"
                response_name = "Unknown"

        LATEST_RESULTS_CACHE["object_prediction"] = "Paused"

    elif current_mode == "object":
        if is_yolo_model_loaded() and is_yolo_general_model_loaded():
            success, result = predict_medicine(image_bytes)
            if success:
                LATEST_RESULTS_CACHE["object_prediction"] = result["detection"]["name"]
                LATEST_RESULTS_CACHE["object_type"] = result["detection"]["type"]
                response_name = result["detection"]["name"]
                response_type = result["detection"]["type"]
            else:
                LATEST_RESULTS_CACHE["object_prediction"] = "No Object"
                response_name = "No Object"

        LATEST_RESULTS_CACHE["face_prediction"] = "Paused"

    return {
        "status": "success",
        "mode": current_mode,
        "name": response_name,
        "type": response_type,
    }, 200


def get_latest_results():
    with buffer_lock:
        results = LATEST_RESULTS_CACHE.copy()
    results["current_server_mode"] = get_active_mode()
    return results, 200
