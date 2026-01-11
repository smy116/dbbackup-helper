#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密模块
提供 7z 文件加密功能，使用系统 7z 命令行工具
"""

import os
import subprocess
from typing import List, Optional
from app.logger import logger


class Encryption:
    """加密管理类"""

    def __init__(self, password: str):
        """
        初始化加密器

        Args:
            password: 加密密码
        """
        self.password = password

    def create_encrypted_7z(self, files: List[str], output_file: str, compression_level: int = 1) -> str:
        """
        创建加密的 7z 文件（启用文件头加密，隐藏文件名列表）

        Args:
            files: 要打包的文件列表
            output_file: 输出的 7z 文件路径
            compression_level: 压缩级别 (0-9)

        Returns:
            创建的 7z 文件路径
        """
        try:
            logger.info(f'创建加密 7z 文件: {output_file}')
            logger.debug(f'打包文件数量: {len(files)}')

            cmd = [
                '7z', 'a', '-t7z',
                f'-mx={compression_level}',
                '-m0=lzma2',
                '-mhe=on',
                f'-p{self.password}',
                '-b0',
                '-y',
                output_file
            ] + files

            subprocess.run(cmd, check=True, capture_output=True)

            if not os.path.exists(output_file):
                raise Exception(f'加密 7z 文件创建失败: {output_file}')

            file_size = os.path.getsize(output_file)
            logger.info(f'加密 7z 文件创建成功: {output_file} ({self._format_size(file_size)})')

            return output_file

        except subprocess.CalledProcessError as e:
            logger.error(f'创建加密 7z 文件失败: {e.stderr.decode() if e.stderr else str(e)}')
            raise
        except Exception as e:
            logger.error(f'创建加密 7z 文件失败: {e}')
            raise

    def create_7z(self, files: List[str], output_file: str, compression_level: int = 1) -> str:
        """
        创建普通（不加密）的 7z 文件

        Args:
            files: 要打包的文件列表
            output_file: 输出的 7z 文件路径

        Returns:
            创建的 7z 文件路径
        """
        try:
            logger.info(f'创建 7z 文件: {output_file}')
            logger.debug(f'打包文件数量: {len(files)}')

            cmd = [
                '7z', 'a', '-t7z',
                f'-mx={compression_level}',
                '-m0=lzma2',
                '-mhe=on',
                '-b0',
                '-y',
                output_file
            ] + files

            subprocess.run(cmd, check=True, capture_output=True)

            if not os.path.exists(output_file):
                raise Exception(f'7z 文件创建失败: {output_file}')

            file_size = os.path.getsize(output_file)
            logger.info(f'7z 文件创建成功: {output_file} ({self._format_size(file_size)})')

            return output_file

        except subprocess.CalledProcessError as e:
            logger.error(f'创建 7z 文件失败: {e.stderr.decode() if e.stderr else str(e)}')
            raise
        except Exception as e:
            logger.error(f'创建 7z 文件失败: {e}')
            raise

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 字节大小

        Returns:
            格式化后的大小字符串
        """
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f'{size:.2f} {unit}'
            size /= 1024.0
        return f'{size:.2f} TB'


def create_backup_archive(files: List[str], output_file: str, password: Optional[str] = None) -> str:
    """
    创建备份归档文件（支持加密和不加密）

    Args:
        files: 要打包的文件列表
        output_file: 输出的 7z 文件路径
        password: 加密密码（可选）

    Returns:
        创建的归档文件路径
    """
    if password:
        encryption = Encryption(password)
        return encryption.create_encrypted_7z(files, output_file)
    else:
        encryption = Encryption('')
        return encryption.create_7z(files, output_file)
