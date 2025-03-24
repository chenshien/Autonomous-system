from flask import current_app
import jwt
from datetime import datetime, timedelta
import secrets
import string
import re
import hashlib
import uuid
import bcrypt

def generate_jwt_token(user_id, token_type='access'):
    """
    生成JWT令牌
    :param user_id: 用户ID
    :param token_type: 令牌类型，'access' 或 'refresh'
    :return: JWT令牌字符串
    """
    now = datetime.utcnow()
    
    # 设置过期时间
    if token_type == 'access':
        expires = now + current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
    else:  # refresh
        expires = now + current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
    
    # 设置令牌负载
    payload = {
        'user_id': user_id,
        'token_type': token_type,
        'exp': expires,
        'iat': now,
        'jti': str(uuid.uuid4())  # JWT ID，用于防止重放攻击
    }
    
    # 生成令牌
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return token

def verify_jwt_token(token):
    """
    验证JWT令牌
    :param token: JWT令牌字符串
    :return: 解码后的负载，如果验证失败则返回None
    """
    try:
        payload = jwt.decode(
            token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        # 令牌已过期
        return None
    except jwt.InvalidTokenError:
        # 令牌无效
        return None

def generate_password(length=12):
    """
    生成强密码
    :param length: 密码长度，默认12位
    :return: 生成的密码
    """
    # 确保密码包含大小写字母、数字和特殊字符
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?'
    
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # 检查密码强度
        if (any(c.islower() for c in password) and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)):
            return password

def validate_password_strength(password):
    """
    验证密码强度
    :param password: 密码
    :return: (bool, str) 表示密码是否强健及原因
    """
    if len(password) < 8:
        return False, '密码长度必须至少为8个字符'
    
    if not re.search(r'[A-Z]', password):
        return False, '密码必须包含至少一个大写字母'
    
    if not re.search(r'[a-z]', password):
        return False, '密码必须包含至少一个小写字母'
    
    if not re.search(r'[0-9]', password):
        return False, '密码必须包含至少一个数字'
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>\/?]', password):
        return False, '密码必须包含至少一个特殊字符'
    
    return True, '密码强度符合要求'

def generate_csrf_token():
    """
    生成CSRF令牌
    :return: CSRF令牌
    """
    return secrets.token_hex(16)

def hash_data(data, salt=None):
    """
    使用bcrypt哈希数据
    :param data: 要哈希的数据
    :param salt: 盐值，如果不提供则生成新的
    :return: (哈希值, 盐值)
    """
    if not salt:
        salt = bcrypt.gensalt()
    
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    hashed = bcrypt.hashpw(data, salt)
    return hashed, salt

def verify_hash(data, hashed):
    """
    验证数据与哈希值
    :param data: 原始数据
    :param hashed: 哈希值
    :return: 是否匹配
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return bcrypt.checkpw(data, hashed)

def generate_secure_token():
    """
    生成安全令牌，用于各种临时标识如重置密码链接
    :return: 安全令牌
    """
    return secrets.token_urlsafe(32) 