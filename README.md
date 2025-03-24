# 自动化流程系统

基于Flask框架开发的企业级自动化流程管理系统，支持自定义工作流、流程审批、用户权限管理等功能。

## 功能特点

- **用户和权限管理**：支持角色、权限的细粒度控制
- **工作流引擎**：支持自定义流程定义、条件分支、多级审批
- **可视化设计器**：直观创建和编辑工作流
- **多种认证方式**：支持本地认证和第三方认证（如LDAP）
- **系统监控**：详细的日志记录和状态监控
- **高并发支持**：采用异步处理提高系统性能
- **容错机制**：支持流程异常自动恢复

## 安装部署

### 环境要求

- Python 3.7+
- PostgreSQL 10+（推荐）或 MySQL 5.7+
- Redis（可选，用于任务队列和缓存）

### 安装步骤

1. 克隆代码库

```bash
git clone https://yourrepository.com/workflow-system.git
cd workflow-system
```

2. 创建并激活虚拟环境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 修改配置

复制`config.py.example`为`config.py`，并根据实际环境修改配置项。

5. 初始化数据库

```bash
flask db init
flask db migrate -m "initial migration"
flask db upgrade
```

6. 启动服务

```bash
flask run
# 或用于生产环境
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 快速开始

1. 使用默认管理员账号登录系统
   - 用户名：admin
   - 密码：Admin@123

2. 在管理页面创建角色和用户，分配权限

3. 使用工作流设计器创建您的第一个工作流

4. 启动工作流实例并开始自动化流程

## 系统架构

- **前端**：基于Bootstrap和Vue.js的响应式界面
- **后端**：Flask RESTful API
- **数据库**：支持PostgreSQL/MySQL
- **工作流引擎**：自研高效工作流处理引擎

## 开发指南

### 项目结构

```
app/
  ├── api/                # API模块
  │   ├── admin/         # 管理员API
  │   ├── auth/          # 认证API
  │   ├── user/          # 用户API
  │   └── workflow/      # 工作流API
  ├── models/            # 数据库模型
  ├── services/          # 业务服务层
  ├── static/            # 静态资源
  ├── templates/         # 前端模板
  ├── utils/             # 工具函数
  └── __init__.py        # 应用初始化
migrations/              # 数据库迁移文件
tests/                   # 测试代码
config.py                # 配置文件
app.py                   # 应用入口
```

### 如何贡献

1. Fork项目代码库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

该项目采用MIT许可证 - 详情请参阅 [LICENSE](LICENSE) 文件 