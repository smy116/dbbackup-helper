#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NotifyMux 通知模块
仅在备份存在失败项时发送通知
"""

from datetime import datetime
from typing import Any, Dict, List

import requests

from app.logger import logger


SUCCESS_STATUS_CODES = {200, 201, 202, 204}


class NotifyMuxNotifier:
    """NotifyMux 通知器"""

    def __init__(self, endpoint: str, api_key: str, job_name: str):
        """
        初始化 NotifyMux 通知器

        Args:
            endpoint: NotifyMux 基础地址，例如 https://push.smy.me/
            api_key: NotifyMux API Key
            job_name: 备份任务名称
        """
        self.url = f'{endpoint.rstrip("/")}/send'
        self.api_key = api_key
        self.job_name = job_name

    def send(self, data: Dict[str, Any], timeout: int = 30) -> bool:
        """
        发送 NotifyMux 通知

        Args:
            data: 通知数据
            timeout: 请求超时时间（秒）

        Returns:
            是否发送成功
        """
        try:
            logger.info(f'发送 NotifyMux 通知到: {self.url}')
            response = requests.post(
                self.url,
                json=data,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': self.api_key,
                },
                timeout=timeout,
            )

            if response.status_code in SUCCESS_STATUS_CODES:
                logger.info(f'NotifyMux 通知发送成功: {response.status_code}')
                return True

            logger.warning(f'NotifyMux 通知响应异常: {response.status_code} - {response.text}')
            return False

        except requests.exceptions.Timeout:
            logger.error('NotifyMux 请求超时')
            return False
        except Exception as e:
            logger.error(f'NotifyMux 通知发送失败: {e}')
            return False

    def format_notification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化 NotifyMux 通知数据

        Args:
            results: 备份结果

        Returns:
            NotifyMux 请求体
        """
        success_items = self._format_success_items(results.get('success', []))
        failed_items = self._format_failed_items(results.get('failed', []))

        end_time = results.get('end_time') or datetime.now()
        start_time = results.get('start_time') or end_time
        duration_seconds = max((end_time - start_time).total_seconds(), 0)
        duration_str = self._format_duration(duration_seconds)

        is_partial_failure = bool(success_items)
        status = 'partial_failed' if is_partial_failure else 'failed'
        status_text = '部分失败' if is_partial_failure else '全部失败'
        title_status = '部分失败' if is_partial_failure else '失败'

        return {
            'title': f'[{self.job_name}] 数据库备份{title_status}',
            'body': self._format_body(
                status_text=status_text,
                start_time=start_time,
                end_time=end_time,
                duration_str=duration_str,
                success_items=success_items,
                failed_items=failed_items,
            ),
            'channelIds': [],
            'metadata': {
                'service': 'dbbackup-helper',
                'job_name': self.job_name,
                'status': status,
                'status_text': status_text,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration_seconds,
                'success_count': len(success_items),
                'failed_count': len(failed_items),
                'success': success_items,
                'failed': failed_items,
            },
        }

    def _format_body(
        self,
        status_text: str,
        start_time: datetime,
        end_time: datetime,
        duration_str: str,
        success_items: List[Dict[str, Any]],
        failed_items: List[Dict[str, Any]],
    ) -> str:
        """构建通知正文"""
        lines = [
            f'任务名称: {self.job_name}',
            f'备份状态: {status_text}',
            f'开始时间: {start_time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'结束时间: {end_time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'总耗时: {duration_str}',
            f'成功数量: {len(success_items)}',
            f'失败数量: {len(failed_items)}',
            '',
            '失败明细:',
        ]

        for item in failed_items:
            lines.append(f'- {item["type"]}: {item["error"]}')

        if success_items:
            lines.extend(['', '成功明细:'])
            for item in success_items:
                detail = f'- {item["type"]}: {item["file"]} ({item["size"]})'
                if item['databases']:
                    detail += f'，数据库: {", ".join(item["databases"])}'
                lines.append(detail)

        return '\n'.join(lines)

    @staticmethod
    def _format_success_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取成功备份的通知明细"""
        return [
            {
                'type': item.get('type', 'unknown'),
                'file': item.get('file', ''),
                'size': item.get('size', '未知大小'),
                'databases': item.get('databases', []),
            }
            for item in items
        ]

    @staticmethod
    def _format_failed_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取失败备份的通知明细"""
        return [
            {
                'type': item.get('type', 'unknown'),
                'error': item.get('error', '未知错误'),
            }
            for item in items
        ]

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化耗时"""
        if seconds < 60:
            return f'{int(seconds)}秒'
        if seconds < 3600:
            return f'{int(seconds // 60)}分{int(seconds % 60)}秒'

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f'{hours}小时{minutes}分'


def send_backup_notification(results: Dict[str, Any], config) -> bool:
    """
    发送备份失败通知

    Args:
        results: 备份结果
        config: 配置对象

    Returns:
        是否处理成功
    """
    if not results.get('failed'):
        logger.info('本次备份没有失败项，跳过 NotifyMux 通知')
        return True

    if not config.notifymux_api_key:
        logger.info('未配置 NOTIFYMUX_API_KEY，跳过 NotifyMux 通知')
        return True

    if not config.notifymux_endpoint:
        logger.error('已配置 NOTIFYMUX_API_KEY，但未配置 NOTIFYMUX_ENDPOINT')
        return False

    try:
        notifier = NotifyMuxNotifier(
            endpoint=config.notifymux_endpoint,
            api_key=config.notifymux_api_key,
            job_name=config.notifymux_job_name,
        )
        notification_data = notifier.format_notification(results)
        return notifier.send(notification_data)

    except Exception as e:
        logger.error(f'发送 NotifyMux 备份通知失败: {e}')
        return False
