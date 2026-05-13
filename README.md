# 🧠 Face-Recognition-Service

> **AI-powered inference engine for real-time face recognition, medicine detection, and general object detection — designed for the AlzAware smart glasses platform.**

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Prerequisites](#-prerequisites)
- [Installation & Setup](#-installation--setup)
- [Running the Server](#-running-the-server)
- [API Endpoints](#-api-endpoints)
- [Authentication (JWT)](#-authentication-jwt)
- [AI Models](#-ai-models)
- [Camera Upload Script](#-camera-upload-script)
- [Project Structure](#-project-structure)
- [Dependencies](#-dependencies)

---

## 🌟 Overview

This service is the **AI inference engine** for the AlzAware smart glasses. It receives image frames from the glasses (or any client), processes them through AI models, and returns recognition results in real-time.

The service supports two operational modes:
- **Face Mode**: Identifies people using FaceNet + SVM
- **Object Mode**: Detects medicines (YOLO Expert) and general objects (YOLO General)

---

## ✨ Features

| Feature | Description |
|:---|:---|
| 👤 **Face Recognition** | FaceNet embedding + SVM classifier with MTCNN face detection |
| 💊 **Medicine Detection** | Custom-trained YOLO model for identifying medicines |
| 🔍 **General Object Detection** | YOLO general model for everyday object detection |
| 🔄 **Hot-Reload** | Update AI models from AWS S3 without server restart |
| 🔐 **Authentication** | Mixed auth: JWT for model management, X-Auth-Key for frame uploads |
| ⚡ **In-Memory Models** | Models loaded directly into RAM for fast inference |
| 📸 **Real-Time Processing** | Frame-by-frame analysis from camera stream |

---

## 🏗️ Architecture

```
┌─────────────────────────┐
│   Smart Glasses / App   │
│   (Camera Stream)       │
└──────────┬──────────────┘
           │
           │ POST /api/upload_frame
           │ + Authorization: Bearer <JWT>
           │ + image file
           ▼
┌──────────────────────────────────────────┐
│         Face-Recognition-Service         │
│  ┌────────────────────────────────────┐  │
│  │       JWT Auth Middleware          │  │
│  │  (Verifies token from Auth Svc)   │  │
│  └──────────────┬─────────────────────┘  │
│                 │                        │
│  ┌──────────────▼─────────────────────┐  │
│  │       Mode Controller              │  │
│  │  ┌──────────┐  ┌───────────────┐   │  │
│  │  │Face Mode │  │ Object Mode   │   │  │
│  │  │(FaceNet) │  │(YOLO Expert + │   │  │
│  │  │ + SVM    │  │ YOLO General) │   │  │
│  │  └──────────┘  └───────────────┘   │  │
│  └────────────────────────────────────┘  │
│                 │                        │
│  ┌──────────────▼─────────────────────┐  │
│  │     Results Cache (In-Memory)      │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
           │
           │ Model files
           ▼
    ┌──────────────┐
    │   AWS S3      │
    │  (Model .pkl) │
    └──────────────┘
```

---

## 📦 Prerequisites

- **Python** 3.11 or later
- **AWS Account** with S3 bucket for model storage
- **Auth-ChatBot-Service** running (for JWT token issuance)

> **Note**: TensorFlow and YOLO models require significant RAM. Recommended: 4GB+ RAM.

---

## 🚀 Installation & Setup

### 1. Create virtual environment & install dependencies

```powershell
cd Face-Recognition-Service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment

Create or edit the `.env` file:

```env
# JWT Secret — MUST match the SECRET_KEY in Auth-ChatBot-Service/.env
SECRET_KEY=your-secret-key-change-in-production
```

> ⚠️ **Critical**: This `SECRET_KEY` **must be identical** to the one in `Auth-ChatBot-Service/.env`. If they don't match, the JWT authentication will fail and users won't be able to upload frames.

### 3. Run the server

```powershell
python app.py
```

Server will listen on: **http://localhost:5000**

### Startup Output

On successful startup you should see:
```
Starting server initialization...
✅ Face Recognition model loaded successfully.
✅ Medicine Detection (YOLO Expert) model loaded successfully.
✅ General Object Detection (YOLO General) model loaded successfully.
--- Server initialized ---
```

If a model fails to load, you'll see a warning but the server will still start:
```
⚠️ WARNING: Server started WITHOUT Face Recognition model.
```

---

## 📡 API Endpoints

### 1. Upload Frame — `POST /api/upload_frame` 🔒

Upload an image frame for AI analysis. **Requires X-Auth-Key header.**

| Detail | Value |
|:---|:---|
| **Method** | `POST` |
| **URL** | `/api/upload_frame` |
| **Auth** | 🔒 X-Auth-Key |
| **Content-Type** | `multipart/form-data` |
| **Body** | `image` — image file (JPG, PNG) |

#### Request

```bash
curl -X POST http://localhost:5000/api/upload_frame \
  -H "X-Auth-Key: My-Super-Secret-Key-For-Training-1a2b3c4d" \
  -F "image=@photo.jpg"
```

#### Success Response (200)

```json
{
  "status": "success",
  "mode": "face",
  "name": "Ahmed Ali",
  "type": "Person"
}
```

```json
{
  "status": "success",
  "mode": "object",
  "name": "Panadol",
  "type": "Medicine"
}
```

#### Error Responses

**401 — Missing Token:**
```json
{
  "status": "error",
  "code": "AUTH_ERROR",
  "message": "Missing Authorization header. Please provide a Bearer token."
}
```

**401 — Expired Token:**
```json
{
  "status": "error",
  "code": "AUTH_ERROR",
  "message": "Token has expired. Please log in again."
}
```

**401 — Invalid Token:**
```json
{
  "status": "error",
  "code": "AUTH_ERROR",
  "message": "Invalid token signature."
}
```

**400 — No Image:**
```json
{
  "error": "No image file part"
}
```

---

### 2. Set Active Mode — `POST /api/set_active_mode` 🔓

Switch between face recognition and object detection mode.

| Detail | Value |
|:---|:---|
| **Method** | `POST` |
| **URL** | `/api/set_active_mode` |
| **Auth** | 🔓 Public (no token required) |
| **Content-Type** | `application/json` |

#### Request

```bash
curl -X POST http://localhost:5000/api/set_active_mode \
  -H "Content-Type: application/json" \
  -d '{"mode": "face"}'
```

#### Valid Modes

| Mode | Description |
|:---|:---|
| `face` | Face recognition using FaceNet + SVM |
| `object` | Object/medicine detection using YOLO |

#### Response (200)

```json
{
  "status": "success",
  "mode": "face"
}
```

#### Error (400)

```json
{
  "error": "Invalid mode. Use 'face' or 'object'."
}
```

---

### 3. Get Latest Results — `GET /api/get_latest_results` 🔓

Retrieve the most recent recognition results from the cache.

```bash
curl http://localhost:5000/api/get_latest_results
```

#### Response (200)

```json
{
  "face_prediction": "Ahmed Ali",
  "object_prediction": "Paused",
  "current_server_mode": "face"
}
```

---

### 4. Health Check — `GET /health` 🔓

Check if all AI models are loaded and server is healthy.

```bash
curl http://localhost:5000/health
```

#### Response (200)

```json
{
  "status": "success",
  "message": "Server is running and all models are loaded"
}
```

#### Response (500) — Model not loaded

```json
{
  "status": "error",
  "message": "One or more models are not loaded"
}
```

---

### 5. Reload Model — `POST /reload_eng_mo` 🔒

Hot-reload the face recognition (SVM) model from AWS S3 without restarting the server. **Requires JWT authentication.**

```bash
curl -X POST http://localhost:5000/reload_eng_mo \
  -H "Authorization: Bearer <TOKEN_HERE>"
```

#### Response (200)

```json
{
  "status": "success",
  "message": "Model reloaded successfully."
}
```

---

### 6. Start Retraining — `POST /trigger_model_training_s9a7g3f4d8j1k` 🔒 (Trainer Server - port 5001)

Trigger model retraining on the training server. **Requires X-Auth-Key header.**

```bash
curl -X POST http://13.48.209.2:5001/trigger_model_training_s9a7g3f4d8j1k \
  -H "X-Auth-Key: My-Super-Secret-Key-For-Training-1a2b3c4d"
```

#### Response (202)

```json
{
  "message": "Retraining process started!"
}
```

---

## Endpoints Summary

| Method | Endpoint | Auth | Description |
|:---|:---|:---|:---|
| `POST` | `/api/upload_frame` | 🔒 API Key | Upload image for recognition |
| `POST` | `/api/set_active_mode` | 🔓 Public | Switch face/object mode |
| `GET` | `/api/get_latest_results` | 🔓 Public | Get cached results |
| `GET` | `/health` | 🔓 Public | Model health check |
| `POST` | `/reload_eng_mo` | 🔒 JWT | Hot-reload SVM model |
| `POST` | `/trigger_model...` | 🔒 JWT | Trigger retraining (port 5001) |

---

## 🔑 Authentication

This service uses **mixed authentication** depending on the endpoint's purpose.

### 1. JWT Authentication (Model Management)

The `/reload_eng_mo` and `/trigger_model_training_s9a7g3f4d8j1k` endpoints are protected with JWT authentication. Tokens are issued by the **Auth-ChatBot-Service** and verified here using a shared secret key (`SECRET_KEY`).

```bash
# Example: Trigger Training
curl -X POST http://13.48.209.2:5001/trigger_model_training_s9a7g3f4d8j1k \
  -H "Authorization: Bearer <TOKEN_HERE>"
```

### 2. API Key Authentication (Image Uploads)

The `/api/upload_frame` endpoint is protected with a static API Key. It requires the `X-Auth-Key` header. This is optimized for fast, continuous camera uploads where retrieving a JWT token might be inefficient.

```bash
# Example: Upload Frame
curl -X POST http://localhost:5000/api/upload_frame \
  -H "X-Auth-Key: My-Super-Secret-Key-For-Training-1a2b3c4d" \
  -F "image=@photo.jpg"
```

---

## 🧠 AI Models

### 1. Face Recognition Pipeline

| Component | Technology | Purpose |
|:---|:---|:---|
| **Face Detection** | MTCNN | Locates faces in the image |
| **Feature Extraction** | FaceNet (keras-facenet) | Generates 512-D face embeddings |
| **Classification** | SVM (scikit-learn) | Identifies the person |

**Flow**: Image → MTCNN (detect face) → FaceNet (extract 512-D embedding) → SVM (classify identity) → Result

### 2. Medicine Detection

| Component | Technology | Purpose |
|:---|:---|:---|
| **Detection** | YOLO (Expert) | Custom-trained for medicine identification |

### 3. General Object Detection

| Component | Technology | Purpose |
|:---|:---|:---|
| **Detection** | YOLO (General) | Pre-trained for everyday object detection |

### Model Storage

All models are stored on **AWS S3** and loaded into RAM on server startup:

- `svm_model.pkl` — Face recognition SVM model
- YOLO weights — Medicine and general object detection

### Hot Reload

Models can be updated without restarting the server:

```bash
# Reload the face recognition model from S3
curl -X POST http://localhost:5000/reload_eng_mo \
  -H "Authorization: Bearer <TOKEN_HERE>"
```

---

## 📸 Camera Upload Script

The `upload.py` script captures frames from a camera stream and uploads them to AWS S3 continuously.

### Usage

1. Edit the `CAMERA_STREAM_URL` in `upload.py`:
   ```python
   CAMERA_STREAM_URL = "http://192.168.2.37:8080/video"
   ```

2. Run the script:
   ```powershell
   python upload.py
   ```

### How It Works

1. Connects to the camera IP stream
2. Flushes the buffer to get the latest frame
3. Captures a fresh frame
4. Encodes to JPEG
5. Uploads to AWS S3 as `engmo.jpg` (overwriting)
6. Repeats every cycle

---

## 📁 Project Structure

```
Face-Recognition-Service/
├── app.py                          ← Entry point — initializes Flask, loads models
├── controllers/
│   ├── __init__.py                 ← Exports all controllers, registers routes
│   ├── inference_controller.py     ← Frame processing: face/object prediction
│   ├── mode_controller.py          ← Switch between face/object mode
│   └── system_controller.py        ← Health check, model reload, retrain trigger
├── middleware/
│   ├── __init__.py                 ← Middleware package
│   └── auth.py                     ← JWT authentication middleware
├── routes/
│   ├── __init__.py                 ← Route registration
│   ├── api_routes.py               ← REST API route definitions
│   └── page_routes.py              ← Web UI page routes
├── services/
│   ├── __init__.py                 ← Service exports
│   ├── model_loader.py             ← Download & load models from S3
│   ├── prediction_service.py       ← Face prediction & medicine detection
│   ├── model_state.py              ← Global model state management
│   ├── state_store.py              ← Results cache & frame buffer
│   └── worker_service.py           ← Background analysis worker
├── static/                         ← Static files (CSS, JS, images)
├── templates/                      ← HTML templates
├── upload.py                       ← Camera → S3 upload script
├── retrain3.py                     ← Model retraining script
├── .env                            ← Environment config (SECRET_KEY)
└── requirements.txt                ← Python dependencies
```

---

## 📚 Dependencies

| Package | Purpose |
|:---|:---|
| `Flask` >=3.0 | Web framework |
| `requests` >=2.31 | HTTP client (for training server communication) |
| `boto3` >=1.34 | AWS SDK (S3 model storage) |
| `numpy` >=1.26 | Numerical computation |
| `Pillow` >=10.0 | Image processing |
| `joblib` >=1.3 | Model serialization/deserialization |
| `scikit-learn` >=1.4 | SVM classifier |
| `opencv-python-headless` >=4.9 | Computer vision (image processing) |
| `ultralytics` >=8.2 | YOLO object detection models |
| `keras-facenet` >=0.3.2 | FaceNet face embedding model |
| `mtcnn` >=0.1.1 | Multi-task CNN face detection |
| `tensorflow` >=2.15 | Deep learning framework (FaceNet backend) |
| `gunicorn` >=21.2 | Production WSGI server |
| `PyJWT` >=2.8 | JWT token verification |
| `python-dotenv` >=1.0 | `.env` file loading |

---

## 🔒 Security Notes

- The `/reload_eng_mo` and `/trigger_model_training...` endpoints require a valid JWT token (`Authorization: Bearer <TOKEN>`)
- The `/api/upload_frame` endpoint requires a valid `X-Auth-Key` header
- JWT tokens are verified using the same `SECRET_KEY` as Auth-ChatBot-Service
- The `THE_SECRET_API_KEY` should be moved to environment variables in production
- AWS credentials in `upload.py` should be moved to environment variables in production
- In production, use Gunicorn behind Nginx with HTTPS

---

Built and maintained by **Mohamed Ashraf** and team. 🚀
