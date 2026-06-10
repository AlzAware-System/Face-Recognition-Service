import os
import jwt
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv

load_dotenv()

def _get_secret() -> str:
    secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT secret not configured. "
            "Set JWT_SECRET or SECRET_KEY in environment / .env file."
        )
    return secret

def _extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None

def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": "Missing Authorization header. Please provide a Bearer token.",
            }), 401

        try:
            secret = _get_secret()
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": "Token has expired. Please log in again.",
            }), 401
        except jwt.InvalidSignatureError:
            fallback = os.getenv("JWT_SECRET_OLD")
            if fallback:
                try:
                    payload = jwt.decode(token, fallback, algorithms=["HS256"])
                except Exception:
                    return jsonify({
                        "status": "error",
                        "code": "AUTH_ERROR",
                        "message": "Invalid token signature.",
                    }), 401
            else:
                return jsonify({
                    "status": "error",
                    "code": "AUTH_ERROR",
                    "message": "Invalid token signature.",
                }), 401
        except jwt.DecodeError:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": "Token is malformed.",
            }), 401
        except Exception as exc:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": f"Token validation failed: {exc}",
            }), 401

        request.current_user_payload = payload
        return fn(*args, **kwargs)

    return wrapper

THE_SECRET_API_KEY = os.getenv("API_KEY", "My-Super-Secret-Key-For-Training-1a2b3c4d")

def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        received_key = request.headers.get("X-Auth-Key")
        if not received_key or received_key != THE_SECRET_API_KEY:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": "Invalid or missing X-Auth-Key header.",
            }), 401

        return fn(*args, **kwargs)

    return wrapper
