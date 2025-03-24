from flask import jsonify, request, current_app, url_for, render_template, redirect
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import db
from app.api.auth import bp
from app.models import User, Role, LoginLog
from app.utils.decorators import api_required
from app.utils.security import generate_jwt_token, verify_jwt_token
from app.services.log_service import log_login_attempt
from datetime import datetime
import json

@bp.route('/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return jsonify({
            'success': True,
            'message': '用户已登录',
            'user': current_user.to_dict()
        })
    
    data = request.get_json() or {}
    if 'username' not in data or 'password' not in data:
        return jsonify({
            'success': False,
            'message': '用户名和密码不能为空'
        }), 400
        
    user = User.query.filter_by(username=data['username']).first()
    
    if user is None or not user.check_password(data['password']):
        # 记录登录失败日志
        log_login_attempt(data['username'], 'failed', request.remote_addr, request.user_agent.string)
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401
        
    if not user.is_active:
        # 记录登录失败日志
        log_login_attempt(data['username'], 'failed', request.remote_addr, request.user_agent.string, '账户已禁用')
        return jsonify({
            'success': False,
            'message': '账户已禁用，请联系管理员'
        }), 403
    
    # 记录登录成功
    log_login_attempt(user.username, 'success', request.remote_addr, request.user_agent.string)
    
    # 更新最后登录时间
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # 执行登录
    login_user(user, remember=data.get('remember_me', False))
    
    # 生成JWT令牌
    access_token = generate_jwt_token(user.id, 'access')
    refresh_token = generate_jwt_token(user.id, 'refresh')
    
    return jsonify({
        'success': True,
        'message': '登录成功',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    })

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({
        'success': True,
        'message': '已成功登出'
    })

@bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return jsonify({
            'success': False,
            'message': '刷新令牌不能为空'
        }), 400
    
    # 验证刷新令牌
    payload = verify_jwt_token(refresh_token)
    if not payload or payload.get('token_type') != 'refresh':
        return jsonify({
            'success': False,
            'message': '无效的刷新令牌'
        }), 401
    
    user_id = payload.get('user_id')
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        return jsonify({
            'success': False,
            'message': '用户不存在或已禁用'
        }), 401
    
    # 生成新的访问令牌
    access_token = generate_jwt_token(user.id, 'access')
    
    return jsonify({
        'success': True,
        'message': '令牌刷新成功',
        'access_token': access_token
    })

@bp.route('/profile', methods=['GET'])
@login_required
@api_required
def get_profile():
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    })

@bp.route('/profile', methods=['PUT'])
@login_required
@api_required
def update_profile():
    data = request.get_json() or {}
    
    # 可以更新的字段
    allowed_fields = ['fullname', 'email', 'department', 'position']
    
    for field in allowed_fields:
        if field in data:
            setattr(current_user, field, data[field])
    
    # 更新密码如果提供了旧密码和新密码
    if 'old_password' in data and 'new_password' in data:
        if not current_user.check_password(data['old_password']):
            return jsonify({
                'success': False,
                'message': '原密码错误'
            }), 400
        current_user.set_password(data['new_password'])
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '个人资料更新成功',
        'user': current_user.to_dict()
    })

@bp.route('/oauth2/<provider>', methods=['GET'])
def oauth2_authorize(provider):
    """OAuth2认证开始"""
    # 这里应当根据不同的provider实现不同的OAuth2授权逻辑
    # 这是一个示例骨架，实际实现需要针对具体的OAuth2提供商
    return jsonify({
        'success': False,
        'message': f'OAuth2 {provider} 认证未实现'
    }), 501

@bp.route('/oauth2/<provider>/callback', methods=['GET'])
def oauth2_callback(provider):
    """OAuth2认证回调"""
    # 这里应当根据不同的provider实现不同的OAuth2回调逻辑
    return jsonify({
        'success': False,
        'message': f'OAuth2 {provider} 回调未实现'
    }), 501

@bp.route('/qrcode/generate', methods=['GET'])
def generate_qrcode():
    """生成用于扫码登录的二维码"""
    # 这里应当实现生成临时登录码并转为二维码的逻辑
    return jsonify({
        'success': False,
        'message': '扫码登录功能未实现'
    }), 501

@bp.route('/qrcode/verify', methods=['POST'])
def verify_qrcode():
    """验证扫码登录结果"""
    # 这里应当实现验证扫码登录结果的逻辑
    return jsonify({
        'success': False,
        'message': '扫码登录验证功能未实现'
    }), 501 