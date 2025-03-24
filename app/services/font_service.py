import os
import sys
import logging
from flask import current_app
import shutil
from datetime import datetime
import requests
import io
import zipfile

# 定义系统支持的字体列表
SYSTEM_FONTS = {
    # 中文字体
    'chinese': [
        {'name': 'SimSun', 'file': 'simsun.ttc', 'desc': '宋体 - 中文标准字体'},
        {'name': 'SimHei', 'file': 'simhei.ttf', 'desc': '黑体 - 中文粗体字体'},
        {'name': 'KaiTi', 'file': 'kaiti.ttf', 'desc': '楷体 - 中文艺术字体'},
        {'name': 'Microsoft YaHei', 'file': 'msyh.ttc', 'desc': '微软雅黑 - 中文现代字体'},
        {'name': 'FangSong', 'file': 'simfang.ttf', 'desc': '仿宋 - 中文传统字体'}
    ],
    # 英文字体
    'english': [
        {'name': 'Arial', 'file': 'arial.ttf', 'desc': 'Arial - 英文标准字体'},
        {'name': 'Times New Roman', 'file': 'times.ttf', 'desc': 'Times New Roman - 英文衬线字体'},
        {'name': 'Courier New', 'file': 'cour.ttf', 'desc': 'Courier New - 等宽字体'},
        {'name': 'Calibri', 'file': 'calibri.ttf', 'desc': 'Calibri - Office默认字体'},
        {'name': 'Verdana', 'file': 'verdana.ttf', 'desc': 'Verdana - 网页友好字体'}
    ],
    # 特殊符号字体
    'symbol': [
        {'name': 'Symbol', 'file': 'symbol.ttf', 'desc': 'Symbol - 数学符号字体'},
        {'name': 'Wingdings', 'file': 'wingding.ttf', 'desc': 'Wingdings - 装饰符号字体'},
        {'name': 'Webdings', 'file': 'webdings.ttf', 'desc': 'Webdings - Web符号字体'}
    ],
    # 衬线字体
    'serif': [
        {'name': 'Georgia', 'file': 'georgia.ttf', 'desc': 'Georgia - 优雅的衬线字体'},
        {'name': 'Garamond', 'file': 'gara.ttf', 'desc': 'Garamond - 传统印刷字体'}
    ],
    # 无衬线字体
    'sans-serif': [
        {'name': 'Tahoma', 'file': 'tahoma.ttf', 'desc': 'Tahoma - 清晰的无衬线字体'},
        {'name': 'Segoe UI', 'file': 'segoeui.ttf', 'desc': 'Segoe UI - Windows界面字体'}
    ]
}

# 默认必须的字体列表（最基础的功能支持）
REQUIRED_FONTS = ['simsun.ttc', 'msyh.ttc', 'arial.ttf', 'symbol.ttf']

# 常见字体在Windows系统中的位置
WINDOWS_FONT_PATH = 'C:\\Windows\\Fonts'

