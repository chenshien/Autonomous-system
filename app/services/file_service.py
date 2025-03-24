import os
import hashlib
import uuid
import json
from datetime import datetime
from flask import current_app, request
from werkzeug.utils import secure_filename
from app import db
from app.models import FileAttachment, FileOperation, FileSignature, User, WorkflowInstance, WorkflowStep
import mimetypes
from PIL import Image
import io
import base64
import jwt

# 允许的文件类型和MIME类型
ALLOWED_EXTENSIONS = {
    'pdf': ['application/pdf'],
    'doc': ['application/msword'],
    'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'xls': ['application/vnd.ms-excel'],
    'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    'ppt': ['application/vnd.ms-powerpoint'],
    'pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    'txt': ['text/plain'],
    'md': ['text/markdown', 'text/plain'],
    'ofd': ['application/ofd', 'application/octet-stream']
}

# 文件操作映射到权限
FILE_OPERATION_PERMISSIONS = {
    'view': 'view',  # 查看权限
    'edit': 'edit',  # 编辑权限
    'sign': 'sign',  # 签章权限
    'print': 'print'  # 打印权限
}

def get_file_extension(filename):
    """获取文件扩展名"""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def allowed_file(filename):
    """检查文件是否允许上传"""
    extension = get_file_extension(filename)
    return extension in ALLOWED_EXTENSIONS

def get_file_storage_path(instance_id=None):
    """获取文件存储路径"""
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # 确保目录存在
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # 如果关联了工作流实例，则按实例分目录
    if instance_id:
        instance_folder = os.path.join(upload_folder, f'instance_{instance_id}')
        if not os.path.exists(instance_folder):
            os.makedirs(instance_folder)
        return instance_folder
    
    return upload_folder

