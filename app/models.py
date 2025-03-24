from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager
import json
import uuid

# 定义角色与权限的多对多关系表
roles_permissions = db.Table('roles_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)

# 定义用户与角色的多对多关系表
users_roles = db.Table('users_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

class Permission(db.Model):
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    
    # 权限常量定义
    # 用户管理权限
    USER_VIEW = 'user_view'  # 查看用户
    USER_CREATE = 'user_create'  # 创建用户
    USER_EDIT = 'user_edit'  # 编辑用户
    USER_DELETE = 'user_delete'  # 删除用户
    
    # 角色管理权限
    ROLE_VIEW = 'role_view'  # 查看角色
    ROLE_CREATE = 'role_create'  # 创建角色
    ROLE_EDIT = 'role_edit'  # 编辑角色
    ROLE_DELETE = 'role_delete'  # 删除角色
    
    # 流程模板权限
    WORKFLOW_VIEW = 'workflow_view'  # 查看流程模板
    WORKFLOW_CREATE = 'workflow_create'  # 创建流程模板
    WORKFLOW_EDIT = 'workflow_edit'  # 编辑流程模板
    WORKFLOW_DELETE = 'workflow_delete'  # 删除流程模板
    
    # 流程实例权限
    WORKFLOW_INSTANCE_CREATE = 'workflow_instance_create'  # 创建流程实例
    WORKFLOW_INSTANCE_VIEW = 'workflow_instance_view'  # 查看流程实例
    WORKFLOW_APPROVAL = 'workflow_approval'  # 流程审批权限
    WORKFLOW_INSTANCE_CANCEL = 'workflow_instance_cancel'  # 取消流程实例
    
    # 文件权限
    FILE_UPLOAD = 'file_upload'  # 上传文件
    FILE_DOWNLOAD = 'file_download'  # 下载文件
    FILE_DELETE = 'file_delete'  # 删除文件
    FILE_SIGN = 'file_sign'  # 签署文件
    
    # 系统权限
    SYSTEM_SETTINGS = 'system_settings'  # 系统设置
    SYSTEM_LOGS = 'system_logs'  # 查看系统日志
    SYSTEM_BACKUP = 'system_backup'  # 系统备份
    
    def __repr__(self):
        return f'<Permission {self.name}>'

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(255))
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.relationship('Permission', secondary=roles_permissions,
                                  backref=db.backref('roles', lazy='dynamic'), lazy='dynamic')
    
    def add_permission(self, permission):
        if not self.has_permission(permission):
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        if self.has_permission(permission):
            self.permissions.remove(permission)
    
    def reset_permissions(self):
        self.permissions = []
    
    def has_permission(self, permission):
        return permission in self.permissions
    
    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    full_name = db.Column(db.String(64))
    password_hash = db.Column(db.String(128))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    position = db.Column(db.String(64))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    roles = db.relationship('Role', secondary=users_roles,
                           backref=db.backref('users', lazy='dynamic'), lazy='dynamic')
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_permission(self, permission_name):
        """检查用户是否拥有指定的权限"""
        # 管理员拥有所有权限
        if self.is_admin:
            return True
        
        # 查找所有用户角色中的权限
        for role in self.roles:
            for permission in role.permissions:
                if permission.name == permission_name:
                    return True
        return False
    
    def has_role(self, role_name):
        """检查用户是否拥有指定的角色"""
        if self.is_admin:  # 管理员拥有所有角色
            return True
            
        for role in self.roles:
            if role.name == role_name:
                return True
        return False
    
    def add_role(self, role):
        """添加角色"""
        if not self.has_role(role.name):
            self.roles.append(role)
    
    def remove_role(self, role):
        """移除角色"""
        if self.has_role(role.name):
            self.roles.remove(role)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'department_id': self.department_id,
            'position': self.position,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'roles': [role.name for role in self.roles],
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class WorkflowTemplate(db.Model):
    __tablename__ = 'workflow_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text)  # 使用JSON存储步骤定义
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    creator = db.relationship('User', backref=db.backref('created_workflows', lazy='dynamic'))
    instances = db.relationship('WorkflowInstance', backref='template', lazy='dynamic')
    
    def get_steps(self):
        if self.steps:
            return json.loads(self.steps)
        return []
    
    def set_steps(self, steps_list):
        self.steps = json.dumps(steps_list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': self.get_steps(),
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<WorkflowTemplate {self.name}>'

class WorkflowStep(db.Model):
    __tablename__ = 'workflow_steps'
    
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_templates.id'))
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.Text)
    step_order = db.Column(db.Integer)
    approvers = db.Column(db.Text)  # 使用JSON存储审批人定义（可以是角色或指定用户）
    actions = db.Column(db.Text)  # 使用JSON存储步骤可执行的操作
    file_operations = db.Column(db.Text)  # 使用JSON存储文件操作权限
    
    def get_approvers(self):
        if self.approvers:
            return json.loads(self.approvers)
        return {}
    
    def set_approvers(self, approvers_dict):
        self.approvers = json.dumps(approvers_dict)
    
    def get_actions(self):
        if self.actions:
            return json.loads(self.actions)
        return {}
    
    def set_actions(self, actions_dict):
        self.actions = json.dumps(actions_dict)
    
    def get_file_operations(self):
        if self.file_operations:
            return json.loads(self.file_operations)
        return {}
    
    def set_file_operations(self, operations_dict):
        self.file_operations = json.dumps(operations_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'name': self.name,
            'description': self.description,
            'step_order': self.step_order,
            'approvers': self.get_approvers(),
            'actions': self.get_actions(),
            'file_operations': self.get_file_operations()
        }
    
    def __repr__(self):
        return f'<WorkflowStep {self.name} ({self.step_order})>'

class WorkflowInstance(db.Model):
    __tablename__ = 'workflow_instances'
    
    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow_templates.id'))
    title = db.Column(db.String(128), nullable=False)
    data = db.Column(db.Text)  # 使用JSON存储表单数据
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, rejected, canceled
    current_step = db.Column(db.Integer)  # 当前步骤ID
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    creator = db.relationship('User', backref=db.backref('workflow_submissions', lazy='dynamic'))
    approvals = db.relationship('WorkflowApproval', backref='instance', lazy='dynamic')
    
    def get_data(self):
        if self.data:
            return json.loads(self.data)
        return {}
    
    def set_data(self, data_dict):
        self.data = json.dumps(data_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'title': self.title,
            'data': self.get_data(),
            'status': self.status,
            'current_step': self.current_step,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self):
        return f'<WorkflowInstance {self.id} ({self.status})>'

class WorkflowApproval(db.Model):
    __tablename__ = 'workflow_approvals'
    
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey('workflow_instances.id'))
    step_id = db.Column(db.Integer)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(20))  # approve, reject, comment
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    approver = db.relationship('User', backref=db.backref('approvals', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'step_id': self.step_id,
            'approver_id': self.approver_id,
            'approver_name': self.approver.username if self.approver else None,
            'action': self.action,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<WorkflowApproval {self.id} ({self.action})>'

# 文件附件模型
class FileAttachment(db.Model):
    __tablename__ = 'file_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(50))
    content_type = db.Column(db.String(100))
    file_size = db.Column(db.Integer)
    instance_id = db.Column(db.Integer, db.ForeignKey('workflow_instances.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    
    creator = db.relationship('User', backref=db.backref('uploaded_files', lazy='dynamic'))
    instance = db.relationship('WorkflowInstance', backref=db.backref('attachments', lazy='dynamic'))
    operations = db.relationship('FileOperation', backref='file', lazy='dynamic')
    signatures = db.relationship('FileSignature', backref='file', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'content_type': self.content_type,
            'instance_id': self.instance_id,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted
        }
    
    def __repr__(self):
        return f'<FileAttachment {self.original_filename}>'

# 文件操作记录模型
class FileOperation(db.Model):
    __tablename__ = 'file_operations'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file_attachments.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    operation_type = db.Column(db.String(50))  # upload, view, edit, sign, delete, print
    operation_time = db.Column(db.DateTime, default=datetime.utcnow)
    operation_detail = db.Column(db.Text)  # 使用JSON存储操作详情
    
    user = db.relationship('User', backref=db.backref('file_operations', lazy='dynamic'))
    
    def get_detail(self):
        if self.operation_detail:
            return json.loads(self.operation_detail)
        return {}
    
    def set_detail(self, detail_dict):
        self.operation_detail = json.dumps(detail_dict)
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'user_id': self.user_id,
            'user': self.user.to_dict() if self.user else None,
            'operation_type': self.operation_type,
            'operation_time': self.operation_time.isoformat() if self.operation_time else None,
            'operation_detail': self.get_detail()
        }
    
    def __repr__(self):
        return f'<FileOperation {self.id} ({self.operation_type})>'

# 文件签名记录模型
class FileSignature(db.Model):
    __tablename__ = 'file_signatures'
    
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file_attachments.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    instance_id = db.Column(db.Integer, db.ForeignKey('workflow_instances.id'))
    step_id = db.Column(db.Integer)
    position_x = db.Column(db.Float)  # 签名X位置百分比
    position_y = db.Column(db.Float)  # 签名Y位置百分比
    page_num = db.Column(db.Integer)  # 签名页码
    signature_text = db.Column(db.String(255))  # 签名文字
    signature_image = db.Column(db.Text)  # 签名图片（Base64编码）
    signature_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('signatures', lazy='dynamic'))
    workflow_instance = db.relationship('WorkflowInstance', backref=db.backref('file_signatures', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'file_id': self.file_id,
            'user_id': self.user_id,
            'user': self.user.to_dict() if self.user else None,
            'instance_id': self.instance_id,
            'step_id': self.step_id,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'page_num': self.page_num,
            'signature_text': self.signature_text,
            'signature_time': self.signature_time.isoformat() if self.signature_time else None
        }
    
    def __repr__(self):
        return f'<FileSignature {self.id} by {self.user_id}>'

class WorkflowLog(db.Model):
    __tablename__ = 'workflow_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey('workflow_instances.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(50))  # start, approve, reject, comment, complete, cancel
    step_id = db.Column(db.Integer, nullable=True)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    instance = db.relationship('WorkflowInstance', backref=db.backref('logs', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('workflow_logs', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'instance_id': self.instance_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'step_id': self.step_id,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<WorkflowLog {self.id} ({self.action})>'

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(10))  # INFO, WARNING, ERROR
    module = db.Column(db.String(64))
    message = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', foreign_keys=[user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'module': self.module,
            'message': self.message,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<SystemLog {self.id}>'

class LoginLog(db.Model):
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(64))
    status = db.Column(db.String(16))  # success, failed
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    user = db.relationship('User', foreign_keys=[user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'status': self.status,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat(),
        }
    
    def __repr__(self):
        return f'<LoginLog {self.id}>'

# 部门模型
class Department(db.Model):
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, index=True)
    code = db.Column(db.String(32), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    description = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    parent = db.relationship('Department', remote_side=[id], backref=db.backref('children', lazy='dynamic'))
    users = db.relationship('User', backref='department_obj', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'parent_id': self.parent_id,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Department {self.name}>' 