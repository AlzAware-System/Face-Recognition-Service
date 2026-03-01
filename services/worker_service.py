import time
import threading

from .state_store import RAW_FRAME_BUFFER, LATEST_RESULTS_CACHE, buffer_lock


def analysis_worker():
    global LATEST_RESULTS_CACHE, RAW_FRAME_BUFFER
    print("Background analysis worker is running...")

    while True:
        image_to_process = None

        if RAW_FRAME_BUFFER["new_frame"]:
            with buffer_lock:
                image_to_process = RAW_FRAME_BUFFER["image_bytes"]
                RAW_FRAME_BUFFER["new_frame"] = False

            if image_to_process:
                pass

        time.sleep(0.05)


def start_analysis_worker():
    worker_thread = threading.Thread(target=analysis_worker, daemon=True)
    worker_thread.start()
