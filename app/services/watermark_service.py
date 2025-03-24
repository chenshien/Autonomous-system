import os
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from flask import current_app
from flask_login import current_user

def get_font(size=24):
    """获取字体，优先使用系统中文字体"""
    # 尝试常见的中文字体路径
    font_paths = [
        # Windows 常见中文字体
        "c:/windows/fonts/simhei.ttf",
        "c:/windows/fonts/msyh.ttc",
        # Linux 常见中文字体
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        # macOS 常见中文字体
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    # 尝试从应用静态资源加载字体
    try:
        font_path = os.path.join(current_app.static_folder, 'fonts', 'msyh.ttf')
        font_paths.insert(0, font_path)  # 优先使用应用内字体
    except:
        pass
    
    # 尝试加载字体
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # 如果所有尝试都失败，使用默认字体
    return ImageFont.load_default()

def add_viewing_watermark(image_data, file_type='pdf'):
    """
    为在线查看的文件添加水印
    水印内容：用户名+用户真实姓名+服务器时间
    """
    # 对于非图片类型的文件（如PDF），需要在应用层面进行处理
    if file_type.lower() not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        return image_data
    
    try:
        # 打开原始图片
        img = Image.open(BytesIO(image_data))
        
        # 创建一个与原图尺寸相同的透明层用于绘制水印
        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        # 获取字体
        font = get_font(size=int(min(img.width, img.height) / 30))
        
        # 构建水印内容
        username = current_user.username
        fullname = current_user.full_name or "未知用户"
        server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        watermark_text = f"{username} {fullname} {server_time}"
        
        # 在图片上绘制多行水印（斜向排列）
        width, height = img.size
        for i in range(0, width + height, int(min(width, height) / 5)):
            pos = (i - height // 2, i - width // 3)
            draw.text(pos, watermark_text, font=font, fill=(128, 128, 128, 100))
        
        # 将水印层与原图合并
        watermarked = Image.alpha_composite(img.convert('RGBA'), watermark)
        
        # 转换回原始格式
        if img.mode != 'RGBA':
            watermarked = watermarked.convert(img.mode)
        
        # 保存到BytesIO对象并返回
        output = BytesIO()
        watermarked.save(output, format=img.format)
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        current_app.logger.error(f"添加查看水印失败: {str(e)}")
        return image_data  # 出错时返回原始图像

def add_printing_watermark(image_data, file_type='pdf'):
    """
    为在线打印的文件添加水印
    水印内容：克分行在线流程系统+用户名+用户真实姓名+服务器时间
    """
    # 对于非图片类型的文件（如PDF），需要在应用层面进行处理
    if file_type.lower() not in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
        return image_data
    
    try:
        # 打开原始图片
        img = Image.open(BytesIO(image_data))
        
        # 创建一个与原图尺寸相同的透明层用于绘制水印
        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        
        # 获取字体
        font = get_font(size=int(min(img.width, img.height) / 25))
        
        # 构建水印内容
        username = current_user.username
        fullname = current_user.full_name or "未知用户"
        server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        watermark_text = f"克分行在线流程系统 {username} {fullname} {server_time}"
        
        # 在图片上绘制多行水印（斜向排列）
        width, height = img.size
        for i in range(0, width + height, int(min(width, height) / 4)):
            pos = (i - height // 2, i - width // 3)
            draw.text(pos, watermark_text, font=font, fill=(100, 100, 100, 128))
        
        # 将水印层与原图合并
        watermarked = Image.alpha_composite(img.convert('RGBA'), watermark)
        
        # 转换回原始格式
        if img.mode != 'RGBA':
            watermarked = watermarked.convert(img.mode)
        
        # 保存到BytesIO对象并返回
        output = BytesIO()
        watermarked.save(output, format=img.format)
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        current_app.logger.error(f"添加打印水印失败: {str(e)}")
        return image_data  # 出错时返回原始图像

def add_pdf_watermark(pdf_data, watermark_type='view'):
    """
    为PDF文件添加水印
    
    参数:
        pdf_data: PDF文件数据
        watermark_type: 'view' 用于在线查看, 'print' 用于打印
    
    返回:
        添加水印后的PDF数据
    """
    try:
        # 此处需要使用PyPDF2或reportlab等库处理PDF
        # 由于依赖库可能不同，这里提供一个简单的实现框架
        import io
        from PyPDF2 import PdfFileReader, PdfFileWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        # 获取水印文本
        username = current_user.username
        fullname = current_user.full_name or "未知用户"
        server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if watermark_type == 'print':
            watermark_text = f"克分行在线流程系统 {username} {fullname} {server_time}"
        else:
            watermark_text = f"{username} {fullname} {server_time}"
        
        # 创建一个内存中的PDF
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        
        # 设置水印文本属性
        c.setFont("Helvetica", 12)
        c.setFillColorRGB(0.5, 0.5, 0.5, alpha=0.3)  # 灰色，透明度0.3
        
        # 绘制旋转的水印文本
        c.saveState()
        c.translate(300, 400)
        c.rotate(45)
        c.drawString(0, 0, watermark_text)
        c.restoreState()
        
        c.save()
        
        # 移动到开始
        packet.seek(0)
        watermark_pdf = PdfFileReader(packet)
        
        # 读取原始PDF
        existing_pdf = PdfFileReader(io.BytesIO(pdf_data))
        output = PdfFileWriter()
        
        # 将水印添加到每一页
        for i in range(existing_pdf.getNumPages()):
            page = existing_pdf.getPage(i)
            page.mergePage(watermark_pdf.getPage(0))
            output.addPage(page)
        
        # 将结果写入到内存
        result_buffer = io.BytesIO()
        output.write(result_buffer)
        result_buffer.seek(0)
        
        return result_buffer.getvalue()
    except ImportError:
        # 如果缺少必要的库，记录错误并返回原始数据
        current_app.logger.error("缺少处理PDF水印所需的库(PyPDF2/reportlab)")
        return pdf_data
    except Exception as e:
        current_app.logger.error(f"添加PDF水印失败: {str(e)}")
        return pdf_data 