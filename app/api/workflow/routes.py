from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from app import db
from app.api.workflow import bp
from app.models import Workflow, WorkflowInstance, WorkflowApproval, User, Permission
from app.utils.decorators import api_required, permission_required
from app.services.log_service import log_workflow_activity
from app.services.workflow_service import (
    get_workflow_definition, 
    create_workflow_instance, 
    get_workflow_next_step,
    get_user_pending_tasks,
    process_workflow_step,
    get_workflow_history,
    can_user_approve_step
)
import json
from datetime import datetime

# ========== 工作流定义管理 ==========

@bp.route('/definitions', methods=['GET'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_VIEW)
def get_workflows():
    """获取所有工作流定义"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = Workflow.query
    
    # 过滤条件
    if not current_user.is_admin:
        # 非管理员只能看到激活的工作流
        query = query.filter_by(is_active=True)
        
    # 关键字搜索
    keyword = request.args.get('keyword', '')
    if keyword:
        query = query.filter(Workflow.name.contains(keyword) | 
                          Workflow.description.contains(keyword))
    
    # 分页
    pagination = query.order_by(Workflow.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    workflows = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'items': [workflow.to_dict() for workflow in workflows],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/definitions/<int:id>', methods=['GET'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_VIEW)
def get_workflow(id):
    """获取单个工作流定义"""
    workflow = Workflow.query.get_or_404(id)
    
    # 检查权限
    if not current_user.is_admin and not workflow.is_active:
        return jsonify({
            'success': False,
            'message': '无权访问此工作流'
        }), 403
    
    return jsonify({
        'success': True,
        'data': workflow.to_dict()
    })

@bp.route('/definitions', methods=['POST'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_CREATE)
def create_workflow():
    """创建工作流定义"""
    data = request.get_json() or {}
    
    # 验证必填字段
    required_fields = ['name', 'description', 'definition']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {field}'
            }), 400
    
    # 验证工作流名称唯一性
    if Workflow.query.filter_by(name=data['name']).first():
        return jsonify({
            'success': False,
            'message': '工作流名称已存在'
        }), 400
    
    # 验证工作流定义格式
    if not isinstance(data['definition'], dict):
        return jsonify({
            'success': False,
            'message': '工作流定义格式错误'
        }), 400
    
    # 创建工作流
    workflow = Workflow(
        name=data['name'],
        description=data['description'],
        created_by=current_user.id
    )
    workflow.set_definition(data['definition'])
    
    db.session.add(workflow)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'用户 {current_user.username} 创建了工作流 {workflow.name}')
    
    return jsonify({
        'success': True,
        'message': '工作流创建成功',
        'data': workflow.to_dict()
    }), 201

@bp.route('/definitions/<int:id>', methods=['PUT'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_EDIT)
def update_workflow(id):
    """更新工作流定义"""
    workflow = Workflow.query.get_or_404(id)
    data = request.get_json() or {}
    
    # 更新字段
    if 'name' in data and data['name'] != workflow.name:
        # 检查名称唯一性
        if Workflow.query.filter_by(name=data['name']).first():
            return jsonify({
                'success': False,
                'message': '工作流名称已存在'
            }), 400
        workflow.name = data['name']
    
    if 'description' in data:
        workflow.description = data['description']
    
    if 'definition' in data:
        if not isinstance(data['definition'], dict):
            return jsonify({
                'success': False,
                'message': '工作流定义格式错误'
            }), 400
        workflow.set_definition(data['definition'])
        # 更新版本号
        workflow.version += 1
    
    if 'is_active' in data:
        workflow.is_active = data['is_active']
    
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'用户 {current_user.username} 更新了工作流 {workflow.name}')
    
    return jsonify({
        'success': True,
        'message': '工作流更新成功',
        'data': workflow.to_dict()
    })

@bp.route('/definitions/<int:id>', methods=['DELETE'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_DELETE)
def delete_workflow(id):
    """删除工作流定义"""
    workflow = Workflow.query.get_or_404(id)
    
    # 检查是否有依赖该工作流的实例
    instances_count = WorkflowInstance.query.filter_by(workflow_id=workflow.id).count()
    if instances_count > 0:
        return jsonify({
            'success': False,
            'message': f'无法删除此工作流，存在{instances_count}个关联的工作流实例'
        }), 400
    
    name = workflow.name
    db.session.delete(workflow)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'用户 {current_user.username} 删除了工作流 {name}')
    
    return jsonify({
        'success': True,
        'message': '工作流删除成功'
    })

# ========== 工作流实例管理 ==========

@bp.route('/instances', methods=['GET'])
@login_required
@api_required
def get_instances():
    """获取工作流实例列表"""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 10, type=int), 100)
    
    query = WorkflowInstance.query
    
    # 过滤条件
    if not current_user.is_admin and not current_user.has_permission(Permission.WORKFLOW_INSTANCE_VIEW):
        # 普通用户只能看到自己创建的实例
        query = query.filter_by(created_by=current_user.id)
    
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
    
    # 分页
    pagination = query.order_by(WorkflowInstance.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    
    instances = pagination.items
    
    return jsonify({
        'success': True,
        'data': {
            'items': [instance.to_dict() for instance in instances],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
            'per_page': per_page
        }
    })

@bp.route('/instances/<int:id>', methods=['GET'])
@login_required
@api_required
def get_instance(id):
    """获取单个工作流实例"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查权限
    if not current_user.is_admin and not current_user.has_permission(Permission.WORKFLOW_INSTANCE_VIEW) and instance.created_by != current_user.id:
        return jsonify({
            'success': False,
            'message': '无权访问此工作流实例'
        }), 403
    
    # 获取工作流定义
    workflow = Workflow.query.get_or_404(instance.workflow_id)
    
    # 获取审批历史
    approvals = WorkflowApproval.query.filter_by(instance_id=instance.id).all()
    approvals_data = [approval.to_dict() for approval in approvals]
    
    # 添加审批人信息
    for approval_data in approvals_data:
        user = User.query.get(approval_data['user_id'])
        if user:
            approval_data['approver_name'] = user.fullname or user.username
    
    # 获取工作流历史
    history = get_workflow_history(instance.id)
    
    return jsonify({
        'success': True,
        'data': {
            'instance': instance.to_dict(),
            'workflow': workflow.to_dict(),
            'approvals': approvals_data,
            'history': history
        }
    })

@bp.route('/instances', methods=['POST'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_INSTANCE_CREATE)
def create_instance():
    """创建工作流实例"""
    data = request.get_json() or {}
    
    # 验证必填字段
    required_fields = ['workflow_id', 'title', 'data']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {field}'
            }), 400
    
    # 验证工作流存在且激活
    workflow = Workflow.query.get(data['workflow_id'])
    if not workflow:
        return jsonify({
            'success': False,
            'message': '工作流不存在'
        }), 404
    
    if not workflow.is_active:
        return jsonify({
            'success': False,
            'message': '工作流未激活'
        }), 400
    
    # 创建工作流实例
    try:
        instance = create_workflow_instance(
            workflow_id=data['workflow_id'],
            title=data['title'],
            data=data['data'],
            user_id=current_user.id
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'创建工作流实例失败: {str(e)}'
        }), 500
    
    return jsonify({
        'success': True,
        'message': '工作流实例创建成功',
        'data': instance.to_dict()
    }), 201

