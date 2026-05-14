import threading

RAW_FRAME_BUFFER = {
    "image_bytes": None,
    "new_frame": False,
}

LATEST_RESULTS_CACHE = {
    "face_prediction": "Waiting...",
    "object_prediction": "Waiting...",
    "object_type": "none",
}

buffer_lock = threading.Lock()
