#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Splunk App 配置 REST API
提供前端配置参数的读取和保存功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import splunk
import splunk.rest
import splunk.bundle
import logging
import re
from datetime import datetime, timedelta
from config_flag_manager import set_config_flag
from proxy_manager import ProxyManager, ProxyConfig

def set_response(response, body, status=200):
    """设置HTTP响应"""
    response.setHeader('content-type', 'application/json')
    response.setStatus(status)
    response.write(json.dumps(body))

# 配置日志记录器方法
def config_log():
    """配置日志记录器"""
    script_dir = os.path.dirname(os.path.abspath(__file__))  # bin/ 目录
    splunk_app_dir = os.path.dirname(script_dir)  # splunk/ 目录
    log_dir = os.path.join(splunk_app_dir, "var", "log")
    os.makedirs(log_dir, exist_ok=True)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # 获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file_path = os.path.join(log_dir, f'rest_{current_date}.log')
    # 设置日志文件处理器
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    # 清理前一天的日志
    previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    previous_log_file_path = os.path.join(log_dir, f'rest_{previous_date}.log')
    if os.path.exists(previous_log_file_path):
        os.remove(previous_log_file_path)
    return logger

# 基本参数验证方法
def validate_basic_params(search_head_url, token, index_master_url, hec_token, logger):
    """验证基础配置参数"""
    logger.info("开始验证基础配置参数...")

    if not (search_head_url and token and index_master_url and hec_token):
        logger.error("基础信息为必填，请检查基础信息配置")
        logger.error(f"参数检查 - search_head_url: {'✓' if search_head_url else '✗'}, token: {'✓' if token else '✗'}, index_master_url: {'✓' if index_master_url else '✗'}, hec_token: {'✓' if hec_token else '✗'}")
        return False, "Basic configuration parameters are mandatory"

    if ':' not in search_head_url:
        logger.error("search_head_url填写应该包含端口号")
        logger.error(f"search_head_url 格式错误: {search_head_url}")
        return False, "Splunk_URL filling does not meet the specifications"

    logger.info("基础配置参数验证通过")
    return True, None

def validate_spl_rule(spl, required_field, intelligence_type, logger):
    """
    验证SPL规则中是否包含必需的字段

    Args:
        spl: SPL查询语句
        required_field: 必需字段名 (ip, domain, hash)
        intelligence_type: 情报类型 (ip, domain, file)
        logger: 日志记录器

    Returns:
        tuple: (is_valid, error_message)
    """
    if not spl or not isinstance(spl, str):
        return False, f"SPL query in {intelligence_type} intelligence configuration cannot be empty"

    # 查找 rename 子句，与 intelligence_task_manager 中的 _extract_table_fields 保持一致
    rename_match = re.search(r'rename\s+(.+?)(?:\s*\||$)', spl, re.IGNORECASE)
    if not rename_match:
        return False, f"SPL query in {intelligence_type} intelligence configuration must contain rename statement"

    rename_clause = rename_match.group(1).strip()

    # 解析 rename 子句中的字段，与 intelligence_task_manager 中的 _extract_table_fields 保持一致
    # 匹配模式：field_name as alias_name 或 field_name
    field_pattern = r'(\w+)\s+as\s+(\w+)|(\w+)'

    renamed_fields = []
    for match in re.finditer(field_pattern, rename_clause):
        if match.group(1) and match.group(2):  # 有 as 子句
            # 提取 as 后面的字段名
            as_field = match.group(2).strip()
            renamed_fields.append(as_field.lower())
        elif match.group(3):  # 没有 as 子句
            # 使用原字段名
            original_field = match.group(3).strip()
            renamed_fields.append(original_field.lower())

    # 检查是否包含必需字段
    if required_field.lower() not in renamed_fields:
        return False, f"Rename statement in SPL query must contain field '{required_field}'"

    logger.info(f"{intelligence_type}情报SPL规则验证通过: {spl}")
    return True, None

def validate_intelligence_config(config, intelligence_type, logger):
    """
    验证情报配置中的SPL规则

    Args:
        config: 情报配置列表
        intelligence_type: 情报类型 (ip, domain, file)
        logger: 日志记录器

    Returns:
        tuple: (is_valid, error_message)
    """
    if not config or not isinstance(config, list):
        return True, None  # 空配置是允许的

    # 定义必需字段映射
    required_fields = {
        'ip': 'ip',
        'domain': 'domain',
        'file': 'hash'
    }

    required_field = required_fields.get(intelligence_type)
    if not required_field:
        return False, f"未知的情报类型: {intelligence_type}"

    for i, config_item in enumerate(config):
        if not isinstance(config_item, dict):
            continue  # 跳过非对象项

        # 只验证datasource中的SPL规则
        datasource = config_item.get('datasource')
        if not isinstance(datasource, list):
            continue  # 跳过非数组项

        for j, ds in enumerate(datasource):
            if not isinstance(ds, dict):
                continue  # 跳过非对象项

            # 只验证SPL规则
            spl = ds.get('spl')
            if spl:  # 只有当SPL存在时才验证
                is_valid, error_msg = validate_spl_rule(spl, required_field, intelligence_type, logger)
                if not is_valid:
                    return False, f"Item {i+1} datasource {j+1} in {intelligence_type} intelligence configuration: {error_msg}"

    logger.info(f"{intelligence_type}情报配置SPL规则验证通过")
    return True, None

