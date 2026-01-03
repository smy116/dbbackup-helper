#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密模块
提供 ZIP 文件加密功能，使用密码保护
"""

import os
import zipfile
import pyminizip
from typing import List
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
    
    def create_encrypted_zip(self, files: List[str], output_file: str, compression_level: int = 5) -> str:
        """
        创建加密的 ZIP 文件
        
        Args:
            files: 要打包的文件列表
            output_file: 输出的 ZIP 文件路径
            compression_level: 压缩级别 (0-9)
            
        Returns:
            创建的 ZIP 文件路径
        """
        try:
            logger.info(f'创建加密 ZIP 文件: {output_file}')
            logger.debug(f'打包文件数量: {len(files)}')
            
            # 如果只有一个文件，使用 pyminizip
            if len(files) == 1:
                pyminizip.compress(
                    files[0],
                    None,  # 文件在 ZIP 中的路径前缀
                    output_file,
                    self.password,
                    compression_level
                )
            else:
                # 多个文件时，使用 pyminizip 的多文件压缩
                # 获取文件的基本名称（不含路径）
                file_basenames = [os.path.basename(f) for f in files]
                
                pyminizip.compress_multiple(
                    files,
                    file_basenames,
                    output_file,
                    self.password,
                    compression_level
                )
            
            # 验证文件已创建
            if not os.path.exists(output_file):
                raise Exception(f'加密 ZIP 文件创建失败: {output_file}')
            
            file_size = os.path.getsize(output_file)
            logger.info(f'加密 ZIP 文件创建成功: {output_file} ({self._format_size(file_size)})')
            
            return output_file
            
        except Exception as e:
            logger.error(f'创建加密 ZIP 文件失败: {e}')
            raise
    
    def create_zip(self, files: List[str], output_file: str) -> str:
        """
        创建普通（不加密）的 ZIP 文件
        
        Args:
            files: 要打包的文件列表
            output_file: 输出的 ZIP 文件路径
            
        Returns:
            创建的 ZIP 文件路径
        """
        try:
            logger.info(f'创建 ZIP 文件: {output_file}')
            logger.debug(f'打包文件数量: {len(files)}')
            
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    if os.path.exists(file):
                        # 使用文件的基本名称（不含路径）
                        arcname = os.path.basename(file)
                        zipf.write(file, arcname)
                        logger.debug(f'添加文件到 ZIP: {arcname}')
                    else:
                        logger.warning(f'文件不存在，跳过: {file}')
            
            # 验证文件已创建
            if not os.path.exists(output_file):
                raise Exception(f'ZIP 文件创建失败: {output_file}')
            
            file_size = os.path.getsize(output_file)
            logger.info(f'ZIP 文件创建成功: {output_file} ({self._format_size(file_size)})')
            
            return output_file
            
        except Exception as e:
            logger.error(f'创建 ZIP 文件失败: {e}')
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
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f'{size_bytes:.2f} {unit}'
            size_bytes /= 1024.0
        return f'{size_bytes:.2f} TB'


def create_backup_archive(files: List[str], output_file: str, password: str = None) -> str:
    """
    创建备份归档文件（支持加密和不加密）
    
    Args:
        files: 要打包的文件列表
        output_file: 输出的 ZIP 文件路径
        password: 加密密码（可选）
        
    Returns:
        创建的归档文件路径
    """
    if password:
        encryption = Encryption(password)
        return encryption.create_encrypted_zip(files, output_file)
    else:
        encryption = Encryption('')
        return encryption.create_zip(files, output_file)
