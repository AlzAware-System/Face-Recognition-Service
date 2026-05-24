import io
import numpy as np
from PIL import Image
from . import model_state
from .model_loader import is_svm_model_loaded, is_yolo_model_loaded

def predict_face(image_bytes):
    if not is_svm_model_loaded():
        return False, "Model is not loaded"

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_array = np.array(img)
        faces = model_state.detector.detect_faces(img_array)
        if not faces:
            return False, "No face detected"

        x, y, w, h = faces[0]["box"]
        face = img_array[y : y + h, x : x + w]
        face_img = Image.fromarray(face).resize((160, 160))
        face_array = np.array(face_img).astype("float32") / 255.0
        face_array = np.expand_dims(face_array, axis=0)
        embedding = model_state.facenet.predict(face_array)[0]
        embedding = embedding.reshape(1, -1)
        prediction_index = model_state.svm_model.predict(embedding)[0]
        prediction_name = model_state.label_encoder.inverse_transform([prediction_index])[0]
        return True, {"prediction": str(prediction_name)}
    except Exception as exc:
        return False, f"Prediction failed: {exc}"

def predict_medicine(image_bytes):
    if not is_yolo_model_loaded():
        return False, "YOLO Medicine model is not loaded"

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        all_detections = []

        results_medicine = model_state.yolo_medicine_model(img, verbose=False)
        for box in results_medicine[0].boxes:
            all_detections.append(
                {
                    "name": model_state.yolo_medicine_model.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "type": "medicine",
                }
            )

        if not all_detections:
            return False, "No medicine detected"

        # جلب أفضل دقة للأدوية
        best_detection = max(all_detections, key=lambda detection: detection["confidence"])
        return True, {"detection": best_detection}
    except Exception as exc:
        return False, f"Prediction failed: {exc}"
