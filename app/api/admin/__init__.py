from flask import Blueprint

bp = Blueprint('admin', __name__)

from app.api.admin import routes 