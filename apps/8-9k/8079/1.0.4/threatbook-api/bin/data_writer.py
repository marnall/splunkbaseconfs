#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreatBook 数据写入处理器
处理情报结果写入Splunk索引
"""

import json
from typing import Dict, List

import requests
import urllib3

import splunklib.client as client
from logger_utils import get_logger
from splunk_utils import SplunkUtils

# 抑制 InsecureRequestWarning（因为使用自签名证书）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = get_logger()


class DataWriter:
    """数据写入处理器"""

    def __init__(self, service: client.Service):
        self.service = service
        self.batch_size = 100
        self.timeout = 30

    def write_intelligence_results(self, output_index: str, results: List[Dict],
                                   intelligence_type: str, config: Dict = None) -> bool:
        """写入情报结果到指定索引

        Args:
            output_index: 输出索引名称
            results: 结果数据列表
            intelligence_type: 情报类型
            config: 配置信息，如果为None则动态获取

        Returns:
            是否写入成功
        """
        try:
            if not results:
                logger.warning(f"没有数据需要写入索引 {output_index}")
                return True

            # 获取最新配置
            if config is None:
                config = SplunkUtils.get_splunk_config()
            
            hec_token = config.get('hec_token', '')
            index_master_url = config.get('index_master_url', '')

            # 验证配置
            if not self._validate_config(hec_token, index_master_url):
                return False

            logger.debug(f"开始写入 {len(results)} 条 {intelligence_type} 结果到索引 {output_index}")
            return self._write_via_hec(output_index, results, intelligence_type, hec_token, index_master_url)

        except Exception as e:
            logger.error(f"写入情报结果失败: {e}")
            return False

    def _validate_config(self, hec_token: str, index_master_url: str) -> bool:
        """验证HEC配置"""
        if not hec_token:
            logger.error("HEC Token 未配置，无法写入数据")
            return False

        if not index_master_url:
            logger.error("Index Master URL 未配置，无法写入数据")
            return False

        return True

    def _write_via_hec(self, output_index: str, results: List[Dict],
                       intelligence_type: str, hec_token: str, index_master_url: str) -> bool:
        """通过HEC写入数据"""
        try:
            hec_url = f"https://{index_master_url}/services/collector"
            success_count = 0

            # 批量发送数据
            for i in range(0, len(results), self.batch_size):
                batch = results[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1

                # 构建HEC格式的数据
                payload = self._build_hec_payload(batch)

                # 发送请求
                if self._send_hec_request(hec_url, payload, hec_token):
                    success_count += len(batch)
                    logger.debug(f"HEC写入成功: 批次 {batch_num}, {len(batch)} 条记录")
                else:
                    logger.error(f"HEC写入失败: 批次 {batch_num}")

            logger.info(f"HEC写入完成: {success_count}/{len(results)} 条记录")
            return success_count == len(results)

        except Exception as e:
            logger.error(f"HEC写入失败: {e}")
            return False

    def _build_hec_payload(self, batch: List[Dict]) -> str:
        """构建HEC格式的载荷"""
        return '\n'.join(json.dumps(result) for result in batch)

    def _send_hec_request(self, url: str, payload: str, hec_token: str) -> bool:
        """发送HEC请求

        Args:
            url: HEC URL
            payload: 请求数据
            hec_token: HEC Token

        Returns:
            bool: 是否成功
        """
        try:
            headers = {
                "Authorization": f"Splunk {hec_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                url,
                headers=headers,
                data=payload,
                verify=False,
                timeout=self.timeout
            )

            if response.status_code == 200:
                logger.debug(f"HEC响应: {response.text}")
                return True
            else:
                logger.error(f"HEC请求失败: HTTP {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"HEC请求异常: {e}")
            return False


def create_data_writer(service: client.Service) -> DataWriter:
    """创建数据写入器"""
    return DataWriter(service)
