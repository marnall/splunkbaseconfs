#-*-coding:utf-8-*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import socket
import splunk
import splunk.rest
import splunk.bundle
import splunklib.results as results
import splunklib.client as client
import logging
from datetime import datetime, timedelta


def set_response(response, body, status=200):
    response.setHeader('content-type', 'application/json')
    response.setStatus(status)
    response.write(json.dumps(body))

# 配置日志记录器方法
def config_log():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    # 获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file_path = os.path.join(script_dir, f'rest_{current_date}.log')
    # 设置日志文件处理器
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(file_handler)
    # 清理前一天的日志
    previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    previous_log_file_path = os.path.join(script_dir, f'rest_{previous_date}.log')
    if os.path.exists(previous_log_file_path):
        os.remove(previous_log_file_path)
    return logger

# splunk连接服务方法
def connect_to_splunk(host_port_list, token, logger,timeout=5):
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
    return 0

#检查索引是否存在方法
def check_indexes_exist(service, index_name_set, logger):
    logger.info("开始检查输入索引是否存在")
    if index_name_set is None:
        return
    try:
        # 创建搜索查询来获取索引信息
        search_query = "| eventcount summarize=false index=* | dedup index | table index"
        job = service.jobs.create(search_query)
        while not job.is_done():
            pass
        results_reader = results.ResultsReader(job.results())
        index_list = []
        for result in results_reader:
            index_list.append(result)
        indexer_index_names = [result['index'] for result in index_list if 'index' in result]
        logger.info("查询到全部索引列表：",indexer_index_names)
        # 校验输入索引,输入索引支持多个
        for inputindex in index_name_set:
            if inputindex not in indexer_index_names:
                logger.error("当前填写的输入索引未创建，请先创建输入索引：%s", inputindex)
                return 1
    except Exception as e:
        logger.error(f"检查输入索引时出现异常: {e}")
        return 2


# 获取日志源名称并且判断是否重复
def get_log_name(bound_inputindex):
    log_name_list = []
    for str_log in bound_inputindex:
        log_name = str_log["name"]
        if log_name in log_name_list:
            print("日志源名称重复提交")
            return 1
        log_name_list.append(log_name)
    return log_name_list

# 获取输入索引
def get_index_name(bound_config_list):
    index_name_set = set()  # 用于存储唯一的index值
    for bound_config in bound_config_list:
        datasource_list = bound_config.get("datasource")
        if datasource_list:  # 确保datasource_list不为空
            for datasource in datasource_list:
                index = datasource.get("index")
                if index:  # 确保index字段存在且非空
                    index_name_set.add(index)
    return index_name_set

def check_index_result(bound_url, bound_cofig, splunk_service, logger, query_type):
    if bound_url and bound_cofig:
        index_name_set = get_index_name(bound_cofig)
        logger.info("quert_type: %s 获取的输入索引set集合：%s", query_type, index_name_set)
        check_result = check_indexes_exist(splunk_service, index_name_set,logger)
        return check_result
    else:
        logger.info('quert_type: %s 的实例配置或地址为空，不进行入站索引校验检查', query_type)



