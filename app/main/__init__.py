from flask import Blueprint

main_bp = Blueprint(
    'main_bp', __name__,
    static_folder="static",
    static_url_path="/main/static",
    template_folder="templates"
)

from app.main import main