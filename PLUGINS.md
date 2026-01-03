# 数据库插件开发指南

本文档介绍如何为数据库备份工具开发新的数据库插件。

## 插件系统概述

数据库备份工具使用插件化架构，所有数据库插件都继承自 `DatabasePlugin` 基类。这种设计使得添加新数据库类型变得简单且一致。

## 插件基类接口

### 必须实现的属性

```python
@property
@abstractmethod
def db_type(self) -> str:
    """
    数据库类型名称
    返回: 数据库类型（如 postgresql, mysql, cassandra 等）
    """
    pass
```

### 必须实现的方法

#### 1. `is_enabled()` - 检查插件是否启用

```python
@abstractmethod
def is_enabled(self) -> bool:
    """
    检查插件是否启用
    返回: True 表示启用，False 表示禁用
    """
    pass
```

#### 2. `get_databases()` - 获取数据库列表

```python
@abstractmethod
def get_databases(self) -> List[str]:
    """
    获取要备份的数据库列表
    
    如果配置为 'all'，则自动获取所有数据库（排除系统库）
    如果配置为逗号分隔的列表，则返回解析后的列表
    
    返回: 数据库名称列表
    """
    pass
```

#### 3. `backup_database()` - 备份单个数据库

```python
@abstractmethod
def backup_database(self, database: str, output_file: str) -> bool:
    """
    备份单个数据库
    
    参数:
        database: 数据库名称
        output_file: 输出文件路径（.sql 或其他格式）
        
    返回: True 表示成功，False 表示失败
    """
    pass
```

### 可选重写的方法

#### `backup_extra()` - 备份额外数据

```python
def backup_extra(self) -> List[str]:
    """
    备份额外的数据（如 PostgreSQL 的全局对象）
    
    返回: 额外备份文件路径列表
    """
    return []
```

## 开发新插件步骤

### 步骤 1: 创建插件文件

在 `app/plugins/` 目录下创建新文件，例如 `cassandra.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cassandra 数据库插件
使用 cqlsh 备份 Cassandra 数据库
"""

import subprocess
import os
from typing import List
from app.plugins.base import DatabasePlugin
from app.logger import logger


class CassandraPlugin(DatabasePlugin):
    """Cassandra 数据库插件"""
    
    @property
    def db_type(self) -> str:
        return 'cassandra'
    
    def is_enabled(self) -> bool:
        return self.config.get('enabled', False)
    
    def get_databases(self) -> List[str]:
        """获取 Cassandra keyspace 列表"""
        databases_config = self.config.get('databases', 'all')
        
        # 如果指定了具体数据库列表
        if databases_config != 'all':
            databases = [db.strip() for db in databases_config.split(',') if db.strip()]
            return databases
        
        # 自动获取所有 keyspace
        try:
            logger.info('正在获取 Cassandra keyspace 列表...')
            
            cmd = [
                'cqlsh',
                self.config.get('host', 'localhost'),
                str(self.config.get('port', 9042)),
                '-e', "DESCRIBE KEYSPACES;"
            ]
            
            # 添加认证（如果有）
            user = self.config.get('user', '')
            password = self.config.get('password', '')
            if user and password:
                cmd.extend(['-u', user, '-p', password])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 排除系统 keyspace
                system_keyspaces = ['system', 'system_schema', 'system_auth', 'system_traces']
                keyspaces = [
                    ks.strip() 
                    for ks in result.stdout.strip().split() 
                    if ks.strip() and ks.strip() not in system_keyspaces
                ]
                logger.info(f'找到 {len(keyspaces)} 个 Cassandra keyspace')
                return keyspaces
            else:
                logger.error(f'获取 keyspace 列表失败: {result.stderr}')
                return []
                
        except Exception as e:
            logger.error(f'获取 keyspace 列表异常: {e}')
            return []
    
    def backup_database(self, database: str, output_file: str) -> bool:
        """备份单个 Cassandra keyspace"""
        try:
            cmd = [
                'cqlsh',
                self.config.get('host', 'localhost'),
                str(self.config.get('port', 9042)),
                '-e', f"DESCRIBE KEYSPACE {database};"
            ]
            
            # 添加认证
            user = self.config.get('user', '')
            password = self.config.get('password', '')
            if user and password:
                cmd.extend(['-u', user, '-p', password])
            
            # 执行备份并重定向到文件
            with open(output_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600
                )
            
            if result.returncode == 0:
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    logger.info(f'Keyspace {database} 备份成功: {self._format_size(file_size)}')
                    return True
                else:
                    logger.error(f'备份文件未生成: {output_file}')
                    return False
            else:
                logger.error(f'cqlsh 执行失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f'备份超时: {database}')
            return False
        except Exception as e:
            logger.error(f'备份异常: {e}')
            return False
```

### 步骤 2: 注册插件

在 `app/plugins/__init__.py` 中导入并导出新插件：

```python
from app.plugins.cassandra import CassandraPlugin

__all__ = [
    'DatabasePlugin',
    'PostgreSQLPlugin',
    'MySQLPlugin',
    'MariaDBPlugin',
    'MongoDBPlugin',
    'RedisPlugin',
    'CassandraPlugin',  # 添加新插件
]
```

### 步骤 3: 集成到备份管理器

在 `app/backup_manager.py` 的 `_init_plugins()` 方法中添加初始化逻辑：

```python
def _init_plugins(self) -> List:
    plugins = []
    
    # ... 其他插件 ...
    
    # Cassandra
    if self.config.cassandra_enabled:
        cassandra_config = self.config.get_database_config('cassandra')
        plugins.append(CassandraPlugin(cassandra_config, self.config.temp_dir))
        logger.info('Cassandra 插件已启用')
    
    return plugins
```

