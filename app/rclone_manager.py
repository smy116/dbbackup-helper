#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rclone 管理模块
封装 Rclone 命令，提供文件上传和清理功能
"""

import os
import subprocess
from datetime import datetime, timedelta
from typing import Optional
from app.logger import logger


class RcloneManager:
    """Rclone 管理类"""
    
    def __init__(self, remote: str, config_file: str = '/config/rclone.conf', 
                 insecure_skip_verify: bool = False):
        """
        初始化 Rclone 管理器
        
        Args:
            remote: Rclone 远程存储名称
            config_file: Rclone 配置文件路径
            insecure_skip_verify: 是否忽略 SSL 证书错误
        """
        self.remote = remote
        self.config_file = config_file
        self.insecure_skip_verify = insecure_skip_verify
        
        # 验证配置文件存在
        if not os.path.exists(config_file):
            raise FileNotFoundError(f'Rclone 配置文件不存在: {config_file}')
        
        logger.info(f'Rclone 管理器已初始化: remote={remote}, insecure_skip_verify={insecure_skip_verify}')
    
    def _build_base_cmd(self, command: str, *args) -> list:
        """
        构建基础的 rclone 命令，自动添加配置文件和 SSL 选项
        
        Args:
            command: rclone 子命令（如 copy, delete, ls, listremotes）
            *args: 其他命令参数
            
        Returns:
            命令列表
        """
        cmd = ['rclone', command] + list(args) + ['--config', self.config_file]
        if self.insecure_skip_verify:
            cmd.append('--no-check-certificate')
        return cmd
    
    def upload_file(self, local_file: str, remote_path: str) -> bool:
        """
        上传文件到远程存储
        
        Args:
            local_file: 本地文件路径
            remote_path: 远程路径（相对于 remote 根目录）
            
        Returns:
            是否上传成功
        """
        try:
            if not os.path.exists(local_file):
                logger.error(f'本地文件不存在: {local_file}')
                return False
            
            # 构建远程完整路径
            full_remote_path = f'{self.remote}:{remote_path}'
            
            logger.info(f'开始上传文件: {local_file} -> {full_remote_path}')
            
            # 执行 rclone copy 命令
            cmd = self._build_base_cmd('copy', local_file, full_remote_path, '-v')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )
            
            if result.returncode == 0:
                logger.info(f'文件上传成功: {full_remote_path}')
                return True
            else:
                logger.error(f'文件上传失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error('文件上传超时')
            return False
        except Exception as e:
            logger.error(f'文件上传异常: {e}')
            return False
    
    def cleanup_old_backups(self, remote_path: str, retention_days: int) -> bool:
        """
        清理远程存储中的过期备份
        
        Args:
            remote_path: 远程路径
            retention_days: 保留天数
            
        Returns:
            是否清理成功
        """
        try:
            # 构建远程完整路径
            full_remote_path = f'{self.remote}:{remote_path}'
            
            logger.info(f'开始清理过期备份: {full_remote_path}, 保留天数: {retention_days}')
            
            # 使用 rclone delete 命令删除超过指定天数的文件
            # --min-age 参数指定文件最小年龄
            cmd = self._build_base_cmd('delete', full_remote_path, '--min-age', f'{retention_days}d', '-v')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )
            
            if result.returncode == 0:
                logger.info(f'过期备份清理成功: {full_remote_path}')
                return True
            else:
                logger.warning(f'过期备份清理失败: {result.stderr}')
                return False
                
        except subprocess.TimeoutExpired:
            logger.error('清理操作超时')
            return False
        except Exception as e:
            logger.error(f'清理操作异常: {e}')
            return False
    
    def list_files(self, remote_path: str) -> Optional[str]:
        """
        列出远程路径下的文件
        
        Args:
            remote_path: 远程路径
            
        Returns:
            文件列表字符串，失败返回 None
        """
        try:
            full_remote_path = f'{self.remote}:{remote_path}'
            
            cmd = self._build_base_cmd('ls', full_remote_path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f'列出文件失败: {result.stderr}')
                return None
                
        except Exception as e:
            logger.error(f'列出文件异常: {e}')
            return None
    
    def verify_config(self) -> bool:
        """
        验证 Rclone 配置是否有效
        
        Returns:
            配置是否有效
        """
        try:
            cmd = self._build_base_cmd('listremotes')
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                remotes = result.stdout.strip().split('\n')
                remotes = [r.rstrip(':') for r in remotes if r]
                
                if self.remote in remotes:
                    logger.info(f'Rclone 配置验证成功，remote "{self.remote}" 存在')
                    return True
                else:
                    logger.error(f'Remote "{self.remote}" 在配置中不存在')
                    logger.info(f'可用的 remotes: {", ".join(remotes)}')
                    return False
            else:
                logger.error(f'Rclone 配置验证失败: {result.stderr}')
                return False
                
        except Exception as e:
            logger.error(f'Rclone 配置验证异常: {e}')
            return False
