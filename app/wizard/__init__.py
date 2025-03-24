from flask import Blueprint

wizard_bp = Blueprint('wizard', __name__, url_prefix='/install')

from . import routes 