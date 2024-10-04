from flask import Blueprint

dsn_bp = Blueprint(
    'dsn_bp', __name__,
    static_folder="static",
    static_url_path="/dsn/static",
    template_folder="templates"
)

from app.dsn import dsn