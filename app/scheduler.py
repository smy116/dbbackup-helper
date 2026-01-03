#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度器模块
使用 APScheduler 实现定时任务调度
"""

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from app.logger import logger


class BackupScheduler:
    """备份调度器"""
    
    def __init__(self, cron_expression: str):
        """
        初始化调度器
        
        Args:
            cron_expression: Cron 表达式
        """
        self.cron_expression = cron_expression
        self.scheduler = BlockingScheduler(timezone='UTC')
        
        logger.info(f'备份调度器已初始化: {cron_expression}')
    
    def add_job(self, func, **kwargs):
        """
        添加定时任务
        
        Args:
            func: 要执行的函数
            **kwargs: 其他参数
        """
        try:
            # 解析 Cron 表达式
            trigger = CronTrigger.from_crontab(self.cron_expression)
            
            # 添加任务
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                **kwargs
            )
            
            logger.info(f'定时任务已添加: {self.cron_expression}')
            
        except Exception as e:
            logger.error(f'添加定时任务失败: {e}')
            raise
    
    def start(self):
        """启动调度器"""
        try:
            logger.info('启动调度器...')
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info('调度器已停止')
            self.shutdown()
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info('调度器已关闭')
