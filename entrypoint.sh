#!/bin/bash
# 容器启动脚本

set -e

echo "========================================"
echo "数据库备份工具启动中..."
echo "========================================"

# 检查 Rclone 配置文件
if [ ! -f "/config/rclone.conf" ]; then
    echo "警告: 未找到 Rclone 配置文件 /config/rclone.conf"
    echo "请确保已挂载 Rclone 配置文件到容器"
    echo "示例: -v /path/to/rclone.conf:/config/rclone.conf"
fi

# 设置 Rclone 配置文件路径
export RCLONE_CONFIG=/config/rclone.conf

# 确保日志目录存在
mkdir -p /logs

# 确保临时文件目录存在
mkdir -p /tmp

# 显示环境信息
echo "时区: ${TZ}"
echo "备份计划: ${BACKUP_CRON:-0 2 * * *}"
echo "Rclone 远程: ${RCLONE_REMOTE:-backup}"

if [ "${BACKUP_ENCRYPT}" = "true" ]; then
    echo "加密: 已启用"
else
    echo "加密: 未启用"
fi

echo "========================================"
echo "启动备份服务..."
echo "========================================"

# 设置 Python 路径以支持模块导入
export PYTHONPATH=/app:$PYTHONPATH

# 启动主程序
exec python3 /app/app/main.py
