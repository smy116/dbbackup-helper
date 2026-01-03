#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库插件包初始化
自动加载所有数据库插件
"""

from app.plugins.base import DatabasePlugin
from app.plugins.postgresql import PostgreSQLPlugin
from app.plugins.mysql import MySQLPlugin
from app.plugins.mariadb import MariaDBPlugin
from app.plugins.mongodb import MongoDBPlugin
from app.plugins.redis import RedisPlugin

__all__ = [
    'DatabasePlugin',
    'PostgreSQLPlugin',
    'MySQLPlugin',
    'MariaDBPlugin',
    'MongoDBPlugin',
    'RedisPlugin',
]
