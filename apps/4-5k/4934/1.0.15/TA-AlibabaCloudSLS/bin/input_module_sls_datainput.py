# encoding = utf-8

import os
import sys
import time
from aliyun.log.consumer import *
from aliyun.log.pulllog_response import PullLogResponse
from aliyun.log.platform import is_linux_x64, is_py37_or_higher
import json
import socket
import requests
from requests.adapters import HTTPAdapter

SUCCESS = 0
FAIL = 1


use_linux_x64_processor = False

if is_linux_x64() and is_py37_or_higher():
    try:
        from aliyun_log_splunk_utils import SplunkPrivateConverter, SplunkHecConverter
        use_linux_x64_processor = True
    except Exception as ex:
        use_linux_x64_processor = False

class SyncDataBase(ConsumerProcessorBase):
    """
    this consumer will forward logs to Splunk.
    """
    
    def log_info(self, msg):
        self.helper.log_info('[' + self.input_name + '] ' + msg)
    
    def log_warning(self, msg):
        self.helper.log_warning('[' + self.input_name + '] ' + msg)

    def __init__(self, helper, ew, splunk_setting=None):
        super(SyncDataBase, self).__init__()  # remember to call base's init
        self.helper = helper
        self.input_name = str(self.helper.get_input_stanza_names())

        self.option = splunk_setting
        self.protocol = self.option.get("protocol")
        self.event_source = self.option.get("event_source")
        self.event_sourcetype = self.option.get("event_sourcetype")
        self.event_retry_times = sys.maxsize if 0 == self.option.get("event_retry_times") else self.option.get(
            "event_retry_times")
        self.retry_sleep_time = 0.1
        self.threshold_times_of_retry_sleep = 3
        self.topic_filter_list = [x for x in self.option.get("topic_filter").split(';') if x]
        if self.option.get("unfolded_fields"):
            self.unfolded_fields_map = json.loads(self.option.get("unfolded_fields"))
        else:
            self.unfolded_fields_map = {}

        if self.protocol == "private":
            self.ew = ew
            self.log_info("SLS info: SyncData init. protocol[{0}], topic_filter[{1}], unfolded_fileds[{2}]"
                                 .format(self.protocol, str(self.topic_filter_list), self.unfolded_fields_map))
        else:
            self.hec_timeout = self.option["hec_timeout"]

            # Testing connectivity
            s = socket.socket()
            s.settimeout(self.hec_timeout)
            s.connect((self.option["hec_host"], self.option['hec_port']))

            self.r = requests.session()
            self.r.max_redirects = 1
            self.r.verify = self.option.get("hec_ssl_verify")
            self.r.headers['Authorization'] = "Splunk {}".format(self.option['hec_token'])
            self.hec_url = "{0}://{1}:{2}/services/collector" \
                .format(self.protocol, self.option['hec_host'], self.option['hec_port'])

            self.log_info("SLS info: SyncData init. protocol[{0}], hec_ssl_verify[{1}]"
                                 "hec_url[{2}], hec_timeout[{3}], topic_filter[{4}], unfolded_fileds[{5}]"
                                 .format(self.protocol, self.r.verify, self.hec_url,
                                         self.hec_timeout, str(self.topic_filter_list), self.unfolded_fields_map))


    def send_event_by_private(self, send_event):
        for t in range(self.event_retry_times):
            try:
                self.ew.write_event(send_event)
            except Exception as err:
                self.log_warning(
                    "SLS info: Failed to write [{0}] remote Splunk server using event_writer. Exception: {1}, times: {2}"
                        .format(send_event, err, t + 1))
                if t >= self.threshold_times_of_retry_sleep:
                    time.sleep(self.retry_sleep_time)
            else:
                return SUCCESS
        return FAIL

    def send_event_by_hec(self, send_event):
        for t in range(self.event_retry_times):
            try:
                req = self.r.post(self.hec_url, data=send_event, timeout=self.hec_timeout)
                req.raise_for_status()
            except Exception as err:
                self.log_warning(
                    "SLS info: Failed to write [{0}] remote Splunk server ({1}) using hec. Exception: {2}, times: {3}"
                        .format(send_event, self.hec_url, err, t + 1))
                if t >= self.threshold_times_of_retry_sleep:
                    time.sleep(self.retry_sleep_time)
            else:
                return SUCCESS
        return FAIL

    def send_private(self, inner_event_str, index, log_time=None):
        if log_time is None:
            send_event = self.helper.new_event(source=self.event_source, index=index,
                                               sourcetype=self.event_sourcetype, data=inner_event_str)
        else:
            send_event = self.helper.new_event(source=self.event_source, index=index,
                                               time=log_time,
                                               sourcetype=self.event_sourcetype, data=inner_event_str)
        self.helper.logger.debug("SLS info: ew process %s", inner_event_str)
        return SUCCESS == self.send_event_by_private(send_event)

    def send_hec(self, hec_event_str):
        self.helper.logger.debug("SLS info: hec process %s", hec_event_str)
        return SUCCESS == self.send_event_by_hec(hec_event_str)