def save_uploaded_file(file, instance_id=None, user_id=None):
    """
    保存上传的文件
    
    Args:
        file: 上传的文件对象
        instance_id: 关联的工作流实例ID（可选）
        user_id: 上传用户ID
    
    Returns:
        FileAttachment: 已保存的文件附件记录
    """
    # 获取和清理文件名
    original_filename = secure_filename(file.filename)
    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    
    # 验证文件类型
    content_type = file.content_type or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
    
    # 生成唯一文件名
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else f"{uuid.uuid4().hex}"
    
    # 创建上传目录
    upload_dir = os.path.join(current_app.config.get('BASEDIR', ''), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # 构建文件路径
    file_path = os.path.join('uploads', unique_filename)
    full_path = os.path.join(current_app.config.get('BASEDIR', ''), file_path)
    
    # 保存文件
    file.save(full_path)
    
    # 创建文件记录
    file_attachment = FileAttachment(
        original_filename=original_filename,
        file_path=file_path,
        file_type=file_extension,
        content_type=content_type,
        file_size=os.path.getsize(full_path),
        instance_id=instance_id,
        created_by=user_id
    )
    
    # 添加操作记录
    operation = FileOperation(
        operation_type='upload',
        file=file_attachment,
        user_id=user_id,
        operation_detail=json.dumps({
            'action': 'upload',
            'instance_id': instance_id
        })
    )
    
    db.session.add(file_attachment)
    db.session.add(operation)
    db.session.commit()
    
    return file_attachment

def log_file_operation(file_id, user_id, operation_type, instance_id=None, step_id=None, details=None):
    """
    记录文件操作日志
    :param file_id: 文件ID
    :param user_id: 用户ID
    :param operation_type: 操作类型
    :param instance_id: 工作流实例ID
    :param step_id: 当前步骤ID
    :param details: 操作详情
    :return: 操作日志对象
    """
    operation = FileOperation(
        file_id=file_id,
        user_id=user_id,
        operation_type=operation_type,
        instance_id=instance_id,
        step_id=step_id,
        operation_ip=request.remote_addr,
        operation_details=json.dumps(details) if details else None
    )
    
    db.session.add(operation)
    db.session.commit()
    
    return operation

def get_current_step_id(instance_id):
    """获取工作流实例当前步骤ID"""
    if not instance_id:
        return None
    
    instance = WorkflowInstance.query.get(instance_id)
    if instance:
        return instance.current_step
    
    return None

def check_file_operation_permission(instance_id, user_id, file_id, operation_type):
    """
    检查用户是否有权限对文件执行指定操作
    
    Args:
        instance_id: 工作流实例ID（如果有）
        user_id: 当前用户ID
        file_id: 文件ID
        operation_type: 操作类型（view, edit, sign, print等）
    
    Returns:
        tuple: (has_permission, error_message)
    """
    # 获取用户
    user = User.query.get(user_id)
    if not user:
        return False, '用户不存在'
    
    # 如果是管理员，始终允许所有操作
    if user.is_admin:
        return True, ''
    
    # 获取文件
    file = FileAttachment.query.get(file_id)
    if not file:
        return False, '文件不存在'
    
    if file.is_deleted:
        return False, '文件已被删除'
    
    # 如果没有关联工作流实例，仅允许文件创建者进行操作
    if not instance_id and not file.instance_id:
        if file.created_by == user_id:
            return True, ''
        else:
            return False, '您不是文件的创建者，无权操作'
    
    # 如果有关联工作流实例
    instance_id = instance_id or file.instance_id
    if instance_id:
        # 获取工作流实例
        instance = WorkflowInstance.query.get(instance_id)
        if not instance:
            return False, '工作流实例不存在'
        
        # 如果是实例创建者，始终允许所有操作
        if instance.created_by == user_id:
            return True, ''
        
        # 获取当前步骤
        current_step_id = instance.current_step
        if not current_step_id:
            return False, '工作流实例没有当前步骤'
        
        step = WorkflowStep.query.get(current_step_id)
        if not step:
            return False, '工作流步骤不存在'
        
        # 检查当前用户是否参与此步骤
        from app.services.workflow_service import can_user_approve_step
        if not can_user_approve_step(instance, user_id):
            return False, '您不是当前步骤的处理人，无权操作'
        
        # 检查操作类型是否在此步骤允许的操作中
        allowed_operations = step.file_operations or {}
        if isinstance(allowed_operations, str):
            try:
                allowed_operations = json.loads(allowed_operations)
            except:
                allowed_operations = {}
        
        if operation_type not in allowed_operations.get('allowed_operations', []):
            return False, f'当前步骤不允许{operation_type}操作'
        
        return True, ''
    
    return False, '无法确定文件操作权限'

def get_file_for_operation(file_id, user_id, operation_type, instance_id=None):
    """
    获取文件并检查操作权限
    
    Args:
        file_id: 文件ID
        user_id: 当前用户ID
        operation_type: 操作类型
        instance_id: 工作流实例ID（可选）
    
    Returns:
        FileAttachment: 文件对象
    
    Raises:
        ValueError: 如果用户无权操作或文件不存在
    """
    # 获取文件
    file = FileAttachment.query.get(file_id)
    if not file:
        raise ValueError('文件不存在')
    
    if file.is_deleted:
        raise ValueError('文件已被删除')
    
    # 检查操作权限
    has_permission, error_msg = check_file_operation_permission(
        instance_id=instance_id or file.instance_id,
        user_id=user_id,
        file_id=file_id,
        operation_type=operation_type
    )
    
    if not has_permission:
        raise ValueError(error_msg)
    
    # 添加操作记录
    operation = FileOperation(
        operation_type=operation_type,
        file_id=file_id,
        user_id=user_id,
        operation_detail=json.dumps({
            'action': operation_type,
            'instance_id': instance_id or file.instance_id
        })
    )
    
    db.session.add(operation)
    db.session.commit()
    
    return file

def get_file_viewer_url(file_id, operation='view'):
    """
    获取文件查看器URL
    :param file_id: 文件ID
    :param operation: 操作类型
    :return: 查看器URL
    """
    base_url = f'/file/{operation}/{file_id}'
    
    # 添加防篡改参数
    timestamp = int(datetime.utcnow().timestamp())
    token = generate_file_access_token(file_id, operation, timestamp)
    
    return f'{base_url}?t={timestamp}&token={token}'

def generate_file_access_token(file_id, user_id, expires_in=3600):
    """
    生成文件访问令牌
    
    Args:
        file_id: 文件ID
        user_id: 当前用户ID
        expires_in: 过期时间（秒）
    
    Returns:
        str: 访问令牌
    """
    payload = {
        'file_id': file_id,
        'user_id': user_id,
        'exp': datetime.utcnow() + datetime.timedelta(seconds=expires_in)
    }
    
    token = jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token

def verify_file_access_token(token):
    """
    验证文件访问令牌
    
    Args:
        token: 访问令牌
    
    Returns:
        dict: 包含file_id和user_id的字典
    
    Raises:
        ValueError: 如果令牌无效或已过期
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        
        return {
            'file_id': payload['file_id'],
            'user_id': payload['user_id']
        }
    except jwt.ExpiredSignatureError:
        raise ValueError('令牌已过期')
    except (jwt.InvalidTokenError, KeyError):
        raise ValueError('无效的令牌')

def add_file_signature(file_id, user_id, position_x, position_y, page_num, 
                      instance_id=None, step_id=None, signature_text=None, signature_image=None):
    """
    为文件添加签名
    
    Args:
        file_id: 文件ID
        user_id: 当前用户ID
        position_x: 签名X坐标位置（百分比）
        position_y: 签名Y坐标位置（百分比）
        page_num: 签名页码
        instance_id: 工作流实例ID（可选）
        step_id: 工作流步骤ID（可选）
        signature_text: 签名文本（可选）
        signature_image: Base64编码的签名图片（可选）
    
    Returns:
        FileSignature: 签名记录对象
    
    Raises:
        ValueError: 如果用户无权操作或文件不存在
    """
    # 检查操作权限
    file = get_file_for_operation(
        file_id=file_id,
        user_id=user_id,
        operation_type='sign',
        instance_id=instance_id
    )
    
    # 获取用户
    user = User.query.get(user_id)
    if not user:
        raise ValueError('用户不存在')
    
    # 创建签名记录
    signature = FileSignature(
        file_id=file_id,
        user_id=user_id,
        position_x=position_x,
        position_y=position_y,
        page_num=page_num,
        instance_id=instance_id,
        step_id=step_id,
        signature_text=signature_text or user.full_name or user.username,
        signature_image=signature_image,
        signature_time=datetime.utcnow()
    )
    
    # 添加操作记录
    operation = FileOperation(
        operation_type='sign',
        file_id=file_id,
        user_id=user_id,
        operation_detail=json.dumps({
            'action': 'sign',
            'instance_id': instance_id,
            'step_id': step_id,
            'position': f'x:{position_x}%,y:{position_y}%',
            'page': page_num
        })
    )
    
    db.session.add(signature)
    db.session.add(operation)
    db.session.commit()
    
    return signature

def mark_file_as_deleted(file_id, user_id, instance_id=None):
    """
    标记文件为已删除（逻辑删除）
    
    Args:
        file_id: 文件ID
        user_id: 当前用户ID
        instance_id: 工作流实例ID（可选）
    
    Returns:
        FileAttachment: 文件对象
    
    Raises:
        ValueError: 如果用户无权操作或文件不存在
    """
    # 检查操作权限
    # 对于删除操作，只允许管理员和文件创建者进行
    file = FileAttachment.query.get(file_id)
    if not file:
        raise ValueError('文件不存在')
    
    user = User.query.get(user_id)
    if not user:
        raise ValueError('用户不存在')
    
    # 检查权限 - 只有管理员和文件创建者可以删除
    if not user.is_admin and file.created_by != user_id:
        raise ValueError('您不是文件的创建者或管理员，无权删除')
    
    # 标记为已删除
    file.is_deleted = True
    
    # 添加操作记录
    operation = FileOperation(
        operation_type='delete',
        file_id=file_id,
        user_id=user_id,
        operation_detail=json.dumps({
            'action': 'delete',
            'instance_id': instance_id or file.instance_id
        })
    )
    
    db.session.add(operation)
    db.session.commit()
    
    return file 