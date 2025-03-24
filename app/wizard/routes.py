import os
import json
import logging
from flask import render_template, request, redirect, url_for, current_app, jsonify, session, flash
from . import wizard_bp
from ..services.font_service import font_manager
from ..models import db, User, Role, Department
from werkzeug.security import generate_password_hash
import sqlalchemy
import shutil
import platform
import psutil
import sys

# 日志配置
logger = logging.getLogger(__name__)

# 初始化步骤常量
STEP_WELCOME = 'welcome'        # 欢迎页
STEP_SYSTEM_CHECK = 'system_check'  # 系统检查
STEP_DATABASE = 'database'      # 数据库配置
STEP_ADMIN = 'admin'            # 管理员账户
STEP_FONTS = 'fonts'            # 字体配置
STEP_COMPLETE = 'complete'      # 安装完成

# 初始化状态检查
def installation_required():
    """检查是否需要初始化安装"""
    # 检查数据库连接是否正常
    try:
        # 检查是否存在管理员用户
        admin_exists = User.query.filter_by(role_id=Role.ROLE_ADMIN).first() is not None
        if admin_exists:
            return False
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.ProgrammingError):
        # 数据库连接错误或表不存在，需要初始化
        return True
    except Exception as e:
        # 其他错误，需要初始化
        logger.exception(f"检查初始化状态时发生错误: {str(e)}")
        return True
    
    # 检查配置文件是否完整
    config_path = os.path.join(current_app.instance_path, 'config.json')
    if not os.path.exists(config_path):
        return True
    
    return False


@wizard_bp.before_request
def check_installation():
    """检查是否需要初始化，如果已初始化则重定向"""
    # 忽略静态资源和安装完成页面
    if request.endpoint and (
        request.endpoint.startswith('static') or 
        request.endpoint == 'wizard.installation_complete'
    ):
        return
    
    # 如果不需要初始化且不是查看已完成页面，则重定向到首页
    if not installation_required() and request.endpoint != 'wizard.installation_complete':
        return redirect(url_for('main.index'))


@wizard_bp.route('/')
def index():
    """初始化向导首页"""
    return redirect(url_for('wizard.step', step=STEP_WELCOME))


@wizard_bp.route('/step/<step>', methods=['GET', 'POST'])
def step(step):
    """处理初始化向导的各个步骤"""
    # 如果安装已完成，重定向到完成页面
    if not installation_required() and step != STEP_COMPLETE:
        return redirect(url_for('wizard.installation_complete'))
    
    # 根据步骤分发到不同的处理函数
    if step == STEP_WELCOME:
        return handle_welcome()
    elif step == STEP_SYSTEM_CHECK:
        return handle_system_check()
    elif step == STEP_DATABASE:
        return handle_database()
    elif step == STEP_ADMIN:
        return handle_admin()
    elif step == STEP_FONTS:
        return handle_fonts()
    elif step == STEP_COMPLETE:
        return handle_complete()
    else:
        # 未知步骤，重定向到首页
        return redirect(url_for('wizard.index'))


def handle_welcome():
    """处理欢迎页面"""
    return render_template('wizard/welcome.html',
                           next_step=STEP_SYSTEM_CHECK)


