import os
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file, abort, current_app, send_from_directory, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.file import bp
from app.models import FileAttachment, FileOperation, FileSignature, WorkflowInstance
from app.services.file_service import (
    save_uploaded_file, 
    get_file_for_operation, 
    add_file_signature, 
    mark_file_as_deleted, 
    check_file_operation_permission,
    verify_file_access_token
)
from app.services.workflow_service import get_current_step_id
from app.utils.decorators import api_required
from app.services.watermark_service import add_viewing_watermark, add_printing_watermark, add_pdf_watermark
import json
import mimetypes
import io

# 文件处理配置
# 删除在线Office查看服务
# OFFICE_ONLINE_VIEWER_URL = 'https://view.officeapps.live.com/op/view.aspx?src='
# 改为本地部署的查看服务
LOCAL_OFFICE_VIEWER_PATH = '/static/vendor/office-viewer/'
ALLOWED_FILE_TYPES = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'ofd']

@bp.route('/upload', methods=['POST'])
@login_required
@api_required
def upload_file():
    """上传文件API接口"""
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'message': '未找到文件'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': '未选择文件'
        }), 400
    
    instance_id = request.form.get('instance_id', None)
    if instance_id:
        instance_id = int(instance_id)
        
        # 检查实例是否存在
        instance = WorkflowInstance.query.get(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'message': '工作流实例不存在'
            }), 404
        
        # 检查是否是实例创建者或管理员
        if not current_user.is_admin and instance.created_by != current_user.id:
            return jsonify({
                'success': False,
                'message': '无权为此工作流实例上传文件'
            }), 403
    
    try:
        # 保存文件
        file_attachment = save_uploaded_file(
            file=file,
            instance_id=instance_id,
            user_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'data': file_attachment.to_dict()
        }), 201
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
    
    except Exception as e:
        current_app.logger.error(f'文件上传失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '文件上传失败，请重试'
        }), 500

@bp.route('/files', methods=['GET'])
@login_required
@api_required
def get_files():
    """获取文件列表API接口"""
    instance_id = request.args.get('instance_id', None)
    
    query = FileAttachment.query.filter(FileAttachment.is_deleted == False)
    
    if instance_id:
        instance_id = int(instance_id)
        
        # 检查实例是否存在
        instance = WorkflowInstance.query.get(instance_id)
        if not instance:
            return jsonify({
                'success': False,
                'message': '工作流实例不存在'
            }), 404
        
        query = query.filter_by(instance_id=instance_id)
        
        # 检查用户是否有权限查看此实例的文件
        if not current_user.is_admin and instance.created_by != current_user.id:
            from app.services.workflow_service import can_user_approve_step
            if not can_user_approve_step(instance, current_user.id):
                return jsonify({
                    'success': False,
                    'message': '无权查看此工作流实例的文件'
                }), 403
    else:
        # 非管理员只能查看自己上传的文件
        if not current_user.is_admin:
            query = query.filter_by(created_by=current_user.id)
    
    files = query.all()
    return jsonify({
        'success': True,
        'data': [file.to_dict() for file in files]
    })

@bp.route('/files/<int:id>', methods=['GET'])
@login_required
@api_required
def get_file(id):
    """获取单个文件信息API接口"""
    file = FileAttachment.query.get_or_404(id)
    
    # 检查文件是否已删除
    if file.is_deleted:
        return jsonify({
            'success': False,
            'message': '文件已删除'
        }), 404
    
    # 检查权限
    instance_id = file.instance_id
    has_permission, error_msg = check_file_operation_permission(
        instance_id=instance_id,
        user_id=current_user.id,
        file_id=id,
        operation_type='view'
    )
    
    if not has_permission:
        return jsonify({
            'success': False,
            'message': error_msg
        }), 403
    
    return jsonify({
        'success': True,
        'data': file.to_dict()
    })

@bp.route('/files/<int:id>/download', methods=['GET'])
@login_required
def download_file(id):
    """下载文件"""
    try:
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='view',
            instance_id=None  # 下载时不指定实例ID，由service自己获取
        )
        
        # 构建文件路径
        file_path = os.path.join(current_app.config.get('BASEDIR', ''), file.file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            flash('文件不存在或已被删除', 'danger')
            return redirect(request.referrer or url_for('main.index'))
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file.original_filename,
            mimetype=file.content_type
        )
    
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(request.referrer or url_for('main.index'))
    
    except Exception as e:
        current_app.logger.error(f'文件下载失败: {str(e)}')
        flash('文件下载失败，请重试', 'danger')
        return redirect(request.referrer or url_for('main.index'))

