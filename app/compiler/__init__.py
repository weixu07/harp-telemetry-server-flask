from flask import Blueprint

compiler_bp = Blueprint(
    'compiler_bp', __name__,
    static_folder="static",
    static_url_path="/compiler/static",
    template_folder="templates"
)

from app.compiler import compiler