class ConfigAPI(splunk.rest.BaseRestHandler):
    """配置管理REST API处理器"""

    _logger = config_log()

    # 辅助函数：获取配置字段并处理 JSON 解析
    def get_config_value(self, conf, key, default_value):
        """获取配置值并处理JSON解析"""
        value = conf.get(key, default_value)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 如果 JSON 解析失败，则返回默认值
                self._logger.error(f"Failed to parse JSON for {key}. Returning default value.")
                return default_value
        return value

    def handle_GET(self):
        """读取当前配置"""
        self._logger.info("开始读取配置...")
        try:
            conf = splunk.bundle.getConf('my', self.sessionKey)['config']
            search_head_url = conf.get('search_head_url', '')
            token = conf.get('token', '')
            index_master_url = conf.get('index_master_url', '')
            hec_token = conf.get('hec_token', '')
            ip_intelligence_url = conf.get('ip_intelligence_url', '')
            ip_intelligence_config = self.get_config_value(conf, 'ip_intelligence_config', [])
            domain_intelligence_url = conf.get('domain_intelligence_url', '')
            domain_intelligence_config = self.get_config_value(conf, 'domain_intelligence_config', [])
            file_intelligence_url = conf.get('file_intelligence_url', '')
            file_intelligence_config = self.get_config_value(conf, 'file_intelligence_config', [])

            # 读取代理配置（提供默认值）
            proxyEnabled = conf.get('proxyEnabled', 'true')
            proxyType = conf.get('proxyType', 'HTTP')
            proxyHost = conf.get('proxyHost', '')
            proxyPort = conf.get('proxyPort', '')
            proxyUsername = conf.get('proxyUsername', '')
            proxyPassword = conf.get('proxyPassword', '')
            proxyRemoteDNS = conf.get('proxyRemoteDNS', 'false')

            self._logger.info("配置读取成功")

        except Exception as e:
            self._logger.error(f"读取配置失败: {str(e)}")
            search_head_url = token = index_master_url = hec_token = ''
            ip_intelligence_url = domain_intelligence_url = file_intelligence_url = ''
            ip_intelligence_config = domain_intelligence_config = file_intelligence_config = []
            proxyEnabled = 'true'
            proxyType = 'HTTP'
            proxyHost = proxyPort = proxyUsername = proxyPassword = ''
            proxyRemoteDNS = 'false'

        set_response(self.response, {
            'search_head_url': search_head_url,
            'token': token,
            'index_master_url': index_master_url,
            'hec_token': hec_token,
            'ip_intelligence_url': ip_intelligence_url,
            'ip_intelligence_config': ip_intelligence_config,
            'domain_intelligence_url': domain_intelligence_url,
            'domain_intelligence_config': domain_intelligence_config,
            'file_intelligence_url': file_intelligence_url,
            'file_intelligence_config': file_intelligence_config,
            'proxyEnabled': proxyEnabled,
            'proxyType': proxyType,
            'proxyHost': proxyHost,
            'proxyPort': proxyPort,
            'proxyUsername': proxyUsername,
            'proxyPassword': proxyPassword,
            'proxyRemoteDNS': proxyRemoteDNS
        })

    def handle_POST(self):
        """保存配置参数或测试代理连接"""
        self._logger.info("开始处理POST请求...")

        # 获取请求体并解析 JSON 数据
        try:
            request_body = self.request['payload']
            data = json.loads(request_body)  # 将JSON字符串解析为Python字典
            self._logger.info("JSON 数据解析成功")
        except Exception as e:
            error_message = str(e)  # 获取具体的异常信息
            self._logger.error("解析post传参失败：%s", error_message)
            set_response(self.response, {'error': 'Invalid JSON format','details': error_message}, 400)
            return

        # 获取 action 参数，默认为 "save"
        action = data.get('action', 'save').lower()

        # 如果是测试模式，调用测试逻辑
        if action == 'test':
            self._handle_proxy_test(data)
            return

        # 否则执行保存逻辑
        self._logger.info("执行配置保存逻辑...")

        # 获取基础配置参数
        search_head_url = data.get('search_head_url')
        token = data.get('token')
        index_master_url = data.get('index_master_url')
        hec_token = data.get('hec_token')

        # 验证基础配置参数
        is_valid, error_msg = validate_basic_params(search_head_url, token, index_master_url, hec_token, self._logger)
        if not is_valid:
            self._logger.error(f"基础配置参数验证失败: {error_msg}")
            set_response(self.response, {'error': error_msg}, 400)
            return

        # 获取其他配置参数
        ip_intelligence_url = data.get('ip_intelligence_url', '')
        ip_intelligence_config = data.get('ip_intelligence_config', [])
        domain_intelligence_url = data.get('domain_intelligence_url', '')
        domain_intelligence_config = data.get('domain_intelligence_config', [])
        file_intelligence_url = data.get('file_intelligence_url', '')
        file_intelligence_config = data.get('file_intelligence_config', [])

        # 获取代理配置
        proxy_enabled = data.get('proxyEnabled', 'true')
        proxy_type = data.get('proxyType', 'HTTP')
        proxy_host = data.get('proxyHost', '').strip()
        proxy_port_str = str(data.get('proxyPort', '')).strip()
        proxy_username = data.get('proxyUsername', '').strip()
        proxy_password = data.get('proxyPassword', '').strip()
        proxy_remote_dns = data.get('proxyRemoteDNS', 'false')

        # 清理 Host（去协议头）
        try:
            proxy_host = ProxyManager.clean_host(proxy_host)
        except ValueError as e:
            self._logger.error(f"代理 Host 格式错误: {str(e)}")
            set_response(self.response, {
                'error': str(e),
                'title': 'Configuration Error'
            }, 400)
            return

        # 转换 Port 为整数
        try:
            proxy_port = int(proxy_port_str) if proxy_port_str else 0
        except ValueError:
            self._logger.error(f"代理端口格式错误: {proxy_port_str}")
            set_response(self.response, {'error': 'Invalid proxy port format'}, 400)
            return

        # 构建 ProxyConfig 对象
        proxy_config = ProxyConfig(
            enabled=(proxy_enabled.lower() == 'true' if isinstance(proxy_enabled, str) else proxy_enabled),
            proxy_type=proxy_type.upper(),
            host=proxy_host,
            port=proxy_port,
            username=proxy_username,
            password=proxy_password,
            remote_dns=(proxy_remote_dns.lower() == 'true' if isinstance(proxy_remote_dns, str) else proxy_remote_dns)
        )

        # 验证代理配置
        is_valid, error_msg = ProxyManager.validate_config(proxy_config)
        if not is_valid:
            self._logger.error(f"代理配置验证失败: {error_msg}")
            set_response(self.response, {
                'error': 'Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.',
                'title': 'Connection Failed'}, 400)
            return

        # 校验情报配置中的SPL规则
        self._logger.info("开始校验情报配置中的SPL规则...")

        # 校验IP情报配置SPL规则
        if ip_intelligence_config:
            is_valid, error_msg = validate_intelligence_config(ip_intelligence_config, 'ip', self._logger)
            if not is_valid:
                self._logger.error(f"IP情报配置SPL规则校验失败: {error_msg}")
                set_response(self.response, {'error': f'IP intelligence configuration SPL validation failed: {error_msg}'}, 400)
                return

        # 校验域名情报配置SPL规则
        if domain_intelligence_config:
            is_valid, error_msg = validate_intelligence_config(domain_intelligence_config, 'domain', self._logger)
            if not is_valid:
                self._logger.error(f"域名情报配置SPL规则校验失败: {error_msg}")
                set_response(self.response, {'error': f'Domain intelligence configuration SPL validation failed: {error_msg}'}, 400)
                return

        # 校验文件情报配置SPL规则
        if file_intelligence_config:
            is_valid, error_msg = validate_intelligence_config(file_intelligence_config, 'file', self._logger)
            if not is_valid:
                self._logger.error(f"文件情报配置SPL规则校验失败: {error_msg}")
                set_response(self.response, {'error': f'File intelligence configuration SPL validation failed: {error_msg}'}, 400)
                return

        self._logger.info("情报配置SPL规则校验通过")

        # 保存配置
        try:
            self._logger.info("开始保存配置到 Splunk...")
            bun = splunk.bundle.getConf('my', self.sessionKey)

            # 检查配置节是否存在，如果不存在则创建
            if 'config' not in bun:
                bun.create('config')

            bun.beginBatch()
            conf = bun['config']

            # 保存基础配置
            conf['search_head_url'] = search_head_url
            conf['token'] = token
            conf['index_master_url'] = index_master_url
            conf['hec_token'] = hec_token

            # 保存情报配置
            conf['ip_intelligence_url'] = ip_intelligence_url
            conf['ip_intelligence_config'] = json.dumps(ip_intelligence_config) if ip_intelligence_config else '[]'
            conf['domain_intelligence_url'] = domain_intelligence_url
            conf['domain_intelligence_config'] = json.dumps(domain_intelligence_config) if domain_intelligence_config else '[]'
            conf['file_intelligence_url'] = file_intelligence_url
            conf['file_intelligence_config'] = json.dumps(file_intelligence_config) if file_intelligence_config else '[]'

            # 保存代理配置
            conf['proxyEnabled'] = 'true' if proxy_config.enabled else 'false'
            conf['proxyType'] = proxy_config.proxy_type
            conf['proxyHost'] = proxy_config.host
            conf['proxyPort'] = str(proxy_config.port)
            conf['proxyUsername'] = proxy_config.username
            conf['proxyPassword'] = proxy_config.password
            conf['proxyRemoteDNS'] = 'true' if proxy_config.remote_dns else 'false'

            bun.commitBatch()

        except Exception as e:
            self._logger.error("保存配置文件信息时出现异常：%s", str(e))
            set_response(self.response, {'error': f'Error saving configuration: {str(e)}'}, 400)
            return

        # 配置保存成功后，更新配置标志
        if set_config_flag("True", timestamp=True):
            self._logger.info("配置更新标志已设置")


        self._logger.info("配置保存成功")
        set_response(self.response, {"ok": "setting success!"})

    def _handle_proxy_test(self, data):
        """处理代理测试请求（私有方法）

        Args:
            data: 请求数据字典
        """
        self._logger.info("开始测试代理连接...")

        # 解析临时代理配置
        proxy_enabled = data.get('proxyEnabled', 'true')
        proxy_type = data.get('proxyType', 'HTTP')
        proxy_host = data.get('proxyHost', '').strip()
        proxy_port_str = str(data.get('proxyPort', '')).strip()
        proxy_username = data.get('proxyUsername', '').strip()
        proxy_password = data.get('proxyPassword', '').strip()
        proxy_remote_dns = data.get('proxyRemoteDNS', 'false')

        # 转换 enabled 为布尔值
        is_enabled = (proxy_enabled.lower() == 'true' if isinstance(proxy_enabled, str) else proxy_enabled)

        # 如果代理未启用，直接返回提示
        if not is_enabled:
            self._logger.info("代理已禁用，无需测试")
            set_response(self.response, {
                'error': 'Proxy is disabled. Please enable proxy before testing.',
                'title': 'Configuration Error'
            }, 400)
            return

        # 清理 Host（去协议头）
        try:
            proxy_host = ProxyManager.clean_host(proxy_host)
        except ValueError as e:
            self._logger.error(f"代理 Host 格式错误: {str(e)}")
            set_response(self.response, {
                'error': str(e),
                'title': 'Configuration Error'
            }, 400)
            return

        # 转换 Port 为整数
        try:
            proxy_port = int(proxy_port_str) if proxy_port_str else 0
        except ValueError:
            self._logger.error(f"代理端口格式错误: {proxy_port_str}")
            set_response(self.response, {
                'error': 'Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.',
                'title': 'Configuration Error'
            }, 400)
            return

        # 构建 ProxyConfig 对象
        proxy_config = ProxyConfig(
            enabled=is_enabled,
            proxy_type=proxy_type.upper(),
            host=proxy_host,
            port=proxy_port,
            username=proxy_username,
            password=proxy_password,
            remote_dns=(proxy_remote_dns.lower() == 'true' if isinstance(proxy_remote_dns, str) else proxy_remote_dns)
        )

        # 先验证配置格式
        is_valid, error_msg = ProxyManager.validate_config(proxy_config)
        if not is_valid:
            self._logger.error(f"代理配置验证失败: {error_msg}")
            set_response(self.response, {
                'error': 'Invalid Host format. Please ensure no protocol prefixes (e.g., "http://") are included in the Host field.',
                'title': 'Connection Failed'
            }, 400)
            return

        # 使用固定的测试 URL 验证代理连通性
        # 使用 ThreatBook API 根地址，会返回 405 但证明网络通畅
        test_url = "https://api.threatbook.io"
        self._logger.info(f"使用测试 URL: {test_url}")

        # 执行测试
        self._logger.info(f"开始测试代理连接: {proxy_config.proxy_type}://{proxy_config.host}:{proxy_config.port}")
        result = ProxyManager.test_connection(proxy_config, test_url, timeout=10)

        self._logger.info(f"代理测试结果: {result}")
        set_response(self.response, result)