# 字体管理类
class FontManager:
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化应用的字体资源"""
        self.app = app
        font_dir = os.path.join(app.static_folder, 'fonts')
        
        # 确保字体目录存在
        if not os.path.exists(font_dir):
            os.makedirs(font_dir)
        
        # 注册方法到模板上下文
        @app.context_processor
        def inject_font_functions():
            return {
                'get_fonts': self.get_available_fonts,
                'get_font_url': self.get_font_url,
                'get_font_categories': self.get_font_categories
            }
    
    def get_font_url(self, font_file):
        """获取字体文件的URL"""
        return f'/static/fonts/{font_file}'
    
    def get_system_fonts_path(self):
        """获取系统字体目录"""
        if sys.platform.startswith('win'):
            return WINDOWS_FONT_PATH
        elif sys.platform.startswith('darwin'):  # MacOS
            return '/Library/Fonts'
        else:  # Linux和其他系统
            return '/usr/share/fonts'
    
    def get_available_fonts(self):
        """获取系统中可用的字体列表"""
        font_dir = os.path.join(self.app.static_folder, 'fonts')
        available_fonts = []
        
        for category, fonts in SYSTEM_FONTS.items():
            for font in fonts:
                font_path = os.path.join(font_dir, font['file'])
                if os.path.exists(font_path):
                    font_data = font.copy()
                    font_data['available'] = True
                    font_data['url'] = self.get_font_url(font['file'])
                    font_data['category'] = category
                    available_fonts.append(font_data)
                else:
                    font_data = font.copy()
                    font_data['available'] = False
                    font_data['category'] = category
                    available_fonts.append(font_data)
        
        return available_fonts
    
    def copy_font_from_system(self, font_file):
        """从系统字体目录复制字体到应用"""
        system_font_path = os.path.join(self.get_system_fonts_path(), font_file)
        app_font_path = os.path.join(self.app.static_folder, 'fonts', font_file)
        
        if os.path.exists(system_font_path):
            try:
                shutil.copy2(system_font_path, app_font_path)
                self.logger.info(f"复制字体成功: {font_file}")
                return True
            except Exception as e:
                self.logger.error(f"复制字体失败 {font_file}: {str(e)}")
                return False
        else:
            self.logger.warning(f"系统中未找到字体: {font_file}")
            return False
    
    def check_required_fonts(self):
        """检查并复制必需的字体"""
        font_dir = os.path.join(self.app.static_folder, 'fonts')
        missing_fonts = []
        
        for font_file in REQUIRED_FONTS:
            font_path = os.path.join(font_dir, font_file)
            if not os.path.exists(font_path):
                success = self.copy_font_from_system(font_file)
                if not success:
                    missing_fonts.append(font_file)
        
        return missing_fonts
    
    def generate_font_css(self):
        """生成字体CSS文件"""
        available_fonts = self.get_available_fonts()
        css_content = ["/* 系统字体定义 */", f"/* 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */", ""]
        
        # 按类别分组
        categories = {}
        for font in available_fonts:
            if font['available']:
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
        symbol_fonts = [f"'{font['name']}'" for font in categories.get('symbol', [])[:2]]
        if symbol_fonts:
            css_content.append(f".font-symbol {{ \n  font-family: {', '.join(symbol_fonts)}, sans-serif; \n}}")
        
        # 等宽字体
        mono_fonts = ["monospace"]
        css_content.append(f".font-monospace {{ \n  font-family: {', '.join(mono_fonts)}; \n}}")
        
        # 数学字体
        math_fonts = [f"'{font['name']}'" for font in categories.get('symbol', [])[:1]]
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
        math_font = f"'{categories['symbol'][0]['name']}'" if 'symbol' in categories and categories['symbol'] else "serif"
        css_content.append(f".math-formula {{\n  font-family: {math_font}, serif;\n}}")
        
        css_content.append("\n/* 代码样式 */")
        css_content.append("pre, code {\n  font-family: Consolas, monospace;\n}")
        
        # 写入CSS文件
        css_path = os.path.join(self.app.static_folder, 'css', 'fonts.css')
        os.makedirs(os.path.dirname(css_path), exist_ok=True)
        
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(css_content))
        
        return css_path
        
    def download_all_fonts(self):
        """下载所有预定义的常用字体
        
        Returns:
            tuple: (成功数量, 总数量, 错误信息列表)
        """
        # 预定义开源字体列表
        OPEN_SOURCE_FONTS = [
            {
                'name': 'Noto Sans SC',
                'file': 'NotoSansSC-Regular.otf',
                'url': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansSC-Regular.otf',
                'category': 'chinese'
            },
            {
                'name': 'Noto Sans TC',
                'file': 'NotoSansTC-Regular.otf',
                'url': 'https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf',
                'category': 'chinese'
            },
            {
                'name': 'Noto Serif SC',
                'file': 'NotoSerifSC-Regular.otf',
                'url': 'https://github.com/googlefonts/noto-cjk/raw/main/Serif/OTF/SimplifiedChinese/NotoSerifSC-Regular.otf',
                'category': 'chinese'
            },
            {
                'name': 'Source Han Sans',
                'file': 'SourceHanSansSC-Regular.otf',
                'url': 'https://github.com/adobe-fonts/source-han-sans/releases/download/2.004R/SourceHanSansSC.zip',
                'category': 'chinese'
            },
            {
                'name': 'Source Han Serif',
                'file': 'SourceHanSerifSC-Regular.otf',
                'url': 'https://github.com/adobe-fonts/source-han-serif/releases/download/2.001R/SourceHanSerifSC.zip',
                'category': 'chinese'
            },
            {
                'name': 'JetBrains Mono',
                'file': 'JetBrainsMono-Regular.ttf',
                'url': 'https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip',
                'category': 'monospace'
            },
            {
                'name': 'Ubuntu Mono',
                'file': 'UbuntuMono-Regular.ttf',
                'url': 'https://github.com/canonical/UbuntuMono-fonts/raw/main/fonts/ttf/UbuntuMono-Regular.ttf',
                'category': 'monospace'
            },
            {
                'name': 'Latin Modern Math',
                'file': 'latinmodern-math.otf',
                'url': 'https://www.gust.org.pl/projects/e-foundry/lm-math/download/latinmodern-math-1959.zip',
                'category': 'math'
            },
            {
                'name': 'STIX Two Math',
                'file': 'STIXTwoMath-Regular.otf',
                'url': 'https://github.com/stipub/stixfonts/raw/master/fonts/static_otf/STIXTwoMath-Regular.otf',
                'category': 'math'
            },
            {
                'name': 'Fira Sans',
                'file': 'FiraSans-Regular.ttf',
                'url': 'https://github.com/mozilla/Fira/raw/master/ttf/FiraSans-Regular.ttf',
                'category': 'english'
            },
            {
                'name': 'Roboto',
                'file': 'Roboto-Regular.ttf',
                'url': 'https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf',
                'category': 'english'
            },
            {
                'name': 'Open Sans',
                'file': 'OpenSans-Regular.ttf',
                'url': 'https://github.com/googlefonts/opensans/raw/main/fonts/ttf/OpenSans-Regular.ttf',
                'category': 'english'
            }
        ]
        
        # 确保目录存在
        font_dir = os.path.join(self.app.static_folder, 'fonts')
        os.makedirs(font_dir, exist_ok=True)
        
        success_count = 0
        errors = []
        
        for font in OPEN_SOURCE_FONTS:
            if self.download_font(font):
                success_count += 1
            else:
                errors.append(f"下载失败: {font['name']} ({font['file']})")
        
        # 如果成功，更新字体CSS
        if success_count > 0:
            try:
                self.generate_font_css()
            except Exception as e:
                errors.append(f"更新字体CSS失败: {str(e)}")
        
        return success_count, len(OPEN_SOURCE_FONTS), errors

    def get_font_categories(self):
        """获取所有字体分类"""
        return list(SYSTEM_FONTS.keys())

    def download_font(self, font_info):
        """从网络下载字体文件
        
        Args:
            font_info: 包含字体信息的字典，必须包含name、file字段，可选包含url和category字段
            
        Returns:
            bool: 下载是否成功
        """
        if 'url' not in font_info:
            self.logger.error(f"缺少下载URL: {font_info.get('name', '未知字体')}")
            return False
            
        font_dir = os.path.join(self.app.static_folder, 'fonts')
        target_path = os.path.join(font_dir, font_info['file'])
        
        # 如果已存在，跳过下载
        if os.path.exists(target_path):
            self.logger.info(f"字体已存在，跳过下载: {font_info['name']} ({font_info['file']})")
            return True
        
        self.logger.info(f"正在下载字体: {font_info['name']} ({font_info.get('category', '未分类')})")
        
        try:
            # 获取文件扩展名
            _, file_ext = os.path.splitext(font_info['url'])
            
            # 下载字体文件
            response = requests.get(font_info['url'], stream=True, timeout=30)
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
                            self.logger.info(f"从压缩包中提取并保存字体: {font_filename}")
                            return True
                    
                    # 如果没有直接匹配，尝试找任何相关字体
                    for file_info in zf.infolist():
                        if file_info.filename.endswith(('.ttf', '.otf', '.ttc')) and (
                           font_info['name'].lower() in file_info.filename.lower() or
                           os.path.splitext(font_filename)[0].lower() in file_info.filename.lower()):
                            with open(target_path, 'wb') as f:
                                f.write(zf.read(file_info.filename))
                            self.logger.info(f"从压缩包中提取并保存字体: {file_info.filename} -> {font_filename}")
                            return True
                            
                    self.logger.error(f"在压缩包中未找到匹配的字体文件: {font_filename}")
                    return False
            else:
                # 直接保存字体文件
                with open(target_path, 'wb') as f:
                    f.write(response.content)
                self.logger.info(f"字体下载并保存成功: {font_info['file']}")
                return True
                
        except Exception as e:
            self.logger.error(f"下载字体失败 {font_info['name']}: {str(e)}")
            return False

# 创建实例
font_manager = FontManager() 