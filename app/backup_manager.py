#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理器模块
协调所有数据库插件的备份过程，实现容错机制
"""

import os
import traceback
from datetime import datetime
from typing import List, Dict, Any
from app.logger import logger
from app.encryption import create_backup_archive
from app.rclone_manager import RcloneManager
from app.plugins import (
    PostgreSQLPlugin,
    MySQLPlugin,
    MariaDBPlugin,
    MongoDBPlugin,
    RedisPlugin
)


class BackupManager:
    """备份管理器"""
    
    def __init__(self, config):
        """
        初始化备份管理器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.rclone = RcloneManager(
            remote=config.rclone_remote,
            config_file=config.rclone_config
        )
        
        # 初始化所有插件
        self.plugins = self._init_plugins()
        
        logger.info(f'备份管理器已初始化，启用 {len(self.plugins)} 个插件')
    
    def _init_plugins(self) -> List:
        """
        初始化所有启用的数据库插件
        
        Returns:
            插件列表
        """
        plugins = []
        
        # PostgreSQL
        if self.config.postgresql_enabled:
            pg_config = self.config.get_database_config('postgresql')
            pg_config['auth_db'] = None  # PostgreSQL 不需要 auth_db
            plugins.append(PostgreSQLPlugin(pg_config, self.config.temp_dir))
            logger.info('PostgreSQL 插件已启用')
        
        # MySQL
        if self.config.mysql_enabled:
            mysql_config = self.config.get_database_config('mysql')
            plugins.append(MySQLPlugin(mysql_config, self.config.temp_dir))
            logger.info('MySQL 插件已启用')
        
        # MariaDB
        if self.config.mariadb_enabled:
            mariadb_config = self.config.get_database_config('mariadb')
            plugins.append(MariaDBPlugin(mariadb_config, self.config.temp_dir))
            logger.info('MariaDB 插件已启用')
        
        # MongoDB
        if self.config.mongodb_enabled:
            mongodb_config = self.config.get_database_config('mongodb')
            mongodb_config['auth_db'] = self.config.mongodb_auth_db
            plugins.append(MongoDBPlugin(mongodb_config, self.config.temp_dir))
            logger.info('MongoDB 插件已启用')
        
        # Redis
        if self.config.redis_enabled:
            redis_config = self.config.get_database_config('redis')
            plugins.append(RedisPlugin(redis_config, self.config.temp_dir))
            logger.info('Redis 插件已启用')
        
        return plugins
    
    def run_backup(self) -> Dict[str, Any]:
        """
        执行备份任务
        
        Returns:
            备份结果字典
        """
        logger.info('=' * 60)
        logger.info('开始执行备份任务')
        logger.info('=' * 60)
        
        results = {
            'success': [],
            'failed': [],
            'start_time': datetime.now(),
            'end_time': None
        }
        
        # 遍历所有插件
        for plugin in self.plugins:
            temp_files = []  # 记录临时文件
            
            try:
                logger.info(f'\n{"=" * 60}')
                logger.info(f'开始备份 {plugin.db_type}')
                logger.info(f'{"=" * 60}')
                
                # 执行备份，获取所有 SQL 文件
                sql_files = plugin.backup_all_databases()
                
                if not sql_files:
                    logger.warning(f'{plugin.db_type}: 没有生成备份文件')
                    continue
                
                temp_files.extend(sql_files)
                
                # 生成 ZIP 文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                zip_filename = f'{plugin.db_type}_{timestamp}.zip'
                zip_path = os.path.join(self.config.temp_dir, zip_filename)
                
                # 创建 ZIP 文件（加密或不加密）
                logger.info(f'打包备份文件: {zip_filename}')
                if self.config.backup_encrypt:
                    archive_file = create_backup_archive(
                        sql_files,
                        zip_path,
                        password=self.config.backup_password
                    )
                else:
                    archive_file = create_backup_archive(
                        sql_files,
                        zip_path
                    )
                
                temp_files.append(archive_file)
                
                # 上传到远程存储
                remote_path = f'{plugin.db_type}'
                logger.info(f'上传备份到远程存储: {self.config.rclone_remote}:{remote_path}')
                
                if self.rclone.upload_file(archive_file, remote_path):
                    # 清理过期备份
                    logger.info(f'清理 {self.config.backup_retention_days} 天前的过期备份')
                    self.rclone.cleanup_old_backups(remote_path, self.config.backup_retention_days)
                    
                    # 记录成功
                    file_size = os.path.getsize(archive_file)
                    results['success'].append({
                        'type': plugin.db_type,
                        'file': zip_filename,
                        'size': self._format_size(file_size),
                        'databases': [os.path.basename(f).replace('.sql', '').replace('.tar.gz', '') for f in sql_files]
                    })
                    
                    logger.info(f'{plugin.db_type} 备份成功 ✓')
                else:
                    raise Exception('上传到远程存储失败')
                
            except Exception as e:
                logger.error(f'{plugin.db_type} 备份失败: {str(e)}')
                logger.error(traceback.format_exc())
                
                results['failed'].append({
                    'type': plugin.db_type,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
            
            finally:
                # 清理临时文件
                logger.info(f'清理 {plugin.db_type} 的临时文件...')
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                            logger.debug(f'已删除: {temp_file}')
                    except Exception as e:
                        logger.warning(f'清理临时文件失败 {temp_file}: {e}')
        
        # 记录结束时间
        results['end_time'] = datetime.now()
        
        # 汇总结果
        logger.info('\n' + '=' * 60)
        logger.info('备份任务完成')
        logger.info('=' * 60)
        logger.info(f'成功: {len(results["success"])} 个')
        logger.info(f'失败: {len(results["failed"])} 个')
        logger.info(f'总耗时: {(results["end_time"] - results["start_time"]).total_seconds():.2f} 秒')
        logger.info('=' * 60)
        
        return results
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.2f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.2f} TB'
