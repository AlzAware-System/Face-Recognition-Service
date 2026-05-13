from flask import Flask, jsonify, request # لازم نضيف 'request'
import subprocess
import os

app = Flask(__name__)

# --- 1. كلمة السر (الباسورد) ---
# الموبايل لازم يبعت الباسورد ده عشان السيرفر يوافق
# !! غيّره لكلمة سر معقدة جداً ومحدش يعرفها !!
THE_SECRET_API_KEY = "My-Super-Secret-Key-For-Training-1a2b3c4d"


# --- 2. المسارات المهمة (زي ما هي) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# !! تأكد من المسار ده لنسخة البايثون جوه الـ venv
PYTHON_EXECUTABLE = os.path.join(BASE_DIR, "venv/bin/python3.12")
RETRAIN_SCRIPT_PATH = os.path.join(BASE_DIR, "retrain6.py")


# --- 3. الـ Endpoint (باسم صعب التخمين) ---
# ده اللينك اللي الموبايل هيكلمه
@app.route('/trigger_model_training_s9a7g3f4d8j1k', methods=['POST'])
def start_training_endpoint():
    """
    بيستقبل الأوامر من الموبايل (لو الباسورد صح)
    """

    # --- 4. التحقق من الباسورد (الأمان) ---
    # هنتفق إن الموبايل هيبعت الباسورد في "Header" اسمه 'X-Auth-Key'
    received_key = request.headers.get('X-Auth-Key')

    if not received_key or received_key != THE_SECRET_API_KEY:
        # لو الباسورد غلط أو مش موجود، ارفض الطلب
        print("Access denied: Invalid or missing API key.")
        return jsonify({"error": "Unauthorized"}), 401 # 401 = غير مصرح له

    # --- 5. لو الباسورد صح، شغل الكود ---
    print("Access granted. Received training request...")
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
