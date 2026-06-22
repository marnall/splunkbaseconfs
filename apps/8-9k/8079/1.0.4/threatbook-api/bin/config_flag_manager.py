#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置标志符管理工具类
提供配置更新标志的设置、获取和清除功能
标志文件存放在 var/lib/conf_updated
"""

import os
import logging
from datetime import datetime


class ConfigFlagManager:
    """配置标志符管理器"""
    
    def __init__(self, logger=None):
        """
        初始化配置标志符管理器
        
        Args:
            logger: 日志记录器，如果为None则创建默认日志记录器
        """
        self.logger = logger or self._create_default_logger()
        self._init_paths()
    
    def _create_default_logger(self):
        """创建默认日志记录器"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger
    
    def _init_paths(self):
        """初始化路径配置"""
        script_dir = os.path.dirname(os.path.abspath(__file__))  # bin/ 目录
        self.splunk_app_dir = os.path.dirname(script_dir)  # splunk/ 目录
        self.var_lib_dir = os.path.join(self.splunk_app_dir, "var", "lib")
        self.flag_file_path = os.path.join(self.var_lib_dir, "conf_updated")
    
    def set_flag(self, value="True", timestamp=True):
        """
        设置配置更新标志
        
        Args:
            value: 标志值，默认为"True"
            timestamp: 是否在标志中包含时间戳，默认为True
            
        Returns:
            bool: 设置成功返回True，失败返回False
        """
        try:
            # 确保var/lib目录存在
            os.makedirs(self.var_lib_dir, exist_ok=True)
            
            # 构建标志内容
            flag_content = value
            if timestamp:
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                flag_content = f"{value}|{current_time}"
            
            # 写入标志文件
            with open(self.flag_file_path, 'w', encoding='utf-8') as f:
                f.write(flag_content)
            
            self.logger.info(f"配置更新标志已设置: {self.flag_file_path} = {flag_content}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置配置更新标志失败: {str(e)}")
            return False
    
    def get_flag(self):
        """
        获取配置更新标志
        
        Returns:
            tuple: (flag_value, timestamp, exists) 
                   - flag_value: 标志值，如果文件不存在返回None
                   - timestamp: 时间戳，如果没有时间戳返回None
                   - exists: 标志文件是否存在
        """
        try:
            if not os.path.exists(self.flag_file_path):
                self.logger.debug(f"配置更新标志文件不存在: {self.flag_file_path}")
                return None, None, False
            
            with open(self.flag_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 解析内容，支持带时间戳和不带时间戳的格式
            if '|' in content:
                flag_value, timestamp = content.split('|', 1)
                return flag_value, timestamp, True
            else:
                return content, None, True
                
        except Exception as e:
            self.logger.error(f"获取配置更新标志失败: {str(e)}")
            return None, None, False
    
    def clear_flag(self):
        """
        清除配置更新标志
        
        Returns:
            bool: 清除成功返回True，失败返回False
        """
        try:
            if os.path.exists(self.flag_file_path):
                os.remove(self.flag_file_path)
                self.logger.info(f"配置更新标志已清除: {self.flag_file_path}")
            else:
                self.logger.debug(f"配置更新标志文件不存在，无需清除: {self.flag_file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"清除配置更新标志失败: {str(e)}")
            return False
    
    def is_flag_set(self):
        """
        检查配置更新标志是否已设置
        
        Returns:
            bool: 标志已设置返回True，否则返回False
        """
        flag_value, _, exists = self.get_flag()
        return exists and flag_value is not None
    
    def get_flag_info(self):
        """
        获取标志的详细信息
        
        Returns:
            dict: 包含标志信息的字典
        """
        flag_value, timestamp, exists = self.get_flag()
        
        return {
            'exists': exists,
            'value': flag_value,
            'timestamp': timestamp,
            'file_path': self.flag_file_path,
            'is_set': exists and flag_value is not None
        }


# 创建全局实例，方便直接使用
config_flag_manager = ConfigFlagManager()


# 便捷函数
def set_config_flag(value="True", timestamp=True):
    """设置配置更新标志的便捷函数"""
    return config_flag_manager.set_flag(value, timestamp)


def get_config_flag():
    """获取配置更新标志的便捷函数"""
    return config_flag_manager.get_flag()


def clear_config_flag():
    """清除配置更新标志的便捷函数"""
    return config_flag_manager.clear_flag()


def is_config_flag_set():
    """检查配置更新标志是否已设置的便捷函数"""
    return config_flag_manager.is_flag_set()


def get_config_flag_info():
    """获取配置标志详细信息的便捷函数"""
    return config_flag_manager.get_flag_info()
