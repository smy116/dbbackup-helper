# 数据库备份工具 - Dockerfile
# 基于 Debian 12 构建，支持多种数据库备份
# 支持平台: linux/amd64, linux/arm64

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
    python3-requests \
    python3-dateutil \
    python3-tz \
    && rm -rf /var/lib/apt/lists/*

# 添加 PostgreSQL 官方 APT 源
RUN install -d /usr/share/postgresql-common/pgdg && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
    gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg && \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] \
    https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > \
    /etc/apt/sources.list.d/pgdg.list

# 安装非 MongoDB 的数据库客户端工具
RUN apt-get update && apt-get install -y \
    postgresql-client \
    default-mysql-client \
    mariadb-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 安装 MongoDB 工具 (使用官方二进制包，支持多架构)
RUN ARCH=$(dpkg --print-architecture) && \
    echo "Installing MongoDB tools for architecture: $ARCH" && \
    if [ "$ARCH" = "amd64" ]; then \
        # mongosh for amd64
        curl -fsSL https://downloads.mongodb.com/compass/mongosh-2.1.1-linux-x64.tgz -o /tmp/mongosh.tgz && \
        tar -xzf /tmp/mongosh.tgz -C /tmp && \
        cp /tmp/mongosh-*/bin/mongosh /usr/local/bin/ && \
        # mongodb-database-tools for amd64
        curl -fsSL https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-x86_64-100.9.4.tgz -o /tmp/mongodb-tools.tgz && \
        tar -xzf /tmp/mongodb-tools.tgz -C /tmp && \
        cp /tmp/mongodb-database-tools-*/bin/* /usr/local/bin/ ; \
    elif [ "$ARCH" = "arm64" ]; then \
        # mongosh for arm64
        curl -fsSL https://downloads.mongodb.com/compass/mongosh-2.1.1-linux-arm64.tgz -o /tmp/mongosh.tgz && \
        tar -xzf /tmp/mongosh.tgz -C /tmp && \
        cp /tmp/mongosh-*/bin/mongosh /usr/local/bin/ && \
        # mongodb-database-tools for arm64
        curl -fsSL https://fastdl.mongodb.org/tools/db/mongodb-database-tools-debian12-aarch64-100.9.4.tgz -o /tmp/mongodb-tools.tgz && \
        tar -xzf /tmp/mongodb-tools.tgz -C /tmp && \
        cp /tmp/mongodb-database-tools-*/bin/* /usr/local/bin/ ; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1 ; \
    fi && \
    rm -rf /tmp/mongosh* /tmp/mongodb*

# 安装 Rclone
RUN curl https://rclone.org/install.sh | bash

# 安装 Python 依赖（只安装系统包没有的）
RUN pip3 install --no-cache-dir --break-system-packages APScheduler pyminizip || \
    pip3 install --no-cache-dir --break-system-packages --index-url https://pypi.tuna.tsinghua.edu.cn/simple APScheduler pyminizip

# 创建工作目录
WORKDIR /app

# 复制应用程序代码
COPY app/ ./app/

# 复制启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 创建必要的目录
RUN mkdir -p /logs /tmp /config

# 设置入口点
ENTRYPOINT ["/entrypoint.sh"]
