# 数据库备份助手 (Database Backup Helper)

[![Docker Build](https://github.com/smy116/dbbackup-helper/actions/workflows/docker-build.yml/badge.svg)](https://github.com/smy116/dbbackup-helper/actions/workflows/docker-build.yml)

一个基于 Docker 的多数据库定时备份工具，支持插件化扩展，使用 Python + Rclone 构建。

## ✨ 特性

- 🗄️ **多数据库支持** - 原生支持 PostgreSQL、MySQL、MariaDB、MongoDB、Redis
- 🔌 **插件化架构** - 易于扩展新的数据库类型
- ⏰ **灵活的定时备份** - 支持 Cron 表达式
- ☁️ **云存储同步** - 集成 Rclone，支持 40+ 种存储服务
- 🔐 **安全加密** - 支持 ZIP 密码保护
- 🧹 **自动清理** - 基于保留天数自动清理过期备份
- 📢 **Webhook 通知** - 支持通用 Webhook
- 🏗️ **多平台支持** - 支持 amd64、arm64 架构

## 📋 快速开始

### 1. 准备 Rclone 配置

创建 `rclone.conf` 文件，配置您的远程存储后端：

```ini
[backup]
type = s3
provider = AWS
access_key_id = your-access-key
secret_access_key = your-secret-key
region = us-east-1
```

更多配置示例请参考 [examples/rclone.conf.example](examples/rclone.conf.example)。

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  db-backup:
    image: ghcr.io/smy116/dbbackup-helper:latest
    container_name: db-backup
    restart: unless-stopped
    environment:
      TZ: Asia/Shanghai
      BACKUP_CRON: "0 2 * * *"  # 每天凌晨2点
      BACKUP_ENCRYPT: "true"
      BACKUP_PASSWORD: "your-secure-password"
      BACKUP_RETENTION_DAYS: "7"
      RCLONE_REMOTE: "backup"
      
      # PostgreSQL配置
      POSTGRESQL_ENABLED: "true"
      POSTGRESQL_HOST: "your-postgres-host"
      POSTGRESQL_PORT: "5432"
      POSTGRESQL_USER: "postgres"
      POSTGRESQL_PASSWORD: "your-password"
      POSTGRESQL_DATABASES: "all"
    volumes:
      - ./rclone.conf:/config/rclone.conf:ro
      - ./logs:/logs
```

### 3. 启动服务

```bash
docker-compose up -d
```

## 📚 环境变量说明

### 通用配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `TZ` | 时区设置 | `UTC` |
| `BACKUP_CRON` | Cron 表达式 | `0 2 * * *` |
| `BACKUP_ENCRYPT` | 是否加密备份 | `false` |
| `BACKUP_PASSWORD` | 加密密码 | - |
| `BACKUP_RETENTION_DAYS` | 保留天数 | `7` |
| `BACKUP_ON_START` | 启动时立即备份 | `false` |
| `RCLONE_REMOTE` | Rclone 远程名称 | `backup` |
| `RCLONE_INSECURE_SKIP_VERIFY` | 是否忽略 SSL 证书错误 | `false` |

### Webhook 通知配置

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `WEBHOOK_URL` | Webhook URL | - |
| `WEBHOOK_METHOD` | HTTP 方法 | `POST` |
| `WEBHOOK_TYPE` | 类型（`generic`/`message-pusher`） | `generic` |
| `MESSAGE_PUSHER_TOKEN` | Message Pusher 令牌 | - |
| `MESSAGE_PUSHER_CHANNEL` | Message Pusher 通道 | - |

### 数据库配置

每种数据库都有相似的配置项（以 PostgreSQL 为例）：

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `POSTGRESQL_ENABLED` | 是否启用 | `false` |
| `POSTGRESQL_HOST` | 主机地址 | `localhost` |
| `POSTGRESQL_PORT` | 端口 | `5432` |
| `POSTGRESQL_USER` | 用户名 | `postgres` |
| `POSTGRESQL_PASSWORD` | 密码 | - |
| `POSTGRESQL_DATABASES` | 数据库列表或 `all` | `all` |
| `POSTGRESQL_EXTRA_OPTS` | 额外参数 | - |

其他数据库（`MYSQL_*`、`MARIADB_*`、`MONGODB_*`、`REDIS_*`）遵循相同的命名模式。

## 🎯 使用示例

### 备份 PostgreSQL

```yaml
environment:
  POSTGRESQL_ENABLED: "true"
  POSTGRESQL_HOST: "postgres"
  POSTGRESQL_PORT: "5432"
  POSTGRESQL_USER: "postgres"
  POSTGRESQL_PASSWORD: "password"
  POSTGRESQL_DATABASES: "all"  # 备份所有数据库
  # POSTGRESQL_DATABASES: "db1,db2"  # 或指定数据库列表
```

### 备份 MySQL

```yaml
environment:
  MYSQL_ENABLED: "true"
  MYSQL_HOST: "mysql"
  MYSQL_PORT: "3306"
  MYSQL_USER: "root"
  MYSQL_PASSWORD: "password"
  MYSQL_DATABASES: "all"  # 备份所有数据库
  # MYSQL_DATABASES: "app,users"  # 或指定数据库列表
```

### 备份 MariaDB

```yaml
environment:
  MARIADB_ENABLED: "true"
  MARIADB_HOST: "mariadb"
  MARIADB_PORT: "3306"
  MARIADB_USER: "root"
  MARIADB_PASSWORD: "password"
  MARIADB_DATABASES: "all"  # 备份所有数据库
  # MARIADB_DATABASES: "website,blog"  # 或指定数据库列表
```

### 备份 MongoDB

```yaml
environment:
  MONGODB_ENABLED: "true"
  MONGODB_HOST: "mongodb"
  MONGODB_PORT: "27017"
  MONGODB_USER: "admin"
  MONGODB_PASSWORD: "password"
  MONGODB_DATABASES: "all"  # 备份所有数据库
  # MONGODB_DATABASES: "production,staging"  # 或指定数据库列表
  # MONGODB_AUTH_DB: "admin"  # 认证数据库（可选）
```

### 备份 Redis

```yaml
environment:
  REDIS_ENABLED: "true"
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  REDIS_PASSWORD: "password"  # 如果 Redis 启用了密码保护
  # REDIS_DB: "0"  # Redis 数据库编号（可选，默认为所有）
```

### 备份多个数据库

```yaml
environment:
  # PostgreSQL
  POSTGRESQL_ENABLED: "true"
  POSTGRESQL_HOST: "postgres"
  POSTGRESQL_USER: "postgres"
  POSTGRESQL_PASSWORD: "pg-password"
  POSTGRESQL_DATABASES: "all"
  
  # MySQL
  MYSQL_ENABLED: "true"
  MYSQL_HOST: "mysql"
  MYSQL_USER: "root"
  MYSQL_PASSWORD: "mysql-password"
  MYSQL_DATABASES: "app,users"  # 逗号分隔
  
  # MongoDB
  MONGODB_ENABLED: "true"
  MONGODB_HOST: "mongodb"
  MONGODB_USER: "admin"
  MONGODB_PASSWORD: "mongo-password"
  MONGODB_DATABASES: "all"
  
  # Redis
  REDIS_ENABLED: "true"
  REDIS_HOST: "redis"
  REDIS_PASSWORD: "redis-password"
```

### 使用 Message Pusher 通知

```yaml
environment:
  WEBHOOK_URL: "https://push.example.com"
  WEBHOOK_TYPE: "message-pusher"
  MESSAGE_PUSHER_TOKEN: "your-token"
  MESSAGE_PUSHER_CHANNEL: "email"
```

完整示例请参考 [examples/](examples/) 目录。

## 📁 备份文件结构

备份文件按数据库类型组织：

```
{RCLONE_REMOTE}/
├── postgresql/20260103_020000.zip
├── mysql/20260103_020000.zip
└── redis/20260103_020000.zip
```

每个 ZIP 文件包含该类型的所有数据库：

```
postgresql_20260103_020000.zip
├── myapp.sql
├── testdb.sql
└── postgresql_globals.sql  # PostgreSQL 全局对象
```

## 🔄 数据恢复方法

### PostgreSQL 恢复

1. **下载并解压备份文件**

```bash
# 使用 rclone 下载备份
rclone copy backup:postgresql/20260103_020000.zip ./

# 如果备份已加密，需要先解密
unzip -P your-password 20260103_020000.zip
```

2. **恢复全局对象（角色、权限等）**

```bash
# 恢复全局对象（需要超级用户权限）
psql -h localhost -U postgres -f postgresql_globals.sql
```

3. **恢复数据库**

```bash
# 方法1：恢复单个数据库
psql -h localhost -U postgres -d myapp -f myapp.sql

# 方法2：先创建数据库再恢复
createdb -h localhost -U postgres myapp
psql -h localhost -U postgres -d myapp -f myapp.sql
```

### MySQL 恢复

1. **下载并解压备份文件**

```bash
# 使用 rclone 下载备份
rclone copy backup:mysql/20260103_020000.zip ./

# 解压备份
unzip -P your-password 20260103_020000.zip
```

2. **恢复数据库**

```bash
# 方法1：恢复单个数据库（数据库需已存在）
mysql -h localhost -u root -p myapp < myapp.sql

# 方法2：先创建数据库再恢复
mysql -h localhost -u root -p -e "CREATE DATABASE myapp;"
mysql -h localhost -u root -p myapp < myapp.sql

# 方法3：批量恢复所有数据库
for sql_file in *.sql; do
    db_name=$(basename "$sql_file" .sql)
    mysql -h localhost -u root -p -e "CREATE DATABASE IF NOT EXISTS $db_name;"
    mysql -h localhost -u root -p $db_name < "$sql_file"
done
```

### MariaDB 恢复

MariaDB 的恢复方法与 MySQL 相同：

```bash
# 下载并解压
rclone copy backup:mariadb/20260103_020000.zip ./
unzip -P your-password 20260103_020000.zip

# 恢复单个数据库
mysql -h localhost -u root -p myapp < myapp.sql

# 或先创建数据库
mysql -h localhost -u root -p -e "CREATE DATABASE myapp;"
mysql -h localhost -u root -p myapp < myapp.sql
```

### MongoDB 恢复

1. **下载并解压备份文件**

```bash
# 使用 rclone 下载备份
rclone copy backup:mongodb/20260103_020000.zip ./

# 解压备份（会得到 mongodump 格式的目录结构）
unzip -P your-password 20260103_020000.zip
```

2. **恢复数据库**

```bash
# 方法1：恢复单个数据库
mongorestore --host localhost --port 27017 \
  --username admin --password password \
  --authenticationDatabase admin \
  --db myapp myapp/

# 方法2：恢复到不同名称的数据库
mongorestore --host localhost --port 27017 \
  --username admin --password password \
  --authenticationDatabase admin \
  --db new_myapp myapp/

# 方法3：恢复整个备份目录（多个数据库）
mongorestore --host localhost --port 27017 \
  --username admin --password password \
  --authenticationDatabase admin \
  ./
```

**注意事项：**
- 使用 `--drop` 参数会在恢复前删除现有集合
- 使用 `--nsInclude` 可以选择性恢复特定集合

### Redis 恢复

Redis 备份使用 RDB 文件格式，恢复方法如下：

1. **下载备份文件**

```bash
# 使用 rclone 下载备份
rclone copy backup:redis/20260103_020000.zip ./

# 解压获得 RDB 文件
unzip -P your-password 20260103_020000.zip
# 会得到 dump.rdb 文件
```

2. **恢复数据**

**方法1：停止 Redis 服务并替换 RDB 文件**

```bash
# 停止 Redis 服务
sudo systemctl stop redis

# 备份现有 RDB 文件（可选）
sudo cp /var/lib/redis/dump.rdb /var/lib/redis/dump.rdb.backup

# 复制备份的 RDB 文件
sudo cp dump.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb

# 启动 Redis 服务
sudo systemctl start redis
```

**方法2：使用 Docker 容器恢复**

```bash
# 创建临时目录
mkdir -p redis-data

# 复制 RDB 文件到数据目录
cp dump.rdb redis-data/

# 启动 Redis 容器，挂载数据目录
docker run -d --name redis-restore \
  -v $(pwd)/redis-data:/data \
  redis:latest

# 验证数据
docker exec -it redis-restore redis-cli
> KEYS *
> GET some_key
```

**方法3：在线恢复（使用 redis-cli --pipe）**

对于某些 Redis 版本，可以使用 AOF 格式的备份进行在线恢复，但本工具使用的是 RDB 格式，建议使用方法1或方法2。

**注意事项：**
- RDB 文件恢复会覆盖所有现有数据
- 建议在恢复前备份现有数据
- Redis 数据目录路径可能因安装方式而异，常见路径：
  - `/var/lib/redis/`
  - `/data/`（Docker）
  - 使用 `CONFIG GET dir` 查询实际路径

## 🏗️ 从源码构建

```bash
# 克隆仓库
git clone https://github.com/smy116/dbbackup-helper.git
cd dbbackup-helper

# 构建镜像
docker build -t dbbackup-helper .

# 运行
docker-compose up -d
```

### 添加新的数据库插件

1. 在 `app/plugins/` 创建新插件文件
2. 继承 `DatabasePlugin` 基类
3. 实现必需的方法
4. 在 `__init__.py` 中注册插件

## 🙏 致谢

- [Rclone](https://rclone.org/) - 云存储同步