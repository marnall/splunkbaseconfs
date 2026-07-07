# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import json
import splunk.clilib.cli_common as cli_common
import splunklib.client as client
import splunklib.results as results
from datetime import datetime, timedelta
import time
import ipaddress
import requests 
import logging


def read_configuration():
    # 指定配置文件名称和配置节名称
    conf_file = 'application'
    stanza = 'config'
    # 使用 getConfStanza 函数读取配置内容
    try:
        config = cli_common.getConfStanza(conf_file, stanza)
        return config
    except Exception as e:
        # 处理读取配置文件失败的情况
        return None


 # 判断ip是否是公网，公网为true
def is_public_ip(ip):
    try:
        ip_address = ipaddress.ip_address(ip)
        return not ip_address.is_private and not ip_address.is_loopback
    except ValueError:
        return False
    

# splunk服务连接与索引检查
def connect_splunk(host, port, username, password, inputindex, outputindex):
     #读取输入索引的数据进行分析
    try:
        service = client.connect(
        host=host,
        port=port,
        username=username,
        password=password
        )
    except:
        return 0
    #判断输入、输出索引是否存在
    indexes = service.indexes
    if inputindex not in indexes:       
        return 1
    if outputindex not in indexes:
        return 2
    return service

def get_time(current_time, minutes):
    # 将秒级时间戳转换为datetime对象
    current_dt = datetime.fromtimestamp(current_time)
    # 计算前minutes分钟的时间
    delta = timedelta(minutes=-minutes)
    # 计算前minutes分钟的时间戳
    previous_dt = current_dt + delta
    previous_timestamp = previous_dt.timestamp()
    return int(previous_timestamp)


# 查询索引数据
def seletct_event(inputindex, start_timestamp, future_timestamp, service):
    # 构建输入索引搜索查询
    input_query = "search index={} _indextime>{} _indextime<{}".format(inputindex, start_timestamp, future_timestamp)
    job = service.jobs.create(input_query)
    # 等待搜索完成
    while not job.is_done():
        pass
    # 获取搜索结果
    search_results = results.ResultsReader(job.results())
    return search_results,job


# 数据输出到输出索引
def output_index(apikey, resource, url, event_data, service, outputindex,lang):
    query = {"apikey" : apikey, "resource" : resource, "lang" : lang}
    headers = {"Content-Type": "application/json;charset=utf-8"}
    response = requests.get(url,headers=headers, params=query)
    json_data = json.loads(response.text)
    if json_data["response_code"] == 0:
        first_data_item = json_data['data'][0]
        raw_log = {}
        raw_log['raw'] = event_data
        first_data_item.update(raw_log)
        json_string = json.dumps(first_data_item)
        service.indexes[outputindex].submit(json_string)
    

