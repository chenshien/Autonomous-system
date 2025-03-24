from app import create_app, db
from app.models import User, Role, Permission, Department, WorkflowTemplate, WorkflowInstance, WorkflowApproval, WorkflowLog, SystemLog, LoginLog

app = create_app()
with app.app_context():
    print("正在创建数据库表...")
    db.create_all()
    print("数据库表创建完成")

    # 检查是否需要创建默认权限
    if Permission.query.count() == 0:
        # 创建默认权限
        for attr in dir(Permission):
            if not attr.startswith('__') and not callable(getattr(Permission, attr)) and isinstance(getattr(Permission, attr), str):
                perm = Permission(name=getattr(Permission, attr), description=attr)
                db.session.add(perm)
        
        db.session.commit()
        print("默认权限已创建")
    
    # 检查是否需要创建默认角色
    if Role.query.count() == 0:
        # 创建管理员角色
        admin_role = Role(
            name='管理员',
            description='系统管理员，拥有所有权限'
        )
        
        # 添加所有权限
        for perm in Permission.query.all():
            admin_role.add_permission(perm)
        
        db.session.add(admin_role)
        
        # 创建普通用户角色
        user_role = Role(
            name='普通用户',
            description='普通用户，拥有基本权限'
        )
        
        # 添加基本权限
        basic_permissions = [
            'workflow_view',
            'workflow_instance_create',
            'workflow_instance_view',
            'workflow_approval',
            'file_upload',
            'file_download'
        ]
        
        for perm_name in basic_permissions:
            perm = Permission.query.filter_by(name=perm_name).first()
            if perm:
                user_role.add_permission(perm)
        
        db.session.add(user_role)
        db.session.commit()
        print("默认角色已创建")
    
    # 检查是否需要创建默认部门
    if Department.query.count() == 0:
        default_dept = Department(
            name='系统管理部',
            code='admin',
            description='系统管理部门'
        )
        db.session.add(default_dept)
        db.session.commit()
        print("默认部门已创建")
    
    # 检查是否需要创建默认管理员
    if User.query.count() == 0:
        admin_role = Role.query.filter_by(name='管理员').first()
        default_dept = Department.query.filter_by(code='admin').first()
        
        if admin_role and default_dept:
            admin = User(
                username='admin',
                email='admin@example.com',
                full_name='系统管理员',
                is_active=True,
                is_admin=True,
                department_id=default_dept.id,
                position='管理员'
            )
            
            admin.password = 'Admin@123'
            admin.roles.append(admin_role)
            
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账号已创建")

print("数据库初始化完成") 