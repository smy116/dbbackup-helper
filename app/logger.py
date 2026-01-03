#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的日志接口，支持控制台和文件输出
日志文件按年月分割（格式：YYYYMM.log）
"""

import logging
import os
from datetime import datetime
from logging.handlers import BaseRotatingHandler


class MonthlyRotatingFileHandler(BaseRotatingHandler):
    """按月轮换的日志文件处理器"""
    
    def __init__(self, log_dir='/logs', encoding='utf-8'):
        """
        初始化处理器
        
        Args:
            log_dir: 日志目录路径
            encoding: 文件编码
        """
        self.log_dir = log_dir
        self.encoding = encoding
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        # 获取当前日志文件路径
        filename = self._get_current_log_file()
        
        # 调用父类初始化
        BaseRotatingHandler.__init__(self, filename, 'a', encoding=encoding, delay=False)
    
    def _get_current_log_file(self):
        """
        获取当前月份的日志文件路径
        
        Returns:
            日志文件的完整路径
        """
        current_month = datetime.now().strftime('%Y%m')
        return os.path.join(self.log_dir, f'{current_month}.log')
    
    def shouldRollover(self, record):
        """
        判断是否需要切换日志文件（当月份变化时）
        
        Args:
            record: 日志记录
            
        Returns:
            是否需要切换文件
        """
        current_log_file = self._get_current_log_file()
        return self.baseFilename != current_log_file
    
    def doRollover(self):
        """执行日志文件切换"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # 更新到新的日志文件
        self.baseFilename = self._get_current_log_file()
        self.stream = self._open()


def setup_logger(name='db-backup', level=logging.INFO, log_dir='/logs'):
    """
    配置并返回日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_dir: 日志目录
        
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（按月轮换）
    try:
        file_handler = MonthlyRotatingFileHandler(log_dir=log_dir)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f'无法创建文件日志处理器: {e}')
    
    return logger


# 创建默认日志记录器
logger = setup_logger()
