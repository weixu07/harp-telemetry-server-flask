from flask import Blueprint

udp_bp = Blueprint(
    'udp_bp', __name__,
    static_folder="static",
    static_url_path="/udp/static",
    template_folder="templates"
)

from app.udport import udport