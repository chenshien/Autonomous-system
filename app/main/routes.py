from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.main import bp
from app.models import WorkflowTemplate, WorkflowInstance, User, Permission
from app.utils.decorators import permission_required
from app.services.workflow_service import get_user_pending_tasks
from datetime import datetime
import json

# 定义星期几的中文名称
weekday_names = ['一', '二', '三', '四', '五', '六', '日']

@bp.route('/')
@login_required
def index():
    """首页"""
    current_date = datetime.now()
    return render_template('index.html', 
                          current_date=current_date, 
                          weekday_names=weekday_names)

@bp.route('/workflows')
@login_required
@permission_required(Permission.WORKFLOW_VIEW)
def workflows():
    """流程管理页面"""
    return render_template('workflows.html')

@bp.route('/workflow/<int:id>')
@login_required
@permission_required(Permission.WORKFLOW_VIEW)
def workflow_detail(id):
    """流程详情页面"""
    workflow = WorkflowTemplate.query.get_or_404(id)
    return render_template('workflow_detail.html', workflow=workflow)

@bp.route('/workflow/designer')
@login_required
@permission_required(Permission.WORKFLOW_EDIT)
def workflow_designer():
    """流程设计器页面"""
    workflow_id = request.args.get('id', None)
    workflow = None
    if workflow_id:
        workflow = WorkflowTemplate.query.get_or_404(workflow_id)
    return render_template('workflow_designer.html', workflow=workflow)

@bp.route('/my-tasks')
@login_required
def my_tasks():
    """我的任务页面"""
    return render_template('my_tasks.html')

@bp.route('/my-submissions')
@login_required
def my_submissions():
    """我的申请页面"""
    return render_template('my_submissions.html')

@bp.route('/new-workflow-instance')
@login_required
@permission_required(Permission.WORKFLOW_INSTANCE_CREATE)
def new_workflow_instance():
    """新建流程实例页面"""
    workflow_id = request.args.get('workflow_id', None)
    workflow = None
    if workflow_id:
        workflow = WorkflowTemplate.query.get_or_404(workflow_id)
    
    available_workflows = WorkflowTemplate.query.filter_by(is_active=True).all()
    return render_template('new_workflow_instance.html', 
                          workflow=workflow,
                          available_workflows=available_workflows)

@bp.route('/workflow-instance/<int:id>')
@login_required
def workflow_instance_detail(id):
    """流程实例详情页面"""
    instance = WorkflowInstance.query.get_or_404(id)
    
    # 检查用户权限
    if not current_user.is_admin and instance.created_by != current_user.id:
        # 检查用户是否是审批人
        is_approver = False
        current_step = instance.get_current_step()
        if current_step:
            role_ids = [int(role_id) for role_id in current_step.get('approver_roles', [])]
            user_role_ids = [role.id for role in current_user.roles]
            if any(role_id in role_ids for role_id in user_role_ids):
                is_approver = True
                
        if not is_approver:
            flash('您没有权限查看此流程实例', 'danger')
            return redirect(url_for('main.index'))
    
    # 获取流程定义
    workflow = WorkflowTemplate.query.get(instance.workflow_id)
    if not workflow:
        flash('此流程实例关联的流程定义不存在', 'danger')
        return redirect(url_for('main.index'))
    
    # 解析流程定义
    workflow_definition = json.loads(workflow.definition)
    
    return render_template('workflow_instance_detail.html', 
                          instance=instance,
                          workflow=workflow,
                          workflow_definition=workflow_definition)

@bp.route('/workflow/create', methods=['GET', 'POST'])
@login_required
@permission_required(Permission.WORKFLOW_CREATE)
def create_workflow():
    # Implementation of the create_workflow route
    pass 