from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from app import db
from app.api.user import bp
from app.models import User, Role, Workflow, WorkflowInstance, WorkflowApproval, Permission
from app.utils.decorators import api_required
from app.services.log_service import log_system_activity
from app.services.workflow_service import get_user_pending_tasks
from datetime import datetime

@bp.route('/profile', methods=['GET'])
@login_required
@api_required
def get_user_profile():
    """获取当前用户的详细资料"""
    user_data = current_user.to_dict()
    
    # 获取用户的角色和权限
    roles = [role.to_dict() for role in current_user.roles]
    permissions = []
    for role in current_user.roles:
        permissions.extend(role.get_permissions())
    
    # 去重
    permissions = list(set(permissions))
    
    # 添加到响应
    user_data['role_data'] = roles
    user_data['permissions'] = permissions
    
    return jsonify({
        'success': True,
        'data': user_data
    })

@bp.route('/profile', methods=['PUT'])
@login_required
@api_required
def update_user_profile():
    """更新当前用户的个人资料"""
    data = request.get_json() or {}
    
    # 可以更新的字段
    allowed_fields = ['fullname', 'email', 'department', 'position']
    
    for field in allowed_fields:
        if field in data:
            # 如果是邮箱，需要检查唯一性
            if field == 'email' and data['email'] != current_user.email:
                if User.query.filter_by(email=data['email']).first():
                    return jsonify({
                        'success': False,
                        'message': '邮箱地址已存在'
                    }), 400
            setattr(current_user, field, data[field])
    
    # 更新密码
    if 'old_password' in data and 'new_password' in data:
        if not current_user.check_password(data['old_password']):
            return jsonify({
                'success': False,
                'message': '原密码错误'
            }), 400
        current_user.set_password(data['new_password'])
    
    db.session.commit()
    
    # 记录日志
    log_system_activity(
        level='INFO',
        module='用户',
        message=f'用户 {current_user.username} 更新了个人资料'
    )
    
    return jsonify({
        'success': True,
        'message': '个人资料更新成功',
        'data': current_user.to_dict()
    })

@bp.route('/tasks', methods=['GET'])
@login_required
@api_required
def get_user_tasks():
    """获取当前用户的待办任务"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    # 获取用户待处理任务
    tasks, total = get_user_pending_tasks(current_user.id, page, per_page)
    
    return jsonify({
        'success': True,
        'data': {
            'items': tasks,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page > 0 else 0
        }
    })

@bp.route('/workflows', methods=['GET'])
@login_required
@api_required
def get_available_workflows():
    """获取当前用户可以使用的工作流"""
    # 管理员可以查看所有激活的工作流
    if current_user.is_admin:
        workflows = Workflow.query.filter_by(is_active=True).all()
    # 普通用户需要有创建实例的权限
    elif current_user.has_permission(Permission.WORKFLOW_INSTANCE_CREATE):
        workflows = Workflow.query.filter_by(is_active=True).all()
    else:
        workflows = []
    
    return jsonify({
        'success': True,
        'data': [workflow.to_dict() for workflow in workflows]
    })

@bp.route('/instances', methods=['GET'])
@login_required
@api_required
def get_user_instances():
    """获取当前用户创建的工作流实例"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = WorkflowInstance.query.filter_by(created_by=current_user.id)
    
    # 状态过滤
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # 工作流过滤
    workflow_id = request.args.get('workflow_id', type=int)
    if workflow_id:
        query = query.filter_by(workflow_id=workflow_id)
    
    # 关键字搜索
    keyword = request.args.get('keyword', '')
    if keyword:
        query = query.filter(WorkflowInstance.title.contains(keyword))
    
    # 排序
    sort_by = request.args.get('sort_by', 'created_at')
    sort_dir = request.args.get('sort_dir', 'desc')
    
    if sort_by in ['id', 'title', 'created_at', 'updated_at']:
        sort_field = getattr(WorkflowInstance, sort_by)
        if sort_dir.lower() == 'desc':
            sort_field = sort_field.desc()
        query = query.order_by(sort_field)
    
    # 分页
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    instances = pagination.items
    
    # 获取工作流名称
    results = []
    for instance in instances:
        workflow = Workflow.query.get(instance.workflow_id)
        
        result = instance.to_dict()
        result['workflow_name'] = workflow.name if workflow else '未知工作流'
        
        results.append(result)
    
    return jsonify({
        'success': True,
        'data': {
            'items': results,
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/instances/<int:id>', methods=['GET'])
@login_required
@api_required
def get_user_instance(id):
    """获取当前用户创建的单个工作流实例"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查是否为创建者
    if instance.created_by != current_user.id and not current_user.is_admin:
        # 检查是否为审批者
        approval = WorkflowApproval.query.filter_by(
            instance_id=instance.id,
            user_id=current_user.id
        ).first()
        
        if not approval:
            return jsonify({
                'success': False,
                'message': '无权访问此工作流实例'
            }), 403
    
    # 获取工作流定义
    workflow = Workflow.query.get(instance.workflow_id)
    
    # 获取审批历史
    approvals = WorkflowApproval.query.filter_by(instance_id=instance.id).all()
    approvals_data = []
    
    for approval in approvals:
        user = User.query.get(approval.user_id)
        
        approval_data = approval.to_dict()
        approval_data['approver_name'] = (user.fullname or user.username) if user else '未知用户'
        
        approvals_data.append(approval_data)
    
    result = {
        'instance': instance.to_dict(),
        'workflow': workflow.to_dict() if workflow else None,
        'approvals': approvals_data
    }
    
    return jsonify({
        'success': True,
        'data': result
    })

@bp.route('/settings', methods=['GET'])
@login_required
@api_required
def get_user_settings():
    """获取当前用户的应用设置"""
    # 这里可以从数据库中加载用户的个性化设置
    # 这是一个简单的示例
    settings = {
        'theme': 'light',
        'notify_email': True,
        'language': 'zh_CN'
    }
    
    return jsonify({
        'success': True,
        'data': settings
    })

@bp.route('/settings', methods=['PUT'])
@login_required
@api_required
def update_user_settings():
    """更新当前用户的应用设置"""
    data = request.get_json() or {}
    
    # 这里可以更新用户的个性化设置到数据库
    # 这是一个简单的示例
    settings = {
        'theme': data.get('theme', 'light'),
        'notify_email': data.get('notify_email', True),
        'language': data.get('language', 'zh_CN')
    }
    
    log_system_activity(
        level='INFO',
        module='用户',
        message=f'用户 {current_user.username} 更新了应用设置'
    )
    
    return jsonify({
        'success': True,
        'message': '设置更新成功',
        'data': settings
    }) 