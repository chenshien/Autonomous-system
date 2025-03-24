from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.admin import bp
from app.models import User, Role, Permission, Department, WorkflowTemplate
from app.utils.decorators import admin_required
from app import db

@bp.route('/')
@login_required
@admin_required
def index():
    """管理员控制面板首页"""
    user_count = User.query.count()
    role_count = Role.query.count()
    dept_count = Department.query.count()
    workflow_count = WorkflowTemplate.query.count()
    
    stats = {
        'user_count': user_count,
        'role_count': role_count,
        'dept_count': dept_count,
        'workflow_count': workflow_count
    }
    
    return render_template('admin/index.html', stats=stats) 