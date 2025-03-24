from functools import wraps
from flask import request, jsonify, current_app, flash, redirect, url_for
from flask_login import current_user
from app.utils.security import verify_jwt_token

def api_required(f):
    """验证API请求的装饰器，同时支持session和JWT认证"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # 先检查是否通过Flask-Login会话认证
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        
        # 然后检查是否通过JWT认证
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'message': '缺少认证令牌'
            }), 401
            
        token = auth_header.split('Bearer ')[1]
        payload = verify_jwt_token(token)
        
        if not payload or payload.get('token_type') != 'access':
            return jsonify({
                'success': False,
                'message': '无效的访问令牌'
            }), 401
        
        # 如果需要，可以在这里设置current_user
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """验证用户是否为管理员的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('该操作需要管理员权限', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission):
    """验证用户是否拥有指定权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_permission(permission):
                flash('您没有权限执行此操作', 'danger')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(role_name):
    """验证用户是否具有特定角色的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'success': False,
                    'message': '用户未登录'
                }), 401
                
            if not current_user.has_role(role_name) and not current_user.is_admin:
                return jsonify({
                    'success': False,
                    'message': '需要特定角色权限'
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_key_required(f):
    """验证API密钥的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != current_app.config.get('API_KEY'):
            return jsonify({'error': 'API密钥无效'}), 401
        return f(*args, **kwargs)
    return decorated_function

def jwt_required(f):
    """验证JWT令牌的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': '缺少或格式错误的授权头'}), 401
        
        token = auth_header.split(' ')[1]
        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': '无效的令牌'}), 401
        
        # 将用户ID添加到请求对象中
        request.user_id = payload.get('user_id')
        
        return f(*args, **kwargs)
    return decorated_function 