import os
from app import create_app, db
from app.models import User, Role, WorkflowTemplate, WorkflowInstance, WorkflowApproval, WorkflowLog, SystemLog, LoginLog, Permission, Department
from flask_migrate import Migrate

app = create_app()
migrate = Migrate(app, db)

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User, 
        'Role': Role,
        'WorkflowTemplate': WorkflowTemplate,
        'WorkflowInstance': WorkflowInstance,
        'WorkflowApproval': WorkflowApproval,
        'WorkflowLog': WorkflowLog,
        'SystemLog': SystemLog,
        'LoginLog': LoginLog,
        'Permission': Permission,
        'Department': Department
    }

@app.before_first_request
def init_app():
    """初始化应用，创建默认管理员和角色"""
    # 如果数据库中没有用户，创建默认管理员
    if User.query.count() == 0:
        # 创建管理员角色
        admin_role = Role(
            name='管理员',
            description='系统管理员，拥有所有权限'
        )
        
        # 添加所有权限
        permissions = []
        for attr in dir(Permission):
            if not attr.startswith('__') and not callable(getattr(Permission, attr)):
                permissions.append(getattr(Permission, attr))
                
        admin_role.set_permissions(permissions)
        db.session.add(admin_role)
        
        # 创建普通用户角色
        user_role = Role(
            name='普通用户',
            description='普通用户，拥有基本权限'
        )
        
        # 添加基本权限
        basic_permissions = [
            Permission.WORKFLOW_VIEW,
            Permission.WORKFLOW_INSTANCE_CREATE,
            Permission.WORKFLOW_INSTANCE_VIEW,
            Permission.WORKFLOW_APPROVAL
        ]
        
        user_role.set_permissions(basic_permissions)
        db.session.add(user_role)
        
        db.session.commit()
        
        # 创建管理员用户
        admin = User(
            username='admin',
            email='admin@example.com',
            fullname='系统管理员',
            is_active=True,
            is_admin=True
        )
        
        admin.set_password('Admin@123')
        admin.roles.append(admin_role)
        
        db.session.add(admin)
        db.session.commit()
        
        app.logger.info('初始化完成，创建了默认管理员账号和角色')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 