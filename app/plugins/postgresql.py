#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据库插件
使用 pg_dump 和 pg_dumpall 备份 PostgreSQL 数据库
"""

import subprocess
import os
from typing import List
from app.plugins.base import DatabasePlugin
from app.logger import logger


class PostgreSQLPlugin(DatabasePlugin):
    """PostgreSQL 数据库插件"""
    
    @property
    def db_type(self) -> str:
        return 'postgresql'
    
    def is_enabled(self) -> bool:
        return self.config.get('enabled', False)
    
    def get_databases(self) -> List[str]:
        """
        获取 PostgreSQL 数据库列表
        如果配置为 'all'，则自动获取所有数据库
        
        Returns:
            数据库名称列表
        """
        databases_config = self.config.get('databases', 'all')
        
        # 如果指定了具体数据库列表
        if databases_config != 'all':
            # 支持逗号分隔
            databases = [db.strip() for db in databases_config.split(',') if db.strip()]
            return databases
        
        # 自动获取所有数据库
        try:
            logger.info('正在获取 PostgreSQL 数据库列表...')
            
            # 构建连接环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.get('password', '')
            
            # 使用 psql 查询数据库列表
            cmd = [
                'psql',
                '-h', self.config.get('host', 'localhost'),
                '-p', str(self.config.get('port', 5432)),
                '-U', self.config.get('user', 'postgres'),
                '-t',  # 只输出数据，不输出表头
                '-A',  # 不对齐输出
                '-c', "SELECT datname FROM pg_database WHERE datistemplate = false;"
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                databases = [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]
                logger.info(f'找到 {len(databases)} 个 PostgreSQL 数据库: {", ".join(databases)}')
                return databases
            else:
                error = result.stderr.strip() or result.stdout.strip() or f'退出码 {result.returncode}'
                logger.error(f'获取数据库列表失败: {error}')
                raise RuntimeError(f'获取数据库列表失败: {error}')
                
        except subprocess.TimeoutExpired as e:
            logger.error('获取数据库列表超时')
            raise RuntimeError('获取数据库列表超时') from e
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f'获取数据库列表异常: {e}')
            raise RuntimeError(f'获取数据库列表异常: {e}') from e
    
    def backup_database(self, database: str, output_file: str) -> bool:
        """
        备份单个 PostgreSQL 数据库
        
        Args:
            database: 数据库名称
            output_file: 输出文件路径
            
        Returns:
            是否备份成功
        """
        try:
            # 构建连接环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.get('password', '')
            
            # 构建 pg_dump 命令
            cmd = [
                'pg_dump',
                '-h', self.config.get('host', 'localhost'),
                '-p', str(self.config.get('port', 5432)),
                '-U', self.config.get('user', 'postgres'),
                '-d', database,
                '-f', output_file
            ]
            
            # 添加额外参数
            extra_opts = self.config.get('extra_opts', '')
            if extra_opts:
                cmd.extend(extra_opts.split())
            
            # 执行备份
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                # 检查文件是否生成
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    logger.info(f'数据库 {database} 备份成功: {self._format_size(file_size)}')
                    return True
                else:
                    logger.error(f'备份文件未生成: {output_file}')
                    raise RuntimeError(f'备份文件未生成: {output_file}')
            else:
                error = result.stderr.strip() or result.stdout.strip() or f'退出码 {result.returncode}'
                logger.error(f'pg_dump 执行失败: {error}')
                raise RuntimeError(f'pg_dump 执行失败: {error}')
                
        except subprocess.TimeoutExpired as e:
            logger.error(f'备份超时: {database}')
            raise RuntimeError(f'备份超时: {database}') from e
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f'备份异常: {e}')
            raise RuntimeError(f'备份异常: {e}') from e
    
    def backup_extra(self) -> List[str]:
        """
        备份 PostgreSQL 全局对象（角色、权限等）
        
        Returns:
            全局对象备份文件路径列表
        """
        try:
            logger.info('备份 PostgreSQL 全局对象...')
            
            output_file = os.path.join(self.temp_dir, 'postgresql_globals.sql')
            
            # 构建连接环境变量
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.get('password', '')
            
            # 使用 pg_dumpall --globals-only 备份全局对象
            cmd = [
                'pg_dumpall',
                '-h', self.config.get('host', 'localhost'),
                '-p', str(self.config.get('port', 5432)),
                '-U', self.config.get('user', 'postgres'),
                '--globals-only',
                '-f', output_file
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                logger.info(f'全局对象备份成功: {self._format_size(file_size)}')
                return [output_file]
            else:
                error = result.stderr.strip() or result.stdout.strip() or f'退出码 {result.returncode}'
                logger.error(f'全局对象备份失败: {error}')
                raise RuntimeError(f'全局对象备份失败: {error}')
                
        except subprocess.TimeoutExpired as e:
            logger.error('全局对象备份超时')
            raise RuntimeError('全局对象备份超时') from e
        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f'全局对象备份异常: {e}')
            raise RuntimeError(f'全局对象备份异常: {e}') from e
