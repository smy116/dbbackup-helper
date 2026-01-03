#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库插件基类
定义所有数据库插件必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import os
from datetime import datetime
from app.logger import logger


class DatabasePlugin(ABC):
    """数据库插件抽象基类"""
    
    def __init__(self, config: Dict[str, Any], temp_dir: str = '/tmp'):
        """
        初始化插件
        
        Args:
            config: 数据库配置字典
            temp_dir: 临时文件目录
        """
        self.config = config
        self.temp_dir = temp_dir
        self.enabled = config.get('enabled', False)
        
        # 确保临时目录存在
        os.makedirs(temp_dir, exist_ok=True)
    
    @property
    @abstractmethod
    def db_type(self) -> str:
        """
        数据库类型名称
        
        Returns:
            数据库类型（如 postgresql, mysql 等）
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        检查插件是否启用
        
        Returns:
            是否启用
        """
        pass
    
    @abstractmethod
    def get_databases(self) -> List[str]:
        """
        获取要备份的数据库列表
        
        Returns:
            数据库名称列表
        """
        pass
    
    @abstractmethod
    def backup_database(self, database: str, output_file: str) -> bool:
        """
        备份单个数据库
        
        Args:
            database: 数据库名称
            output_file: 输出文件路径
            
        Returns:
            是否备份成功
        """
        pass
    
    def backup_all_databases(self) -> List[str]:
        """
        备份所有数据库
        
        Returns:
            备份文件路径列表
        """
        if not self.is_enabled():
            logger.info(f'{self.db_type} 插件未启用，跳过备份')
            return []
        
        try:
            logger.info(f'开始备份 {self.db_type} 数据库')
            
            # 获取数据库列表
            databases = self.get_databases()
            
            if not databases:
                logger.warning(f'{self.db_type}: 没有找到要备份的数据库')
                return []
            
            logger.info(f'{self.db_type}: 找到 {len(databases)} 个数据库')
            
            # 备份每个数据库
            backup_files = []
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for db in databases:
                # 生成输出文件路径
                output_file = os.path.join(self.temp_dir, f'{db}.sql')
                
                logger.info(f'备份数据库: {db}')
                
                # 执行备份
                if self.backup_database(db, output_file):
                    backup_files.append(output_file)
                    logger.info(f'数据库备份成功: {db}')
                else:
                    logger.error(f'数据库备份失败: {db}')
            
            # 执行额外的备份任务（如 PostgreSQL 的 globals）
            extra_files = self.backup_extra()
            if extra_files:
                backup_files.extend(extra_files)
            
            logger.info(f'{self.db_type} 备份完成，共 {len(backup_files)} 个文件')
            return backup_files
            
        except Exception as e:
            logger.error(f'{self.db_type} 备份失败: {e}')
            raise
    
    def backup_extra(self) -> List[str]:
        """
        备份额外的数据（如 PostgreSQL 的全局对象）
        子类可以重写此方法
        
        Returns:
            额外备份文件路径列表
        """
        return []
    
    def _generate_timestamp(self) -> str:
        """
        生成时间戳字符串
        
        Returns:
            时间戳字符串（格式：YYYYMMDD_HHMMSS）
        """
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _format_size(self, size_bytes: int) -> str:
        """
        格式化文件大小
        
        Args:
            size_bytes: 字节大小
            
        Returns:
            格式化后的大小字符串
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.2f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.2f} TB'
