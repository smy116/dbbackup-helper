# 数据库备份工具 - Dockerfile
# 基于 Debian 12 构建，支持多种数据库备份

FROM debian:12-slim

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 安装基础依赖和工具
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    wget \
    unzip \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# 添加 PostgreSQL 官方 APT 源
RUN install -d /usr/share/postgresql-common/pgdg && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
    gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] \
    https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > \
    /etc/apt/sources.list.d/pgdg.list

# 安装所有数据库客户端工具
RUN apt-get update && apt-get install -y \
    postgresql-client \
    mysql-client \
    mariadb-client \
    mongodb-clients \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 安装 Rclone
RUN curl https://rclone.org/install.sh | bash

# 创建工作目录
WORKDIR /app

# 复制 Python 依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

# 复制应用程序代码
COPY app/ ./app/

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建必要的目录
RUN mkdir -p /logs /tmp /config

# 设置入口点
ENTRYPOINT ["/entrypoint.sh"]
