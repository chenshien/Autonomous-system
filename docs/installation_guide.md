# 自动化流程系统安装手册

## 1. 系统概述

自动化流程系统是一个基于Web的流程管理平台，用于帮助企业管理文档、流程和任务。系统支持多种文档格式的查看、编辑和打印，内置审批流程引擎，可以自定义工作流程，并支持电子签名功能。

## 2. 系统要求

### 2.1 服务器硬件要求

| 配置项 | 最低要求 | 推荐配置 |
|-------|---------|---------|
| CPU   | 双核 2.0GHz | 四核 3.0GHz 或更高 |
| 内存   | 4GB | 8GB 或更高 |
| 磁盘空间 | 10GB 可用空间 | 20GB 或更高 |
| 网络   | 100Mbps | 1000Mbps |

### 2.2 操作系统要求

本系统支持以下操作系统：

- **Windows**: Windows 10/11, Windows Server 2016/2019/2022
- **Linux**: Ubuntu 18.04/20.04/22.04, CentOS 7/8, Debian 10/11
- **macOS**: 10.14 (Mojave) 或更高版本

### 2.3 软件依赖

- **Python**: 3.7 或更高版本
- **数据库**: 
  - SQLite 3 (默认，适合小型部署)
  - MySQL 5.7+ / MariaDB 10.3+
  - PostgreSQL 10+
- **Web服务器** (生产环境):
  - Nginx
  - Apache
- **PDF处理**:
  - wkhtmltopdf (用于HTML转PDF)
  - Reportlab (用于PDF生成和处理)
- **字体**:
  - 系统必需的基础字体 (安装向导会自动检测和提示)

### 2.4 浏览器支持

用户端支持以下现代浏览器：

- Chrome 80+
- Firefox 78+
- Edge 80+
- Safari 13+

## 3. 安装步骤

### 3.1 Python环境配置

