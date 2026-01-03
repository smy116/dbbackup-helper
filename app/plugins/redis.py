#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 数据库插件
使用 redis-cli 备份 Redis 数据库
"""

import subprocess
import os
import shutil
from typing import List
from app.plugins.base import DatabasePlugin
from app.logger import logger


class RedisPlugin(DatabasePlugin):
    """Redis 数据库插件"""
    
    @property
    def db_type(self) -> str:
        return 'redis'
    
    def is_enabled(self) -> bool:
        return self.config.get('enabled', False)
    
    def get_databases(self) -> List[str]:
        """
        获取 Redis 数据库列表
        Redis 使用数字编号的数据库（0-15）
        如果配置为 'all'，则备份所有数据库
        
        Returns:
            数据库编号列表
        """
        databases_config = self.config.get('databases', 'all')
        
        # 如果指定了具体数据库列表
        if databases_config != 'all':
            databases = [db.strip() for db in databases_config.split(',') if db.strip()]
            return databases
        
        # Redis 默认支持 16 个数据库（0-15）
        # 我们备份整个实例（所有数据库）
        logger.info('Redis 将备份整个实例（所有数据库）')
        return ['all']
    
    def backup_database(self, database: str, output_file: str) -> bool:
        """
        备份 Redis 数据库
        Redis 备份整个实例，使用 SAVE 命令生成 RDB 文件
        
        Args:
            database: 数据库名称（这里实际上会忽略，备份整个实例）
            output_file: 输出文件路径
            
        Returns:
            是否备份成功
        """
        try:
            logger.info('开始备份 Redis 实例...')
            
            # 构建 redis-cli 命令
            cmd = [
                'redis-cli',
                '-h', self.config.get('host', 'localhost'),
                '-p', str(self.config.get('port', 6379))
            ]
            
            # 添加密码（如果有）
            password = self.config.get('password', '')
            if password:
                cmd.extend(['-a', password])
            
            # 使用 --rdb 参数生成 RDB 文件
            temp_rdb = os.path.join(self.temp_dir, 'dump.rdb')
            cmd.extend(['--rdb', temp_rdb])
            
            # 执行备份
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600
            )
            
            # redis-cli --rdb 会等待并下载 RDB 文件
            # 检查文件是否生成
            if os.path.exists(temp_rdb):
                # 重命名为目标文件
                shutil.move(temp_rdb, output_file)
                
                file_size = os.path.getsize(output_file)
                logger.info(f'Redis 实例备份成功: {self._format_size(file_size)}')
                return True
            else:
                # 尝试使用 SAVE 命令
                logger.info('尝试使用 SAVE 命令备份...')
                return self._backup_using_save(output_file)
                
        except subprocess.TimeoutExpired:
            logger.error('备份超时')
            return False
        except Exception as e:
            logger.error(f'备份异常: {e}')
            # 尝试备用方案
            return self._backup_using_save(output_file)
    
    def _backup_using_save(self, output_file: str) -> bool:
        """
        使用 SAVE 命令备份 Redis（备用方案）
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            是否备份成功
        """
        try:
            # 构建 redis-cli 命令
            cmd = [
                'redis-cli',
                '-h', self.config.get('host', 'localhost'),
                '-p', str(self.config.get('port', 6379))
            ]
            
            # 添加密码（如果有）
            password = self.config.get('password', '')
            if password:
                cmd.extend(['-a', password])
            
            # 执行 SAVE 命令
            cmd.append('SAVE')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and 'OK' in result.stdout:
                logger.info('SAVE 命令执行成功')
                
                # 获取 Redis 数据目录和 RDB 文件名
                # 这需要查询 Redis 配置
                config_cmd = cmd[:-1] + ['CONFIG', 'GET', 'dir']
                dir_result = subprocess.run(config_cmd, capture_output=True, text=True, timeout=10)
                
                dbfilename_cmd = cmd[:-1] + ['CONFIG', 'GET', 'dbfilename']
                dbfilename_result = subprocess.run(dbfilename_cmd, capture_output=True, text=True, timeout=10)
                
                if dir_result.returncode == 0 and dbfilename_result.returncode == 0:
                    # 解析结果
                    dir_lines = dir_result.stdout.strip().split('\n')
                    dbfilename_lines = dbfilename_result.stdout.strip().split('\n')
                    
                    if len(dir_lines) >= 2 and len(dbfilename_lines) >= 2:
                        redis_dir = dir_lines[1]
                        db_filename = dbfilename_lines[1]
                        rdb_path = os.path.join(redis_dir, db_filename)
                        
                        if os.path.exists(rdb_path):
                            shutil.copy2(rdb_path, output_file)
                            file_size = os.path.getsize(output_file)
                            logger.info(f'Redis 备份成功: {self._format_size(file_size)}')
                            return True
                
                logger.warning('无法获取 RDB 文件路径，请确保有访问 Redis 数据目录的权限')
                return False
            else:
                logger.error(f'SAVE 命令执行失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'SAVE 命令执行异常: {e}')
            return False
