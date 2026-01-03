#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
从环境变量读取配置并提供统一的配置接口
"""

import os
from typing import Optional


class Config:
    """配置管理类"""
    
    def __init__(self):
        """从环境变量初始化配置"""
        
        # 通用配置
        self.backup_cron = os.getenv('BACKUP_CRON', '0 2 * * *')
        self.backup_encrypt = os.getenv('BACKUP_ENCRYPT', 'false').lower() == 'true'
        self.backup_password = os.getenv('BACKUP_PASSWORD', '')
        self.backup_retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '7'))
        self.rclone_remote = os.getenv('RCLONE_REMOTE', 'backup')
        self.rclone_config = os.getenv('RCLONE_CONFIG', '/config/rclone.conf')
        self.rclone_insecure_skip_verify = os.getenv('RCLONE_INSECURE_SKIP_VERIFY', 'false').lower() == 'true'
        self.backup_on_start = os.getenv('BACKUP_ON_START', 'false').lower() == 'true'
        self.timezone = os.getenv('TZ', 'UTC')
        
        # Webhook 配置
        self.webhook_url = os.getenv('WEBHOOK_URL', '')
        self.webhook_method = os.getenv('WEBHOOK_METHOD', 'POST').upper()
        self.webhook_type = os.getenv('WEBHOOK_TYPE', 'generic').lower()
        
        # Message Pusher 配置
        self.message_pusher_token = os.getenv('MESSAGE_PUSHER_TOKEN', '')
        self.message_pusher_channel = os.getenv('MESSAGE_PUSHER_CHANNEL', '')
        
        # PostgreSQL 配置
        self.postgresql_enabled = os.getenv('POSTGRESQL_ENABLED', 'false').lower() == 'true'
        self.postgresql_host = os.getenv('POSTGRESQL_HOST', 'localhost')
        self.postgresql_port = int(os.getenv('POSTGRESQL_PORT', '5432'))
        self.postgresql_user = os.getenv('POSTGRESQL_USER', 'postgres')
        self.postgresql_password = os.getenv('POSTGRESQL_PASSWORD', '')
        self.postgresql_databases = os.getenv('POSTGRESQL_DATABASES', 'all')
        self.postgresql_extra_opts = os.getenv('POSTGRESQL_EXTRA_OPTS', '')
        
        # MySQL 配置
        self.mysql_enabled = os.getenv('MYSQL_ENABLED', 'false').lower() == 'true'
        self.mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        self.mysql_port = int(os.getenv('MYSQL_PORT', '3306'))
        self.mysql_user = os.getenv('MYSQL_USER', 'root')
        self.mysql_password = os.getenv('MYSQL_PASSWORD', '')
        self.mysql_databases = os.getenv('MYSQL_DATABASES', 'all')
        self.mysql_extra_opts = os.getenv('MYSQL_EXTRA_OPTS', '')
        
        # MariaDB 配置
        self.mariadb_enabled = os.getenv('MARIADB_ENABLED', 'false').lower() == 'true'
        self.mariadb_host = os.getenv('MARIADB_HOST', 'localhost')
        self.mariadb_port = int(os.getenv('MARIADB_PORT', '3306'))
        self.mariadb_user = os.getenv('MARIADB_USER', 'root')
        self.mariadb_password = os.getenv('MARIADB_PASSWORD', '')
        self.mariadb_databases = os.getenv('MARIADB_DATABASES', 'all')
        self.mariadb_extra_opts = os.getenv('MARIADB_EXTRA_OPTS', '')
        
        # MongoDB 配置
        self.mongodb_enabled = os.getenv('MONGODB_ENABLED', 'false').lower() == 'true'
        self.mongodb_host = os.getenv('MONGODB_HOST', 'localhost')
        self.mongodb_port = int(os.getenv('MONGODB_PORT', '27017'))
        self.mongodb_user = os.getenv('MONGODB_USER', '')
        self.mongodb_password = os.getenv('MONGODB_PASSWORD', '')
        self.mongodb_databases = os.getenv('MONGODB_DATABASES', 'all')
        self.mongodb_extra_opts = os.getenv('MONGODB_EXTRA_OPTS', '')
        self.mongodb_auth_db = os.getenv('MONGODB_AUTH_DB', 'admin')
        
        # Redis 配置
        self.redis_enabled = os.getenv('REDIS_ENABLED', 'false').lower() == 'true'
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_password = os.getenv('REDIS_PASSWORD', '')
        self.redis_databases = os.getenv('REDIS_DATABASES', 'all')
        
        # 临时文件目录
        self.temp_dir = '/tmp'
        
    def validate(self):
        """
        验证配置的有效性
        
        Raises:
            ValueError: 当配置无效时抛出
        """
        # 检查加密配置
        if self.backup_encrypt and not self.backup_password:
            raise ValueError('启用加密时必须设置 BACKUP_PASSWORD')
        
        # 检查 Rclone 配置文件
        if not os.path.exists(self.rclone_config):
            raise ValueError(f'Rclone 配置文件不存在: {self.rclone_config}')
        
        # 检查 Message Pusher 配置
        if self.webhook_type == 'message-pusher':
            if not self.webhook_url:
                raise ValueError('使用 message-pusher 时必须设置 WEBHOOK_URL')
            if not self.message_pusher_token:
                raise ValueError('使用 message-pusher 时必须设置 MESSAGE_PUSHER_TOKEN')
        
        # 检查是否至少启用了一个数据库
        if not any([
            self.postgresql_enabled,
            self.mysql_enabled,
            self.mariadb_enabled,
            self.mongodb_enabled,
            self.redis_enabled
        ]):
            raise ValueError('至少需要启用一个数据库备份')
    
    def get_database_config(self, db_type: str) -> dict:
        """
        获取指定数据库类型的配置
        
        Args:
            db_type: 数据库类型（postgresql, mysql, mariadb, mongodb, redis）
            
        Returns:
            数据库配置字典
        """
        prefix = db_type.lower()
        return {
            'enabled': getattr(self, f'{prefix}_enabled'),
            'host': getattr(self, f'{prefix}_host'),
            'port': getattr(self, f'{prefix}_port'),
            'user': getattr(self, f'{prefix}_user', ''),
            'password': getattr(self, f'{prefix}_password', ''),
            'databases': getattr(self, f'{prefix}_databases'),
            'extra_opts': getattr(self, f'{prefix}_extra_opts', ''),
        }


# 创建全局配置实例
config = Config()
