from .page_routes import register_page_routes
from .api_routes import register_api_routes


def register_routes(app):
    register_page_routes(app)
    register_api_routes(app)
