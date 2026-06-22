# -*- coding: utf-8 -*-
"""
配置文件读取器
从Splunk配置文件中读取应用配置
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# import splunk.clilib.cli_common as cli_common

try:
    import splunk.clilib.cli_common as cli_common
except ImportError:
    # 本地开发 mock 一个假的 cli_common
    class MockCliCommon:
        def _parse_conf(self, conf_file):
            """简化的配置文件解析"""
            conf_path = os.path.join(os.path.dirname(__file__), '..', 'local', f'{conf_file}.conf')
            config = {}
            
            if os.path.exists(conf_path):
                with open(conf_path, 'r', encoding='utf-8') as f:
                    current_section = None
                    for line in f:
                        line = line.strip()
                        if line.startswith('[') and line.endswith(']'):
                            current_section = line[1:-1]
                            config[current_section] = {}
                        elif '=' in line and current_section and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            config[current_section][key.strip()] = value.strip()
            
            return config
        
        def getConfStanza(self, conf_file, stanza):
            return self._parse_conf(conf_file).get(stanza)
        
        def getMergedConf(self, conf_file):
            return self._parse_conf(conf_file)
    
    cli_common = MockCliCommon()

import logging
from logger_utils import get_logger


def read_configuration():
    """读取应用程序配置

    Returns:
        dict: 配置字典，如果读取失败返回默认配置
    """
    # 指定配置文件名称和配置节名称
    conf_file = 'my'
    stanza = 'config'
    # 使用 getMergedConf 函数读取合并配置内容
    try:
        merged_config = cli_common.getMergedConf(conf_file)

        # 从合并配置中获取指定节的配置
        if merged_config and stanza in merged_config:
            config = merged_config[stanza]
        else:
            config = None

        if config:
            return {
                'search_head_url': config.get('search_head_url', ''),
                'token': config.get('token', ''),
                'index_master_url': config.get('index_master_url', ''),
                'hec_token': config.get('hec_token', ''),
                'ip_intelligence_url': config.get('ip_intelligence_url', ''),
                'ip_intelligence_config': config.get('ip_intelligence_config', '[]'),
                'domain_intelligence_url': config.get('domain_intelligence_url', ''),
                'domain_intelligence_config': config.get('domain_intelligence_config', '[]'),
                'file_intelligence_url': config.get('file_intelligence_url', ''),
                'file_intelligence_config': config.get('file_intelligence_config', '[]'),
                'proxyType': config.get('proxyType', ''),
                'proxyHost': config.get('proxyHost', ''),
                'proxyPort': config.get('proxyPort', '')
            }
        else:
            return _get_default_config()
    except Exception as e:
        # 处理读取配置文件失败的情况
        logger = get_logger()
        logger.error(f"读取配置失败: {e}")
        return _get_default_config()


def _get_default_config():
    """获取默认配置

    Returns:
        dict: 默认配置字典
    """
    return {
        'search_head_url': '',
        'token': '',
        'index_master_url': '',
        'hec_token': '',
        'ip_intelligence_url': '',
        'ip_intelligence_config': '[]',
        'domain_intelligence_url': '',
        'domain_intelligence_config': '[]',
        'file_intelligence_url': '',
        'file_intelligence_config': '[]',
        'proxyType': '',
        'proxyHost': '',
        'proxyPort': ''
    }


def get_search_head_url():
    """获取Search Head URL

    Returns:
        str: Search Head URL
    """
    return read_configuration().get('search_head_url', '')


def get_token():
    """获取Token

    Returns:
        str: Token
    """
    return read_configuration().get('token', '')


def get_index_master_url():
    """获取Index Master URL

    Returns:
        str: Index Master URL
    """
    return read_configuration().get('index_master_url', '')


def get_hec_token():
    """获取HEC Token

    Returns:
        str: HEC Token
    """
    return read_configuration().get('hec_token', '')


def get_ip_intelligence_url():
    """获取IP情报URL

    Returns:
        str: IP情报URL
    """
    return read_configuration().get('ip_intelligence_url', '')


def get_ip_intelligence_config():
    """获取IP情报配置

    Returns:
        str: IP情报配置JSON字符串
    """
    return read_configuration().get('ip_intelligence_config', '[]')


def get_domain_intelligence_url():
    """获取域名情报URL

    Returns:
        str: 域名情报URL
    """
    return read_configuration().get('domain_intelligence_url', '')


def get_domain_intelligence_config():
    """获取域名情报配置

    Returns:
        str: 域名情报配置JSON字符串
    """
    return read_configuration().get('domain_intelligence_config', '[]')


def get_file_intelligence_url():
    """获取文件情报URL

    Returns:
        str: 文件情报URL
    """
    return read_configuration().get('file_intelligence_url', '')


def get_file_intelligence_config():
    """获取文件情报配置

    Returns:
        str: 文件情报配置JSON字符串
    """
    return read_configuration().get('file_intelligence_config', '[]')


def get_proxy_type():
    """获取代理类型

    Returns:
        str: 代理类型，可选值: http(s) 或 socks，未配置时返回空字符串
    """
    return read_configuration().get('proxyType', '')


def get_proxy_host():
    """获取代理地址

    Returns:
        str: 代理地址
    """
    return read_configuration().get('proxyHost', '')


def get_proxy_port():
    """获取代理端口

    Returns:
        str: 代理端口
    """
    return read_configuration().get('proxyPort', '')


# 向后兼容性：保留原有的类接口
class ConfigReader:
    """配置读取器（已废弃，推荐使用函数接口）"""

    def __init__(self):
        logger = get_logger()
        logger.warning("ConfigReader类已废弃，推荐直接使用read_configuration()函数")

    def get_config(self):
        """获取完整配置"""
        return read_configuration()

    def get_search_head_url(self):
        """获取Search Head URL"""
        return get_search_head_url()

    def get_token(self):
        """获取Token"""
        return get_token()

    def get_index_master_url(self):
        """获取Index Master URL"""
        return get_index_master_url()

    def get_hec_token(self):
        """获取HEC Token"""
        return get_hec_token()

    def get_ip_intelligence_url(self):
        """获取IP情报URL"""
        return get_ip_intelligence_url()

    def get_ip_intelligence_config(self):
        """获取IP情报配置"""
        return get_ip_intelligence_config()

    def get_domain_intelligence_url(self):
        """获取域名情报URL"""
        return get_domain_intelligence_url()

    def get_domain_intelligence_config(self):
        """获取域名情报配置"""
        return get_domain_intelligence_config()

    def get_file_intelligence_url(self):
        """获取文件情报URL"""
        return get_file_intelligence_url()

    def get_file_intelligence_config(self):
        """获取文件情报配置"""
        return get_file_intelligence_config()


# 全局配置读取器实例（向后兼容）
# config_reader = ConfigReader()  # 已移除，避免导入时的警告
