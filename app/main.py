#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序入口
初始化配置，设置定时任务，启动备份服务
"""

import sys
from app.logger import logger, setup_logger
from app.config import config
from app.backup_manager import BackupManager
from app.scheduler import BackupScheduler
from app.webhook import send_backup_notification


def run_backup_task():
    """执行一次备份任务"""
    try:
        # 创建备份管理器
        backup_manager = BackupManager(config)
        
        # 执行备份
        results = backup_manager.run_backup()
        
        # 发送通知
        send_backup_notification(results, config)
        
        return results
        
    except Exception as e:
        logger.error(f'备份任务执行失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        raise


def main():
    """主函数"""
    try:
        logger.info('=' * 60)
        logger.info('数据库备份工具启动')
        logger.info('=' * 60)
        
        # 验证配置
        try:
            config.validate()
            logger.info('配置验证通过 ✓')
        except Exception as e:
            logger.error(f'配置验证失败: {e}')
            sys.exit(1)
        
        # 验证 Rclone 配置
        from app.rclone_manager import RcloneManager
        rclone = RcloneManager(
            config.rclone_remote, 
            config.rclone_config,
            config.rclone_insecure_skip_verify
        )
        if not rclone.verify_config():
            logger.error('Rclone 配置验证失败')
            sys.exit(1)
        
        # 如果启用了启动时立即备份
        if config.backup_on_start:
            logger.info('执行启动时立即备份...')
            run_backup_task()
        
        # 设置定时任务
        logger.info(f'设置定时备份: {config.backup_cron}')
        scheduler = BackupScheduler(config.backup_cron)
        scheduler.add_job(run_backup_task)
        
        # 启动调度器
        logger.info('定时任务已启动，等待执行...')
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info('收到中断信号，正在退出...')
        sys.exit(0)
    except Exception as e:
        logger.error(f'程序异常: {e}')
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
