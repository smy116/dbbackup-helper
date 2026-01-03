#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MongoDB 数据库插件
使用 mongodump 备份 MongoDB 数据库
"""

import subprocess
import os
from typing import List
from app.plugins.base import DatabasePlugin
from app.logger import logger


class MongoDBPlugin(DatabasePlugin):
    """MongoDB 数据库插件"""
    
    @property
    def db_type(self) -> str:
        return 'mongodb'
    
    def is_enabled(self) -> bool:
        return self.config.get('enabled', False)
    
    def get_databases(self) -> List[str]:
        """
        获取 MongoDB 数据库列表
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
            logger.info('正在获取 MongoDB 数据库列表...')
            
            # 构建 mongosh 命令
            cmd = [
                'mongosh',
                '--host', self.config.get('host', 'localhost'),
                '--port', str(self.config.get('port', 27017)),
                '--quiet',
                '--eval', 'db.adminCommand("listDatabases").databases.map(d => d.name).join("\\n")'
            ]
            
            # 添加认证（如果有）
            user = self.config.get('user', '')
            password = self.config.get('password', '')
            if user and password:
                auth_db = self.config.get('auth_db', 'admin')
                cmd.extend(['--username', user, '--password', password, '--authenticationDatabase', auth_db])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 排除系统数据库
                system_dbs = ['admin', 'local', 'config']
                databases = [
                    db.strip() 
                    for db in result.stdout.strip().split('\n') 
                    if db.strip() and db.strip() not in system_dbs
                ]
                logger.info(f'找到 {len(databases)} 个 MongoDB 数据库: {", ".join(databases)}')
                return databases
            else:
                logger.error(f'获取数据库列表失败: {result.stderr}')
                return []
                
        except Exception as e:
            logger.error(f'获取数据库列表异常: {e}')
            return []
    
    def backup_database(self, database: str, output_file: str) -> bool:
        """
        备份单个 MongoDB 数据库
        
        Args:
            database: 数据库名称
            output_file: 输出文件路径（实际会是一个目录）
            
        Returns:
            是否备份成功
        """
        try:
            # MongoDB 的 mongodump 会创建目录，我们需要自己管理
            # 为每个数据库创建临时目录
            dump_dir = os.path.join(self.temp_dir, f'{database}_dump')
            os.makedirs(dump_dir, exist_ok=True)
            
            # 构建 mongodump 命令
            cmd = [
                'mongodump',
                '--host', self.config.get('host', 'localhost'),
                '--port', str(self.config.get('port', 27017)),
                '--db', database,
                '--out', dump_dir
            ]
            
            # 添加认证（如果有）
            user = self.config.get('user', '')
            password = self.config.get('password', '')
            if user and password:
                auth_db = self.config.get('auth_db', 'admin')
                cmd.extend(['--username', user, '--password', password, '--authenticationDatabase', auth_db])
            
            # 添加额外参数
            extra_opts = self.config.get('extra_opts', '')
            if extra_opts:
                cmd.extend(extra_opts.split())
            
            # 执行备份
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            if result.returncode == 0:
                # mongodump 创建的是目录，需要打包成单个文件
                db_dump_path = os.path.join(dump_dir, database)
                if os.path.exists(db_dump_path):
                    # 将整个 dump 目录打包成 ZIP 文件
                    import zipfile
                    import shutil
                    
                    # 创建 ZIP 文件
                    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        # 遍历目录，将所有文件添加到 ZIP
                        for root, dirs, files in os.walk(db_dump_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # 计算相对路径
                                arcname = os.path.relpath(file_path, dump_dir)
                                zipf.write(file_path, arcname)
                    
                    # 清理临时目录
                    shutil.rmtree(dump_dir)
                    
                    file_size = os.path.getsize(output_file)
                    logger.info(f'数据库 {database} 备份成功: {self._format_size(file_size)}')
                    return True
                else:
                    logger.error(f'备份目录未生成: {db_dump_path}')
                    return False
            else:
                logger.error(f'mongodump 执行失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f'备份超时: {database}')
            return False
        except Exception as e:
            logger.error(f'备份异常: {e}')
            return False
