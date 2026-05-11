"""
JWT Authentication Middleware for Face-Recognition-Service.

This module verifies JWT tokens issued by the Auth-ChatBot-Service.
Both services MUST share the same SECRET_KEY (or JWT_SECRET) so that
tokens minted by one can be validated by the other.

Usage:
    from middleware.auth import jwt_required

    @app.route("/api/upload_frame", methods=["POST"])
    @jwt_required
    def upload_frame_route():
        ...
"""

import os
import jwt  # PyJWT
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv

# Load .env if present (so SECRET_KEY can live in a shared .env file)
load_dotenv()


def _get_secret() -> str:
    """Return the JWT signing secret shared with Auth-ChatBot-Service."""
    secret = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT secret not configured. "
            "Set JWT_SECRET or SECRET_KEY in environment / .env file."
        )
    return secret


def _extract_bearer_token() -> str | None:
    """Pull the raw token from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def jwt_required(fn):
    """Decorator that protects a Flask route with JWT authentication.

    On success the decoded payload is stored on:
        request.current_user_payload   – dict with sub, role, iat, exp, …

    On failure a JSON 401 response is returned immediately.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return jsonify({
                "status": "error",
                "code": "AUTH_ERROR",
                "message": "Missing Authorization header. "
                           "Please provide a Bearer token.",
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

        # Make the decoded claims available to the route handler
        request.current_user_payload = payload
        return fn(*args, **kwargs)

    return wrapper
