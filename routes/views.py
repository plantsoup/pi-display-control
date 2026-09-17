"""
HTML Web View Routes.
Renders dashboard UI and fullscreen kiosk viewer templates.
"""

from flask import Blueprint, render_template

views_bp = Blueprint('views', __name__)

@views_bp.route('/')
def index():
    """Render the main control panel dashboard"""
    return render_template('index.html')

@views_bp.route('/viewer')
@views_bp.route('/slideshow')
def viewer():
    """Render the kiosk fullscreen image slideshow / single image viewer"""
    return render_template('viewer.html')
