#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化版字体资源下载脚本

此脚本用于下载系统所需的开源字体资源，直接操作而不依赖Flask应用上下文
"""

import os
import sys
import logging
import time
import zipfile
import io
import requests
import warnings
from datetime import datetime

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 确保日志输出到控制台
    ]
)
logger = logging.getLogger('字体下载')

# 定义字体目录
STATIC_FOLDER = 'app/static'
FONT_DIR = os.path.join(STATIC_FOLDER, 'fonts')
CSS_DIR = os.path.join(STATIC_FOLDER, 'css')

# 预定义开源字体列表
OPEN_SOURCE_FONTS = [
    # 中文字体
    {
        'name': 'Noto Sans SC',
        'file': 'NotoSansSC-Regular.ttf',
        'url': 'https://cdn.jsdelivr.net/gh/notofonts/notofonts.github.io/fonts/NotoSansSC/hinted/ttf/NotoSansSC-Regular.ttf',
        'category': 'chinese'
    },
    # 英文字体
    {
        'name': 'Roboto',
        'file': 'Roboto-Regular.ttf',
        'url': 'https://cdn.jsdelivr.net/gh/google/fonts/apache/roboto/Roboto-Regular.ttf',
        'category': 'english'
    },
    # 等宽字体
    {
        'name': 'JetBrains Mono',
        'file': 'JetBrainsMono-Regular.ttf',
        'url': 'https://download.jetbrains.com/fonts/JetBrainsMono-2.304.zip',
        'category': 'monospace'
    },
    # 数学字体
    {
        'name': 'STIX Two Math',
        'file': 'STIXTwoMath-Regular.otf',
        'url': 'https://cdn.jsdelivr.net/gh/stipub/stixfonts/fonts/static_otf/STIXTwoMath-Regular.otf',
        'category': 'math'
    }
]

# 忽略SSL验证的警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
requests.packages.urllib3.disable_warnings()

# Windows系统字体路径
WINDOWS_FONT_PATH = 'C:\\Windows\\Fonts'

def download_font(font_info):
    """从网络下载字体文件
    
    Args:
        font_info: 包含字体信息的字典，必须包含name、file字段，可选包含url和category字段
        
    Returns:
        bool: 下载是否成功
    """
    if 'url' not in font_info:
        logger.error(f"缺少下载URL: {font_info.get('name', '未知字体')}")
        return False
        
    target_path = os.path.join(FONT_DIR, font_info['file'])
    
    # 如果已存在，跳过下载
    if os.path.exists(target_path):
        logger.info(f"字体已存在，跳过下载: {font_info['name']} ({font_info['file']})")
        return True
    
    logger.info(f"正在下载字体: {font_info['name']} ({font_info.get('category', '未分类')})")
    
    try:
        # 获取文件扩展名
        _, file_ext = os.path.splitext(font_info['url'])
        
        # 下载字体文件，不验证SSL证书以避免可能的SSL错误
        response = requests.get(font_info['url'], stream=True, timeout=60, verify=False)
        response.raise_for_status()  # 确保请求成功
        
        # 检查是否为压缩文件
        if file_ext.lower() in ['.zip']:
            # 解压缩文件并获取目标字体
            with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                font_filename = font_info['file']
                # 查找压缩包中的字体文件
                for file_info in zf.infolist():
                    if file_info.filename.endswith(('.ttf', '.otf', '.ttc')) and os.path.basename(file_info.filename) == font_filename:
                        # 发现目标字体
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(file_info.filename))
                        logger.info(f"从压缩包中提取并保存字体: {font_filename}")
                        return True
                
                # 如果没有直接匹配，尝试找任何相关字体
                for file_info in zf.infolist():
                    if file_info.filename.endswith(('.ttf', '.otf', '.ttc')) and (
                       font_info['name'].lower() in file_info.filename.lower() or
                       os.path.splitext(font_filename)[0].lower() in file_info.filename.lower()):
                        with open(target_path, 'wb') as f:
                            f.write(zf.read(file_info.filename))
                        logger.info(f"从压缩包中提取并保存字体: {file_info.filename} -> {font_filename}")
                        return True
                        
                logger.error(f"在压缩包中未找到匹配的字体文件: {font_filename}")
                return False
        else:
            # 直接保存字体文件
            with open(target_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"字体下载并保存成功: {font_info['file']}")
            return True
            
    except Exception as e:
        logger.error(f"下载字体失败 {font_info['name']}: {str(e)}")
        return False

def download_all_fonts():
    """下载所有预定义的常用字体
    
    Returns:
        tuple: (成功数量, 总数量, 错误信息列表)
    """
    # 确保目录存在
    os.makedirs(FONT_DIR, exist_ok=True)
    os.makedirs(CSS_DIR, exist_ok=True)
    
    success_count = 0
    errors = []
    
    for font in OPEN_SOURCE_FONTS:
        if download_font(font):
            success_count += 1
        else:
            errors.append(f"下载失败: {font['name']} ({font['file']})")
    
    # 如果成功，更新字体CSS
    if success_count > 0:
        try:
            generate_font_css()
        except Exception as e:
            errors.append(f"更新字体CSS失败: {str(e)}")
    
    return success_count, len(OPEN_SOURCE_FONTS), errors

def generate_font_css():
    """生成字体CSS文件"""
    css_content = ["/* 自动生成的字体CSS文件 */", 
                   f"/* 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */", ""]
    
    # 定义系统字体列表
    system_fonts = [
        {'name': 'SimSun', 'file': 'simsun.ttc', 'category': 'chinese'},
        {'name': 'SimHei', 'file': 'simhei.ttf', 'category': 'chinese'},
        {'name': 'Microsoft YaHei', 'file': 'msyh.ttc', 'category': 'chinese'},
        {'name': 'Arial', 'file': 'arial.ttf', 'category': 'english'},
        {'name': 'Times New Roman', 'file': 'times.ttf', 'category': 'english'},
        {'name': 'Courier New', 'file': 'cour.ttf', 'category': 'monospace'},
        {'name': 'Symbol', 'file': 'symbol.ttf', 'category': 'symbol'}
    ]
    
    # 获取所有字体列表（系统字体和开源字体）
    all_fonts = system_fonts + OPEN_SOURCE_FONTS
    
    # 获取已下载的字体
    available_fonts = []
    for font in all_fonts:
        if os.path.exists(os.path.join(FONT_DIR, font['file'])):
            font_data = font.copy()
            font_data['available'] = True
            font_data['url'] = f'/static/fonts/{font["file"]}'
            available_fonts.append(font_data)
    
    # 按类别分组
    categories = {}
    for font in available_fonts:
        category = font['category']
        if category not in categories:
            categories[category] = []
        categories[category].append(font)
    
    # 按类别生成CSS
    for category, fonts in categories.items():
        css_content.append(f"/* {category.capitalize()} 字体 */")
        
        for font in fonts:
            css_content.append(f"""@font-face {{
  font-family: '{font['name']}';
  src: url('{font['url']}') format('truetype');
  font-weight: normal;
  font-style: normal;
  font-display: swap;
}}
""")
        css_content.append("")
    
    # 添加便捷字体类
    css_content.append("/* 便捷字体类 */")
    
    # 中文字体
    chinese_fonts = [f"'{font['name']}'" for font in categories.get('chinese', [])[:3]]
    if chinese_fonts:
        css_content.append(f".font-chinese {{ \n  font-family: {', '.join(chinese_fonts)}, sans-serif; \n}}")
    
    # 英文字体
    english_fonts = [f"'{font['name']}'" for font in categories.get('english', [])[:2]]
    if english_fonts:
        css_content.append(f".font-english {{ \n  font-family: {', '.join(english_fonts)}, sans-serif; \n}}")
    
    # 符号字体
    symbol_fonts = [f"'{font['name']}'" for font in categories.get('symbol', [])[:2]] if 'symbol' in categories else []
    if symbol_fonts:
        css_content.append(f".font-symbol {{ \n  font-family: {', '.join(symbol_fonts)}, sans-serif; \n}}")
    
    # 等宽字体
    mono_fonts = [f"'{font['name']}'" for font in categories.get('monospace', [])[:2]] if 'monospace' in categories else []
    if not mono_fonts:
        mono_fonts = ["monospace"]
    css_content.append(f".font-monospace {{ \n  font-family: {', '.join(mono_fonts)}; \n}}")
    
    # 数学字体
    math_fonts = [f"'{font['name']}'" for font in categories.get('math', [])[:2]] if 'math' in categories else []
    if not math_fonts:
        math_fonts = ["serif"]
    css_content.append(f".font-math {{ \n  font-family: {', '.join(math_fonts)}, serif; \n}}")
    
    # 添加全局字体设置
    css_content.append("\n/* 全局字体设置 */")
    default_fonts = []
    if 'chinese' in categories and categories['chinese']:
        default_fonts.extend([f"'{font['name']}'" for font in categories['chinese'][:2]])
    if 'english' in categories and categories['english']:
        default_fonts.extend([f"'{font['name']}'" for font in categories['english'][:1]])
    if not default_fonts:
        default_fonts = ["sans-serif"]
    css_content.append(f"body {{\n  font-family: {', '.join(default_fonts)}, sans-serif;\n}}")
    
    # 特殊样式
    css_content.append("\n/* 数学公式样式 */")
    math_font = f"'{categories['math'][0]['name']}'" if 'math' in categories and categories['math'] else "serif"
    css_content.append(f".math-formula {{\n  font-family: {math_font}, serif;\n}}")
    
    css_content.append("\n/* 代码样式 */")
    css_content.append("pre, code {\n  font-family: Consolas, monospace;\n}")
    
    # 写入CSS文件
    css_path = os.path.join(CSS_DIR, 'fonts.css')
    os.makedirs(os.path.dirname(css_path), exist_ok=True)
    
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(css_content))
    
    logger.info(f"CSS文件生成成功: {css_path}")
    return css_path

def copy_system_fonts():
    """从Windows系统复制常用字体"""
    system_fonts = [
        {'name': 'SimSun', 'file': 'simsun.ttc', 'category': 'chinese'},
        {'name': 'SimHei', 'file': 'simhei.ttf', 'category': 'chinese'},
        {'name': 'Microsoft YaHei', 'file': 'msyh.ttc', 'category': 'chinese'},
        {'name': 'Arial', 'file': 'arial.ttf', 'category': 'english'},
        {'name': 'Times New Roman', 'file': 'times.ttf', 'category': 'english'},
        {'name': 'Courier New', 'file': 'cour.ttf', 'category': 'monospace'},
        {'name': 'Symbol', 'file': 'symbol.ttf', 'category': 'math'}
    ]
    
    success_count = 0
    errors = []
    
    for font in system_fonts:
        source_path = os.path.join(WINDOWS_FONT_PATH, font['file'])
        target_path = os.path.join(FONT_DIR, font['file'])
        
        # 如果已存在，跳过复制
        if os.path.exists(target_path):
            logger.info(f"字体已存在，跳过复制: {font['name']} ({font['file']})")
            success_count += 1
            continue
        
        # 检查源文件是否存在
        if not os.path.exists(source_path):
            logger.warning(f"系统中未找到字体: {font['file']}")
            errors.append(f"系统中未找到字体: {font['name']} ({font['file']})")
            continue
        
        try:
            import shutil
            shutil.copy2(source_path, target_path)
            logger.info(f"从系统复制字体成功: {font['name']} ({font['file']})")
            success_count += 1
        except Exception as e:
            logger.error(f"复制字体失败 {font['name']}: {str(e)}")
            errors.append(f"复制失败: {font['name']} ({font['file']})")
    
    return success_count, len(system_fonts), errors

def main():
    print("简化版字体下载工具启动...")
    
    # 确保目录存在
    os.makedirs(FONT_DIR, exist_ok=True)
    os.makedirs(CSS_DIR, exist_ok=True)
    
    print(f"字体目录: {os.path.abspath(FONT_DIR)}")
    print(f"CSS目录: {os.path.abspath(CSS_DIR)}")
    
    # 先尝试从系统复制字体
    print('尝试从系统复制字体...')
    sys_success, sys_total, sys_errors = copy_system_fonts()
    print(f'系统字体复制完成: {sys_success}/{sys_total}')
    
    if sys_errors:
        print('以下系统字体复制失败:')
        for error in sys_errors:
            print(f'  - {error}')
    
    # 再尝试从网络下载开源字体
    print('开始下载开源字体资源...')
    start_time = time.time()
    
    success_count, total_count, errors = download_all_fonts()
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f'开源字体下载完成，耗时 {duration:.2f} 秒')
    print(f'成功: {success_count}/{total_count}')
    
    if errors:
        print('以下开源字体下载失败:')
        for error in errors:
            print(f'  - {error}')
    
    # 生成CSS文件
    print('生成字体CSS文件...')
    css_path = generate_font_css()
    print(f'CSS文件已生成: {css_path}')
    print('字体设置完成！')

if __name__ == '__main__':
    main() 