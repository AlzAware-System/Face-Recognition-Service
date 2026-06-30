import threading

RAW_FRAME_BUFFER = {
    "image_bytes": None,
    "new_frame": False,
}

CURRENT_FRAME_RESULT = {
    "face_prediction": "Waiting...",
    "object_prediction": "Waiting...",
    "object_type": "none",
}

buffer_lock = threading.Lock()
frame_processed_event = threading.Event()
