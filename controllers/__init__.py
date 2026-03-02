from .mode_controller import get_active_mode, set_active_mode
from .inference_controller import process_uploaded_frame, get_latest_results
from .system_controller import health_check, reload_model, start_retrain_process


def register_routes(app):
    from routes import register_routes as register_all_routes

    register_all_routes(app)

__all__ = [
    "register_routes",
    "get_active_mode",
    "set_active_mode",
    "process_uploaded_frame",
    "get_latest_results",
    "health_check",
    "reload_model",
    "start_retrain_process",
]
