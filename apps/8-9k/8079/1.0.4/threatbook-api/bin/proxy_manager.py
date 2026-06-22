#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理管理模块

提供统一的代理配置管理、验证、URL构建和连接测试功能
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from urllib.parse import quote

import requests
from logger_utils import get_logger

logger = get_logger()


@dataclass
class ProxyConfig:
    """代理配置数据类"""
    enabled: bool = False
    proxy_type: str = 'HTTP'  # HTTP/HTTPS/SOCKS4/SOCKS5
    host: str = ''
    port: int = 0
    username: str = ''
    password: str = ''
    remote_dns: bool = False


class ProxyManager:
    """代理管理器 - 统一处理所有代理相关逻辑"""

    # 支持的代理类型
    SUPPORTED_TYPES = ['HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5']

    # 协议头模式（用于检测和清理）
    PROTOCOL_PATTERN = re.compile(r'^(https?|socks[45])://', re.IGNORECASE)

    @staticmethod
    def validate_config(config: ProxyConfig) -> Tuple[bool, str]:
        """验证代理配置

        Args:
            config: 代理配置对象

        Returns:
            (is_valid, error_message) - 验证结果和错误信息
        """
        # 如果代理未启用，直接通过
        if not config.enabled:
            return True, ""

        # 验证代理类型
        if config.proxy_type.upper() not in ProxyManager.SUPPORTED_TYPES:
            return False, f"Unsupported proxy type: {config.proxy_type}. Supported types: {', '.join(ProxyManager.SUPPORTED_TYPES)}"

        # 验证 Host 必填
        if not config.host or not config.host.strip():
            return False, "Proxy host is required when proxy is enabled"

        # 验证 Host 不能包含协议头
        if ProxyManager.PROTOCOL_PATTERN.match(config.host):
            return False, "Proxy host cannot contain protocol prefix (e.g., http://, https://, socks4://, socks5://)"

        # 验证 Port 必填且范围正确
        if not config.port or config.port <= 0:
            return False, "Proxy port is required when proxy is enabled"

        if config.port < 1 or config.port > 65535:
            return False, "Proxy port must be between 1 and 65535"

        # 验证用户名长度
        if config.username and len(config.username) > 100:
            return False, "Proxy username cannot exceed 100 characters"

        # 验证密码长度
        if config.password and len(config.password) > 100:
            return False, "Proxy password cannot exceed 100 characters"

        return True, ""

    @staticmethod
    def clean_host(host: str) -> str:
        """清理 Host 字段

        - 去除前后空格
        - 检查是否包含协议头（http://, https://, socks4://, socks5://），如果有则抛出异常

        Args:
            host: 原始 host 字符串

        Returns:
            清理后的 host 字符串

        Raises:
            ValueError: 如果 Host 包含协议头
        """
        if not host:
            return ''

        # 去除前后空格
        host = host.strip()

        # 检查是否包含协议头
        if ProxyManager.PROTOCOL_PATTERN.match(host):
            raise ValueError('Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.')

        return host

    @staticmethod
    def build_proxy_url(config: ProxyConfig) -> Optional[Dict[str, str]]:
        """构建代理 URL

        根据配置构建适用于 requests 库的代理 URL字典

        Args:
            config: 代理配置对象

        Returns:
            {"http": proxy_url, "https": proxy_url} 或 None（代理未启用时）
        """
        if not config.enabled:
            return None

        # 确定协议
        proxy_type = config.proxy_type.upper()

        if proxy_type == 'HTTP':
            protocol = 'http'
        elif proxy_type == 'HTTPS':
            protocol = 'http'
        elif proxy_type == 'SOCKS4':
            protocol = 'socks4'
        elif proxy_type == 'SOCKS5':
            # SOCKS5 + Remote DNS 使用 socks5h 协议
            protocol = 'socks5h' if config.remote_dns else 'socks5'
        else:
            logger.warning(f"不支持的代理类型: {proxy_type}")
            return None

        # 构建认证信息
        auth = ''
        if config.username:
            # URL 编码用户名和密码
            encoded_username = quote(config.username, safe='')
            if config.password:
                encoded_password = quote(config.password, safe='')
                auth = f"{encoded_username}:{encoded_password}@"
            else:
                auth = f"{encoded_username}@"

        # 构建完整的代理 URL
        proxy_url = f"{protocol}://{auth}{config.host}:{config.port}"

        # 返回 requests 库格式的代理字典
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    @staticmethod
    def test_connection(config: ProxyConfig, test_url: str, timeout: int = 10) -> Dict:
        """测试代理连接

        Args:
            config: 代理配置对象
            test_url: 测试目标 URL
            timeout: 超时时间（秒）

        Returns:
            成功时: {"message": "...", "latency": 120}
            失败时: {"error": "...", "title": "..."}
        """
        # 先验证配置
        is_valid, error_msg = ProxyManager.validate_config(config)
        if not is_valid:
            # 配置格式错误
            return {
                'title': 'Configuration Error',
                'error': 'Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.'
            }

        # 构建代理 URL
        proxies = ProxyManager.build_proxy_url(config)
        if not proxies:
            return {
                'title': 'Configuration Error',
                'error': 'Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.'
            }

        try:
            # 记录开始时间
            start_time = time.time()

            # 发送测试请求
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                allow_redirects=False
            )

            # 计算延迟（毫秒）
            latency = int((time.time() - start_time) * 1000)

            # 检查响应状态
            # 对于代理测试，只要能连接到目标服务器就算成功
            if response.status_code in [200, 400, 401, 403, 405]:
                return {
                    'title': 'Connection established.',
                    'message': f'Latency: {latency}ms. The proxy is working correctly.'
                }
            elif response.status_code == 407:
                # 407 表示代理认证失败
                return {
                    'title': 'Authentication Failed',
                    'error': 'The proxy server rejected the connection. Please verify your Proxy Username and Password.'
                }
            else:
                # 其他状态码归类为连接失败
                return {
                    'title': 'Connection Failed',
                    'error': 'Unable to establish a connection through the proxy. Please verify the proxy settings (Host, Port) and ensure your network allows this traffic.'
                }

        except requests.exceptions.ProxyError as e:
            logger.error(f"代理连接错误: {e}")
            error_msg = str(e).lower()
            # 检查错误信息中是否包含认证相关的关键词
            if '407' in error_msg or 'authentication' in error_msg or 'auth' in error_msg:
                return {
                    'title': 'Authentication Failed',
                    'error': 'The proxy server rejected the connection. Please verify your Proxy Username and Password.'
                }
            # 其他代理错误归类为连接失败
            return {
                'title': 'Connection Failed',
                'error': 'Unable to establish a connection through the proxy. Please verify the proxy settings (Host, Port) and ensure your network allows this traffic.'
            }

        except requests.exceptions.Timeout:
            logger.error("代理连接超时")
            return {
                'title': 'Connection Failed',
                'error': 'Unable to establish a connection through the proxy. Please verify the proxy settings (Host, Port) and ensure your network allows this traffic.'
            }

        except requests.exceptions.ConnectionError as e:
            logger.error(f"网络连接错误: {e}")
            return {
                'title': 'Connection Failed',
                'error': 'Unable to establish a connection through the proxy. Please verify the proxy settings (Host, Port) and ensure your network allows this traffic.'
            }

        except Exception as e:
            logger.error(f"测试代理连接时发生未知错误: {e}")
            return {
                'title': 'Connection Failed',
                'error': 'Unable to establish a connection through the proxy. Please verify the proxy settings (Host, Port) and ensure your network allows this traffic.'
            }

    @staticmethod
    def load_from_splunk_config(splunk_config: Dict) -> ProxyConfig:
        """从 Splunk 配置字典加载代理配置

        Args:
            splunk_config: 从 my.conf 读取的配置字典

        Returns:
            ProxyConfig 对象
        """
        # 解析 enabled（字符串转布尔）
        enabled_str = splunk_config.get('proxyEnabled', 'true').strip().lower()
        enabled = enabled_str == 'true'

        # 解析 proxy_type
        proxy_type = splunk_config.get('proxyType', 'HTTP').strip().upper()

        # 解析 host 和 port
        host = splunk_config.get('proxyHost', '').strip()
        port_str = splunk_config.get('proxyPort', '0').strip()
        try:
            port = int(port_str) if port_str else 0
        except ValueError:
            logger.warning(f"无效的代理端口: {port_str}，使用默认值 0")
            port = 0

        # 解析 username 和 password
        username = splunk_config.get('proxyUsername', '').strip()
        password = splunk_config.get('proxyPassword', '').strip()

        # 解析 remote_dns（字符串转布尔）
        remote_dns_str = splunk_config.get('proxyRemoteDNS', 'false').strip().lower()
        remote_dns = remote_dns_str == 'true'

        return ProxyConfig(
            enabled=enabled,
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            remote_dns=remote_dns
        )

    @staticmethod
    def to_splunk_config(config: ProxyConfig) -> Dict:
        """将代理配置转换为 Splunk 配置字典

        Args:
            config: ProxyConfig 对象

        Returns:
            可保存到 my.conf 的配置字典
        """
        return {
            'proxyEnabled': 'true' if config.enabled else 'false',
            'proxyType': config.proxy_type.upper(),
            'proxyHost': config.host,
            'proxyPort': str(config.port),
            'proxyUsername': config.username,
            'proxyPassword': config.password,
            'proxyRemoteDNS': 'true' if config.remote_dns else 'false'
        }

