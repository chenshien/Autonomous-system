from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app.auth import bp
from app.models import User, LoginLog, db
from app.auth.forms import LoginForm, RegistrationForm, PasswordResetRequestForm, PasswordResetForm
from app.auth.captcha import generate_captcha, validate_captcha
from app.utils.decorators import api_required
import datetime
import uuid

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # 验证验证码
        if not validate_captcha(session.get('captcha_id'), form.captcha.data):
            flash('验证码错误，请重新输入', 'danger')
            # 生成新的验证码
            captcha_id, captcha_url = generate_captcha()
            session['captcha_id'] = captcha_id
            return render_template('auth/login.html', form=form, captcha_url=captcha_url)
        
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.verify_password(form.password.data):
            flash('用户名或密码错误', 'danger')
            # 生成新的验证码
            captcha_id, captcha_url = generate_captcha()
            session['captcha_id'] = captcha_id
            return render_template('auth/login.html', form=form, captcha_url=captcha_url)
        
        if not user.is_active:
            flash('账号已被禁用，请联系管理员', 'danger')
            # 生成新的验证码
            captcha_id, captcha_url = generate_captcha()
            session['captcha_id'] = captcha_id
            return render_template('auth/login.html', form=form, captcha_url=captcha_url)
        
        login_user(user, remember=form.remember_me.data)
        
        # 记录登录日志
        log = LoginLog(
            user_id=user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(log)
        
        # 更新最后登录时间
        user.last_seen = datetime.datetime.utcnow()
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('main.index')
        return redirect(next_page)
    
    # 生成验证码
    captcha_id, captcha_url = generate_captcha()
    session['captcha_id'] = captcha_id
    
    return render_template('auth/login.html', form=form, captcha_url=captcha_url)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已退出登录', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # 验证验证码
        if not validate_captcha(session.get('captcha_id'), form.captcha.data):
            flash('验证码错误，请重新输入', 'danger')
            # 生成新的验证码
            captcha_id, captcha_url = generate_captcha()
            session['captcha_id'] = captcha_id
            return render_template('auth/register.html', form=form, captcha_url=captcha_url)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data
        )
        user.password = form.password.data
        
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功，请登录', 'success')
        return redirect(url_for('auth.login'))
    
    # 生成验证码
    captcha_id, captcha_url = generate_captcha()
    session['captcha_id'] = captcha_id
    
    return render_template('auth/register.html', form=form, captcha_url=captcha_url)

@bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # 在实际应用中，这里会发送重置密码邮件
            # 此处简化处理，生成重置token并存入session
            reset_token = str(uuid.uuid4())
            session['reset_token'] = {
                'token': reset_token,
                'email': user.email,
                'expires': (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()
            }
            flash('密码重置邮件已发送，请查收邮件', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('该邮箱未注册', 'danger')
    
    return render_template('auth/reset_password_request.html', form=form)

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # 验证token
    reset_info = session.get('reset_token')
    if not reset_info or reset_info['token'] != token:
        flash('无效的重置链接', 'danger')
        return redirect(url_for('auth.login'))
    
    # 检查token是否过期
    if datetime.datetime.fromisoformat(reset_info['expires']) < datetime.datetime.utcnow():
        flash('重置链接已过期', 'danger')
        return redirect(url_for('auth.login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=reset_info['email']).first()
        if user:
            user.password = form.password.data
            db.session.commit()
            session.pop('reset_token', None)
            flash('密码已重置，请使用新密码登录', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('用户不存在', 'danger')
    
    return render_template('auth/reset_password.html', form=form)

@bp.route('/captcha')
def captcha():
    """生成新的验证码"""
    captcha_id, captcha_url = generate_captcha()
    session['captcha_id'] = captcha_id
    return jsonify({'captcha_url': captcha_url})

# API接口
@bp.route('/api/login', methods=['POST'])
@api_required
def api_login():
    data = request.get_json() or {}
    
    if not all(k in data for k in ('username', 'password')):
        return jsonify({
            'success': False,
            'message': '缺少必要的字段'
        }), 400
    
    user = User.query.filter_by(username=data['username']).first()
    if user is None or not user.verify_password(data['password']):
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'message': '账号已被禁用'
        }), 403
    
    # 记录登录日志
    log = LoginLog(
        user_id=user.id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    
    # 更新最后登录时间
    user.last_seen = datetime.datetime.utcnow()
    db.session.commit()
    
    # 使用JWT生成令牌
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': {
            'token': access_token,
            'user': user.to_dict()
        }
    })

@bp.route('/api/logout', methods=['POST'])
@api_required
def api_logout():
    # 实际项目中应该处理JWT令牌的失效
    # 此处简化处理
    return jsonify({
        'success': True,
        'message': '退出成功'
    })

@bp.route('/api/register', methods=['POST'])
@api_required
def api_register():
    data = request.get_json() or {}
    
    required_fields = ['username', 'email', 'password', 'captcha']
    if not all(k in data for k in required_fields):
        return jsonify({
            'success': False,
            'message': '缺少必要的字段'
        }), 400
    
    # 验证验证码
    if not validate_captcha(session.get('captcha_id'), data['captcha']):
        return jsonify({
            'success': False,
            'message': '验证码错误'
        }), 400
    
    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'success': False,
            'message': '用户名已存在'
        }), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'success': False,
            'message': '邮箱已注册'
        }), 400
    
    user = User(
        username=data['username'],
        email=data['email'],
        full_name=data.get('full_name', '')
    )
    user.password = data['password']
    
    try:
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'data': user.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'注册失败: {str(e)}'
        }), 500 