1. 安装Python 3.7+

   **Windows**:
   从 [Python官网](https://www.python.org/downloads/) 下载并安装Python 3.7或更高版本。
   安装时请选中 "Add Python to PATH" 选项。

   **Linux**:
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3 python3-pip python3-venv

   # CentOS/RHEL
   sudo yum install python3 python3-pip
   ```

   **macOS**:
   ```bash
   # 使用Homebrew
   brew install python3
   ```

2. 创建虚拟环境(推荐)

   ```bash
   # 创建虚拟环境
   python -m venv venv

   # 激活虚拟环境
   # Windows
   venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

### 3.2 获取系统代码

1. 从代码仓库克隆或下载系统代码:

   ```bash
   git clone https://your-repository-url/workflow-system.git
   cd workflow-system
   ```

   或者从提供的压缩包解压:

   ```bash
   unzip workflow-system.zip
   cd workflow-system
   ```

2. 安装依赖包:

   ```bash
   pip install -r requirements.txt
   ```

### 3.3 基本配置

1. 创建配置文件:

   ```bash
   # 复制配置模板
   cp config.example.py instance/config.py
   ```

2. 编辑配置文件 `instance/config.py`, 根据需要修改以下配置:

   ```python
   # 密钥配置
   SECRET_KEY = '生成一个随机字符串作为密钥'
   
   # 数据库配置 (默认SQLite)
   SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
   
   # 或者使用MySQL
   # SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/dbname'
   
   # 上传文件配置
   UPLOAD_FOLDER = 'app/static/uploads'
   MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
   
   # 日志配置
   LOG_LEVEL = 'INFO'
   LOG_FILE = 'logs/app.log'
   ```

### 3.4 初始化数据库

1. 初始化数据库:

   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

2. 创建初始管理员用户:

   ```bash
   flask init-admin
   ```

   按照提示输入管理员用户名、密码和邮箱。

### 3.5 安装外部依赖

1. 安装wkhtmltopdf (用于PDF生成):

   **Windows**:
   从 [wkhtmltopdf官网](https://wkhtmltopdf.org/downloads.html) 下载并安装。
   
   **Linux**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install wkhtmltopdf
   
   # CentOS/RHEL
   sudo yum install wkhtmltopdf
   ```
   
   **macOS**:
   ```bash
   brew install wkhtmltopdf
   ```

2. 字体配置:
   
   初始化向导会自动检测并提示安装必要的字体。如需手动配置，请确保以下字体可用:
   
   - 中文字体: 宋体(SimSun)、微软雅黑(Microsoft YaHei)
   - 英文字体: Arial、Times New Roman
   - 符号字体: Symbol

### 3.6 运行系统初始化向导

1. 启动开发服务器:

   ```bash
   flask run
   ```

2. 访问初始化向导:
   
   打开浏览器访问 `http://127.0.0.1:5000/install`
   
   按照向导步骤完成系统初始化:
   - 系统环境检查
   - 数据库配置
   - 管理员账户创建
   - 字体资源配置

## 4. 生产环境部署

### 4.1 使用Gunicorn(Linux/macOS)

1. 安装Gunicorn:

   ```bash
   pip install gunicorn
   ```

2. 创建系统服务配置文件 `/etc/systemd/system/workflow.service`:

   ```ini
   [Unit]
   Description=Workflow System
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/path/to/workflow-system
   ExecStart=/path/to/workflow-system/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 wsgi:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. 启动服务:

   ```bash
   sudo systemctl enable workflow
   sudo systemctl start workflow
   ```

### 4.2 使用Nginx作为反向代理

1. 安装Nginx:

   ```bash
   # Ubuntu/Debian
   sudo apt install nginx
   
   # CentOS/RHEL
   sudo yum install nginx
   ```

2. 创建Nginx配置文件 `/etc/nginx/sites-available/workflow`:

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       location /static {
           alias /path/to/workflow-system/app/static;
           expires 30d;
       }
   }
   ```

3. 启用配置:

   ```bash
   sudo ln -s /etc/nginx/sites-available/workflow /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

### 4.3 Windows环境(使用waitress)

1. 安装waitress:

   ```bash
   pip install waitress
   ```

2. 创建启动脚本 `start_server.py`:

   ```python
   from waitress import serve
   from app import create_app
   
   app = create_app()
   serve(app, host='0.0.0.0', port=8080)
   ```

3. 运行服务器:

   ```bash
   python start_server.py
   ```

4. 注册为Windows服务(可选):
   
   使用NSSM (Non-Sucking Service Manager)将应用注册为Windows服务

## 5. 系统更新

### 5.1 更新步骤

1. 备份数据:

   ```bash
   # 备份数据库(SQLite)
   cp instance/app.db instance/app.db.backup
   
   # 备份配置文件
   cp instance/config.py instance/config.py.backup
   
   # 备份上传文件
   cp -r app/static/uploads app/static/uploads.backup
   ```

2. 获取最新代码:

   ```bash
   git pull origin main
   ```

3. 更新依赖:

   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. 更新数据库:

   ```bash
   flask db migrate
   flask db upgrade
   ```

5. 重启服务:

   ```bash
   # 使用systemd
   sudo systemctl restart workflow
   
   # 或重启Nginx
   sudo systemctl restart nginx
   ```

## 6. 故障排除

### 6.1 常见问题

1. **数据库连接失败**
   - 检查数据库凭据是否正确
   - 确认数据库服务是否运行
   - 检查网络连接和防火墙设置

2. **文件上传问题**
   - 检查上传目录权限
   - 确认上传文件大小是否超过限制
   - 检查磁盘空间是否充足

3. **PDF生成失败**
   - 确认wkhtmltopdf是否正确安装
   - 检查字体资源是否完整
   - 查看日志文件获取详细错误信息

### 6.2 日志查看

系统日志位于:
- 应用日志: `logs/app.log`
- Web服务器日志:
  - Nginx: `/var/log/nginx/error.log`
  - Apache: `/var/log/apache2/error.log`

### 6.3 联系支持

如需进一步帮助，请联系技术支持:
- 电子邮件: support@example.com
- 技术支持热线: +86-123-4567890

## 7. 附录

### 7.1 系统架构

```
workflow-system/
├── app/                    # 应用主目录
│   ├── static/             # 静态资源
│   ├── templates/          # 模板文件
│   ├── services/           # 服务模块
│   ├── models/             # 数据模型
│   ├── api/                # API接口
│   ├── auth/               # 认证模块
│   ├── admin/              # 管理后台
│   ├── file/               # 文件处理
│   ├── workflow/           # 流程引擎
│   └── __init__.py         # 应用工厂
├── docs/                   # 文档
├── instance/               # 实例配置
├── logs/                   # 日志文件
├── migrations/             # 数据库迁移
├── tests/                  # 测试代码
├── venv/                   # 虚拟环境
├── config.py               # 配置模板
├── requirements.txt        # 依赖清单
└── wsgi.py                 # WSGI入口
```

### 7.2 配置参考

完整的配置选项及说明:

```python
# 基本配置
SECRET_KEY = 'your-secret-key'
DEBUG = False
TESTING = False

# 数据库配置
SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
DATABASE_CONNECT_OPTIONS = {}

# 安全配置
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
REMEMBER_COOKIE_HTTPONLY = True

# 文件上传配置
UPLOAD_FOLDER = 'app/static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip', 'rar', 'jpg', 'jpeg', 'png', 'gif'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# 邮件配置
MAIL_SERVER = 'smtp.example.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@example.com'
MAIL_PASSWORD = 'your-password'
MAIL_DEFAULT_SENDER = 'no-reply@example.com'

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/app.log'
LOG_FORMAT = '%(asctime)s [%(levelname)s] %(module)s: %(message)s'
```

---

版权所有 © 2023 自动化流程系统
技术支持: support@example.com 