from app import db
from app.models import WorkflowTemplate, WorkflowInstance, WorkflowApproval, WorkflowLog, User, Role
from app.services.log_service import log_workflow_activity
from flask import current_app
from datetime import datetime
import json

def get_workflow_definition(workflow_id):
    """
    获取工作流定义
    :param workflow_id: 工作流ID
    :return: 工作流定义JSON
    """
    workflow = WorkflowTemplate.query.get(workflow_id)
    if not workflow:
        raise ValueError(f"工作流ID {workflow_id} 不存在")
    
    return workflow.get_definition()

def create_workflow_instance(workflow_id, title, data, user_id):
    """
    创建一个新的工作流实例
    :param workflow_id: 工作流ID
    :param title: 实例标题
    :param data: 实例数据
    :param user_id: 创建用户ID
    :return: 新创建的工作流实例
    """
    workflow = WorkflowTemplate.query.get(workflow_id)
    if not workflow:
        raise ValueError(f"工作流ID {workflow_id} 不存在")
    
    if not workflow.is_active:
        raise ValueError(f"工作流 '{workflow.name}' 未激活")
    
    # 创建实例
    instance = WorkflowInstance(
        workflow_id=workflow_id,
        title=title,
        created_by=user_id,
        status='pending'
    )
    instance.set_data(data)
    
    db.session.add(instance)
    db.session.commit()
    
    # 记录日志
    log_workflow_activity(
        instance_id=instance.id,
        user_id=user_id,
        action='create',
        message='创建工作流实例'
    )
    
    return instance

def get_workflow_next_step(definition, current_step_id, instance_data=None):
    """
    获取工作流下一步
    :param definition: 工作流定义
    :param current_step_id: 当前步骤ID，如果为None则表示获取第一个步骤
    :param instance_data: 实例数据，用于条件判断
    :return: 下一步的定义，如果没有下一步则返回None
    """
    steps = definition.get('steps', [])
    if not steps:
        return None
    
    # 如果当前步骤为空，则返回第一个步骤
    if current_step_id is None:
        return steps[0]
    
    # 查找当前步骤
    current_step = None
    for step in steps:
        if step['id'] == current_step_id:
            current_step = step
            break
    
    if not current_step:
        raise ValueError(f"步骤ID {current_step_id} 不存在")
    
    # 处理不同类型的流程控制
    transitions = current_step.get('transitions', [])
    
    # 如果没有定义转换，则按顺序获取下一步
    if not transitions:
        current_index = steps.index(current_step)
        if current_index < len(steps) - 1:
            return steps[current_index + 1]
        else:
            return None
    
    # 处理条件转换
    for transition in transitions:
        target_step_id = transition.get('target')
        condition = transition.get('condition')
        
        # 如果没有条件或者条件满足，则返回目标步骤
        if not condition or evaluate_condition(condition, instance_data):
            # 查找目标步骤
            for step in steps:
                if step['id'] == target_step_id:
                    return step
    
    # 如果没有符合条件的转换，则返回None，表示流程结束
    return None

def evaluate_condition(condition, data):
    """
    评估条件表达式
    :param condition: 条件表达式
    :param data: 实例数据
    :return: 条件是否满足
    """
    # 这是一个简单的条件评估实现，实际应用中可能需要更复杂的逻辑
    if not data:
        return False
        
    # 解析条件，条件格式为: "field operator value"
    # 例如: "status == approved" 或 "amount > 1000"
    parts = condition.split()
    if len(parts) != 3:
        return False
        
    field, operator, value = parts
    
    # 获取字段值
    field_value = data.get(field)
    if field_value is None:
        return False
    
    # 转换值类型
    try:
        if value.lower() == 'true':
            compare_value = True
        elif value.lower() == 'false':
            compare_value = False
        elif value.isdigit():
            compare_value = int(value)
            field_value = int(field_value) if isinstance(field_value, str) and field_value.isdigit() else field_value
        elif '.' in value and all(p.isdigit() for p in value.split('.')):
            compare_value = float(value)
            field_value = float(field_value) if isinstance(field_value, str) and all(p.isdigit() for p in field_value.split('.')) else field_value
        else:
            compare_value = value
    except Exception:
        compare_value = value
    
    # 评估操作符
    if operator == '==':
        return field_value == compare_value
    elif operator == '!=':
        return field_value != compare_value
    elif operator == '>':
        return field_value > compare_value
    elif operator == '>=':
        return field_value >= compare_value
    elif operator == '<':
        return field_value < compare_value
    elif operator == '<=':
        return field_value <= compare_value
    elif operator == 'in':
        try:
            compare_list = json.loads(compare_value)
            return field_value in compare_list
        except:
            return False
    elif operator == 'contains':
        return compare_value in field_value
    else:
        return False

