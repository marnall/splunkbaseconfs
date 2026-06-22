#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreatBook 情报API处理器
处理不同情报类型的API调用和数据转换
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from queue import Queue
from typing import Dict, List, Optional

import requests

from logger_utils import get_logger
from cache_manager import cache_manager
from config_reader import read_configuration
from proxy_manager import ProxyManager, ProxyConfig

logger = get_logger()

class IntelligenceType(Enum):
    """情报类型枚举"""
    IP = "ip_intelligence"
    DOMAIN = "domain_intelligence"
    FILE = "file_intelligence"

class IntelligenceAPIHandler:
    """情报API处理器"""

    def __init__(self):
        self.user_agent = 'ThreatBook-Splunk-App/1.0.3'
        self.timeout = 30
        self.cache_manager = cache_manager
        self.max_workers = 20  # 最大并发线程数
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        })

    def _get_proxy_config(self) -> Optional[Dict[str, str]]:
        """获取代理配置
        
        调用 ProxyManager 加载并构建代理配置。
        
        Returns:
            dict: 代理配置字典 {"http": proxy_url, "https": proxy_url}
            None: 代理未启用或配置无效时返回 None
        """
        try:
            config = read_configuration()
            proxy_config = ProxyManager.load_from_splunk_config(config)
            
            if not proxy_config.enabled:
                logger.debug("代理未启用")
                return None
            
            # 验证配置有效性
            is_valid, error_msg = ProxyManager.validate_config(proxy_config)
            if not is_valid:
                logger.warning(f"代理配置无效: {error_msg}，将不使用代理")
                return None
            
            # 构建代理 URL
            proxy_url_dict = ProxyManager.build_proxy_url(proxy_config)
            
            if proxy_url_dict:
                # 使用 **** 遮蔽密码，避免日志泄露
                masked_username = proxy_config.username if proxy_config.username else ''
                logger.info(f"使用代理: {proxy_config.proxy_type}://{masked_username}@{proxy_config.host}:{proxy_config.port}" if masked_username else f"使用代理: {proxy_config.proxy_type}://{proxy_config.host}:{proxy_config.port}")
            
            return proxy_url_dict
            
        except Exception as e:
            logger.error(f"获取代理配置失败: {e}")
            return None

    def _make_http_request(self, url: str, params: Dict[str, str]) -> Optional[Dict]:
        """
        使用 requests 发送 GET 请求
        只有返回 200 状态码的响应才会返回结果，其他状态码返回 None

        Args:
            url: 完整的 API URL
            params: 查询参数

        Returns:
            dict: 解析后的 JSON 响应（仅当状态码为 200 时）
            None: 当状态码不是 200 时返回 None
        """
        try:
            # 每次请求时动态获取代理配置
            proxies = self._get_proxy_config()

            # 发送 GET 请求
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                proxies=proxies if proxies else None
            )

            # 明确检查状态码，只有 200 才处理
            if response.status_code == 200:
                # 解析 JSON
                result = response.json()
                return result
            else:
                # 非 200 状态码，记录日志但不抛出异常
                logger.warning(f"API请求返回非200状态码: {response.status_code}, URL: {url}, 参数: {params}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP请求失败: {e}")
            return None
        except Exception as e:
            logger.error(f"HTTP请求处理失败: {e}")
            return None


    def _query_single_resource(self, resource_tuple: tuple, api_url: str, apikey: str,
                              results_queue: Queue, output_index: str, resource_type: str) -> None:
        """
        查询单个资源的工作函数（用于多线程）

        Args:
            resource_tuple: (resource, dest_ip) 元组
            api_url: API地址
            apikey: API密钥
            results_queue: 线程安全的结果队列
            output_index: 输出索引
            resource_type: 资源类型 ('ip', 'domain', 'file')
        """
        if not resource_tuple or len(resource_tuple) == 0:
            return

        resource = resource_tuple[0]
        dest_ip = resource_tuple[1] if len(resource_tuple) > 1 else ''

        # 验证资源有效性
        if not self._is_valid_resource(resource, resource_type):
            return

        try:
            # 调用API（缓存检查已在主方法中完成）
            logger.debug(f"调用API查询: {resource}")

            # 构建API请求
            params = {'apikey': apikey, 'resource': resource}
            api_endpoint = f"{api_url}/v2/{resource_type}/query"

            # 发送请求并处理结果
            result = self._make_http_request(api_endpoint, params)

            # 只有返回 200 状态码（result 不为 None）时才缓存并收集结果
            if result is not None:
                logger.info(f"API响应: 请求资源{resource}, 响应结果{result}")

                # 将结果存入缓存
                cache_manager.set(resource, resource_type, result)

                # 创建payload并加入结果队列
                payload = self._create_payload(resource_type, result, resource, dest_ip, output_index)
                results_queue.put(payload)

                logger.debug(f"{resource_type.upper()}情报查询成功: {resource}")
            else:
                logger.warning(f"{resource_type.upper()}情报API请求返回非200状态码，跳过缓存和结果收集: {resource}")

        except Exception as e:
            logger.error(f"{resource_type.upper()}情报API请求失败 ({resource}): {e}")

    def _is_valid_resource(self, resource: str, resource_type: str) -> bool:
        """验证资源有效性"""
        if resource_type == 'ip':
            return self._is_valid_ip(resource)
        elif resource_type == 'domain':
            return self._is_valid_domain(resource)
        elif resource_type == 'file':
            return self._is_valid_hash(resource)
        return False

    def call_intelligence_api(self, intelligence_type: IntelligenceType, api_url: str,
                            apikey: str, fields: List[tuple], output_index: str) -> List[Dict]:
        """调用情报API

        Args:
            intelligence_type: 情报类型
            api_url: API地址
            apikey: API密钥
            fields: 要查询的字段列表，每个元素是一个元组，包含资源和dest_ip

        Returns:
            API返回的结果列表
        """
        try:
            if not fields:
                logger.warning(f"{intelligence_type.value} 没有要查询的字段")
                return []

            # 根据情报类型选择不同的处理方式
            results_queue = Queue()
            resource_type_map = {
                IntelligenceType.IP: 'ip',
                IntelligenceType.DOMAIN: 'domain',
                IntelligenceType.FILE: 'file'
            }

            resource_type = resource_type_map.get(intelligence_type)
            if not resource_type:
                logger.error(f"不支持的情报类型: {intelligence_type}")
                return []

            return self._call_intelligence_api_concurrent(api_url, apikey, fields, results_queue, output_index, resource_type)

        except Exception as e:
            logger.error(f"调用情报API失败: {e}")
            return []

    def _call_intelligence_api_concurrent(self, api_url: str, apikey: str, resource_list: List[tuple],
                                         results_queue: Queue, output_index: str, resource_type: str) -> List[Dict]:
        """并发调用情报API的通用方法"""
        try:
            logger.debug(f"开始并发查询 {len(resource_list)} 个{resource_type.upper()}情报")

            # 先检查缓存，分离需要查询和已缓存的数据
            cached_results = []
            resources_to_query = []

            for resource_tuple in resource_list:
                resource = resource_tuple[0]

                # 检查缓存
                cached_data = self.cache_manager.get(resource, resource_type)
                if cached_data:
                    # 缓存命中，直接构造结果
                    result = self._construct_result_from_cache(resource_tuple, cached_data, output_index, resource_type)
                    cached_results.append(result)
                    logger.debug(f"缓存命中: {resource}")
                else:
                    # 缓存未命中，需要查询
                    resources_to_query.append(resource_tuple)
                    logger.debug(f"缓存未命中: {resource}")

            # 将缓存结果放入队列
            for result in cached_results:
                results_queue.put(result)

            # 如果有需要查询的资源，使用线程池执行并发查询
            if resources_to_query:
                logger.info(f"缓存命中 {len(cached_results)} 个，需要查询 {len(resources_to_query)} 个")

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有需要查询的任务
                    future_to_resource = {
                        executor.submit(self._query_single_resource, resource_tuple, api_url, apikey,
                                      results_queue, output_index, resource_type): resource_tuple
                        for resource_tuple in resources_to_query
                    }

                    # 等待所有任务完成
                    for future in as_completed(future_to_resource):
                        resource_tuple = future_to_resource[future]
                        try:
                            future.result()  # 获取结果，如果有异常会抛出
                        except Exception as e:
                            resource = resource_tuple[0] if resource_tuple else "unknown"
                            logger.error(f"{resource_type.upper()}查询任务失败 ({resource}): {e}")
            else:
                logger.info(f"所有 {len(resource_list)} 个资源都命中缓存，无需查询")

            # 从队列中收集所有结果
            results = self._collect_results_from_queue(results_queue)
            logger.info(f"{resource_type.upper()}情报查询完成，共获得 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"{resource_type.upper()}情报API并发调用失败: {e}")
            return []

    def _construct_result_from_cache(self, resource_tuple: tuple, cached_data: Dict, output_index: str, resource_type: str) -> Dict:
        """从缓存数据构造结果，使用与_create_payload相同的格式"""
        resource = resource_tuple[0]
        dest_ip = resource_tuple[1] if len(resource_tuple) > 1 else ""

        # 使用_create_payload方法构造结果，确保格式一致
        result = self._create_payload(resource_type, cached_data, resource, dest_ip, output_index)

        return result

    def _collect_results_from_queue(self, results_queue: Queue) -> List[Dict]:
        """从队列中收集所有结果"""
        results = []
        while not results_queue.empty():
            try:
                result = results_queue.get_nowait()
                results.append(result)
            except:
                break
        return results

    def _call_intelligence_api_sequential(self, api_url: str, apikey: str, resource_list: List[tuple],
                                        output_index: str, resource_type: str) -> List[Dict]:
        """顺序调用情报API的通用方法"""
        try:
            # 过滤有效资源
            valid_resources = [item[0] for item in resource_list if item and len(item) > 0 and self._is_valid_resource(item[0], resource_type)]
            if not valid_resources:
                logger.warning(f"没有有效的{resource_type}资源")
                return []

            results = []
            for resource_tuple in resource_list:
                if not resource_tuple or len(resource_tuple) == 0:
                    continue

                resource = resource_tuple[0]
                dest_ip = resource_tuple[1] if len(resource_tuple) > 1 else ''

                if not self._is_valid_resource(resource, resource_type):
                    continue

                try:
                    # 构建API请求
                    params = {'apikey': apikey, 'resource': resource}
                    api_endpoint = f"{api_url}/v2/{resource_type}/query"

                    # 发送请求并处理结果
                    result = self._make_http_request(api_endpoint, params)

                    # 只有返回 200 状态码（result 不为 None）时才缓存并收集结果
                    if result is not None:
                        # 将结果存入缓存
                        cache_manager.set(resource, resource_type, result)

                        payload = self._create_payload(resource_type, result, resource, dest_ip, output_index)
                        results.append(payload)

                        logger.info(f"{resource_type.upper()}情报查询成功: {resource}")
                    else:
                        logger.warning(f"{resource_type.upper()}情报API请求返回非200状态码，跳过缓存和结果收集: {resource}")

                except Exception as e:
                    logger.error(f"{resource_type.upper()}情报API请求失败 ({resource}): {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"{resource_type.upper()}情报API处理失败: {e}")
            return []

    def _filter_valid_resources(self, resource_list: List[str], resource_type: str) -> List[str]:
        """过滤有效资源的通用方法"""
        valid_resources = []
        for resource in resource_list:
            if resource and self._is_valid_resource(resource.strip(), resource_type):
                valid_resources.append(resource.strip())
        return list(set(valid_resources))  # 去重

    def _is_valid_ip(self, ip: str) -> bool:
        """检查IP地址是否有效"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def _is_valid_domain(self, domain: str) -> bool:
        """检查域名是否有效"""
        if not domain or len(domain) > 253:
            return False
        # 简单的域名格式检查
        if '.' not in domain or domain.startswith('.') or domain.endswith('.'):
            return False
        return True

    def _is_valid_hash(self, hash_value: str) -> bool:
        """检查哈希值是否有效"""
        if not hash_value:
            return False
        # 检查常见的哈希长度
        hash_length = len(hash_value)
        return hash_length in [32, 40, 64]  # MD5, SHA1, SHA256

    def _create_payload(self, query_type: str, result: dict, resource: str, dest_ip: str = '', output_index: str = '') -> dict:
        """
        根据查询类型和结果创建 Splunk payload（借鉴demo.py的逻辑）

        Args:
            query_type: 查询类型 ('ip', 'domain', 'file')
            result: API 返回的数据
            resource: 查询的资源值
            dest_ip: 目标IP地址（可选）

        Returns:
            dict: Splunk HEC payload
        """

        # 创建事件数据结构
        event_data = {
            "result": result
        }

        # 根据查询类型添加特定字段到 event 级别
        if query_type == "ip":
            event_data["ip"] = resource
        elif query_type == "domain":
            event_data["domain"] = resource
        elif query_type == "file":
            event_data["hash"] = resource

        # host 字段设置为 dest_ip（如果存在）
        if dest_ip:
            event_data["host"] = dest_ip

        return {
            "index": output_index,
            "sourcetype": "json",
            "event": event_data
        }



# 全局API处理器实例
api_handler = IntelligenceAPIHandler()