@bp.route('/files/<int:id>/delete', methods=['DELETE'])
@login_required
@api_required
def delete_file(id):
    """删除文件API接口"""
    try:
        # 标记文件为已删除
        file = mark_file_as_deleted(
            file_id=id,
            user_id=current_user.id,
            instance_id=None  # 删除时不指定实例ID，由service自己获取
        )
        
        return jsonify({
            'success': True,
            'message': '文件删除成功'
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 403
    
    except Exception as e:
        current_app.logger.error(f'文件删除失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '文件删除失败，请重试'
        }), 500

@bp.route('/view/<int:id>', methods=['GET'])
@login_required
def view_file(id):
    """文件预览页面"""
    try:
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='view',
            instance_id=None  # 预览时不指定实例ID，由service自己获取
        )
        
        # 获取文件签名记录
        signatures = FileSignature.query.filter_by(file_id=id).all()
        
        # 获取实例信息（如果有）
        instance = None
        if file.instance_id:
            instance = WorkflowInstance.query.get(file.instance_id)
        
        # 构建文件URL
        file_url = url_for('file.file_content', id=id, _external=True)
        
        # 根据文件类型选择不同的预览方式
        file_type = file.file_type.lower()
        view_mode = request.args.get('mode', 'preview')
        
        # 检查当前用户是否有编辑、签章、打印权限
        can_edit, _ = check_file_operation_permission(file.instance_id, current_user.id, id, 'edit')
        can_sign, _ = check_file_operation_permission(file.instance_id, current_user.id, id, 'sign')
        can_print, _ = check_file_operation_permission(file.instance_id, current_user.id, id, 'print')
        
        # 根据文件类型和请求模式返回不同的模板
        template_map = {
            'pdf': 'file/pdf_viewer.html',
            'doc': 'file/office_viewer.html',
            'docx': 'file/office_viewer.html',
            'xls': 'file/office_viewer.html',
            'xlsx': 'file/office_viewer.html',
            'ppt': 'file/office_viewer.html',
            'pptx': 'file/office_viewer.html',
            'txt': 'file/text_viewer.html',
            'md': 'file/markdown_viewer.html',
            'ofd': 'file/ofd_viewer.html'
        }
        
        template = template_map.get(file_type, 'file/generic_viewer.html')
        
        # 如果是签章模式，使用签章模板
        if view_mode == 'sign' and can_sign:
            template = 'file/signature_viewer.html'
        # 如果是编辑模式，使用编辑模板
        elif view_mode == 'edit' and can_edit:
            if file_type in ['txt', 'md']:
                template = 'file/text_editor.html'
            elif file_type in ['doc', 'docx']:
                template = 'file/office_editor.html'
            elif file_type in ['xls', 'xlsx']:
                template = 'file/office_editor.html'
        
        return render_template(template, 
                              file=file,
                              file_url=file_url,
                              instance=instance,
                              signatures=signatures,
                              can_edit=can_edit,
                              can_sign=can_sign,
                              can_print=can_print,
                              local_office_viewer=LOCAL_OFFICE_VIEWER_PATH)
    
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(request.referrer or url_for('main.index'))
    
    except Exception as e:
        current_app.logger.error(f'文件预览失败: {str(e)}')
        flash('文件预览失败，请重试', 'danger')
        return redirect(request.referrer or url_for('main.index'))

@bp.route('/content/<int:id>', methods=['GET'])
@login_required
def file_content(id):
    """获取文件内容"""
    try:
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='view',
            instance_id=None  # 获取内容时不指定实例ID，由service自己获取
        )
        
        # 构建文件路径
        file_path = os.path.join(current_app.config.get('BASEDIR', ''), file.file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在或已被删除'
            }), 404
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 判断是否需要添加水印
        is_print = request.args.get('print', '0') == '1'
        file_type = file.file_type.lower()
        
        # 添加水印
        if is_print:
            # 检查打印权限
            has_print_permission, _ = check_file_operation_permission(
                file.instance_id, current_user.id, id, 'print'
            )
            
            if not has_print_permission:
                return jsonify({
                    'success': False,
                    'message': '无打印权限'
                }), 403
            
            # 记录打印操作
            from app.services.file_service import log_file_operation
            log_file_operation(id, current_user.id, 'print', file.instance_id)
            
            # 添加打印水印
            if file_type == 'pdf':
                file_data = add_pdf_watermark(file_data, 'print')
            else:
                file_data = add_printing_watermark(file_data, file_type)
        else:
            # 添加查看水印
            if file_type == 'pdf':
                file_data = add_pdf_watermark(file_data, 'view')
            else:
                file_data = add_viewing_watermark(file_data, file_type)
        
        return send_file(
            io.BytesIO(file_data),
            mimetype=file.content_type,
            as_attachment=False
        )
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 403
    
    except Exception as e:
        current_app.logger.error(f'获取文件内容失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '获取文件内容失败，请重试'
        }), 500

