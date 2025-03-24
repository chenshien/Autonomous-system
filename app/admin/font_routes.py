from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.admin import bp
from app.models import Permission
from app.utils.decorators import admin_required, permission_required
from app.services.font_service import font_manager
import os

@bp.route('/fonts')
@login_required
@admin_required
def fonts():
    """字体管理页面"""
    return render_template('admin/fonts.html')

@bp.route('/fonts/download', methods=['POST'])
@login_required
@admin_required
def download_font():
    """下载单个字体"""
    data = request.get_json()
    if not data or 'font_file' not in data:
        return jsonify({'success': False, 'message': '缺少字体文件名参数'})
    
    font_file = data['font_file']
    
    # 先尝试从系统复制
    success = font_manager.copy_font_from_system(font_file)
    
    # 如果系统复制失败，尝试从网络下载
    if not success:
        # 查找对应的字体信息
        font_info = None
        for category, fonts in font_manager.SYSTEM_FONTS.items():
            for font in fonts:
                if font['file'] == font_file and 'url' in font:
                    font_info = font
                    break
            if font_info:
                break
        
        if font_info and 'url' in font_info:
            success = font_manager.download_font(font_info)
            if success:
                return jsonify({'success': True, 'message': f"字体 {font_info['name']} 下载成功"})
            else:
                return jsonify({'success': False, 'message': f"字体 {font_info['name']} 下载失败"})
        else:
            return jsonify({'success': False, 'message': f"找不到字体 {font_file} 的下载信息"})
    
    return jsonify({'success': success, 'message': '字体复制成功' if success else '字体复制失败'})

@bp.route('/fonts/download-all', methods=['POST'])
@login_required
@admin_required
def download_all_fonts():
    """下载所有缺失的字体"""
    try:
        success_count, total_count, errors = font_manager.download_all_fonts()
        
        if success_count == total_count:
            flash(f'成功下载了所有 {total_count} 个字体文件', 'success')
        elif success_count > 0:
            flash(f'部分下载成功: {success_count}/{total_count} 个字体', 'warning')
        else:
            flash('所有字体下载失败', 'danger')
        
        return jsonify({
            'success': success_count > 0,
            'message': f'成功下载 {success_count}/{total_count} 个字体',
            'success_count': success_count,
            'total_count': total_count,
            'errors': errors
        })
    except Exception as e:
        current_app.logger.error(f"下载所有字体时出错: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@bp.route('/fonts/generate-css', methods=['POST'])
@login_required
@admin_required
def generate_font_css():
    """生成字体CSS文件"""
    try:
        css_path = font_manager.generate_font_css()
        relative_path = os.path.relpath(css_path, current_app.static_folder)
        return jsonify({'success': True, 'path': relative_path})
    except Exception as e:
        current_app.logger.error(f"生成字体CSS时出错: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}) 