class ApiCron():

    def cron(self):
        
        # 配置日志记录器
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)
        # 获取当前日期
        current_date = datetime.now().strftime('%Y-%m-%d')
        log_file_path = os.path.join(script_dir, f'app_{current_date}.log')
        # 设置日志文件处理器
        file_handler = logging.FileHandler(log_file_path)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # 清理前一天的日志
        previous_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        previous_log_file_path = os.path.join(script_dir, f'app_{previous_date}.log')
        if os.path.exists(previous_log_file_path):
            os.remove(previous_log_file_path)
        logger.info("定时任务开始执行")
        # 调用函数读取配置文件内容
        configuration = read_configuration()
        # 检查是否成功读取配置文件
        if configuration:
            splunk_url = configuration.get('splunk_url')
            username = configuration.get('username')
            password = configuration.get('password')
            inbound_inputindex = configuration.get('inbound_inputindex')
            inbound_outputindex = configuration.get('inbound_outputindex')
            inbound_url = configuration.get('inbound_url')
            inbound_apikey = configuration.get('inbound_apikey')
            outbound_inputindex = configuration.get('outbound_inputindex')
            outbound_outputindex = configuration.get('outbound_outputindex')
            outbound_url = configuration.get('outbound_url')
            outbound_apikey = configuration.get('outbound_apikey') 
            lang = configuration.get('lang') 
            logger.info("配置文件内容读取结果: %s", configuration)
        else:
            logger.error('读取配置文件失败')
        if not (splunk_url and username and password):
            logger.error('基础配置参数是必填', exc_info=True)
            return
        if ':' not in splunk_url:
            logger.error('splunk_url填写不符合规范')
            return 
        host_port = splunk_url.strip().rsplit(':', 1)
        host = host_port[0]
        port = host_port[1]

        current_time = int(time.mktime(datetime.now().timetuple()))

        # 入站配置项都不为空，则进行索引读取操作
        if inbound_inputindex and inbound_outputindex and inbound_url and inbound_apikey:
            #读取输入索引的数据进行分析
            in_service = connect_splunk(host, port, username, password, inbound_inputindex, inbound_outputindex)              
            if in_service == 0:
                logging.error('splunk服务连接异常')
                return
            elif in_service == 1:
                logging.error('入站配置中的输入索引不存在')
                return
            elif in_service == 2:
                logging.error('入站配置中的输出索引不存在')
                return
            
            in_start_timestamp = get_time(current_time, 10)
            future_timestamp = current_time
            logger.info("入站配置查询输入索引开始时间：%d",in_start_timestamp)
            logger.info("入站配置查询输入索引截止时间：%d",future_timestamp)
            # 查询返回结果
            in_search_results, in_job = seletct_event(inbound_inputindex, in_start_timestamp, future_timestamp, in_service)
            if hasattr(in_search_results, '__iter__') and any(in_search_results):
                #遍历搜索结果查询对应的api
                for in_result in in_search_results:
                    if isinstance(in_result, dict):
                        #解析日志中关键字段来判断是否存在域名、ip
                        try:    
                            in_event_data = in_result.get('_raw', '{}')
                            in_event_data = json.loads(in_event_data)
                        except Exception as e:
                            continue
                        # 判断事件是否符合入站标准
                        logger.info("入站配置解析原始日志：%s",in_event_data)
                        in_dest_name = in_event_data.get('dest_name')
                        in_src_ip = in_event_data.get('src_ip')
                        in_dest_ip = in_event_data.get('dest_ip')
                        if not in_dest_name:
                            if in_src_ip and in_dest_ip:
                                if is_public_ip(in_src_ip):                                    
                                    try:
                                        logger.info("入站配置根据ip调用tip api：%s", in_src_ip)
                                        output_index(inbound_apikey, in_src_ip, inbound_url, in_event_data, in_service, inbound_outputindex,lang)
                                        logger.info("入站配置调用完api输出至索引完成") 
                                    except Exception as e:
                                        logger.error('入站配置调用api查询输出索引出错:%s', e)
            else:
                logger.info("入站配置时间范围内查询输入索引无数据")
            #关闭搜索任务
            in_job.cancel()        
        else:
            logger.info("入站配置信息填写不全，不执行定时任务,请先到配置页面进行配置信息填写")


        # 出站配置项都不为空，则进行索引读取操作
        if outbound_inputindex and outbound_outputindex and outbound_url and outbound_apikey:
            outservice = connect_splunk(host, port, username, password, outbound_inputindex, outbound_outputindex)              
            if outservice == 0:
                logger.error('splunk服务连接异常')
                return
            elif outservice == 1:
                logger.error('出站配置中的输入索引不存在')
                return
            elif outservice == 2:
                logger.error('出站配置中的输出索引不存在')
                return
            
            out_start_timestamp = get_time(current_time, 10)
            out_future_timestamp = current_time   
            logger.info("出站配置查询输入索引开始时间：%d",out_start_timestamp)
            logger.info("出站配置查询输入索引截止时间：%d",out_future_timestamp) 
            out_search_results, out_job = seletct_event(outbound_inputindex, out_start_timestamp, out_future_timestamp, outservice)
            if hasattr(out_search_results, '__iter__') and any(out_search_results):
                #遍历搜索结果查询对应的api
                for out_result in out_search_results:
                    if isinstance(out_result, dict):
                        #解析日志中关键字段来判断是否存在域名、ip
                        try:    
                            out_event_data = out_result.get('_raw', '{}')
                            out_event_data = json.loads(out_event_data)
                        except:
                            continue
                        # 判断事件是否符合入站标准
                        logger.info("出站配置解析原始日志：%s", out_event_data)
                        out_dest_name = out_event_data.get('dest_name')
                        out_src_ip = out_event_data.get('src_ip')
                        out_dest_ip = out_event_data.get('dest_ip')
                        try:
                            if not out_dest_name:
                                if out_src_ip and out_dest_ip:
                                    if is_public_ip(out_dest_ip): 
                                        logger.info("出站配置所使用域名调用tip api：%s", out_dest_ip)
                                        output_index(outbound_apikey, out_dest_ip, outbound_url, out_event_data, outservice, outbound_outputindex,lang)
                                        logger.info("出站配置调用完api输出至索引任务完成") 
                            else:
                                logger.info("出站配置所使用域名调用tip api：%s", out_dest_name)
                                output_index(outbound_apikey, out_dest_name, outbound_url, out_event_data, outservice, outbound_outputindex,lang)
                                logger.info("出站配置调用完api输出至索引任务完成") 
                        except Exception as e:
                             logger.error('出站配置调用api查询输出索引出错:%s', e)
            else:
                logger.info("出站配置时间范围内查询输入索引无数据")
            # 关闭搜索任务
            out_job.cancel()         
        else:
            logger.info("出站配置信息填写不全，不执行定时任务,请先到配置页面进行配置信息填写")

if __name__ == "__main__":
    #加上日志清理功能
    ApiCron().cron()
