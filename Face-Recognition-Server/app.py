from flask import Flask
from warnings import simplefilter
try:
    from routes import register_routes
except Exception:
    from controllers import register_routes
from services import load_model_from_s3, load_yolo_model

# Hide TensorFlow/Scikit-learn warnings
simplefilter(action='ignore', category=FutureWarning)

app = Flask(__name__, static_folder='static', template_folder='templates')

register_routes(app)

print("Starting server initialization...")

# 1. Load face model (SVM)
if not load_model_from_s3():
    print("⚠️ WARNING: Server started WITHOUT Face Recognition model.")
else:
    print("✅ Face Recognition model loaded successfully.")

# 2. Load medicine model (YOLO expert)
if not load_yolo_model():
    print("⚠️ WARNING: Server started WITHOUT Medicine Detection model.")
else:
    print("✅ Medicine Detection (YOLO Expert) model loaded successfully.")

print("--- Server initialized ---")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
