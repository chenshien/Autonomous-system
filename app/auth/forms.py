from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Regexp
from app.models import User

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=64, message='用户名长度必须在3-64个字符之间')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=6, message='密码长度不能少于6个字符')
    ])
    captcha = StringField('验证码', validators=[
        DataRequired(message='请输入验证码'),
        Length(min=4, max=10, message='验证码长度不正确')
    ])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=64, message='用户名长度必须在3-64个字符之间'),
        Regexp('^[A-Za-z0-9_]+$', message='用户名只能包含字母、数字和下划线')
    ])
    email = StringField('电子邮箱', validators=[
        DataRequired(message='请输入电子邮箱'),
        Email(message='请输入有效的电子邮箱地址'),
        Length(max=120, message='邮箱长度不能超过120个字符')
    ])
    full_name = StringField('姓名', validators=[
        Length(max=64, message='姓名长度不能超过64个字符')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
        Length(min=8, message='密码长度不能少于8个字符'),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$', 
               message='密码必须包含大小写字母和数字')
    ])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(message='请再次输入密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    captcha = StringField('验证码', validators=[
        DataRequired(message='请输入验证码'),
        Length(min=4, max=10, message='验证码长度不正确')
    ])
    submit = SubmitField('注册')
    
    def validate_username(self, field):
        """验证用户名是否已存在"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('该用户名已被使用')
    
    def validate_email(self, field):
        """验证邮箱是否已存在"""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('该邮箱已被注册')

class PasswordResetRequestForm(FlaskForm):
    """密码重置请求表单"""
    email = StringField('电子邮箱', validators=[
        DataRequired(message='请输入电子邮箱'),
        Email(message='请输入有效的电子邮箱地址'),
        Length(max=120, message='邮箱长度不能超过120个字符')
    ])
    captcha = StringField('验证码', validators=[
        DataRequired(message='请输入验证码'),
        Length(min=4, max=10, message='验证码长度不正确')
    ])
    submit = SubmitField('重置密码')
    
    def validate_email(self, field):
        """验证邮箱是否存在"""
        user = User.query.filter_by(email=field.data).first()
        if not user:
            raise ValidationError('该邮箱未注册')

class PasswordResetForm(FlaskForm):
    """密码重置表单"""
    password = PasswordField('新密码', validators=[
        DataRequired(message='请输入新密码'),
        Length(min=8, message='密码长度不能少于8个字符'),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$', 
               message='密码必须包含大小写字母和数字')
    ])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(message='请再次输入密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    submit = SubmitField('重置密码')

class ChangePasswordForm(FlaskForm):
    """修改密码表单"""
    old_password = PasswordField('当前密码', validators=[
        DataRequired(message='请输入当前密码')
    ])
    password = PasswordField('新密码', validators=[
        DataRequired(message='请输入新密码'),
        Length(min=8, message='密码长度不能少于8个字符'),
        Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).+$', 
               message='密码必须包含大小写字母和数字')
    ])
    password2 = PasswordField('确认密码', validators=[
        DataRequired(message='请再次输入密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    submit = SubmitField('修改密码') 