# 数据库备份工具 - Dockerfile
# 基于 Debian 12 构建，支持多种数据库备份
# 支持平台: linux/amd64, linux/arm64

# ============================================
# 第一阶段：下载和准备工具
# ============================================
FROM debian:12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 下载 MongoDB 工具 (只保留备份需要的工具)
# mongosh: https://github.com/mongodb-js/mongosh/releases
# mongodb-database-tools: https://www.mongodb.com/try/download/database-tools
RUN ARCH=$(dpkg --print-architecture) && \
    echo "Installing MongoDB tools for architecture: $ARCH" && \
    if [ "$ARCH" = "amd64" ]; then \
        MONGOSH_URL="https://downloads.mongodb.com/compass/mongosh-2.3.8-linux-x64.tgz" && \
        TOOLS_URL="https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2404-x86_64-100.14.0.tgz" ; \
    elif [ "$ARCH" = "arm64" ]; then \
        MONGOSH_URL="https://downloads.mongodb.com/compass/mongosh-2.3.8-linux-arm64.tgz" && \
        TOOLS_URL="https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2404-arm64-100.14.0.tgz" ; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1 ; \
    fi && \
    echo "Downloading mongosh from: $MONGOSH_URL" && \
    curl -fsSL -o /tmp/mongosh.tgz "$MONGOSH_URL" && \
    tar -xzf /tmp/mongosh.tgz -C /tmp && \
    mkdir -p /tools && \
    cp /tmp/mongosh-*/bin/mongosh /tools/ && \
    echo "Downloading mongodb-database-tools from: $TOOLS_URL" && \
    curl -fsSL -o /tmp/mongodb-tools.tgz "$TOOLS_URL" && \
    tar -xzf /tmp/mongodb-tools.tgz -C /tmp && \
    # 只保留备份需要的工具：mongodump, mongorestore
    cp /tmp/mongodb-database-tools-*/bin/mongodump /tools/ && \
    cp /tmp/mongodb-database-tools-*/bin/mongorestore /tools/ && \
    chmod +x /tools/* && \
    rm -rf /tmp/mongosh* /tmp/mongodb*

# 下载 Rclone (只获取二进制文件)
RUN ARCH=$(dpkg --print-architecture) && \
    curl -fsSL -o /tmp/rclone.zip "https://downloads.rclone.org/rclone-current-linux-${ARCH}.zip" && \
    unzip -j /tmp/rclone.zip "*/rclone" -d /tools/ && \
    chmod +x /tools/rclone && \
    rm /tmp/rclone.zip

# ============================================
# 第二阶段：最终运行镜像
# ============================================
FROM debian:12-slim

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# 添加 PostgreSQL 官方 APT 源并安装所有依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
       gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] \
       https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > \
       /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends \
       postgresql-client \
       default-mysql-client \
       mariadb-client \
       redis-tools \
       python3 \
       python3-pip \
       python3-dev \
       python3-requests \
       python3-dateutil \
       python3-tz \
       gcc \
       libc6-dev \
       zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制工具
COPY --from=builder /tools/mongosh /usr/local/bin/
COPY --from=builder /tools/mongodump /usr/local/bin/
COPY --from=builder /tools/mongorestore /usr/local/bin/
COPY --from=builder /tools/rclone /usr/local/bin/

# 安装 Python 依赖并清理构建依赖
RUN (pip3 install --no-cache-dir --break-system-packages APScheduler py7zr || \
    pip3 install --no-cache-dir --break-system-packages --index-url https://pypi.tuna.tsinghua.edu.cn/simple APScheduler py7zr) \
    && apt-get update \
    && apt-get purge -y --auto-remove gnupg gcc libc6-dev python3-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/* /tmp/*

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