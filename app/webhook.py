#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook 通知模块
支持通用 Webhook 和 Message Pusher 集成
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Any
from app.logger import logger


class WebhookNotifier:
    """Webhook 通知器基类"""
    
    def __init__(self, url: str, method: str = 'POST'):
        """
        初始化通知器
        
        Args:
            url: Webhook URL
            method: HTTP 方法
        """
        self.url = url
        self.method = method.upper()
    
    def send(self, data: Dict[str, Any], timeout: int = 30) -> bool:
        """
        发送通知
        
        Args:
            data: 通知数据
            timeout: 请求超时时间（秒）
            
        Returns:
            是否发送成功
        """
        try:
            logger.info(f'发送 Webhook 通知到: {self.url}')
            
            if self.method == 'POST':
                response = requests.post(
                    self.url,
                    json=data,
                    headers={'Content-Type': 'application/json'},
                    timeout=timeout
                )
            elif self.method == 'GET':
                response = requests.get(
                    self.url,
                    params=data,
                    timeout=timeout
                )
            else:
                logger.error(f'不支持的 HTTP 方法: {self.method}')
                return False
            
            if response.status_code in [200, 201, 202, 204]:
                logger.info(f'Webhook 通知发送成功: {response.status_code}')
                return True
            else:
                logger.warning(f'Webhook 通知响应异常: {response.status_code} - {response.text}')
                return False
                
        except requests.exceptions.Timeout:
            logger.error('Webhook 请求超时')
            return False
        except Exception as e:
            logger.error(f'Webhook 发送失败: {e}')
            return False


class GenericWebhook(WebhookNotifier):
    """通用 Webhook 通知器"""
    
    def format_notification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化通知数据
        
        Args:
            results: 备份结果
            
        Returns:
            格式化后的通知数据
        """
        # 确定总体状态
        if not results['failed']:
            status = 'success'
        elif not results['success']:
            status = 'failed'
        else:
            status = 'partial_success'
        
        # 计算耗时
        duration = results.get('end_time', datetime.now()) - results['start_time']
        duration_str = self._format_duration(duration.total_seconds())
        
        return {
            'status': status,
            'start_time': results['start_time'].isoformat(),
            'end_time': results.get('end_time', datetime.now()).isoformat(),
            'duration': duration_str,
            'success': results['success'],
            'failed': results['failed']
        }
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f'{int(seconds)}s'
        elif seconds < 3600:
            return f'{int(seconds // 60)}m{int(seconds % 60)}s'
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f'{hours}h{minutes}m'


class MessagePusherWebhook(WebhookNotifier):
    """Message Pusher 通知器"""
    
    def __init__(self, url: str, token: str, channel: str = '', username: str = 'admin'):
        """
        初始化 Message Pusher 通知器
        
        Args:
            url: Message Pusher 服务 URL
            token: 推送令牌
            channel: 推送通道（可选）
            username: 用户名（默认 admin）
        """
        # 构建完整的推送 URL
        push_url = f'{url.rstrip("/")}/push/{username}'
        super().__init__(push_url, 'POST')
        self.token = token
        self.channel = channel
    
    def format_notification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化为 Message Pusher 格式
        
        Args:
            results: 备份结果
            
        Returns:
            Message Pusher 格式的通知数据
        """
        # 确定总体状态
        if not results['failed']:
            status = 'success'
            status_emoji = '✅'
            status_text = '全部成功'
        elif not results['success']:
            status = 'failed'
            status_emoji = '❌'
            status_text = '全部失败'
        else:
            status = 'partial_success'
            status_emoji = '⚠️'
            status_text = '部分成功'
        
        # 计算耗时
        duration = results.get('end_time', datetime.now()) - results['start_time']
        duration_str = self._format_duration(duration.total_seconds())
        
        # 构建 Markdown 内容
        content_lines = [
            '## 数据库备份报告',
            '',
            f'**状态**: {status_text} {status_emoji}',
            f'**开始时间**: {results["start_time"].strftime("%Y-%m-%d %H:%M:%S")}',
            f'**结束时间**: {results.get("end_time", datetime.now()).strftime("%Y-%m-%d %H:%M:%S")}',
            f'**总耗时**: {duration_str}',
            ''
        ]
        
        # 添加成功的备份
        if results['success']:
            content_lines.append('### ✅ 成功')
            for item in results['success']:
                content_lines.append(f'- **{item["type"]}**: {item["file"]} ({item.get("size", "未知大小")})')
                if 'databases' in item:
                    content_lines.append(f'  - 数据库: {", ".join(item["databases"])}')
            content_lines.append('')
        
        # 添加失败的备份
        if results['failed']:
            content_lines.append('### ❌ 失败')
            for item in results['failed']:
                content_lines.append(f'- **{item["type"]}**: {item["error"]}')
            content_lines.append('')
        
        content = '\n'.join(content_lines)
        
        # 构建 Message Pusher 请求数据
        data = {
            'title': '数据库备份通知',
            'description': f'备份状态: {status_text}',
            'content': content,
            'token': self.token
        }
        
        # 添加通道（如果指定）
        if self.channel:
            data['channel'] = self.channel
        
        return data
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f'{int(seconds)}秒'
        elif seconds < 3600:
            return f'{int(seconds // 60)}分{int(seconds % 60)}秒'
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f'{hours}小时{minutes}分'


def create_notifier(webhook_type: str, webhook_url: str, webhook_method: str = 'POST',
                   message_pusher_token: str = '', message_pusher_channel: str = '') -> WebhookNotifier:
    """
    创建通知器实例
    
    Args:
        webhook_type: Webhook 类型（generic 或 message-pusher）
        webhook_url: Webhook URL
        webhook_method: HTTP 方法
        message_pusher_token: Message Pusher 令牌
        message_pusher_channel: Message Pusher 通道
        
    Returns:
        通知器实例
    """
    if webhook_type == 'message-pusher':
        return MessagePusherWebhook(
            url=webhook_url,
            token=message_pusher_token,
            channel=message_pusher_channel
        )
    else:
        return GenericWebhook(webhook_url, webhook_method)


def send_backup_notification(results: Dict[str, Any], config) -> bool:
    """
    发送备份通知
    
    Args:
        results: 备份结果
        config: 配置对象
        
    Returns:
        是否发送成功
    """
    # 检查是否配置了 Webhook
    if not config.webhook_url:
        logger.info('未配置 Webhook URL，跳过通知')
        return True
    
    try:
        # 创建通知器
        notifier = create_notifier(
            webhook_type=config.webhook_type,
            webhook_url=config.webhook_url,
            webhook_method=config.webhook_method,
            message_pusher_token=config.message_pusher_token,
            message_pusher_channel=config.message_pusher_channel
        )
        
        # 格式化通知数据
        notification_data = notifier.format_notification(results)
        
        # 发送通知
        return notifier.send(notification_data)
        
    except Exception as e:
        logger.error(f'发送备份通知失败: {e}')
        return False
