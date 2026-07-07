#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project:
@File   :tj_business.py
@Author :Imocence
@Date   :2024/4/12 
"""
try:
    import configparser
except:
    import ConfigParser
import crontab, json, logging, os, re, time, threading
from multiprocessing.pool import ThreadPool
from tj_entreat import Entreat

spl_home = os.environ.get('SPLUNK_HOME')
current_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
log_format = '%(asctime)s %(levelname)s [%(name)s:%(lineno)d] %(message)s'
log_filename = os.path.join(spl_home, 'var', 'log', 'splunk', 'splunk_instrumentation.log')
logging.basicConfig(format=log_format, level=logging.INFO, filemode='a', filename=log_filename)
logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(logging.WARNING)
cron_exp = "0 30 15 * * ?"
Flag = True


def singleton(cls):
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper


@singleton
class Business(object):

    def __init__(self):
        self._log = logging.getLogger(__name__)
        self.spl_api_url = "https://127.0.0.1:8088/services/collector/event"
        self.tj_api_url = "https://api.tj-un.com/v1/iocs"
        self.tj_app_path = os.path.join(spl_home, 'etc', 'apps', "tjym") if spl_home else current_dir
        self.tj_conf_path = os.path.join(self.tj_app_path, 'default', 'tjym.conf')
        try:
            self.config = configparser.ConfigParser()
        except:
            self.config = ConfigParser.ConfigParser()
        self.read_file()
        if not self.get_conf('tj_token'):
            self.copy_conf()
        if self.config.getboolean('tjym', "job_state"):
            self.cron_job()
        self.spl_token = ""

    def read_file(self):
        try:
            self.config.read(self.tj_conf_path)
        except configparser.Error as e:
            self._log.error("Error reading configuration file:{}".format(e))

    def get_conf(self, _key):
        return self.config.get("tjym", _key)

    def copy_conf(self):
        regex = re.compile("default.old.")
        conf_bak = None
        for entry in os.listdir(self.tj_app_path):
            if regex.match(entry):
                conf_bak = os.path.join(self.tj_app_path, entry, 'tjym.conf')
                break
        if conf_bak:
            self._log.info("bak file path: {}".format(conf_bak))
            self.config.read(conf_bak)
            bak_read = dict(self.config.items('tjym'))
            self.read_file()
            for key, value in bak_read.items():
                self.config.set('tjym', key, str(value))
            with open(self.tj_conf_path, 'w') as configfile:
                self.config.write(configfile)
            self._log.info("copy config success!")

    @staticmethod
    def _get_form_val(argus, key_name):
        """
        从给定的数据中获取指定 token 的值。

        Args:
        - params (dict): 数据字典。
        - key_name (str): 要获取值的名称。

        Returns:
        - str or None: 如果找到了指定 token，则返回其值；否则返回 None。
        """
        try:
            token_value = argus[key_name]
        except KeyError:
            if "form" in argus and isinstance(argus["form"], list):
                token_value = next((item[1] for item in argus["form"] if item[0] == key_name), "")
            else:
                token_value = ""
        return token_value

    @staticmethod
    def deal_iocs_json(iocs):
        """
        解析IOCS
        :param iocs:
        :return:
        """
        result_iocs = []
        for ioc in iocs:
            if ioc.get('type') == "indicator":
                s_label = ioc.pop('labels')
                if s_label is not None:
                    for label in s_label:
                        reputations = label.pop('reputation')
                        if reputations is not None:
                            for reputation in reputations:
                                reputation['type'] = label.get('type')
                                reputation['value'] = label.get('value')
                                reputation.update(label)
                                result_iocs.append(reputation)
            else:
                pass
        return result_iocs

    def _send_request(self, data):
        spl_headers = {'Authorization': 'Splunk {}'.format(self.spl_token)}
        spl_code, spl_body, spl_heads = Entreat(url=self.spl_api_url, method='POST', headers=spl_headers,
                                                content_type=Entreat.CONTENT_TYPE_JSON,
                                                body={'event': data, "sourcetype": '_tjym'}).execute()
        return spl_code

    def __thread_poll(self):
        """
        线程执行任务
        :return:
        """
        self.read_file()
        self._log.info("Thread begin.")
        self.spl_token = self.get_conf("spl_token")
        tj_token = self.get_conf("tj_token")
        poll_params = {"token": tj_token}
        types = self.get_conf("types")
        types = json.loads(types) if types else types
        if types:
            poll_params["type"] = ",".join(types)
        scores = self.get_conf("score")
        scores = json.loads(scores) if scores else scores
        scores = scores if isinstance(scores, list) else [scores]
        if scores and scores[0] and scores[1]:
            poll_params["score_from"] = scores[0]
            poll_params["score_to"] = scores[1]
        limit = self.get_conf("limit")
        if limit:
            poll_params["limit"] = limit
        self._log.info("Execute parameter content: {}\n".format(poll_params))
        if tj_token and self.spl_token:
            _page = '1'
            pool = ThreadPool(processes=10)
            while _page:
                try:
                    self._log.info("Query page: {}.".format(_page))
                    poll_params["page"] = _page
                    r_code, r_body, r_heads = Entreat(url=self.tj_api_url, body=poll_params, method='POST').execute()
                    if r_code == 200:
                        rj = json.loads(r_body)
                        if rj['response_status']['code'] == 1 and Flag:
                            pool.map(self._send_request, self.deal_iocs_json(rj['response_data']))
                            _page = rj['nextpage']
                            time.sleep(1)
                        else:
                            break
                    else:
                        self._log.error("Request to return an error message: {}.".format(r_body.encode('utf-8')))
                except IOError:
                    pass
        else:
            self._log.error("No token was obtained")
        self._log.info("Thread Done.")

    def __start_cron(self):
        """
        定时任务启动
        :return:
        """
        global cron_exp, Flag
        while Flag:
            cron_list = crontab.parse_cron_tab(cron_exp)
            now = time.localtime()
            if now.tm_sec in cron_list['second'] and now.tm_min in cron_list['minutes'] \
                    and now.tm_hour in cron_list['hours'] and now.tm_mday in cron_list['monthdays'] \
                    and now.tm_mon in cron_list['months'] and now.tm_wday in cron_list['weekdays']:
                self._log.info("Thread cron: {}.".format(cron_exp))
                self.__thread_poll()
            time.sleep(1)
        self._log.info("Job stop running!!")

    def cron_job(self):
        threading.Thread(target=self.__start_cron, name="cron_job").start()
        self._log.info("Job starts running.")

    def api_job(self, in_string):
        result = {'msg': "Execution job failed"}
        result_status = 200
        global Flag
        try:
            api_params = json.loads(in_string)
            _Method = api_params['method'].lower()
            if _Method == 'post':  # 开启自动更新
                self.read_file()
                if not self.config.getboolean('tjym', "job_state"):
                    self.config.set('tjym', 'job_state', str(True))
                    with open(self.tj_conf_path, 'w') as configfile:
                        self.config.write(configfile)
                        Flag = True
                    self.cron_job()
                    result['msg'] = "`Get intelligence periodically` setting is activated!"
                else:
                    result['msg'] = "`Get intelligence periodically` has already been set!"
                result['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            elif _Method == 'put':
                self.read_file()
                self.config.set('tjym', 'job_state', str(False))
                with open(self.tj_conf_path, 'w') as configfile:
                    self.config.write(configfile)
                    Flag = False
                    self._log.info("Job stop!")
                result['msg'] = "stop job success"
            elif _Method == 'get':  # 立即更新数据
                self._log.info("Data is updated!!")
                threading.Thread(target=self.__thread_poll).start()
                result['msg'] = "Start to get data from RedQueen periodically!"
            result['state'] = Flag
        except Exception as e:
            result_status = 201
            result['msg'] = "can't start read TianJi Partners IOCS, error: {}".format(str(e))
            self._log.error("Job interface exception: {}".format(e))

        return result, result_status

    def token(self, in_string):
        """
        编辑token信息
        :param in_string:
        :return:
        """
        result = {'msg': "Execution token failed"}
        result_status = 201
        try:
            self.read_file()
            token_params = json.loads(in_string)
            _Method = token_params['method'].lower()
            if _Method == 'post':
                spl_token = self._get_form_val(token_params, "splToken")
                tj_token = self._get_form_val(token_params, "secunToken")
                cron_str = self._get_form_val(token_params, "cronStr").split(':')
                types = list(filter(None, self._get_form_val(token_params, "types")))
                scores = self._get_form_val(token_params, "score")
                limit = self._get_form_val(token_params, "limit")
                if spl_token and tj_token:
                    global cron_exp
                    self.config.set('tjym', 'spl_token', str(spl_token))
                    self.config.set('tjym', 'tj_token', str(tj_token))
                    cron_exp = str('0 {} {} * * ?'.format(cron_str[1], cron_str[0]))
                    self.config.set('tjym', 'cron_str', cron_exp)
                    self.config.set('tjym', 'types', json.dumps(types if isinstance(types, list) else [types]))
                    self.config.set('tjym', 'score', json.dumps(scores if isinstance(scores, list) else []))
                    self.config.set('tjym', 'limit', limit)
                    with open(self.tj_conf_path, 'w') as configfile:
                        self.config.write(configfile)
                    result['msg'] = "save success"
            elif _Method == 'get':
                result['spl_token'] = self.get_conf("spl_token")
                result['tj_token'] = self.get_conf("tj_token")
                result['cron_str'] = crontab.parse_cron_time(self.get_conf("cron_str"))
                result['types'] = self.get_conf("types")
                result['score'] = self.get_conf("score")
                result['limit'] = self.get_conf("limit")
                result['msg'] = "query success"
            result_status = 200
        except Exception as e:
            self._log.error("Token interface exception: {}".format(e))

        return result, result_status

    def index(self):
        """
        判断是否设置token
        :return: 返回对应页面路径
        """
        index_path = "./IndexNoToken"
        try:
            self.read_file()
            spl_token = self.get_conf("spl_token")
            tj_token = self.get_conf("tj_token")
            if spl_token and tj_token:
                index_path = "./Index"
        except IOError:
            pass

        return index_path


if __name__ == '__main__':
     print("111")

