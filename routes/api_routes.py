from flask import request, jsonify
from controllers import (
    set_active_mode,
    process_uploaded_frame,
    get_latest_results,
    health_check,
    reload_model,
    start_retrain_process,
)
from middleware.auth import jwt_required, api_key_required


def register_api_routes(app):
    @app.route("/api/set_active_mode", methods=["POST"])
    def set_active_mode_route():
        payload = request.get_json(silent=True) or {}
        body, status = set_active_mode(payload)
        return jsonify(body), status

    @app.route("/api/upload_frame", methods=["POST"])
    @api_key_required
    def upload_frame_route():
        image_file = request.files.get("image")
        body, status = process_uploaded_frame(image_file)
        return jsonify(body), status

    @app.route("/api/get_latest_results")
    def get_latest_results_route():
        body, status = get_latest_results()
        return jsonify(body), status

    @app.route("/health")
    def health_check_route():
        body, status = health_check()
        return jsonify(body), status

    @app.route("/api/reload_model", methods=["POST"])
    @jwt_required
    def reload_model_route():
        body, status = reload_model()
        return jsonify(body), status

    @app.route("/api/start-retrain", methods=["POST"])
    def start_retrain_process_route():
        body, status = start_retrain_process()
        return jsonify(body), status