@bp.route('/instances/<int:id>/submit', methods=['POST'])
@login_required
@api_required
def submit_instance(id):
    """提交工作流实例，开始流程"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查权限
    if not current_user.is_admin and instance.created_by != current_user.id:
        return jsonify({
            'success': False,
            'message': '无权提交此工作流实例'
        }), 403
    
    # 检查实例状态
    if instance.status != 'pending':
        return jsonify({
            'success': False,
            'message': f'工作流实例当前状态为 {instance.status}，无法提交'
        }), 400
    
    # 获取工作流定义
    workflow = Workflow.query.get_or_404(instance.workflow_id)
    definition = workflow.get_definition()
    
    # 获取第一个步骤
    try:
        first_step = get_workflow_next_step(definition, None)
        if not first_step:
            return jsonify({
                'success': False,
                'message': '工作流定义错误，无法找到第一个步骤'
            }), 400
        
        # 更新实例状态
        instance.status = 'running'
        instance.current_step = first_step['id']
        db.session.commit()
        
        # 记录日志
        log_workflow_activity(
            instance_id=instance.id,
            user_id=current_user.id,
            action='submit',
            message='提交工作流实例，开始流程'
        )
        
        # 如果第一个步骤是自动步骤，则自动处理
        if first_step.get('type') == 'auto':
            process_workflow_step(
                instance_id=instance.id,
                step_id=first_step['id'],
                action='auto',
                user_id=current_user.id
            )
        
        return jsonify({
            'success': True,
            'message': '工作流实例提交成功',
            'data': {
                'instance': instance.to_dict(),
                'next_step': first_step
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'提交工作流实例失败: {str(e)}'
        }), 500

@bp.route('/instances/<int:id>/approve', methods=['POST'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_APPROVAL)
def approve_instance(id):
    """审批工作流实例当前步骤"""
    instance = WorkflowInstance.query.get_or_404(id)
    data = request.get_json() or {}
    
    # 检查实例状态
    if instance.status != 'running':
        return jsonify({
            'success': False,
            'message': f'工作流实例当前状态为 {instance.status}，无法审批'
        }), 400
    
    # 检查是否有权限审批当前步骤
    if not can_user_approve_step(instance, current_user.id):
        return jsonify({
            'success': False,
            'message': '无权审批此工作流步骤'
        }), 403
    
    # 获取操作类型和评论
    action = data.get('action', 'approve')
    if action not in ['approve', 'reject']:
        return jsonify({
            'success': False,
            'message': f'无效的操作类型: {action}'
        }), 400
    
    comment = data.get('comment', '')
    
    try:
        # 处理工作流步骤
        result = process_workflow_step(
            instance_id=instance.id,
            step_id=instance.current_step,
            action=action,
            user_id=current_user.id,
            comment=comment
        )
        
        return jsonify({
            'success': True,
            'message': '工作流步骤处理成功',
            'data': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'处理工作流步骤失败: {str(e)}'
        }), 500

@bp.route('/instances/<int:id>/cancel', methods=['POST'])
@login_required
@api_required
def cancel_instance(id):
    """取消工作流实例"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查权限
    if not current_user.is_admin and instance.created_by != current_user.id:
        return jsonify({
            'success': False,
            'message': '无权取消此工作流实例'
        }), 403
    
    # 检查实例状态
    if instance.status not in ['pending', 'running']:
        return jsonify({
            'success': False,
            'message': f'工作流实例当前状态为 {instance.status}，无法取消'
        }), 400
    
    # 更新实例状态
    instance.status = 'cancelled'
    db.session.commit()
    
    # 记录日志
    log_workflow_activity(
        instance_id=instance.id,
        user_id=current_user.id,
        action='cancel',
        message='取消工作流实例'
    )
    
    return jsonify({
        'success': True,
        'message': '工作流实例已取消',
        'data': instance.to_dict()
    })

@bp.route('/instances/<int:id>', methods=['DELETE'])
@login_required
@api_required
@permission_required(Permission.WORKFLOW_INSTANCE_DELETE)
def delete_instance(id):
    """删除工作流实例"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查实例状态，只允许删除已完成、已拒绝或已取消的实例
    if instance.status not in ['completed', 'rejected', 'cancelled']:
        return jsonify({
            'success': False,
            'message': f'无法删除状态为 {instance.status} 的工作流实例'
        }), 400
    
    # 删除相关的审批记录
    WorkflowApproval.query.filter_by(instance_id=instance.id).delete()
    
    # 删除实例
    db.session.delete(instance)
    db.session.commit()
    
    # 记录日志
    current_app.logger.info(f'用户 {current_user.username} 删除了工作流实例 #{instance.instance_id}')
    
    return jsonify({
        'success': True,
        'message': '工作流实例删除成功'
    })

# ========== 用户任务管理 ==========

@bp.route('/tasks', methods=['GET'])
@login_required
@api_required
def get_tasks():
    """获取用户待处理的任务"""
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
            'pages': (total + per_page - 1) // per_page
        }
    }) 