def handle_system_check():
    """处理系统检查页面"""
    # 收集系统信息
    system_info = {
        'os': platform.system() + ' ' + platform.release(),
        'python': platform.python_version(),
        'cpu': platform.processor(),
        'memory': f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
        'disk': f"{round(psutil.disk_usage('/').total / (1024**3), 2)} GB",
        'free_disk': f"{round(psutil.disk_usage('/').free / (1024**3), 2)} GB"
    }
    
    # 检查必须的库和依赖
    dependencies = {
        'flask': {'required': True, 'status': 'ok', 'version': ''},
        'sqlalchemy': {'required': True, 'status': 'ok', 'version': ''},
        'pdfkit': {'required': True, 'status': 'ok', 'version': ''},
        'reportlab': {'required': True, 'status': 'ok', 'version': ''},
    }
    
    # 检查各依赖库
    import importlib
    for lib in dependencies:
        try:
            module = importlib.import_module(lib)
            if hasattr(module, '__version__'):
                dependencies[lib]['version'] = getattr(module, '__version__')
            elif hasattr(module, 'VERSION'):
                dependencies[lib]['version'] = getattr(module, 'VERSION')
            else:
                dependencies[lib]['version'] = '未知'
        except ImportError:
            dependencies[lib]['status'] = 'missing'
    
    # 检查必要目录是否可写
    directories = {
        '配置目录': {'path': current_app.instance_path, 'writable': os.access(current_app.instance_path, os.W_OK)},
        '上传目录': {'path': os.path.join(current_app.static_folder, 'uploads'), 'writable': False},
        '日志目录': {'path': os.path.join(current_app.root_path, 'logs'), 'writable': False},
        '字体目录': {'path': os.path.join(current_app.static_folder, 'fonts'), 'writable': False},
    }
    
    # 创建并检查目录权限
    for name, info in directories.items():
        if not os.path.exists(info['path']):
            try:
                os.makedirs(info['path'])
                info['writable'] = True
            except:
                info['writable'] = False
        else:
            info['writable'] = os.access(info['path'], os.W_OK)
    
    if request.method == 'POST':
        # 保存系统检查结果到会话
        session['system_check'] = {
            'system_info': system_info,
            'dependencies': dependencies,
            'directories': directories
        }
        return redirect(url_for('wizard.step', step=STEP_DATABASE))
    
    return render_template('wizard/system_check.html',
                           system_info=system_info,
                           dependencies=dependencies,
                           directories=directories,
                           next_step=STEP_DATABASE)


