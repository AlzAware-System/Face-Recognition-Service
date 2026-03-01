import boto3
import cv2
import os
from datetime import datetime
import time

# --- AWS Credentials and S3 Settings ---
AWS_ACCESS_KEY_ID = "AKIAVYEWBBZULJUHUSE7"
AWS_SECRET_ACCESS_KEY = "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"
S3_BUCKET_NAME = "elasticbeanstalk-eu-north-1-395451633256"
S3_REGION = "eu-north-1"

# Create a connection to S3
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=S3_REGION
)

def run_camera_loop(camera_url, s3_client, bucket_name):
    """
    Connects to the camera, flushes the buffer, and uploads a
    fresh frame every 3 seconds.
    """
    print(f"Attempting to connect to camera: {camera_url}...")
    video_capture = cv2.VideoCapture(camera_url)

    if not video_capture.isOpened():
        print("Error: Could not connect to the camera stream. Please check the URL.")
        return

    print("Successfully connected. Starting capture loop (every 3 seconds)...")
    print("Press Ctrl+C to stop the program.")

    try:
        while True:
            
            # ==========================================================
            # ===   NEW UPDATE: flush camera buffer before reading    ===
            # ===   Read and discard old frames so the next frame     ===
            # ===   is the most recent one available.                 ===
            # ==========================================================
            for _ in range(40):
                video_capture.grab() # .grab() is faster than .read() when discarding frames

            # 1. Capture the latest frame
            # .read() now returns the latest available frame
            ret, frame = video_capture.read()
            if not ret:
                print("Error: Failed to read a frame from the camera. Attempting to reconnect...")
                # (... reconnection flow remains as-is ...)
                video_capture.release()
                video_capture = cv2.VideoCapture(camera_url)
                if not video_capture.isOpened():
                    print("Reconnect failed. Waiting 10 seconds...")
                    time.sleep(0.1)
                continue

            print("Frame captured successfully (it's the latest one).")

            # 2. Encode the frame to JPG format in memory
            is_success, buffer = cv2.imencode(".jpg", frame)
            if not is_success:
                print("Error: Failed to encode frame to JPG.")
                time.sleep(0.1)
                continue

            image_bytes = buffer.tobytes()

            # 3. Create a unique filename
            file_name = "engmo.jpg" # Use the fixed filename as requested
        
            # 4. Upload the image to S3
            try:
                print(f"Uploading {file_name} to {bucket_name} (overwriting)...")
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_name,
                    Body=image_bytes,
                    ContentType='image/jpeg'
                )
                print(f"Upload successful: {file_name}")

            except Exception as e:
                print(f"An error occurred during S3 upload: {e}")

            # 5. Wait for 5 seconds
            # Note: the message says 1 second and the sleep value matches that behavior
            print("--- Waiting for 1 second ---") 
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nLoop stopped by user.")
    except Exception as e:
        print(f"An unexpected error occurred in the main loop: {e}")
    finally:
        print("Releasing camera connection.")
        video_capture.release()


if name == "main":
    # ==========================================================
    # ===   MUST EDIT: set your camera stream URL here        ===
    # ==========================================================
    CAMERA_STREAM_URL = "http://192.168.2.37:8080/video" # <--- Replace with your camera URL
    # ==========================================================

    # Start the continuous loop
    run_camera_loop(CAMERA_STREAM_URL, s3_client, S3_BUCKET_NAME)