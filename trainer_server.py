from flask import Flask, jsonify, request
import subprocess
import os
from middleware.auth import jwt_required

app = Flask(__name__)

# --- 1. المسارات المهمة ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# !! تأكد من المسار ده لنسخة البايثون جوه الـ venv
PYTHON_EXECUTABLE = os.path.join(BASE_DIR, "venv/bin/python3.12")
RETRAIN_SCRIPT_PATH = os.path.join(BASE_DIR, "retrain6.py")


# --- 2. الـ Endpoint ---
@app.route('/trigger_model_training_s9a7g3f4d8j1k', methods=['POST'])
@jwt_required
def start_training_endpoint():
    """
    بيستقبل الأوامر من الموبايل ويبدأ تدريب الموديل
    محمي بواسطة JWT من الـ Auth-ChatBot-Service
    """
    print("Access granted via JWT. Received training request...")
    try:
        command = [PYTHON_EXECUTABLE, RETRAIN_SCRIPT_PATH]
        subprocess.Popen(command)
        print("Training process started in background.")
        return jsonify({"message": "Training process started!"}), 200

    except Exception as e:
        print(f"Error starting retrain script: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # هنشغله على بورت 5001 ومفتوح للكل
    app.run(host='0.0.0.0', port=5001)