class SyncData(SyncDataBase):
    def __init__(self, helper, ew, splunk_setting=None):
        super(SyncData, self).__init__(helper, ew, splunk_setting)
        self.exclude_fields_set = set(splunk_setting.get("exclude_fields").split(",") if splunk_setting.get("exclude_fields") else [])

    def process(self, log_groups, check_point_tracker):
        logs = PullLogResponse.loggroups_to_flattern_list(log_groups, time_as_str=True, decode_bytes=True)
        index = self.helper.get_output_index()
        self.helper.logger.info("SLS info: Get data from shard %d, log count: %d, protocol: %s, "
                                "source: %s, index: %s, sourcetype: %s, stanza_name: %s",
                                self.shard_id, len(logs), self.protocol,
                                self.event_source, index, self.event_sourcetype,
                                self.helper.get_input_stanza_names())

        success_send_num = 0
        topic_filter_num = 0
        for log in logs:
            # Put your sync code here to send to remote.
            # the format of log is just a dict with example as below (Note, all strings are unicode):
            #    Python2: {u"__time__": u"12312312", u"__topic__": u"topic", u"field1": u"value1", u"field2": u"value2"}
            #    Python3: {"__time__": "12312312", "__topic__": "topic", "field1": "value1", "field2": "value2"}
            # self.helper.log_info("log = {0}".format(log))
            # del log['__time__']

            # topic filter
            topic = log.get("__topic__", "")
            if topic in self.topic_filter_list:
                topic_filter_num += 1
                continue

            # field unfold
            if topic in self.unfolded_fields_map:
                try:
                    for field in self.unfolded_fields_map[topic]:
                        log[field] = json.loads(log[field])
                except Exception as ex:
                    pass

            for field in self.exclude_fields_set:
                if field in log:
                    del log[field]

            inner_event_str = json.dumps(log, ensure_ascii=False)

            if self.protocol == "private":
                if self.send_private(inner_event_str, index, log_time=log[u'__time__']):
                    success_send_num += 1
            else:
                hec_event_str = self.to_hec_event(inner_event_str, log[u'__time__'], index)
                if self.send_hec(hec_event_str):
                    success_send_num += 1

        self.helper.logger.info("SLS info: Complete send data to remote. "
                                "total[%d], success_send_num[%d], topic_filter_num[%d], fail_num[%d], stanza_name: %s",
                                len(logs), success_send_num, topic_filter_num,
                                len(logs) - success_send_num - topic_filter_num,
                                self.helper.get_input_stanza_names())

        self.save_checkpoint(check_point_tracker)
    
    def to_hec_event(self, inner_event_str, log_time_str, index):
        event = {}
        event['time'] = log_time_str
        event['event'] = inner_event_str
        event['index'] = index
        if self.event_sourcetype:
            event['sourcetype'] = self.event_sourcetype
        if self.event_source:
            event['source'] = self.event_source

        send_event = json.dumps(event, sort_keys=True, ensure_ascii=False)
        return send_event

class SyncDataLinuxX64(SyncDataBase):
    def __init__(self, helper, ew, splunk_setting=None):
        super(SyncDataLinuxX64, self).__init__(helper, ew, splunk_setting)
        topic_filters = self.option.get("topic_filter")
        unfolded_fields_map = self.option.get("unfolded_fields")
        exclude_fields = self.option.get("exclude_fields")
        index = self.helper.get_output_index()
        if self.protocol == "private":
            self.converter = SplunkPrivateConverter(
                topic_filters=topic_filters, unfolded_fields_map=unfolded_fields_map, exclude_fields=exclude_fields)
        else:
            self.converter = SplunkHecConverter(
                index=index, event_source=self.event_source,
                source_type=self.event_sourcetype,
                topic_filters=topic_filters,
                unfolded_fields_map=unfolded_fields_map,
                exclude_fields=exclude_fields)
        self.cached_events = []

    def process(self, data, check_point_tracker):
        event_strs, log_times, topic_filter_num = data
        index = self.helper.get_output_index()
        self.helper.logger.info("SLS info: Get data from shard %d, log count: %d, protocol: %s, "
                                "source: %s, index: %s, sourcetype: %s, stanza_name: %s",
                                self.shard_id, len(event_strs), self.protocol,
                                self.event_source, index, self.event_sourcetype,
                                self.helper.get_input_stanza_names())
        success_send_num = 0
        length = len(event_strs)
        for i in range(length):
            event_str = event_strs[i] # str
            log_time = log_times[i] # int
            if self.protocol == "private":
                if self.send_private(event_str, index, log_time):
                    success_send_num += 1
            else:
                if self.send_hec_batched(event_str, i >= length - 1):
                    success_send_num += 1

        self.helper.logger.info("SLS info: Complete send data to remote. "
                                "total[%d], success_send_num[%d], topic_filter_num[%d], fail_num[%d]",
                                len(event_strs), success_send_num, topic_filter_num,
                                len(event_strs) - success_send_num - topic_filter_num)

        self.save_checkpoint(check_point_tracker)

    def _override_preprocess(self, pull_log_response):
        if pull_log_response._raw_uncompressed_body is None:
            return []
        return self.converter.convert(pull_log_response._raw_uncompressed_body)
    
    def send_hec_batched(self, event_str, is_last_log):
        self.cached_events.append(event_str)
        if len(self.cached_events) > 500 or is_last_log:
            to_send = "\n".join(self.cached_events)
            self.cached_events = []
            self.send_hec(to_send)
        return True

