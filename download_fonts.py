#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
字体资源下载脚本

此脚本用于下载系统所需的开源字体资源，并生成字体CSS文件
"""

import os
import sys
import logging
import time
import argparse
from flask import Flask

print("字体下载脚本启动...")

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 确保日志输出到控制台
    ]
)
logger = logging.getLogger('字体下载')

def create_app():
    """创建一个临时Flask应用实例"""
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='temp_key_for_font_download',
        STATIC_FOLDER='app/static'
    )
    return app

def main():
    print("初始化字体下载工具...")
    parser = argparse.ArgumentParser(description='下载系统所需的开源字体资源')
    parser.add_argument('--all', action='store_true', help='下载所有字体')
    parser.add_argument('--css', action='store_true', help='只生成CSS文件')
    parser.add_argument('--category', type=str, help='指定要下载的字体类别')
    
    args = parser.parse_args()
    print(f"解析参数: --all={args.all}, --css={args.css}, --category={args.category}")
    
    # 创建临时应用上下文
    try:
        print("创建Flask应用上下文...")
        app = create_app()
        
        with app.app_context():
            print("正在导入font_manager...")
            # 动态导入字体管理器，避免循环导入
            from app.services.font_service import font_manager
            
            # 确保目录存在
            font_dir = os.path.join(app.static_folder, 'fonts')
            os.makedirs(font_dir, exist_ok=True)
            print(f"字体目录已就绪: {font_dir}")
            
            if args.css:
                # 只生成CSS文件
                print('正在生成字体CSS文件...')
                css_path = font_manager.generate_font_css()
                print(f'CSS文件已生成: {css_path}')
                return
                
            if args.all:
                # 下载所有字体
                print('开始下载所有字体资源...')
                start_time = time.time()
                
                success_count, total_count, errors = font_manager.download_all_fonts()
                
                end_time = time.time()
                duration = end_time - start_time
                
                print(f'字体下载完成，耗时 {duration:.2f} 秒')
                print(f'成功: {success_count}/{total_count}')
                
                if errors:
                    print('以下字体下载失败:')
                    for error in errors:
                        print(f'  - {error}')
                
                # 生成CSS文件
                print('正在生成字体CSS文件...')
                css_path = font_manager.generate_font_css()
                print(f'CSS文件已生成: {css_path}')
                
            elif args.category:
                # 下载指定类别的字体
                print(f'开始下载{args.category}类别的字体...')
                # 实现按类别下载的功能
                print('按类别下载功能尚未实现')
                
            else:
                print('未指定下载选项，请使用 --all 下载所有字体，或 --css 只生成CSS')
                parser.print_help()
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    main() 