class ApiUrl(splunk.rest.BaseRestHandler):

    _logger = config_log()

    # 辅助函数：获取配置字段并处理 JSON 解析
    def get_config_value(self, conf, key, default_value):
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
        try:
            conf = splunk.bundle.getConf('application', self.sessionKey,namespace='Threatbook-TIP-v9',owner='nobody')['config']
            search_head_url = conf.get('search_head_url', '')
            token = conf.get('token', '')
            index_master_url = conf.get('index_master_url', '')
            hec_token = conf.get('hec_token', '')
            inbound_url = conf.get('inbound_url', '')
            inbound_config = self.get_config_value(conf, 'inbound_config', [])
            outbound_url = conf.get('outbound_url', '')
            outbound_config = self.get_config_value(conf, 'outbound_config', [])
            hash_url = conf.get('hash_url', '')
            hash_config = self.get_config_value(conf, 'hash_config', [])
            lang = conf.get('lang', '')
        except Exception as e:
           self._logger.error(f"Error reading configuration: {str(e)}")
           search_head_url = token = index_master_url = hec_token = ''
           inbound_url = outbound_url = hash_url = ''
           inbound_config = outbound_config = hash_config = []
           lang = ''
        set_response(self.response, {'search_head_url':search_head_url,
        'token':token, 'index_master_url':index_master_url,'hec_token':hec_token,'inbound_url':inbound_url,
        'inbound_config':inbound_config, 'outbound_url':outbound_url,'outbound_config':outbound_config,'hash_url':hash_url,
        'hash_config':hash_config,'lang':lang})


    def handle_POST(self):
        # 获取请求体并解析 JSON 数据
        try:
            request_body = self.request['payload']
            data = json.loads(request_body)  # 将JSON字符串解析为Python字典
        except Exception as e:
            error_message = str(e)  # 获取具体的异常信息
            self._logger.error("解析post传参失败：%s", error_message)
            set_response(self.response, {'error': 'Invalid JSON format','details': error_message}, 400)
            return
        search_head_url = data.get('search_head_url')
        token = data.get('token')
        index_master_url = data.get('index_master_url')
        hec_token = data.get('hec_token')
        if not (search_head_url and token and index_master_url and hec_token):
            self._logger.error("基础信息为必填，请检查基础信息配置")
            set_response(self.response, {'error': 'Basic configuration parameters are mandatory'}, 400)
            return
        if ':' not in search_head_url:
            self._logger.error("search_head_url填写应该包含端口号")
            set_response(self.response, {'error': 'Splunk_URL filling does not meet the specifications'}, 400)
            return 
        host_port_list = search_head_url.strip().rsplit(';')
        #获取splunk服务的连接
        splunk_service = connect_to_splunk(host_port_list, token,self._logger)
        if splunk_service == 0:
            set_response(self.response, {'error': 'Splunk service connection exception'}, 400)
            return

        inbound_url = data.get("inbound_url")
        inbound_config = data.get('inbound_config')
        outbound_url = data.get("outbound_url")
        outbound_config = data.get("outbound_config")
        hash_url = data.get("hash_url")
        hash_config = data.get("hash_config")
        # 对其输入索引是否存在进行判断
        check_result = check_index_result(inbound_url, inbound_config, splunk_service, self._logger, 'in')
        if check_result == 1:
            set_response(self.response, {'error': 'The input index does not exist in the inbound configuration'}, 400)
            return
        elif check_result == 2:
            set_response(self.response, {'error': 'Exception occurred while reading index'}, 400)
            return

        check_result = check_index_result(outbound_url, outbound_config, splunk_service,self._logger, 'out')
        if check_result == 1:
            set_response(self.response, {'error': 'The input index does not exist in the outbound configuration'}, 400)
            return
        elif check_result == 2:
            set_response(self.response, {'error': 'Exception occurred while reading index'}, 400)
            return

        check_result = check_index_result(hash_url, hash_config, splunk_service,self._logger, 'hash')
        if check_result == 1:
            set_response(self.response, {'error': 'The input index does not exist in the hash configuration'}, 400)
            return
        elif check_result == 2:
            set_response(self.response, {'error': 'Exception occurred while reading index'}, 400)
            return

        # 保存配置
        try:
            bun = splunk.bundle.getConf('application', self.sessionKey,namespace='Threatbook-TIP-v9',owner='nobody')
            bun.beginBatch()
            conf = bun['config']
            for key, value in data.items():
                if isinstance(value, list):  # 如果是列表或其他复杂数据结构
                    conf[key] = json.dumps(value)
                else:
                    conf[key] = value
            bun.commitBatch()
        except Exception as e:
            self._logger.error("保存配置文件信息时出现异常：%s", str(e))
            set_response(self.response, {'error': f'Error saving configuration: {str(e)}'}, 400)
            return
        set_response(self.response, {"ok": "setting success!"})

