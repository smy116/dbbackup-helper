#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库插件
使用 mysqldump 备份 MySQL 数据库
"""

import subprocess
import os
from typing import List
from app.plugins.base import DatabasePlugin
from app.logger import logger


class MySQLPlugin(DatabasePlugin):
    """MySQL 数据库插件"""
    
    @property
    def db_type(self) -> str:
        return 'mysql'
    
    def is_enabled(self) -> bool:
        return self.config.get('enabled', False)
    
    def get_databases(self) -> List[str]:
        """
        获取 MySQL 数据库列表
        如果配置为 'all'，则自动获取所有数据库（排除系统库）
        
        Returns:
            数据库名称列表
        """
        databases_config = self.config.get('databases', 'all')
        
        # 如果指定了具体数据库列表
        if databases_config != 'all':
            databases = [db.strip() for db in databases_config.split(',') if db.strip()]
            return databases
        
        # 自动获取所有数据库
        try:
            logger.info('正在获取 MySQL 数据库列表...')
            
            # 构建 mysql 命令
            cmd = [
                'mysql',
                '-h', self.config.get('host', 'localhost'),
                '-P', str(self.config.get('port', 3306)),
                '-u', self.config.get('user', 'root'),
                '-N',  # 不输出列名
                '-e', 'SHOW DATABASES;'
            ]
            
            # 添加密码（如果有）
            password = self.config.get('password', '')
            if password:
                cmd.insert(6, f'-p{password}')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 排除系统数据库
                system_dbs = ['information_schema', 'performance_schema', 'mysql', 'sys']
                databases = [
                    db.strip() 
                    for db in result.stdout.strip().split('\n') 
                    if db.strip() and db.strip() not in system_dbs
                ]
                logger.info(f'找到 {len(databases)} 个 MySQL 数据库: {", ".join(databases)}')
                return databases
            else:
                logger.error(f'获取数据库列表失败: {result.stderr}')
                return []
                
        except Exception as e:
            logger.error(f'获取数据库列表异常: {e}')
            return []
    
    def backup_database(self, database: str, output_file: str) -> bool:
        """
        备份单个 MySQL 数据库
        
        Args:
            database: 数据库名称
            output_file: 输出文件路径
            
        Returns:
            是否备份成功
        """
        try:
            # 构建 mysqldump 命令
            cmd = [
                'mysqldump',
                '-h', self.config.get('host', 'localhost'),
                '-P', str(self.config.get('port', 3306)),
                '-u', self.config.get('user', 'root'),
                '--single-transaction',  # 使用事务确保一致性
                '--routines',  # 包含存储过程和函数
                '--triggers',  # 包含触发器
                '--events',  # 包含事件
                database
            ]
            
            # 添加密码（如果有）
            password = self.config.get('password', '')
            if password:
                cmd.insert(6, f'-p{password}')
            
            # 添加额外参数
            extra_opts = self.config.get('extra_opts', '')
            if extra_opts:
                cmd.extend(extra_opts.split())
            
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
                    logger.info(f'数据库 {database} 备份成功: {self._format_size(file_size)}')
                    return True
                else:
                    logger.error(f'备份文件未生成: {output_file}')
                    return False
            else:
                logger.error(f'mysqldump 执行失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f'备份超时: {database}')
            return False
        except Exception as e:
            logger.error(f'备份异常: {e}')
            return False