def parse_data_fetch_interval(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

class EcsRamCredentialsRefresher(object):
    def __init__(self, role_name):
        self.ecs_meta_url = 'http://100.100.100.200/latest/meta-data/ram/security-credentials/%s' % role_name

    def __call__(self):
        session = requests.Session()
        session.mount('http://', HTTPAdapter(max_retries=5))
        session.mount('https://', HTTPAdapter(max_retries=5))

        resp = session.get(self.ecs_meta_url).json()
        return resp.get("AccessKeyId"), resp.get("AccessKeySecret"), resp.get("SecurityToken")


def get_monitor_option(helper):
    ##########################
    # Basic options
    ##########################
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    # load connection info env and consumer group name from envs
    accessKeyId = helper.get_arg('sls_accesskey')['username']
    accessKey = helper.get_arg('sls_accesskey')['password']
    endpoint = helper.get_arg('sls_endpoint')
    project = helper.get_arg('sls_project')
    logstore = helper.get_arg('sls_logstore')
    consumer_group = helper.get_arg('sls_cg')

    # check if use ECS RAM role
    securityToken = None
    ecs_ram_role = None
    refresher = None
    if accessKeyId == "ECS_RAM_ROLE":
        ecs_ram_role = accessKey
        refresher = EcsRamCredentialsRefresher(ecs_ram_role)
        try:
            accessKeyId, accessKey, securityToken = refresher()
        except Exception as ex:
            helper.log_error("ECS RAM Role detected in user config, but failed to get ECS RAM credentials. "
                             "Please check if ECS instance and RAM role '{role_name}' are configured appropriately. "
                             "details: {details}".format(role_name=ecs_ram_role, details=str(ex)))
            return None, None

    ssl_verify = os.environ.get('HEC_SSL_VERIFY', '')
    if "True" == ssl_verify:
        hec_ssl_verify = True
    else:
        hec_ssl_verify = False

    # splunk options
    hec_port = 0
    hec_timeout = 0
    if helper.get_arg('protocol') == 'https':
        hec_port_str = helper.get_arg('hec_port')
        if hec_port_str is not None and hec_port_str != '' and hec_port_str.isdigit():
            hec_port = int(hec_port_str)
        hec_timeout_str = helper.get_arg('hec_timeout')
        if hec_timeout_str is not None and hec_timeout_str != '' and hec_timeout_str.isdigit():
            hec_timeout = int(hec_timeout_str)

    consume_processor = helper.get_arg('consume_processor')
    if consume_processor == '':
        consume_processor = None

    settings = {
        'protocol': helper.get_arg('protocol'),
        "topic_filter": "" if None == helper.get_arg('topic_filter') else helper.get_arg('topic_filter'),
        'unfolded_fields': "" if None == helper.get_arg('unfolded_fields') else helper.get_arg('unfolded_fields'),
        'event_retry_times': int(helper.get_arg('event_retry_times')),
        "event_source": "" if None == helper.get_arg('event_source') else helper.get_arg('event_source'),
        "event_sourcetype": "" if None == helper.get_arg('event_sourcetype') else helper.get_arg('event_sourcetype'),
        "hec_host": helper.get_arg('hec_host'),
        "hec_port": hec_port,
        "hec_token": helper.get_arg('hec_token'),
        'hec_timeout': hec_timeout,
        'hec_ssl_verify': hec_ssl_verify,
        'exclude_fields': "" if None == helper.get_arg('exclude_fields') else helper.get_arg('exclude_fields'),
    }

    assert endpoint and accessKeyId and accessKey and project and logstore and consumer_group, \
        ValueError("endpoint/access_id/key/project/logstore/consumer_group/name cannot be empty")

    ##########################
    # Some advanced options
    ##########################

    # DON'T configure the consumer name especially when you need to run this program in parallel
    consumer_name = "{0}-{1}-{2}".format(consumer_group, helper.get_arg("name"), helper.get_arg('protocol'))

    # This options is used for initialization, will be ignored once consumer group is created and each shard has beeen started to be consumed.
    # Could be "begin", "end", "specific time format in ISO", it's log receiving time.
    cursor_start_time = helper.get_arg('sls_cursor_start_time')

    # once a client doesn't report to server * heartbeat_interval * 2 interval, server will consider it's offline and re-assign its task to another consumer.
    # thus  don't set the heatbeat interval too small when the network badwidth or performance of consumtion is not so good.
    heartbeat_interval = int(helper.get_arg('sls_heartbeat_interval'))

    # if the coming data source data is not so frequent, please don't configure it too small (<1s)
    data_fetch_interval = parse_data_fetch_interval(helper.get_arg('sls_data_fetch_interval'))

    # fetch size in each request, normally use default. maximum is 1000, could be lower. the lower the size the memory efficiency might be better.
    max_fetch_log_group_size = int(helper.get_arg('sls_max_fetch_log_group_size'))

    # create one consumer in the consumer group
    option = LogHubConfig(endpoint, accessKeyId, accessKey, project, logstore, consumer_group, consumer_name,
                          cursor_position=CursorPosition.SPECIAL_TIMER_CURSOR,
                          cursor_start_time=cursor_start_time,
                          heartbeat_interval=heartbeat_interval,
                          data_fetch_interval=data_fetch_interval,
                          max_fetch_log_group_size=max_fetch_log_group_size,
                          security_token=securityToken,
                          credentials_refresher=refresher,
                          processor=consume_processor
                          )

    helper.log_info("SLS info: input started, endpoint[{0}], project[{1}], logstore[{2}], "
                    "consumer_group[{3}], loglevel[{4}], cursor_start_time[{5}], input_name={6}, consume_processor[{7}]"
                    .format(endpoint, project, logstore, consumer_group, loglevel, cursor_start_time, str(helper.get_input_stanza_names()), consume_processor if consume_processor else "None"))

    return option, settings


'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


# For advanced users, if you want to create single instance mod input, uncomment this method.
# def use_single_instance_mode():
#     return True

def is_json(input_string):
    try:
        json.loads(input_string)
    except Exception:
        return False
    return True


def validate_data_fetch_interval(s):
    if s.isdigit():
        return

    try:
        float(s)
        return
    except ValueError:
        raise ValueError("sls_data_fetch_interval must be digit.")

def require_not_empty(definition, name):
    if None == definition.parameters.get(name, None):
        raise ValueError("Invalid hec config {}: {}.".format(name,definition.parameters.get(name, None)))

    if definition.parameters.get(name, None) == '':
        raise ValueError("Invalid hec config {}: {}.".format(name, definition.parameters.get(name, None)))

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    helper.log_info("SLS info: definition[{0}]".format(definition.parameters))
    if not definition.parameters.get('sls_heartbeat_interval').isdigit():
        raise ValueError("sls_heartbeat_interval must be digit.")

    validate_data_fetch_interval(definition.parameters.get('sls_data_fetch_interval'))

    if not definition.parameters.get('sls_max_fetch_log_group_size').isdigit():
        raise ValueError("sls_max_fetch_log_group_size must be digit.")

    if not definition.parameters.get('event_retry_times').isdigit():
        raise ValueError("event_retry_times must be digit.")

    if not (None == definition.parameters.get('unfolded_fields')
            or "" == definition.parameters.get('unfolded_fields')
            or is_json(definition.parameters.get('unfolded_fields'))):
        raise ValueError("unfolded_fields must be none or json.")

    if "private" != definition.parameters.get('protocol'):
        require_not_empty(definition, 'hec_host')
        require_not_empty(definition, 'hec_port')
        require_not_empty(definition, 'hec_token')
        require_not_empty(definition, 'hec_timeout')

        if not (definition.parameters.get('hec_port').isdigit() and definition.parameters.get('hec_timeout').isdigit()):
            raise ValueError("HEC_PORT and HEC_TIMEOUT must be digit.")

        if not (int(definition.parameters.get('hec_port')) > 0 and int(definition.parameters.get('hec_timeout')) > 0):
            raise ValueError("HEC_PORT and HEC_TIMEOUT must be greater than 0.")

    helper.log_info("SLS info: definition passed validation")


def parse_processor_settings(s):
    return s.lower() == "true" or s.lower() == '1'

def collect_events(helper, ew):
    option, settings = get_monitor_option(helper)
    if option and settings:
        helper.log_info("SLS info: *** start to consume data now...")
        if use_linux_x64_processor and parse_processor_settings(helper.get_arg('use_linux_x86_64_processor')):
            worker = ConsumerWorker(SyncDataLinuxX64, option, args=(helper, ew, settings,))
        else:
            worker = ConsumerWorker(SyncData, option, args=(helper, ew, settings,))
        worker.start(join=True)



