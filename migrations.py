import os
from datetime import datetime

# 创建迁移记录
migration_record = """
# 数据库迁移记录

## 添加字体管理和初始化向导功能
- 时间: {time}
- 内容:
  - 添加了字体管理功能
  - 添加了系统初始化向导
  - 添加了部门管理功能
  - 更新了用户模型，增加了部门和职位字段

## 初始数据
- 创建了基础权限配置
- 创建了管理员和普通用户角色
- 创建了默认系统管理部门
- 创建了默认管理员账号

## 完成情况
- [x] 数据库表结构更新
- [x] 初始化基础数据
- [x] 字体资源目录创建
""".format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# 确保migrations目录存在
if not os.path.exists('migrations'):
    os.makedirs('migrations')

# 写入迁移记录
with open('migrations/migration_record.md', 'w', encoding='utf-8') as f:
    f.write(migration_record)

print("迁移记录已创建: migrations/migration_record.md") 