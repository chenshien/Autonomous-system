import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config
from datetime import datetime

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
moment = Moment()
mail = Mail()
bootstrap = Bootstrap()
cors = CORS()

# 导入字体管理器
from .services.font_service import font_manager

def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)
    
    # 加载配置
    if not config_name:
        config_name = os.getenv('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 使用ProxyFix处理反向代理
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    moment.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    cors.init_app(app)
    
    # 配置登录
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问该页面'
    login_manager.login_message_category = 'info'
    
    # 初始化字体管理器
    font_manager.init_app(app)
    
    # 确保第一次启动时尝试加载必要的字体
    with app.app_context():
        try:
            # 尝试复制或下载必要的字体
            missing_fonts = font_manager.check_required_fonts()
            if missing_fonts:
                app.logger.warning(f"系统缺少以下字体资源: {', '.join(missing_fonts)}")
            else:
                app.logger.info("所有必要的字体资源已就绪")
            
            # 生成字体CSS
            css_path = font_manager.generate_font_css()
            app.logger.info(f"生成字体CSS文件: {css_path}")
        except Exception as e:
            app.logger.error(f"初始化字体资源时出错: {str(e)}")
    
    # 注册蓝图
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.file import bp as file_bp
    app.register_blueprint(file_bp)
    
    # 注册初始化向导蓝图
    from app.wizard import wizard_bp
    app.register_blueprint(wizard_bp)
    
    # 注册管理员蓝图
    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # 设置日志
    if not app.debug and not app.testing:
        # 确保日志目录存在
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # 设置日志文件
        file_handler = RotatingFileHandler(
            'logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('应用启动')
    
    # 注册上下文处理器，向模板注入变量
    @app.context_processor
    def inject_global_vars():
        """注入全局变量到模板"""
        from app.models import Permission
        return {
            'Permission': Permission,
            'current_year': datetime.now().year,
            'now': datetime.now(),
            'version': '1.0.0'
        }
    
    # 错误处理页面
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    return app

from app.models import User

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id)) 