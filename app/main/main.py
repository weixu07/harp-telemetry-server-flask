from flask import render_template
from logging import getLogger
from . import main_bp

logger = getLogger(__file__)


@main_bp.route('/harp/')
def home():
    logger.debug("rendering home page")
    return render_template('main.html')