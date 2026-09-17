"""
Routes registration module.
Registers all Flask blueprints onto the application instance.
"""

from .views import views_bp
from .api_display import api_display_bp
from .api_media import api_media_bp
from .api_schedules import api_schedules_bp

def register_routes(app):
    """Register all modular blueprints on Flask app"""
    app.register_blueprint(views_bp)
    app.register_blueprint(api_display_bp)
    app.register_blueprint(api_media_bp)
    app.register_blueprint(api_schedules_bp)

__all__ = [
    'register_routes',
    'views_bp',
    'api_display_bp',
    'api_media_bp',
    'api_schedules_bp'
]
