from flask import Blueprint

paramset_bp = Blueprint(
    'paramset_bp', __name__,
    static_folder="static",
    static_url_path="/paramset/static",
    template_folder="templates"
)

from app.paramset import paramset