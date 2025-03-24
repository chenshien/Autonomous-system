from flask import Blueprint

bp = Blueprint('file', __name__)

from app.file import routes 