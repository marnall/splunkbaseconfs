# -*- coding: utf-8 -*-
"""
@Time ： 2024/12/28 18:14
@Auth ： fbx
@File ：test_script.py

"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from threading import current_thread, Lock
from concurrent.futures import ThreadPoolExecutor,as_completed
import splunk.clilib.cli_common as cli_common
import json
import splunklib.results as results
from datetime import datetime, timedelta
import time
import ipaddress
import requests
import logging
import socket
import splunklib.client as client
import itertools
import configparser

# 创建一个全局计数器，为每种类型的任务生成唯一ID
task_counter = itertools.count(1)

# 配置日志记录器方法
def config_log():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
    logger = logging.getLogger(__name__)
    # 清除已有的处理器，避免重复
    if logger.hasHandlers():
        logger.handlers.clear()
    # 获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file_path = os.path.join(script_dir, f'app_{current_date}.log')
    # 设置日志文件处理器
    file_handler = logging.FileHandler(log_file_path)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # 清理前一天的日志
    previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    previous_log_file_path = os.path.join(script_dir, f'app_{previous_date}.log')
    if os.path.exists(previous_log_file_path):
        os.remove(previous_log_file_path)
    return logger


# splunk连接服务方法
def connect_to_splunk(host_port_list, token, logger, timeout=5):
    socket.setdefaulttimeout(timeout)
    for host_port in host_port_list:
        try:
            host_port = host_port.strip().split(':')
            service = client.connect(
                host=host_port[0],
                port=host_port[1],
                token=token
            )
            logger.info("成功连接splunk服务")
            return service
        except Exception as e:
            logger.error(f"连接splunk服务出现异常: {e}")
    return None


def read_configuration(logger):
    conf_file = 'application.conf'
    stanza = 'config'
    try:
        current_script_path = os.path.abspath(__file__)
        app_root_dir = os.path.dirname(os.path.dirname(current_script_path))
        # 构建 local 目录路径（与 bin 同级）
        config_path = os.path.join(app_root_dir, 'local', conf_file)

        # 读取配置文件
        config = configparser.ConfigParser()
        config.read(config_path)

        # 获取指定 stanza 的配置
        if stanza in config:
            return dict(config[stanza])
        else:
            logger.error(f"配置文件中未找到 stanza: {stanza}")
            return None
    except Exception as e:
        # 处理读取配置文件失败的情况
        logger.error(f"读取配置文件时出现异常：{str(e)}")
        return None

class ApiCron():

    # 单例模式实现
    _instance = None
    _lock = Lock() # 添加线程锁，防止创建多个splunk连接实例
    _task_end_times = {'ip': {}, 'ioc': {}, 'hash': {}}

    # 定义字段映射字典
    FIELD_MAPPING = {
        'ip': ['src_ip', 'dest_ip'],  # IP 查询时使用的字段
        'ioc': ['domain', 'src_ip', 'dest_ip', 'dest_port'],  # ioc查询的字段名
        'hash': ['sha256']  # hash查询的字段名
    }

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:  # 双重检查锁机制
                if not cls._instance:
                    cls._instance = super(ApiCron, cls).__new__(cls)
        return cls._instance

    def __init__(self, logger):
        # 避免多次初始化
        if not hasattr(self, '_initialized'):
            self._logger = logger
            self._executor = ThreadPoolExecutor(max_workers=6) # 创建线程池，避免每次创建
            self._initialized = True

    def clear_tasks_and_threads(self):
        # 清理所有任务和线程池
        # 清空 task_end_times 字典，防止过期数据影响新的任务调度
        self._task_end_times = {'ip': {}, 'ioc': {}, 'hash': {}}
        self._logger.info("已清空任务结束时间记录 (self._task_end_times).")


    # 执行 Splunk 查询，按批次流式获取数据，并根据查询类型动态获取不同的字段
    def fetch_splunk_results_in_batches(self, splunk_service, spl_query, query_type,  apikey, index_master_url, hec_token, bound_url, output_index, lang, batch_size=5000):
        # 根据查询类型选择需要的字段
        if query_type not in self.FIELD_MAPPING:
            self._logger.error(f"未知的查询类型: {query_type}")
            return []
        # 获取对应查询类型的字段
        fields_to_extract = self.FIELD_MAPPING[query_type]
        self._logger.info("开始进行流式处理批量获取索引日志")

        try:
            # 创建搜索作业
            self._logger.info("开始创建job搜索spl_query")
            job = splunk_service.jobs.create(spl_query, timeout=3600, count=0)
            # 轮询等待作业完成
            while not job.is_done():
                time.sleep(2)  # 等待2秒再检查
            offset = 0
        except Exception as e:
            self._logger.error("创建spl的检索作业失败：%s", str(e))

        # 按批次获取数据并处理每批,流式处理,一次处理5000条
        while True:
            try:
                # 分批获取数据
                batch_results = job.results(count=batch_size, offset=offset)
                results_reader = results.ResultsReader(batch_results)
                batch_event_list = []
                # 处理当前批次的结果并追加到batch_event_list
                for result in results_reader:
                    event = {}
                    for field in fields_to_extract:
                        # 获取当前字段值，默认空字符串
                        if query_type == "ip":
                            event['src_ip'] = result.get('src_ip', '')
                            event['dest_ip'] = result.get('dest_ip', '')
                        elif query_type == "ioc":
                            event['src_ip'] = result.get('src_ip', '')
                            event['dest_ip'] = result.get('dest_ip', '')
                            event['domain'] = result.get('domain', '')
                            event['dest_port'] = result.get('dest_port', '')
                        elif query_type == "hash":
                            event['sha256'] = result.get('sha256','')
                    # 根据查询类型处理字段（可以根据不同类型定制不同的处理逻辑）
                    batch_event_list.append(event)
                self._logger.info("获取用于调用api的信息列表：%s", batch_event_list)

                # 如果批次有数据，处理并返回这一批
                if len(batch_event_list) > 0:
                    self._logger.info('quert_type: %s 当前sql: %s 获取到event_list数量为: %d', query_type, spl_query, len(batch_event_list))
                    # 根据查询类型调用不同的处理逻辑
                    self._logger.info("开始准备与TIP的API进行情报碰撞")
                    self.process_batch_by_query_type(query_type, batch_event_list, apikey, index_master_url,hec_token, bound_url, output_index, lang)

                # 如果当前批次数据少于批量大小，说明是最后一批，跳出循环
                if len(batch_event_list) < batch_size:
                    self._logger.info("获取query_type: %s 的当前批次数据数量为最后一批数量")
                    break
                # 更新偏移量以获取下一批数据
                offset += batch_size

            except Exception as e:
                self._logger.error(f"Error fetching results at offset {offset}: {e}")
                # 继续获取下一批数据
                offset += batch_size
                continue


    # 专门处理 IP 查询的执行
    def execute_ip_query_task(self, spl_query, apikey, output_index, select_rate, inbound_url, lang,
                              index_master_url, hec_token,splunk_service):
        try:
            inbound_url = inbound_url + '/tip_api/v4/ip'
            self._logger.info('当前入站来自的spl语句是: %s', spl_query)
            current_time = int(time.mktime(datetime.now().timetuple()))

            # 配置查询时间, 获取任务的结束时间（out_future_timestamp），用于下一次查询的开始时间
            with self._lock:
                task_id = f"ip_{spl_query}"
                if task_id in self._task_end_times['ip']:
                    in_start_timestamp = self._task_end_times['ip'][task_id]
                else:
                    in_start_timestamp = self.get_time(current_time, select_rate)
                self._task_end_times['ip'][task_id] = current_time  # 更新任务结束时间

            future_timestamp = current_time
            self._logger.info("入站配置查询输入索引开始时间：%d", in_start_timestamp)
            self._logger.info("入站配置查询输入索引截止时间：%d", future_timestamp)

            # 查询当前频率时间范围内的所需ip情报信息
            input_query = f"search earliest={in_start_timestamp} latest={future_timestamp} {spl_query} | table src_ip, dest_ip"
            self._logger.info("打印完整拼接后的spl查询语句为: %s", input_query)  # 打印查询语句以调试
            self.fetch_splunk_results_in_batches(splunk_service, input_query, 'ip', apikey, index_master_url, hec_token, inbound_url, output_index, lang)
            self._logger.info('当前入站的spl语句: %s 执行查询任务完成', spl_query)
        except Exception as e:
            self._logger.error("执行 IP 查询任务时发生异常：%s", str(e))


    # 专门处理 IOC 查询的执行
    def execute_ioc_query_task(self,spl_query, apikey, output_index,select_rate, outbound_url, lang, index_master_url, hec_token,splunk_service):
        outbound_url = outbound_url + '/tip_api/v4/dns'
        self._logger.info('当前出站来自的spl语句是: %s', spl_query)
        current_time = int(time.mktime(datetime.now().timetuple()))

        with self._lock:
            # 配置查询时间
            task_id = f"ioc_{spl_query}"
            if task_id in self._task_end_times['ioc']:
                out_start_timestamp = self._task_end_times['ioc'][task_id]
            else:
                out_start_timestamp = self.get_time(current_time, select_rate)
            self._task_end_times['ioc'][task_id] = current_time

        out_future_timestamp = current_time
        self._logger.info("出站配置查询输入索引开始时间：%d", out_start_timestamp)
        self._logger.info("出站配置查询输入索引截止时间：%d", out_future_timestamp)

        # 查询当前频率时间范围内的所需ip情报信息
        output_query = f"search earliest={out_start_timestamp} latest={out_future_timestamp} {spl_query} | table domain, src_ip, dest_ip, dest_port"
        self._logger.info("OUT Generated SPL Query: %s", output_query)  # 打印查询语句以调试
        self.fetch_splunk_results_in_batches(splunk_service, output_query, 'ioc', apikey, index_master_url, hec_token, outbound_url, output_index, lang)
        self._logger.info('当前出站的spl语句: %s 执行查询任务完成', spl_query)


    # 专门处理hash查询的执行
    def execute_hash_query_task(self,spl_query, apikey, output_index, select_rate, hash_url, lang, index_master_url, hec_token,splunk_service):
        try:
            hash_url = hash_url + '/v3/file/report'
            self._logger.info("当前hash来自的spl语句是: %s", spl_query)
            current_time = int(time.mktime(datetime.now().timetuple()))
            with self._lock:
                task_id = f"hash_{spl_query}"
                if task_id in self._task_end_times['hash']:
                    hash_start_timestamp = self._task_end_times['hash'][task_id]
                else:
                    hash_start_timestamp = self.get_time(current_time, select_rate)
                self._task_end_times['hash'][task_id] = current_time # 更新hash的存储时间

            hash_future_timestamp = current_time
            self._logger.info("hash配置查询输入索引开始时间%d", hash_start_timestamp)
            self._logger.info("hash配置查询输入索引截止时间%d", hash_future_timestamp)
            # 查询当前时间范围内的所需的hash情报信息
            hash_query = f"search earliest={hash_start_timestamp} latest={hash_future_timestamp} {spl_query} | table sha256"
            self._logger.info("打印hash完整拼接后的spl查询语句为: %s", hash_query)  # 打印查询语句以调试
            self.fetch_splunk_results_in_batches(splunk_service, hash_query, 'hash', apikey, index_master_url, hec_token, hash_url, output_index, lang)
            self._logger.info('当前的hash语句: %s 执行查询任务完成', spl_query)
        except Exception as e:
            self._logger.error("执行 hash查询任务时发生异常：%s", str(e))


    # 根据查询类型处理批次数据
    def process_batch_by_query_type(self, query_type, batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang):
        if query_type == 'ip':
            self._logger.info("开始进行ip情报碰撞")
            self.process_ip_batch(batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang)
        elif query_type == 'ioc':
            self._logger.info("开始进行ioc情报碰撞")
            self.process_ioc_batch(batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang)
        elif query_type == 'hash':
            self._logger.info("开始进行hash情报碰撞")
            self.process_hash_batch(batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang)
        else:
            self._logger.error(f"未知的查询类型: {query_type}")


    # 处理 IP 查询的批次数据
    def process_ip_batch(self, batch_event_list,  apikey, index_master_url,hec_token, inbound_url, output_index, lang):
        for event in batch_event_list:
            in_src_ip = event['src_ip']
            in_dest_ip = event['dest_ip']
            if in_src_ip and self.is_public_ip(in_src_ip):  # 测试时先取消，内网ip不参与碰撞
                try:
                    self._logger.info("入站配置根据ip调用tip api:%s", in_src_ip)
                    json_string = self.get_tip_api(apikey, in_src_ip, in_dest_ip, inbound_url, lang, 'ip')
                    if json_string:
                        self.write_output_index(json_string, output_index, hec_token, index_master_url)
                        self._logger.info("入站配置调用完api输出至索引完成")
                    else:
                        self._logger.info("入站碰撞情报无结果不输出")
                except Exception as e:
                    self._logger.error("入站配置调用api查询输出索引出错: %s", e)
            else:
                self._logger.info("解析的源ip为空或者非公网ip,不碰撞情报")


    # 处理 IOC 查询的批次数据
    def process_ioc_batch(self, batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang):
        for event in batch_event_list:
            out_dest_name = event['domain']
            out_dest_ip = event['dest_ip']
            if not out_dest_name:
                if out_dest_ip:  # 如果域名为空，查询dest_ip+dest_port
                    try:
                        dest_port = event['dest_port']
                        host = event['src_ip']
                        self._logger.info("出站配置所使用域名调用tip api: %s", out_dest_ip)
                        self._logger.info("出站配置所使用域名调用tip api端口: %s", dest_port)
                        if dest_port:
                            resource = out_dest_ip + ':' + dest_port
                        else:
                            resource = out_dest_ip
                        json_string = self.get_tip_api(apikey, resource, host, bound_url, lang, 'ioc')
                        if json_string:
                            self.write_output_index(json_string, output_index, hec_token, index_master_url)
                            self._logger.info("出站配置调用完api输出至索引任务完成")
                        else:
                            self._logger.info("出站碰撞情报无结果不输出")
                    except Exception as e:
                        self._logger.error('出站配置调用api查询输出索引出错:%s', e)
                else:
                    self._logger.info("域名为空, dest_ip也为空不进行情报查询")

            else:  # 如果域名有值直接查域名
                try:
                    self._logger.info("出站配置所使用域名调用tip api: %s", out_dest_name)
                    resource = out_dest_name
                    host = event['src_ip']
                    json_string = self.get_tip_api(apikey, resource, host, bound_url, lang, 'ioc')
                    if json_string:
                        self.write_output_index(json_string, output_index, hec_token, index_master_url)
                        self._logger.info("出站配置调用完api输出至索引任务完成")
                    else:
                        self._logger.info("出站碰撞情报无结果不输出")
                except Exception as e:
                    self._logger.error('出站配置调用api查询输出索引出错:%s', e)


    # 处理 Hash 查询的批次数据
    def process_hash_batch(self, batch_event_list, apikey, index_master_url, hec_token, bound_url,output_index, lang):
        for event in batch_event_list:
            sha256 = event['sha256']
            if sha256:
                try:
                    self._logger.info("hash配置根据sha256调用tip api: %s", sha256)
                    json_string = self.get_tip_api(apikey, sha256, None, bound_url, lang, 'hash')
                    if json_string:
                        self.write_output_index(json_string, output_index, hec_token, index_master_url)
                        self._logger.info("hash配置调用完api输出至索引完成")
                    else:
                        self._logger.info("hash碰撞情报无结果不输出")
                except Exception as e:
                    self._logger.error("hash配置调用api查询输出索引出错:%s", e)
            else:
                self._logger.info("解析的sha256字段为空，不碰撞hash情报")



    # 获取当前时间前多少分钟的时间戳
    def get_time(self,current_time, minutes):
        # 将秒级时间戳转换为datetime对象
        current_dt = datetime.fromtimestamp(current_time)
        # 计算前minutes分钟的时间
        delta = timedelta(minutes=-minutes)
        # 计算前minutes分钟的时间戳
        previous_dt = current_dt + delta
        previous_timestamp = previous_dt.timestamp()
        return int(previous_timestamp)


    # 判断ip是否是公网，公网为true
    def is_public_ip(self, ip):
        try:
            ip_address = ipaddress.ip_address(ip)
            return not ip_address.is_private and not ip_address.is_loopback
        except ValueError:
            return False


    # 碰撞情报,组合字段
    def get_tip_api(self, apikey, resource, host, url, lang, query_type, timeout=10):
        if host:
            query = {"apikey": apikey, "resource": resource, "host": host, "lang": lang}
        else:
            query = {"apikey": apikey, "resource": resource, "lang": lang}
        headers = {"Content-Type": "application/json;charset=utf-8"}
        try:
            response = requests.get(url, headers=headers, params=query, timeout=timeout)
            response.raise_for_status()  # 检查请求是否成功
        except Exception as e:
            self._logger.error("请求TIP的API查询出错：%s", e)
            return None
        # 响应一定是json，无需异常处理
        json_data = json.loads(response.text)
        if json_data.get("response_code") == 0:
            if query_type == "ip" or query_type == "ioc":
                first_data_item = json_data['data'][0]
            elif query_type == "hash":
                first_data_item = json_data['data']
            json_string = json.dumps(first_data_item)
            self._logger.info('调用TIP的API有结果')
            return json_string
        else:
            verbose_msg = json_data.get("verbose_msg")
            self._logger.info('调用TIP的API返回状态码不等于0：%s', verbose_msg)
            return None


    # 向索引器中写入数据使用HEC token方式
    def write_output_index(self, json_string, outputindex, hec_token, hec_url, timeout=10):
        headers = {
            "Authorization": f"Splunk {hec_token}",
            "Content-Type": "application/json"
        }
        data = {
            "sourcetype": "tip",
            "index": outputindex,
            "event": json_string
        }
        try:
            hec_url = hec_url + '/services/collector/event'
            response = requests.post(hec_url, headers=headers, json=data, verify=False,timeout=timeout)
            response.raise_for_status()
            response_json = response.json()
            self._logger.info(f"Response: {response_json}")
            if response_json.get("code") == 0:
                self._logger.info(f"查询结果数据写入到输出索引成功: {outputindex}")
            else:
                self._logger.info(f"响应内容中代码表示失败: {response_json.get('code')}")
        except Exception as e:
            self._logger.error(f"在提交输出索引数据时出现异常 '{outputindex}': {e}")


def main():
    logger = config_log() # 初始化日志记录器
    while True:
        config_data = read_configuration(logger)
        if not config_data:
            logger.warning("未读取到有效配置，5分钟后重试")
            time.sleep(5 * 60)
            continue

        logger.info("读取到配置文件的内容为：%s", config_data)
        search_head_url = config_data.get('search_head_url')
        token = config_data.get('token')
        index_master_url = config_data.get('index_master_url')
        hec_token = config_data.get('hec_token')
        if not (search_head_url and token and index_master_url and hec_token):
            logger.error("基础配置信息填写不全，不执行定时任务")
            time.sleep(5 * 60)
            continue

        # 在配置信息中校验至少有一项配置完整才可执行脚本
        inbound_config, outbound_config, hash_config = (config_data.get("inbound_config"), config_data.get("outbound_config"), config_data.get("hash_config"),)
        inbound_url, outbound_url, hash_url = (config_data.get("inbound_url"), config_data.get("outbound_url"), config_data.get("hash_url"), )
        lang = config_data.get('lang', 'default_lang')
        if not any([
            inbound_config and inbound_url,
            outbound_config and outbound_url,
            hash_config and hash_url
        ]):
            logger.info("至少保证 ip、ioc、hash 其中一组配置项完整，5分钟后重试")
            time.sleep(5 * 60)
            continue

        # 获取splunk服务的连接
        splunk_service = connect_to_splunk(search_head_url.strip().rsplit(';'), token, logger)
        if not splunk_service:
            logger.error("获取 splunk 连接对象出错")
            time.sleep(5 * 60)
            continue

        # 转换'inbound_config', 'outbound_config', 'hash_config'为json
        try:
            config_data = {key: json.loads(config_data[key])
                            for key in ['inbound_config', 'outbound_config', 'hash_config']
                            if key in config_data and isinstance(config_data[key], str)}
        except json.JSONDecodeError as e:
            logger.error("解析配置信息失败: %s", e)
            time.sleep(5 * 60)
            continue

        config_dict = {"ip": config_data.get('inbound_config', []),"ioc": config_data.get('outbound_config', []), "hash": config_data.get('hash_config', [])}
        logger.info("解析成功后的config_dict数据为：%s", config_dict)
        # 开始解析ip、ioc和hash的配置实例
        tasks = []
        for query_name, config_list in config_dict.items():
            if not config_list:
                logger.warning(f"{query_name} 配置为空，跳过")
                continue
            for config_item in config_list:
                logger.info("当前 %s 的配置项：%s", query_name, config_item)
                apikey = config_item['apikey']
                output_index = config_item.get("output_index", f'mbag_apac_cn_aws_threatbook_{query_name}_intel_raw')
                select_rate = config_item.get("select_rate")

                # 解析日志配置
                for data_source in config_item['datasource']:
                    spl_query = data_source.get('spl')
                    # 判断spl语句是否为空
                    if not spl_query:
                        continue

                    apicron = ApiCron(logger)
                    task_id = next(task_counter)
                    task_fn = {
                            "ip": apicron.execute_ip_query_task,
                            "ioc": apicron.execute_ioc_query_task,
                            "hash": apicron.execute_hash_query_task,}.get(query_name)

                    if task_fn:
                        future = apicron._executor.submit(task_fn,spl_query,apikey,output_index,select_rate,
                                                           inbound_url if query_name == "ip" else (outbound_url if query_name == "ioc" else hash_url),
                                                            lang,index_master_url,hec_token,splunk_service)
                        tasks.append(future)

        # 等待所有任务完成
        logger.info(f"等待 {len(tasks)} 个任务完成")
        logger.info("等待所有子任务完成...")
        for future in as_completed(tasks):
            try:
                future.result()  # 获取任务结果，若任务抛出异常会在此触发
            except Exception as e:
                logger.error(f"任务执行时发生错误: {e}")

        logger.info("所有子任务已完成")
        logger.info("等待下一次轮询定时任务开始 ---------------------------------------------------------------------------------------------------")
        # 每次循环更新日志配置，确保日志切换到新的一天时重新配置
        logger = config_log()
        time.sleep(5 * 60)


if __name__ == '__main__':
    # config = {'hash_config': '[]', 'hash_url': '', 'hec_token': 'cb226dc1-1f03-45ad-9af1-978bf60ce414', 'inbound_config': '[{"apikey": "d4e14129957e4562959718b0abed6db3", "outputindex": "in-out1", "select_rate": 1, "datasource": [{"name": "datasource1", "spl": "index=test_input |  rename src_ip as src_ip, dest_ip as dest_ip", "index": "test_input"}]}]', 'inbound_url': 'http://192.168.100.87:8090', 'index_master_url': 'http://192.168.100.91:8088', 'lang': '', 'outbound_config': '[]', 'outbound_url': '', 'search_head_url': '192.168.100.91:8089', 'token': 'eyJraWQiOiJzcGx1bmsuc2VjcmV0IiwiYWxnIjoiSFM1MTIiLCJ2ZXIiOiJ2MiIsInR0eXAiOiJzdGF0aWMifQ.eyJpc3MiOiJmYnh0ZXN0IGZyb20ga2Fma2Etc2luZ2xlIiwic3ViIjoiZmJ4dGVzdCIsImF1ZCI6ImRkZCIsImlkcCI6IlNwbHVuayIsImp0aSI6IjQ4NDcyMGE0YmQ3ODg5OGMwMzdiYzc3YmI0OGMxYTNiYzNmZDA1Y2IyZjUyZDNiZjgzZGQyYWU4OGI0Y2I1NDYiLCJpYXQiOjE3MzY2NzMyODksImV4cCI6MTczOTI2NTI4OSwibmJyIjoxNzM2NjczMjg5fQ.SL-oQkxpfspLRyKPtnCJ1MFQFbvn6FCDkTfI4_v_-Ropy9fHxebvHLm5j1MSXeV0DgMfEBFTS3WxIrWeTfE08Q'}
   main()