@bp.route('/sign/<int:id>', methods=['POST'])
@login_required
@api_required
def sign_file(id):
    """签署文件API接口"""
    try:
        data = request.get_json() or {}
        
        # 验证必填字段
        required_fields = ['position_x', 'position_y', 'page_num']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'message': f'缺少必填字段: {field}'
                }), 400
        
        # 获取实例ID（如果有）
        file = FileAttachment.query.get_or_404(id)
        instance_id = file.instance_id
        
        # 获取当前步骤ID（如果有）
        step_id = None
        if instance_id:
            instance = WorkflowInstance.query.get(instance_id)
            if instance:
                step_id = instance.current_step
        
        # 添加签名
        signature = add_file_signature(
            file_id=id,
            user_id=current_user.id,
            position_x=data['position_x'],
            position_y=data['position_y'],
            page_num=data['page_num'],
            instance_id=instance_id,
            step_id=step_id,
            signature_text=data.get('signature_text'),
            signature_image=data.get('signature_image')
        )
        
        return jsonify({
            'success': True,
            'message': '文件签署成功',
            'data': signature.to_dict()
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 403
    
    except Exception as e:
        current_app.logger.error(f'文件签署失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '文件签署失败，请重试'
        }), 500

@bp.route('/text-content/<int:id>', methods=['GET'])
@login_required
@api_required
def get_text_content(id):
    """获取文本文件内容API接口"""
    try:
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='view',
            instance_id=None
        )
        
        # 检查文件类型
        if file.file_type.lower() not in ['txt', 'md']:
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400
        
        # 构建文件路径
        file_path = os.path.join(current_app.config.get('BASEDIR', ''), file.file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在或已被删除'
            }), 404
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'data': {
                'content': content,
                'file': file.to_dict()
            }
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 403
    
    except Exception as e:
        current_app.logger.error(f'获取文本内容失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '获取文本内容失败，请重试'
        }), 500

@bp.route('/text-content/<int:id>', methods=['PUT'])
@login_required
@api_required
def update_text_content(id):
    """更新文本文件内容API接口"""
    try:
        data = request.get_json() or {}
        
        if 'content' not in data:
            return jsonify({
                'success': False,
                'message': '缺少必填字段: content'
            }), 400
        
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='edit',
            instance_id=None
        )
        
        # 检查文件类型
        if file.file_type.lower() not in ['txt', 'md']:
            return jsonify({
                'success': False,
                'message': '不支持的文件类型'
            }), 400
        
        # 构建文件路径
        file_path = os.path.join(current_app.config.get('BASEDIR', ''), file.file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'message': '文件不存在或已被删除'
            }), 404
        
        # 写入文件内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data['content'])
        
        return jsonify({
            'success': True,
            'message': '文件内容更新成功'
        })
    
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 403
    
    except Exception as e:
        current_app.logger.error(f'更新文本内容失败: {str(e)}')
        return jsonify({
            'success': False,
            'message': '更新文本内容失败，请重试'
        }), 500

@bp.route('/operations/<int:id>', methods=['GET'])
@login_required
@api_required
def get_file_operations(id):
    """获取文件操作记录API接口"""
    # 检查文件是否存在
    file = FileAttachment.query.get_or_404(id)
    
    # 检查权限
    has_permission, error_msg = check_file_operation_permission(
        instance_id=file.instance_id,
        user_id=current_user.id,
        file_id=id,
        operation_type='view'
    )
    
    if not has_permission:
        return jsonify({
            'success': False,
            'message': error_msg
        }), 403
    
    # 获取操作记录
    operations = FileOperation.query.filter_by(file_id=id).order_by(FileOperation.operation_time.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [operation.to_dict() for operation in operations]
    })

@bp.route('/signatures/<int:id>', methods=['GET'])
@login_required
@api_required
def get_file_signatures(id):
    """获取文件签名记录API接口"""
    # 检查文件是否存在
    file = FileAttachment.query.get_or_404(id)
    
    # 检查权限
    has_permission, error_msg = check_file_operation_permission(
        instance_id=file.instance_id,
        user_id=current_user.id,
        file_id=id,
        operation_type='view'
    )
    
    if not has_permission:
        return jsonify({
            'success': False,
            'message': error_msg
        }), 403
    
    # 获取签名记录
    signatures = FileSignature.query.filter_by(file_id=id).order_by(FileSignature.signature_time.desc()).all()
    
    return jsonify({
        'success': True,
        'data': [signature.to_dict() for signature in signatures]
    })

@bp.route('/print/<int:id>', methods=['GET'])
@login_required
def print_file(id):
    """打印文件"""
    try:
        # 获取文件并检查权限
        file = get_file_for_operation(
            file_id=id,
            user_id=current_user.id,
            operation_type='print',
            instance_id=None
        )
        
        # 获取实例信息（如果有）
        instance = None
        if file.instance_id:
            instance = WorkflowInstance.query.get(file.instance_id)
        
        # 构建文件URL，添加打印参数
        file_url = url_for('file.file_content', id=id, print=1, _external=True)
        
        # 根据文件类型选择打印模板
        file_type = file.file_type.lower()
        
        if file_type == 'pdf':
            template = 'file/print_pdf.html'
        elif file_type in ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
            template = 'file/print_office.html'
        else:
            template = 'file/print_generic.html'
        
        return render_template(template,
                               file=file,
                               file_url=file_url,
                               instance=instance)
    
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(request.referrer or url_for('main.index'))
    
    except Exception as e:
        current_app.logger.error(f'文件打印失败: {str(e)}')
        flash('文件打印失败，请重试', 'danger')
        return redirect(request.referrer or url_for('main.index')) 