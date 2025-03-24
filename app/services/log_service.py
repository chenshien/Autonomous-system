from app import db
from app.models import SystemLog, LoginLog, WorkflowLog
from flask import current_app, has_request_context, request
from flask_login import current_user
import logging
import json
from datetime import datetime

def log_system_activity(level, module, message, user_id=None, ip_address=None):
    """
    记录系统日志
    :param level: 日志级别 (INFO, WARNING, ERROR)
    :param module: 模块名称
    :param message: 日志消息
    :param user_id: 用户ID，如果不提供则尝试从current_user获取
    :param ip_address: IP地址，如果不提供则尝试从request获取
    """
    try:
        # 获取用户ID
        if user_id is None and has_request_context() and current_user.is_authenticated:
            user_id = current_user.id
            
        # 获取IP地址
        if ip_address is None and has_request_context():
            ip_address = request.remote_addr
            
        # 创建系统日志
        log = SystemLog(
            level=level,
            module=module,
            message=message,
            user_id=user_id,
            ip_address=ip_address
        )
        
        db.session.add(log)
        db.session.commit()
        
        # 同时使用应用日志记录
        app_logger = current_app.logger
        if level == 'INFO':
            app_logger.info(f"[{module}] {message}")
        elif level == 'WARNING':
            app_logger.warning(f"[{module}] {message}")
        elif level == 'ERROR':
            app_logger.error(f"[{module}] {message}")
            
    except Exception as e:
        # 如果数据库操作失败，确保仍然记录到应用日志
        current_app.logger.error(f"记录系统日志失败: {str(e)}")
        
def log_login_attempt(username, status, ip_address, user_agent, message=None):
    """
    记录登录尝试
    :param username: 用户名
    :param status: 状态 ('success', 'failed')
    :param ip_address: IP地址
    :param user_agent: 用户代理
    :param message: 附加消息
    """
    try:
        user_id = None
        if status == 'success' and current_user.is_authenticated:
            user_id = current_user.id
            
        log = LoginLog(
            user_id=user_id,
            username=username,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log)
        db.session.commit()
        
        # 记录到系统日志
        action = "登录成功" if status == 'success' else "登录失败"
        log_message = f"用户 '{username}' {action}"
        if message:
            log_message += f" - {message}"
            
        level = "INFO" if status == 'success' else "WARNING"
        log_system_activity(level, "认证", log_message, user_id, ip_address)
        
    except Exception as e:
        current_app.logger.error(f"记录登录日志失败: {str(e)}")
        
def log_workflow_activity(instance_id, user_id, action, step_id=None, message=None):
    """
    记录工作流活动
    :param instance_id: 工作流实例ID
    :param user_id: 用户ID
    :param action: 操作类型 (create, submit, approve, reject, cancel)
    :param step_id: 步骤ID
    :param message: 附加消息
    """
    try:
        log = WorkflowLog(
            instance_id=instance_id,
            user_id=user_id,
            action=action,
            step_id=step_id,
            message=message
        )
        
        db.session.add(log)
        db.session.commit()
        
        # 记录到系统日志
        action_map = {
            'create': '创建',
            'submit': '提交',
            'approve': '批准',
            'reject': '拒绝',
            'cancel': '取消'
        }
        
        action_text = action_map.get(action, action)
        step_text = f" 步骤 '{step_id}'" if step_id else ""
        log_message = f"工作流实例 #{instance_id}{step_text} 被{action_text}"
        
        log_system_activity("INFO", "工作流", log_message, user_id)
        
    except Exception as e:
        current_app.logger.error(f"记录工作流日志失败: {str(e)}")
        
class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理日期时间等特殊类型"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj) 