import os
import uuid
import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from flask import current_app, url_for
import base64
import time
import hmac
import hashlib

# 验证码配置
CAPTCHA_WIDTH = 160
CAPTCHA_HEIGHT = 60
CAPTCHA_LENGTH = 4
CAPTCHA_FONT_SIZE = 36
CAPTCHA_EXPIRATION = 300  # 验证码有效期，单位：秒

# 验证码存储
captcha_store = {}  # 生产环境应该使用Redis或其他分布式存储

def generate_random_string(length=CAPTCHA_LENGTH):
    """生成随机字符串"""
    # 排除容易混淆的字符，如0和O，1和l
    chars = '23456789abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ'
    return ''.join(random.choice(chars) for _ in range(length))

def generate_captcha():
    """生成验证码图片和对应的ID"""
    # 生成随机验证码字符串
    captcha_text = generate_random_string()
    
    # 创建图像对象
    image = Image.new('RGB', (CAPTCHA_WIDTH, CAPTCHA_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # 尝试加载字体
    try:
        font_path = os.path.join(current_app.static_folder, 'fonts', 'arial.ttf')
        if not os.path.exists(font_path):
            # 使用系统默认字体
            font = ImageFont.load_default()
        else:
            font = ImageFont.truetype(font_path, CAPTCHA_FONT_SIZE)
    except Exception:
        # 出错时使用默认字体
        font = ImageFont.load_default()
    
    # 绘制文本
    text_width, text_height = draw.textsize(captcha_text, font=font)
    x = (CAPTCHA_WIDTH - text_width) // 2
    y = (CAPTCHA_HEIGHT - text_height) // 2
    
    # 添加噪点
    for _ in range(random.randint(100, 200)):
        draw.point([random.randint(0, CAPTCHA_WIDTH), random.randint(0, CAPTCHA_HEIGHT)], 
                  fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)))
    
    # 绘制干扰线
    for _ in range(random.randint(3, 5)):
        x1 = random.randint(0, CAPTCHA_WIDTH)
        y1 = random.randint(0, CAPTCHA_HEIGHT)
        x2 = random.randint(0, CAPTCHA_WIDTH)
        y2 = random.randint(0, CAPTCHA_HEIGHT)
        draw.line([(x1, y1), (x2, y2)], 
                 fill=(random.randint(0, 200), random.randint(0, 200), random.randint(0, 200)),
                 width=random.randint(1, 2))
    
    # 绘制验证码文本
    for i, char in enumerate(captcha_text):
        # 每个字符有轻微的角度变化
        char_image = Image.new('RGB', (CAPTCHA_FONT_SIZE, CAPTCHA_FONT_SIZE + 10), (255, 255, 255))
        char_draw = ImageDraw.Draw(char_image)
        
        # 随机颜色
        color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
        
        # 随机位置微调
        x_offset = x + i * (text_width // len(captcha_text))
        y_offset = y + random.randint(-5, 5)
        
        char_draw.text((0, 0), char, font=font, fill=color)
        
        # 随机旋转
        angle = random.uniform(-30, 30)
        char_image = char_image.rotate(angle, expand=True, fillcolor=(255, 255, 255))
        
        # 放置到原图
        image.paste(char_image, (x_offset, y_offset), mask=char_image)
    
    # 将图像转换为base64编码
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    
    # 生成验证码ID并存储验证码内容
    captcha_id = str(uuid.uuid4())
    captcha_store[captcha_id] = {
        'text': captcha_text.lower(),  # 存储验证码文本（转为小写，用于不区分大小写的验证）
        'expires_at': int(time.time()) + CAPTCHA_EXPIRATION  # 验证码过期时间
    }
    
    # 清理过期验证码
    cleanup_expired_captchas()
    
    # 返回验证码ID和图片的base64编码
    captcha_url = f"data:image/png;base64,{img_str}"
    return captcha_id, captcha_url

def validate_captcha(captcha_id, captcha_input):
    """验证验证码是否正确"""
    if not captcha_id or not captcha_input:
        return False
    
    # 获取存储的验证码信息
    captcha_info = captcha_store.get(captcha_id)
    if not captcha_info:
        return False
    
    # 检查是否过期
    if captcha_info['expires_at'] < int(time.time()):
        # 删除过期验证码
        captcha_store.pop(captcha_id, None)
        return False
    
    # 验证验证码（不区分大小写）
    is_valid = captcha_info['text'] == captcha_input.lower()
    
    # 验证成功后删除验证码，防止重复使用
    if is_valid:
        captcha_store.pop(captcha_id, None)
    
    return is_valid

def cleanup_expired_captchas():
    """清理过期的验证码"""
    current_time = int(time.time())
    expired_ids = [captcha_id for captcha_id, info in captcha_store.items() 
                   if info['expires_at'] < current_time]
    
    for captcha_id in expired_ids:
        captcha_store.pop(captcha_id, None)
    
    return len(expired_ids)

def generate_captcha_signature(captcha_text, timestamp):
    """生成验证码签名，用于安全性更高的验证方式"""
    secret_key = current_app.config.get('SECRET_KEY', '')
    message = f"{captcha_text.lower()}:{timestamp}"
    
    # 使用HMAC-SHA256生成签名
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return signature 