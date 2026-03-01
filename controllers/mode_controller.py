CURRENT_ACTIVE_MODE = "face"


def get_active_mode():
    return CURRENT_ACTIVE_MODE


def set_active_mode(data):
    global CURRENT_ACTIVE_MODE
    try:
        new_mode = (data or {}).get("mode")

        if new_mode in ["face", "object"]:
            CURRENT_ACTIVE_MODE = new_mode
            print(f"🔄 Server Mode switched to: {CURRENT_ACTIVE_MODE}")
            return {"status": "success", "mode": CURRENT_ACTIVE_MODE}, 200

        return {"error": "Invalid mode. Use 'face' or 'object'."}, 400
    except Exception as exc:
        return {"error": str(exc)}, 500
