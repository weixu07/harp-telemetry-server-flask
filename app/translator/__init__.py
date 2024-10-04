from flask import Blueprint

translator_bp = Blueprint(
    'translator_bp', __name__,
    static_folder="static",
    static_url_path="/translator/static",
    template_folder="templates"
)

from app.translator import translator