### 步骤 4: 添加配置支持

在 `app/config.py` 的 `Config` 类中添加相应的环境变量：

```python
class Config:
    def __init__(self):
        # ... 其他配置 ...
        
        # Cassandra 配置
        self.cassandra_enabled = os.getenv('CASSANDRA_ENABLED', 'false').lower() == 'true'
        self.cassandra_host = os.getenv('CASSANDRA_HOST', 'localhost')
        self.cassandra_port = int(os.getenv('CASSANDRA_PORT', '9042'))
        self.cassandra_user = os.getenv('CASSANDRA_USER', '')
        self.cassandra_password = os.getenv('CASSANDRA_PASSWORD', '')
        self.cassandra_databases = os.getenv('CASSANDRA_DATABASES', 'all')
        self.cassandra_extra_opts = os.getenv('CASSANDRA_EXTRA_OPTS', '')
```

### 步骤 5: 更新 Dockerfile

如果新数据库需要额外的客户端工具，在 `Dockerfile` 中安装：

```dockerfile
# 安装 Cassandra 客户端
RUN apt-get update && apt-get install -y \
    cassandra-tools \
    && rm -rf /var/lib/apt/lists/*
```

## 最佳实践

### 1. 错误处理

```python
try:
    # 执行备份操作
    result = subprocess.run(cmd, ...)
    
    if result.returncode == 0:
        # 验证文件是否生成
        if os.path.exists(output_file):
            logger.info(f'备份成功')
            return True
    else:
        logger.error(f'命令执行失败: {result.stderr}')
        return False
        
except subprocess.TimeoutExpired:
    logger.error('备份超时')
    return False
except Exception as e:
    logger.error(f'备份异常: {e}')
    return False
```

### 2. 日志记录

- 使用 `logger.info()` 记录正常流程
- 使用 `logger.warning()` 记录警告信息
- 使用 `logger.error()` 记录错误信息
- 使用 `logger.debug()` 记录调试信息

### 3. 超时设置

为防止命令挂起，始终设置超时：

```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=3600  # 1小时超时
)
```

### 4. 系统数据库过滤

在 `get_databases()` 中过滤系统数据库：

```python
system_dbs = ['system', 'admin', 'information_schema']
databases = [db for db in all_dbs if db not in system_dbs]
```

### 5. 文件大小格式化

使用继承的 `_format_size()` 方法：

```python
file_size = os.path.getsize(output_file)
logger.info(f'备份成功: {self._format_size(file_size)}')
```

## 测试新插件

### 1. 单元测试

创建测试文件 `tests/test_cassandra_plugin.py`：

```python
import pytest
from app.plugins.cassandra import CassandraPlugin

def test_cassandra_plugin():
    config = {
        'enabled': True,
        'host': 'localhost',
        'port': 9042,
        'databases': 'test_keyspace'
    }
    
    plugin = CassandraPlugin(config)
    
    assert plugin.db_type == 'cassandra'
    assert plugin.is_enabled() == True
    assert 'test_keyspace' in plugin.get_databases()
```

### 2. 集成测试

使用 Docker Compose 测试：

```yaml
version: '3.8'

services:
  cassandra:
    image: cassandra:latest
    container_name: test-cassandra
    environment:
      CASSANDRA_CLUSTER_NAME: "TestCluster"
    networks:
      - test-network
  
  db-backup:
    build: .
    environment:
      CASSANDRA_ENABLED: "true"
      CASSANDRA_HOST: "cassandra"
      CASSANDRA_DATABASES: "all"
      BACKUP_ON_START: "true"
    volumes:
      - ./rclone.conf:/config/rclone.conf:ro
    networks:
      - test-network
    depends_on:
      - cassandra

networks:
  test-network:
```

## 环境变量命名规范

遵循以下命名规范：

- `{DATABASE}_ENABLED` - 是否启用
- `{DATABASE}_HOST` - 主机地址
- `{DATABASE}_PORT` - 端口
- `{DATABASE}_USER` - 用户名
- `{DATABASE}_PASSWORD` - 密码
- `{DATABASE}_DATABASES` - 数据库列表或 `all`
- `{DATABASE}_EXTRA_OPTS` - 额外参数

## 常见问题

### Q: 如何处理需要认证的数据库？

A: 在命令中添加认证参数，参考 MongoDB 和 Redis 插件的实现。

### Q: 如何处理导出目录而非单文件？

A: 参考 MongoDB 插件，使用 `zipfile` 将目录打包成 ZIP 文件。

### Q: 如何备份特殊对象（如存储过程、触发器）？

A: 参考 PostgreSQL 的 `backup_extra()` 方法，在单独的方法中处理。

### Q: 如何处理大型数据库的备份超时？

A: 调整 `timeout` 参数，或使用数据库的增量备份功能。

## 贡献指南

开发完新插件后：

1. 确保代码包含详细的中文注释
2. 添加单元测试
3. 更新 README.md 文档
4. 在 examples/ 目录添加使用示例
5. 提交 Pull Request

## 参考资源

- [PostgreSQL 插件](app/plugins/postgresql.py) - 完整示例，包含全局对象备份
- [MySQL 插件](app/plugins/mysql.py) - 简单直接的实现
- [MongoDB 插件](app/plugins/mongodb.py) - 处理目录结构的示例
- [Redis 插件](app/plugins/redis.py) - 备份整个实例的示例

## 需要帮助？

如有问题，请提交 [Issue](https://github.com/yourusername/db-backup-helper/issues)。
