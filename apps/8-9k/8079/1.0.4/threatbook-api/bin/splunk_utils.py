#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Splunk 工具类
提供Splunk连接、配置读取等通用功能
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import splunklib.client as client

from config_reader import read_configuration
from logger_utils import get_logger

logger = get_logger()

class SplunkUtils:
    """Splunk工具类"""

    @staticmethod
    def connect_to_splunk() -> client.Service:
        """连接到 Splunk 服务

        Returns:
            client.Service: Splunk服务连接对象

        Raises:
            SystemExit: 连接失败时退出程序
        """
        # 从配置文件读取配置
        config = read_configuration()
        logger.debug(f"读取到的配置: {config}")

        search_head_url = config.get('search_head_url', '')
        token = config.get('token', '')

        if not search_head_url:
            logger.error("请在 my.conf 配置文件中设置 search_head_url")
            sys.exit(1)

        if not token:
            logger.error("请在 my.conf 配置文件中设置 token")
            sys.exit(1)

        # 解析 search_head_url，支持多个地址用分号分隔
        host_port_list = search_head_url.strip().split(';')

        # 尝试连接第一个可用的地址
        for host_port in host_port_list:
            try:
                host_port = host_port.strip()
                if ':' not in host_port:
                    logger.error("search_head_url 格式错误，应包含端口号: %s", host_port)
                    continue

                host, port = host_port.split(':', 1)
                port = int(port)

                logger.debug("连接 Splunk: %s:%s", host, port)
                service = client.connect(host=host, port=port, token=token)
                logger.debug("连接成功！")
                return service
            except Exception as e:
                logger.warning("连接 %s:%s 失败: %s", host, port, e)
                continue

        logger.error("所有 Splunk 地址连接失败")
        sys.exit(1)

    @staticmethod
    def get_splunk_config() -> dict:
        """获取Splunk配置

        Returns:
            dict: 配置字典
        """
        return read_configuration()

    @staticmethod
    def get_search_head_url() -> str:
        """获取Search Head URL

        Returns:
            str: Search Head URL
        """
        config = read_configuration()
        return config.get('search_head_url', '')

    @staticmethod
    def get_token() -> str:
        """获取Token

        Returns:
            str: Token
        """
        config = read_configuration()
        return config.get('token', '')

    @staticmethod
    def get_index_master_url() -> str:
        """获取Index Master URL

        Returns:
            str: Index Master URL
        """
        config = read_configuration()
        return config.get('index_master_url', '')

    @staticmethod
    def get_hec_token() -> str:
        """获取HEC Token

        Returns:
            str: HEC Token
        """
        config = read_configuration()
        return config.get('hec_token', '')

    @staticmethod
    def test_connection() -> bool:
        """测试Splunk连接

        Returns:
            bool: 连接是否成功
        """
        try:
            service = SplunkUtils.connect_to_splunk()
            if service:
                logger.info("Splunk连接测试成功")
                return True
        except Exception as e:
            logger.error(f"Splunk连接测试失败: {e}")
        return False

# 向后兼容的函数接口
def connect_to_splunk() -> client.Service:
    """连接到Splunk服务（向后兼容函数）"""
    return SplunkUtils.connect_to_splunk()

def get_splunk_config() -> dict:
    """获取Splunk配置（向后兼容函数）"""
    return SplunkUtils.get_splunk_config()

def test_splunk_connection() -> bool:
    """测试Splunk连接（向后兼容函数）"""
    return SplunkUtils.test_connection()
