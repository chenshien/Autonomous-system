from flask import Blueprint

bp = Blueprint('workflow', __name__)

from app.api.workflow import routes 