def handle_database():
    """处理数据库配置页面"""
    # 默认配置
    default_config = {
        'SQLALCHEMY_DATABASE_URI': os.environ.get('DATABASE_URL', 'sqlite:///app.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    
    if request.method == 'POST':
        # 获取提交的数据库配置
        db_type = request.form.get('db_type', 'sqlite')
        db_host = request.form.get('db_host', '')
        db_port = request.form.get('db_port', '')
        db_name = request.form.get('db_name', 'app.db')
        db_user = request.form.get('db_user', '')
        db_password = request.form.get('db_password', '')
        
        # 构建数据库URI
        if db_type == 'sqlite':
            db_uri = f'sqlite:///{db_name}'
        elif db_type == 'mysql':
            db_uri = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        elif db_type == 'postgresql':
            db_uri = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        else:
            # 不支持的数据库类型
            flash('不支持的数据库类型', 'error')
            return render_template('wizard/database.html', 
                                  config=default_config,
                                  next_step=STEP_ADMIN)
        
        # 测试数据库连接
        try:
            test_config = current_app.config.copy()
            test_config['SQLALCHEMY_DATABASE_URI'] = db_uri
            
            # 临时使用测试配置创建引擎
            from flask_sqlalchemy import SQLAlchemy
            test_db = SQLAlchemy()
            test_app = current_app._get_current_object()
            prev_uri = test_app.config.get('SQLALCHEMY_DATABASE_URI')
            test_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
            
            with test_app.app_context():
                # 测试连接
                test_db.init_app(test_app)
                conn = test_db.engine.connect()
                conn.close()
            
            # 恢复原始配置
            test_app.config['SQLALCHEMY_DATABASE_URI'] = prev_uri
            
            # 连接成功，保存配置
            config = {
                'SQLALCHEMY_DATABASE_URI': db_uri,
                'SQLALCHEMY_TRACK_MODIFICATIONS': False
            }
            
            # 保存配置到配置文件
            config_dir = current_app.instance_path
            os.makedirs(config_dir, exist_ok=True)
            
            config_path = os.path.join(config_dir, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            # 保存到会话
            session['database_config'] = config
            
            # 尝试初始化数据库
            try:
                current_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
                with current_app.app_context():
                    db.create_all()
                flash('数据库配置成功并初始化', 'success')
                return redirect(url_for('wizard.step', step=STEP_ADMIN))
            except Exception as e:
                flash(f'数据库初始化失败: {str(e)}', 'error')
                logger.exception(f"数据库初始化错误: {str(e)}")
        
        except Exception as e:
            flash(f'数据库连接测试失败: {str(e)}', 'error')
            logger.exception(f"数据库连接测试错误: {str(e)}")
    
    return render_template('wizard/database.html', 
                           config=default_config,
                           next_step=STEP_ADMIN)


def handle_admin():
    """处理管理员账户设置页面"""
    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        email = request.form.get('email')
        real_name = request.form.get('real_name')
        
        # 验证数据
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('wizard/admin.html', next_step=STEP_FONTS)
        
        if password != password_confirm:
            flash('两次输入的密码不一致', 'error')
            return render_template('wizard/admin.html', next_step=STEP_FONTS)
        
        try:
            # 创建管理员角色（如果不存在）
            admin_role = Role.query.filter_by(id=Role.ROLE_ADMIN).first()
            if not admin_role:
                admin_role = Role(id=Role.ROLE_ADMIN, name='管理员')
                db.session.add(admin_role)
            
            # 创建默认部门（如果不存在）
            default_dept = Department.query.filter_by(name='系统管理部').first()
            if not default_dept:
                default_dept = Department(name='系统管理部', code='admin')
                db.session.add(default_dept)
            
            # 提交这些更改，确保有ID
            db.session.commit()
            
            # 创建管理员用户
            admin_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                real_name=real_name,
                role_id=Role.ROLE_ADMIN,
                department_id=default_dept.id
            )
            db.session.add(admin_user)
            db.session.commit()
            
            # 保存管理员信息到会话
            session['admin_created'] = True
            flash('管理员账户创建成功', 'success')
            return redirect(url_for('wizard.step', step=STEP_FONTS))
            
        except Exception as e:
            flash(f'创建管理员账户失败: {str(e)}', 'error')
            logger.exception(f"创建管理员账户错误: {str(e)}")
    
    return render_template('wizard/admin.html', next_step=STEP_FONTS)


def handle_fonts():
    """处理字体配置页面"""
    # 检查系统字体并尝试复制必需字体
    missing_fonts = font_manager.check_required_fonts()
    
    # 获取所有可用字体
    available_fonts = font_manager.get_available_fonts()
    
    if request.method == 'POST':
        # 生成字体CSS
        try:
            css_path = font_manager.generate_font_css()
            session['fonts_configured'] = True
            flash('字体配置成功', 'success')
            return redirect(url_for('wizard.step', step=STEP_COMPLETE))
        except Exception as e:
            flash(f'字体配置失败: {str(e)}', 'error')
            logger.exception(f"字体配置错误: {str(e)}")
    
    return render_template('wizard/fonts.html', 
                          missing_fonts=missing_fonts,
                          available_fonts=available_fonts,
                          required_fonts=font_manager.REQUIRED_FONTS,
                          next_step=STEP_COMPLETE)


def handle_complete():
    """处理安装完成页面"""
    # 确认所有步骤已完成
    all_steps_completed = (
        session.get('system_check') and
        session.get('database_config') and
        session.get('admin_created') and
        session.get('fonts_configured')
    )
    
    # 标记安装完成
    if all_steps_completed:
        # 创建安装完成标记文件
        with open(os.path.join(current_app.instance_path, 'installation_completed'), 'w') as f:
            from datetime import datetime
            f.write(f"Installation completed at: {datetime.now().isoformat()}")
        
        # 清除安装会话数据
        for key in ['system_check', 'database_config', 'admin_created', 'fonts_configured']:
            if key in session:
                session.pop(key)
    
    return render_template('wizard/complete.html')


@wizard_bp.route('/installation-complete')
def installation_complete():
    """显示安装已完成页面"""
    return render_template('wizard/already_installed.html')


@wizard_bp.route('/ajax/test-font', methods=['POST'])
def test_font():
    """测试字体是否可用的Ajax接口"""
    font_file = request.json.get('font_file')
    if not font_file:
        return jsonify({'success': False, 'message': '未指定字体文件'})
    
    # 从系统复制字体
    success = font_manager.copy_font_from_system(font_file)
    
    return jsonify({
        'success': success,
        'message': '字体复制成功' if success else '字体复制失败'
    }) 