def get_user_pending_tasks(user_id, page=1, per_page=10):
    """
    获取用户待处理的任务
    :param user_id: 用户ID
    :param page: 页码
    :param per_page: 每页条数
    :return: (任务列表, 总数)
    """
    user = User.query.get(user_id)
    if not user:
        return [], 0

    # 超级管理员可以看到所有任务
    if user.is_admin:
        query = WorkflowInstance.query.filter_by(status='running')
    else:
        # 获取用户角色
        role_ids = [role.id for role in user.roles]
        
        # 查询所有运行中的工作流实例
        instances = WorkflowInstance.query.filter_by(status='running').all()
        
        # 存储用户可以处理的实例ID
        instance_ids = []
        
        for instance in instances:
            workflow = WorkflowTemplate.query.get(instance.workflow_id)
            if not workflow:
                continue
                
            definition = workflow.get_definition()
            steps = definition.get('steps', [])
            
            # 查找当前步骤
            current_step = None
            for step in steps:
                if step['id'] == instance.current_step:
                    current_step = step
                    break
            
            if not current_step:
                continue
                
            # 检查步骤类型，只处理需要人工审批的步骤
            if current_step.get('type') != 'approval':
                continue
                
            # 检查审批人设置
            approvers = current_step.get('approvers', {})
            
            # 检查用户是否在审批人列表中
            if 'users' in approvers and user_id in approvers['users']:
                instance_ids.append(instance.id)
                continue
                
            # 检查用户角色是否在审批角色列表中
            if 'roles' in approvers and any(role_id in approvers['roles'] for role_id in role_ids):
                instance_ids.append(instance.id)
                continue
                
            # 检查是否为部门主管审批
            if approvers.get('department_manager') and user.position and 'manager' in user.position.lower():
                # 获取创建人
                creator = User.query.get(instance.created_by)
                if creator and creator.department_obj == user.department_obj:
                    instance_ids.append(instance.id)
                    continue
        
        # 如果没有待处理任务，直接返回空列表
        if not instance_ids:
            return [], 0
            
        query = WorkflowInstance.query.filter(WorkflowInstance.id.in_(instance_ids))
    
    # 计算总数
    total = query.count()
    
    # 分页查询
    instances = query.order_by(WorkflowInstance.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # 构建任务列表
    tasks = []
    for instance in instances:
        workflow = WorkflowTemplate.query.get(instance.workflow_id)
        creator = User.query.get(instance.created_by)
        
        task = {
            'instance_id': instance.id,
            'title': instance.title,
            'workflow_name': workflow.name if workflow else '未知工作流',
            'creator_name': (creator.fullname or creator.username) if creator else '未知用户',
            'current_step': instance.current_step,
            'created_at': instance.created_at.isoformat(),
            'updated_at': instance.updated_at.isoformat()
        }
        tasks.append(task)
    
    return tasks, total

def process_workflow_step(instance_id, step_id, action, user_id, comment=None):
    """
    处理工作流步骤
    :param instance_id: 实例ID
    :param step_id: 步骤ID
    :param action: 操作（approve, reject, auto）
    :param user_id: 用户ID
    :param comment: 评论
    :return: 处理结果
    """
    instance = WorkflowInstance.query.get(instance_id)
    if not instance:
        raise ValueError(f"工作流实例ID {instance_id} 不存在")
        
    if instance.status != 'running':
        raise ValueError(f"工作流实例状态为 {instance.status}，无法处理步骤")
        
    if instance.current_step != step_id:
        raise ValueError(f"工作流实例当前步骤为 {instance.current_step}，不是 {step_id}")
    
    # 获取工作流定义
    workflow = WorkflowTemplate.query.get(instance.workflow_id)
    if not workflow:
        raise ValueError(f"工作流ID {instance.workflow_id} 不存在")
        
    definition = workflow.get_definition()
    
    # 获取当前步骤定义
    steps = definition.get('steps', [])
    current_step = None
    for step in steps:
        if step['id'] == step_id:
            current_step = step
            break
    
    if not current_step:
        raise ValueError(f"步骤ID {step_id} 不存在")
    
    # 处理不同类型的步骤
    step_type = current_step.get('type', 'approval')
    
    # 处理自动步骤
    if step_type == 'auto' and action == 'auto':
        # 记录日志
        log_workflow_activity(
            instance_id=instance.id,
            user_id=user_id,
            action='auto',
            step_id=step_id,
            message='自动处理步骤'
        )
        
        # 获取下一步
        next_step = get_workflow_next_step(definition, step_id, instance.get_data())
        
        if next_step:
            # 更新实例状态
            instance.current_step = next_step['id']
            db.session.commit()
            
            # 如果下一步也是自动步骤，则递归处理
            if next_step.get('type') == 'auto':
                return process_workflow_step(
                    instance_id=instance.id,
                    step_id=next_step['id'],
                    action='auto',
                    user_id=user_id
                )
            
            return {
                'instance': instance.to_dict(),
                'next_step': next_step
            }
        else:
            # 流程结束
            instance.status = 'completed'
            instance.current_step = None
            db.session.commit()
            
            # 记录日志
            log_workflow_activity(
                instance_id=instance.id,
                user_id=user_id,
                action='complete',
                message='工作流完成'
            )
            
            return {
                'instance': instance.to_dict(),
                'next_step': None
            }
    
    # 处理审批步骤
    elif step_type == 'approval':
        # 验证用户是否有权限审批
        if not can_user_approve_step(instance, user_id):
            raise ValueError("无权审批此工作流步骤")
        
        # 创建审批记录
        approval = WorkflowApproval(
            instance_id=instance.id,
            step_id=step_id,
            user_id=user_id,
            status=action,
            comment=comment
        )
        
        db.session.add(approval)
        db.session.commit()
        
        # 记录日志
        action_map = {
            'approve': '批准',
            'reject': '拒绝'
        }
        log_workflow_activity(
            instance_id=instance.id,
            user_id=user_id,
            action=action,
            step_id=step_id,
            message=f"{action_map.get(action, action)}步骤 {current_step.get('name', step_id)}"
        )
        
        # 如果拒绝，则结束流程
        if action == 'reject':
            instance.status = 'rejected'
            db.session.commit()
            
            return {
                'instance': instance.to_dict(),
                'next_step': None
            }
        
        # 获取下一步
        next_step = get_workflow_next_step(definition, step_id, instance.get_data())
        
        if next_step:
            # 更新实例状态
            instance.current_step = next_step['id']
            db.session.commit()
            
            # 如果下一步是自动步骤，则自动处理
            if next_step.get('type') == 'auto':
                return process_workflow_step(
                    instance_id=instance.id,
                    step_id=next_step['id'],
                    action='auto',
                    user_id=user_id
                )
            
            return {
                'instance': instance.to_dict(),
                'next_step': next_step
            }
        else:
            # 流程结束
            instance.status = 'completed'
            instance.current_step = None
            db.session.commit()
            
            # 记录日志
            log_workflow_activity(
                instance_id=instance.id,
                user_id=user_id,
                action='complete',
                message='工作流完成'
            )
            
            return {
                'instance': instance.to_dict(),
                'next_step': None
            }
    else:
        raise ValueError(f"不支持的步骤类型: {step_type}")

def can_user_approve_step(instance, user_id):
    """
    检查用户是否有权限审批步骤
    :param instance: 工作流实例
    :param user_id: 用户ID
    :return: 是否有权限
    """
    # 超级管理员始终有权限
    user = User.query.get(user_id)
    if not user:
        return False
        
    if user.is_admin:
        return True
    
    # 获取工作流定义
    workflow = WorkflowTemplate.query.get(instance.workflow_id)
    if not workflow:
        return False
        
    definition = workflow.get_definition()
    
    # 获取当前步骤定义
    steps = definition.get('steps', [])
    current_step = None
    for step in steps:
        if step['id'] == instance.current_step:
            current_step = step
            break
    
    if not current_step:
        return False
    
    # 检查步骤类型，只有审批步骤才需要检查权限
    if current_step.get('type') != 'approval':
        return False
    
    # 检查审批人设置
    approvers = current_step.get('approvers', {})
    
    # 检查用户是否在审批人列表中
    if 'users' in approvers and user_id in approvers['users']:
        return True
    
    # 检查用户角色是否在审批角色列表中
    if 'roles' in approvers:
        role_ids = [role.id for role in user.roles]
        if any(role_id in approvers['roles'] for role_id in role_ids):
            return True
    
    # 检查是否为部门主管审批
    if approvers.get('department_manager') and user.position and 'manager' in user.position.lower():
        # 获取创建人
        creator = User.query.get(instance.created_by)
        if creator and creator.department_obj == user.department_obj:
            return True
    
    return False

def get_workflow_history(instance_id):
    """
    获取工作流历史
    :param instance_id: 实例ID
    :return: 历史记录列表
    """
    logs = WorkflowLog.query.filter_by(instance_id=instance_id).order_by(WorkflowLog.created_at).all()
    
    history = []
    for log in logs:
        user = User.query.get(log.user_id)
        username = (user.fullname or user.username) if user else '系统'
        
        history.append({
            'id': log.id,
            'user_id': log.user_id,
            'username': username,
            'action': log.action,
            'step_id': log.step_id,
            'message': log.message,
            'created_at': log.created_at.isoformat()
        })
    
    return history

def recover_workflows():
    """
    恢复异常终止的工作流
    :return: 恢复的工作流实例数
    """
    try:
        # 查找所有运行中但超时的工作流实例
        timeout = current_app.config.get('WORKFLOW_INSTANCE_TIMEOUT', 24 * 60 * 60)  # 默认24小时
        instances = WorkflowInstance.query.filter_by(status='running').all()
        
        recovered_count = 0
        
        for instance in instances:
            # 尝试恢复工作流
            try:
                # 检查是否有审批记录但未更新状态
                approvals = WorkflowApproval.query.filter_by(instance_id=instance.id, step_id=instance.current_step).all()
                
                if approvals:
                    # 获取最新的审批记录
                    latest_approval = max(approvals, key=lambda a: a.created_at)
                    
                    # 如果已审批但未更新状态，则尝试更新
                    if latest_approval.status in ['approve', 'reject']:
                        process_workflow_step(
                            instance_id=instance.id,
                            step_id=instance.current_step,
                            action=latest_approval.status,
                            user_id=latest_approval.user_id,
                            comment=f"自动恢复: {latest_approval.comment}" if latest_approval.comment else "自动恢复"
                        )
                        recovered_count += 1
            except Exception as e:
                current_app.logger.error(f"恢复工作流实例 #{instance.instance_id} 失败: {str(e)}")
        
        return recovered_count
    
    except Exception as e:
        current_app.logger.error(f"恢复工作流失败: {str(e)}")
        return 0

def get_current_step_id(instance_id):
    """
    获取当前工作流实例的步骤ID
    :param instance_id: 工作流实例ID
    :return: 当前步骤ID或None
    """
    instance = WorkflowInstance.query.get(instance_id)
    if instance and instance.status == 'running':
        return instance.current_step
    return None 