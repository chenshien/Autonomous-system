from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from app import db
from app.api.admin import bp
from app.models import User, Role, Workflow, WorkflowInstance, SystemLog, LoginLog, Permission
from app.utils.decorators import api_required, admin_required
from app.utils.security import generate_password, validate_password_strength
from app.services.workflow_service import recover_workflows
from datetime import datetime, timedelta
import json

# ========== 用户管理 ==========

@bp.route('/users', methods=['GET'])
@login_required
@api_required
@admin_required
def get_users():
    """获取用户列表"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = User.query
    
    # 关键字搜索
    keyword = request.args.get('keyword', '')
    if keyword:
        query = query.filter(
            User.username.contains(keyword) | 
            User.email.contains(keyword) |
            User.fullname.contains(keyword) |
            User.department.contains(keyword)
        )
    
    # 角色过滤
    role_id = request.args.get('role_id', type=int)
    if role_id:
        query = query.join(User.roles).filter(Role.id == role_id)
    
    # 状态过滤
    is_active = request.args.get('is_active')
    if is_active is not None:
        is_active = is_active.lower() == 'true'
        query = query.filter_by(is_active=is_active)
    
    # 排序
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    if sort_by in ['id', 'username', 'email', 'created_at', 'last_login']:
        sort_field = getattr(User, sort_by)
        if sort_dir.lower() == 'desc':
            sort_field = sort_field.desc()
        query = query.order_by(sort_field)
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'items': [user.to_dict() for user in users],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/users/<int:id>', methods=['GET'])
@login_required
@api_required
@admin_required
def get_user(id):
    """获取单个用户"""
    user = User.query.get_or_404(id)
    
    return jsonify({
        'success': True,
        'data': user.to_dict()
    })

@bp.route('/users', methods=['POST'])
@login_required
@api_required
@admin_required
def create_user():
    """创建用户"""
    data = request.get_json() or {}
    
    # 验证必填字段
    required_fields = ['username', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {field}'
            }), 400
    
    # 验证用户名和邮箱唯一性
    if User.query.filter_by(username=data['username']).first():
        return jsonify({
            'success': False,
            'message': '用户名已存在'
        }), 400
        
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'success': False,
            'message': '邮箱地址已存在'
        }), 400
    
    # 验证密码强度
    is_strong, reason = validate_password_strength(data['password'])
    if not is_strong:
        return jsonify({
            'success': False,
            'message': f'密码强度不足: {reason}'
        }), 400
    
    # 创建用户
    user = User(
        username=data['username'],
        email=data['email'],
        fullname=data.get('fullname', ''),
        department=data.get('department', ''),
        position=data.get('position', ''),
        is_active=data.get('is_active', True),
        is_admin=data.get('is_admin', False)
    )
    user.set_password(data['password'])
    
    # 添加角色
    role_ids = data.get('role_ids', [])
    if role_ids:
        for role_id in role_ids:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
    
    db.session.add(user)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 创建了用户 {user.username}')
    
    return jsonify({
        'success': True,
        'message': '用户创建成功',
        'data': user.to_dict()
    }), 201

@bp.route('/users/<int:id>', methods=['PUT'])
@login_required
@api_required
@admin_required
def update_user(id):
    """更新用户"""
    user = User.query.get_or_404(id)
    data = request.get_json() or {}
    
    # 更新用户名，需要检查唯一性
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({
                'success': False,
                'message': '用户名已存在'
            }), 400
        user.username = data['username']
    
    # 更新邮箱，需要检查唯一性
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                'success': False,
                'message': '邮箱地址已存在'
            }), 400
        user.email = data['email']
    
    # 更新密码
    if 'password' in data:
        is_strong, reason = validate_password_strength(data['password'])
        if not is_strong:
            return jsonify({
                'success': False,
                'message': f'密码强度不足: {reason}'
            }), 400
        user.set_password(data['password'])
    
    # 更新其他字段
    if 'fullname' in data:
        user.fullname = data['fullname']
    
    if 'department' in data:
        user.department = data['department']
    
    if 'position' in data:
        user.position = data['position']
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    if 'is_admin' in data:
        # 防止将最后一个管理员降级
        if user.is_admin and not data['is_admin']:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({
                    'success': False,
                    'message': '无法降级最后一个管理员'
                }), 400
        user.is_admin = data['is_admin']
    
    # 更新角色
    if 'role_ids' in data:
        # 清除现有角色
        user.roles = []
        
        # 添加新角色
        for role_id in data['role_ids']:
            role = Role.query.get(role_id)
            if role:
                user.roles.append(role)
    
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 更新了用户 {user.username}')
    
    return jsonify({
        'success': True,
        'message': '用户更新成功',
        'data': user.to_dict()
    })

@bp.route('/users/<int:id>', methods=['DELETE'])
@login_required
@api_required
@admin_required
def delete_user(id):
    """删除用户"""
    user = User.query.get_or_404(id)
    
    # 禁止删除当前用户
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': '无法删除当前登录用户'
        }), 400
    
    # 禁止删除最后一个管理员
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            return jsonify({
                'success': False,
                'message': '无法删除最后一个管理员'
            }), 400
    
    username = user.username
    
    # 删除用户
    db.session.delete(user)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 删除了用户 {username}')
    
    return jsonify({
        'success': True,
        'message': '用户删除成功'
    })

@bp.route('/users/generate-password', methods=['GET'])
@login_required
@api_required
@admin_required
def generate_random_password():
    """生成随机强密码"""
    length = request.args.get('length', 12, type=int)
    if length < 8:
        length = 8
    elif length > 32:
        length = 32
    
    password = generate_password(length)
    
    return jsonify({
        'success': True,
        'data': {
            'password': password
        }
    })

# ========== 角色管理 ==========

@bp.route('/roles', methods=['GET'])
@login_required
@api_required
@admin_required
def get_roles():
    """获取角色列表"""
    roles = Role.query.all()
    
    return jsonify({
        'success': True,
        'data': [role.to_dict() for role in roles]
    })

@bp.route('/roles/<int:id>', methods=['GET'])
@login_required
@api_required
@admin_required
def get_role(id):
    """获取单个角色"""
    role = Role.query.get_or_404(id)
    
    return jsonify({
        'success': True,
        'data': role.to_dict()
    })

@bp.route('/roles', methods=['POST'])
@login_required
@api_required
@admin_required
def create_role():
    """创建角色"""
    data = request.get_json() or {}
    
    # 验证必填字段
    if 'name' not in data:
        return jsonify({
            'success': False,
            'message': '缺少必填字段: name'
        }), 400
    
    # 验证角色名唯一性
    if Role.query.filter_by(name=data['name']).first():
        return jsonify({
            'success': False,
            'message': '角色名已存在'
        }), 400
    
    # 创建角色
    role = Role(
        name=data['name'],
        description=data.get('description', '')
    )
    
    # 添加权限
    if 'permissions' in data and isinstance(data['permissions'], list):
        role.set_permissions(data['permissions'])
    
    db.session.add(role)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 创建了角色 {role.name}')
    
    return jsonify({
        'success': True,
        'message': '角色创建成功',
        'data': role.to_dict()
    }), 201

@bp.route('/roles/<int:id>', methods=['PUT'])
@login_required
@api_required
@admin_required
def update_role(id):
    """更新角色"""
    role = Role.query.get_or_404(id)
    data = request.get_json() or {}
    
    # 更新角色名，需要检查唯一性
    if 'name' in data and data['name'] != role.name:
        if Role.query.filter_by(name=data['name']).first():
            return jsonify({
                'success': False,
                'message': '角色名已存在'
            }), 400
        role.name = data['name']
    
    # 更新描述
    if 'description' in data:
        role.description = data['description']
    
    # 更新权限
    if 'permissions' in data and isinstance(data['permissions'], list):
        role.set_permissions(data['permissions'])
    
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 更新了角色 {role.name}')
    
    return jsonify({
        'success': True,
        'message': '角色更新成功',
        'data': role.to_dict()
    })

@bp.route('/roles/<int:id>', methods=['DELETE'])
@login_required
@api_required
@admin_required
def delete_role(id):
    """删除角色"""
    role = Role.query.get_or_404(id)
    
    # 检查是否有用户使用此角色
    if role.users.count() > 0:
        return jsonify({
            'success': False,
            'message': f'无法删除角色，有{role.users.count()}个用户使用此角色'
        }), 400
    
    name = role.name
    db.session.delete(role)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'管理员 {current_user.username} 删除了角色 {name}')
    
    return jsonify({
        'success': True,
        'message': '角色删除成功'
    })

@bp.route('/permissions', methods=['GET'])
@login_required
@api_required
@admin_required
def get_permissions():
    """获取权限列表"""
    # 从Permission类中获取所有权限
    permissions = []
    for attr in dir(Permission):
        if not attr.startswith('__') and not callable(getattr(Permission, attr)):
            value = getattr(Permission, attr)
            
            # 解析权限分类
            if ':' in value:
                category, action = value.split(':')
            else:
                category = 'other'
                action = value
            
            permissions.append({
                'id': value,
                'category': category,
                'action': action
            })
    
    # 按分类分组
    categories = {}
    for perm in permissions:
        category = perm['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(perm)
    
    return jsonify({
        'success': True,
        'data': {
            'permissions': permissions,
            'categories': categories
        }
    })

# ========== 系统管理 ==========

@bp.route('/system/logs', methods=['GET'])
@login_required
@api_required
@admin_required
def get_system_logs():
    """获取系统日志"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = SystemLog.query
    
    # 日志级别过滤
    level = request.args.get('level')
    if level:
        query = query.filter_by(level=level)
    
    # 模块过滤
    module = request.args.get('module')
    if module:
        query = query.filter_by(module=module)
    
    # 用户过滤
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    # 时间范围过滤
    start_time = request.args.get('start_time')
    if start_time:
        try:
            start_datetime = datetime.fromisoformat(start_time)
            query = query.filter(SystemLog.created_at >= start_datetime)
        except ValueError:
            pass
    
    end_time = request.args.get('end_time')
    if end_time:
        try:
            end_datetime = datetime.fromisoformat(end_time)
            query = query.filter(SystemLog.created_at <= end_datetime)
        except ValueError:
            pass
    
    # 关键字搜索
    keyword = request.args.get('keyword', '')
    if keyword:
        query = query.filter(SystemLog.message.contains(keyword))
    
    # 分页
    pagination = query.order_by(SystemLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    logs = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'items': [log.to_dict() for log in logs],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/system/login-logs', methods=['GET'])
@login_required
@api_required
@admin_required
def get_login_logs():
    """获取登录日志"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = LoginLog.query
    
    # 用户过滤
    username = request.args.get('username')
    if username:
        query = query.filter_by(username=username)
    
    # 状态过滤
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # IP过滤
    ip_address = request.args.get('ip_address')
    if ip_address:
        query = query.filter_by(ip_address=ip_address)
    
    # 时间范围过滤
    start_time = request.args.get('start_time')
    if start_time:
        try:
            start_datetime = datetime.fromisoformat(start_time)
            query = query.filter(LoginLog.created_at >= start_datetime)
        except ValueError:
            pass
    
    end_time = request.args.get('end_time')
    if end_time:
        try:
            end_datetime = datetime.fromisoformat(end_time)
            query = query.filter(LoginLog.created_at <= end_datetime)
        except ValueError:
            pass
    
    # 分页
    pagination = query.order_by(LoginLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    logs = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'items': [log.to_dict() for log in logs],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/system/summary', methods=['GET'])
@login_required
@api_required
@admin_required
def get_system_summary():
    """获取系统概览数据"""
    # 用户统计
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    
    # 工作流统计
    total_workflows = Workflow.query.count()
    active_workflows = Workflow.query.filter_by(is_active=True).count()
    
    # 实例统计
    total_instances = WorkflowInstance.query.count()
    running_instances = WorkflowInstance.query.filter_by(status='running').count()
    completed_instances = WorkflowInstance.query.filter_by(status='completed').count()
    rejected_instances = WorkflowInstance.query.filter_by(status='rejected').count()
    
    # 最近登录统计
    last_24h = datetime.utcnow() - timedelta(hours=24)
    logins_24h = LoginLog.query.filter(LoginLog.created_at >= last_24h).count()
    
    # 最近活跃用户
    active_user_ids = db.session.query(LoginLog.user_id, db.func.max(LoginLog.created_at).label('last_login'))\
        .filter(LoginLog.user_id != None)\
        .filter(LoginLog.status == 'success')\
        .group_by(LoginLog.user_id)\
        .order_by(db.desc('last_login'))\
        .limit(5)\
        .all()
    
    active_users_data = []
    for user_id, last_login in active_user_ids:
        user = User.query.get(user_id)
        if user:
            active_users_data.append({
                'id': user.id,
                'username': user.username,
                'fullname': user.fullname,
                'last_login': last_login.isoformat()
            })
    
    # 最近工作流实例
    recent_instances = WorkflowInstance.query.order_by(WorkflowInstance.created_at.desc()).limit(5).all()
    recent_instances_data = []
    
    for instance in recent_instances:
        workflow = Workflow.query.get(instance.workflow_id)
        creator = User.query.get(instance.created_by)
        
        recent_instances_data.append({
            'id': instance.id,
            'title': instance.title,
            'workflow_name': workflow.name if workflow else '未知工作流',
            'creator_name': (creator.fullname or creator.username) if creator else '未知用户',
            'status': instance.status,
            'created_at': instance.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'data': {
            'users': {
                'total': total_users,
                'active': active_users
            },
            'workflows': {
                'total': total_workflows,
                'active': active_workflows
            },
            'instances': {
                'total': total_instances,
                'running': running_instances,
                'completed': completed_instances,
                'rejected': rejected_instances
            },
            'logins_24h': logins_24h,
            'active_users': active_users_data,
            'recent_instances': recent_instances_data
        }
    })

@bp.route('/system/recover-workflows', methods=['POST'])
@login_required
@api_required
@admin_required
def recover_workflows_endpoint():
    """手动触发恢复异常工作流"""
    try:
        recovered_count = recover_workflows()
        
        return jsonify({
            'success': True,
            'message': f'成功恢复 {recovered_count} 个工作流实例',
            'data': {
                'recovered_count': recovered_count
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'恢复工作流失败: {str(e)}'
        }), 500 