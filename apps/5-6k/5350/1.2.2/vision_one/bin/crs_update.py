import sys

major_version = sys.version_info.major
if major_version == 2:
    import ConfigParser
elif major_version == 3:
    import configparser as ConfigParser

import time, json, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client
import splunklib.results as results
import ssl
import jwt
from crs_config import *
from log_uploader import LogUploader

enable_upload_log = True
LAST_UPLOAD_INDEX_TIMESTAMP_KEY = 'upload_index_timestamp'


class SplunkWrapper(object):

    def __init__(self, splunk_id="splunk_user_id", instance_id="splunk_instance_id", http_proxy=None, https_proxy=None,
                 app_version="1.0.0"):
        self.splunk_id = splunk_id
        self.instance_id = instance_id
        self.http_proxy = http_proxy
        self.https_proxy = https_proxy
        self.default_ssl_context = ssl._create_default_https_context
        self.new_task_file = "was_task_status_0.status.tmp"
        self.expired_task_file = "was_task_status_1.status.tmp"
        self.lock_file_handle = None
        self.app_version = app_version

    def check_config(self):
        search_query = json.dumps({"_key": "was_setup_config"})
        ssl._create_default_https_context = ssl._create_unverified_context
        search_res = self.common_collection.data.query(query=search_query)
        ssl._create_default_https_context = self.default_ssl_context

        if len(search_res) == 0:
            logger.error("User information is not configure!")
            return False

        try:
            self.splunk_id = search_res[0]["email_address"]
            self.user_name = search_res[0]["user_name"]
            self.is_receive_news = 0
            self.upload_token = search_res[0].get('upload_token', '')
            self.vendor_name = search_res[0].get('vendor_name', '')
            self.is_rdnslookup = search_res[0].get('rdnslookup_users', 0)

            logger.debug(
                "check_config >> splunk_id:{} rdnslookup:{}".format(self.splunk_id, self.is_rdnslookup))

            self.upload_fqdn = SplunkWrapper.parse_token(self.upload_token)
            if not self.upload_fqdn:
                # logger.error("invalid token -> {}".format(self.upload_token))
                logger.error("invalid token")
                self.set_update_error(ErrorCode.upload_invalid_token)
                return False

            if search_res[0]["enable_proxy"]:
                user_info = ""
                if search_res[0]["proxy_username"] != "":
                    user_info = "%s:%s@" % (search_res[0]["proxy_username"], search_res[0]["proxy_password"])

                proxy_url = search_res[0]["proxy_type"] + "://" + user_info + search_res[0]["proxy_server"] + ":" + \
                            str(search_res[0]["proxy_port"])
                self.http_proxy = proxy_url
                self.https_proxy = proxy_url
                logger.debug("check_config >> proxy:{}".format(proxy_url))

            if enable_upload_log:
                custom_data = {
                    "user_name": self.user_name,
                    "email_address": self.splunk_id,
                    "vendor_name": self.vendor_name
                }
                self.uploader = LogUploader(self.upload_fqdn, self.upload_token, self.get_log_path(), self.http_proxy,
                                            self.https_proxy, custom_data=custom_data)

            error_code = self.check_network()
            # Update error string in UI. "success" error code will clear previous error string in UI.
            self.set_update_error(error_code)
            if error_code != ErrorCode.success:
                return False

            warning_code = self.check_app_version()
            self.set_update_warning(warning_code)

        except Exception as e:
            logger.error(e)
            return False

        return True

    @classmethod
    def parse_token(cls, token):
        fqdn = ''
        try:
            res = jwt.decode(token, options={"verify_signature": False})
            fqdn = res.get('pl', '')
        except Exception as e:
            logger.error(e)
        return fqdn

    @classmethod
    def get_upload_error_code(cls, ret):
        if ret == LogUploader.RET_SUCCSS:
            return ErrorCode.success
        elif ret == LogUploader.RET_INVLIAD_TOKEN:
            return ErrorCode.invalid_token
        elif ret == LogUploader.RET_NETWORK_ISSUE:
            return ErrorCode.upload_network_issue
        elif ret == LogUploader.RET_UNKNOWN:
            return ErrorCode.upload_unknown
        else:
            return ErrorCode.upload_unknown

    def check_app_version(self):
        # should call after check_network
        logger.info("check_app_version start")
        return WarningCode.success

    def check_network(self):
        logger.debug("check_network start")

        if enable_upload_log:
            rc = self.uploader.check_token()
            logger.debug("uploader> check_token:{}".format(rc))
            error_code = SplunkWrapper.get_upload_error_code(rc)
            print("error_code:{}".format(error_code))
            logger.debug("uploader> error_code:{}".format(error_code))
            return error_code

    def connect(self, username=None, password=None, token=None):
        ssl._create_default_https_context = ssl._create_unverified_context
        try:
            if token == None:
                # connect use username
                self.service = client.connect(host="localhost", port=8089, username=username, password=password,
                                              app=APP_NAME)
            else:
                self.service = client.connect(host="localhost", port=8089, token=token, app=APP_NAME)

            self.dstcrs_collection = self.service.kvstore['dstcrscollection']
            self.common_collection = self.service.kvstore['commoncollection']

            logger.info("SplunkWrapper connect success")
        except Exception as e:
            logger.error(e)

        ssl._create_default_https_context = self.default_ssl_context

    def set_init_flag(self, init_finish):
        try:
            search_res = [{"_key": "was_crs_init", "InitFinish": init_finish, "type": "warning"}]
            ssl._create_default_https_context = ssl._create_unverified_context
            self.common_collection.data.batch_save(*search_res)
            ssl._create_default_https_context = self.default_ssl_context

            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_init_flag(self):
        try:
            search_query = json.dumps({"_key": "was_crs_init"})
            ssl._create_default_https_context = ssl._create_unverified_context
            search_res = self.common_collection.data.query(query=search_query)
            ssl._create_default_https_context = self.default_ssl_context
            logger.info("get_init_flag search_res" + str(search_res))
            init_flag = search_res[0]["InitFinish"]
            return init_flag
        except Exception as e:
            logger.info(e)
            return 0

    def set_update_warning(self, warning_code):
        if type(warning_code) != int:
            warning_code = warning_code.value
        try:
            search_res = [
                {"_key": "was_crs_warning", "WarningCode": warning_code, "WarningString": WARNING_STRING[warning_code],
                 "type": "warning"}]
            ssl._create_default_https_context = ssl._create_unverified_context
            self.common_collection.data.batch_save(*search_res)
            ssl._create_default_https_context = self.default_ssl_context
            return True
        except Exception as e:
            logger.error(e)
            return False

    def set_update_error(self, error_code):
        if type(error_code) != int:
            error_code = error_code.value
        try:
            search_res = [{"_key": "was_crs_error", "ErrorCode": error_code, "ErrorString": ERROR_STRING[error_code],
                           "type": "error"}]
            ssl._create_default_https_context = ssl._create_unverified_context
            self.common_collection.data.batch_save(*search_res)
            ssl._create_default_https_context = self.default_ssl_context
            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_task_status(self, task_id):
        # 1 means task is running
        # 0 means task is not running
        try:

            lock_file_name = ""
            if task_id == 0:
                lock_file_name = self.new_task_file
            else:
                lock_file_name = self.expired_task_file

            if os.path.exists(lock_file_name):
                # if file exists, but no process ocupied it, means no task running
                if PLATFORM_STR == "Windows":
                    os.remove(lock_file_name)
                    return 0
                else:
                    # In linux, file can be delete if another process opened it.
                    return 1
            else:
                return 0

        except Exception as e:
            # someone opened lock_file, so there is another task running
            logger.warning(e)
            return 1

    def set_task_status(self, task_id, value):
        try:
            lock_file_name = ""
            if task_id == 0:
                lock_file_name = self.new_task_file
            else:
                lock_file_name = self.expired_task_file

            # value
            # 0: finish task
            # 1: task running
            if value == 0:
                if self.lock_file_handle:
                    self.lock_file_handle.close()
                try:
                    os.remove(lock_file_name)
                except Exception as e:
                    logger.info(e)
            else:
                self.lock_file_handle = open(lock_file_name, "w+")

            return True
        except Exception as e:
            logger.error(e)
            return False

    def set_cache(self, key, value):
        try:
            search_res = [{"_key": key, "DestDataBookMark": value, "type": "info"}]
            ssl._create_default_https_context = ssl._create_unverified_context
            self.common_collection.data.batch_save(*search_res)
            ssl._create_default_https_context = self.default_ssl_context
            return True
        except Exception as e:
            logger.error(e)
            return False

    def get_cache(self, key):
        # return 0 if not exist
        try:
            search_query = json.dumps({"_key": key})
            ssl._create_default_https_context = ssl._create_unverified_context
            search_res = self.common_collection.data.query(query=search_query)
            ssl._create_default_https_context = self.default_ssl_context
            logger.info("get cache: {} - {}".format(key, str(search_res)))
            last_item = search_res[0]["DestDataBookMark"]
            return last_item
        except Exception as e:
            logger.info(e)
            return 0

    def get_log_path(self):
        log_path = './'
        home = get_splunk_home()
        if home:
            log_path = os.path.join(home, 'etc', 'apps', APP_NAME, 'bin')
        return log_path

    @classmethod
    def next_search_time(cls, prev_search_time, current_time, max_interval, min_interval):
        # try to search hours
        interval = max_interval
        next_search_time = (prev_search_time + interval) // interval * interval
        if next_search_time > current_time:
            # downgrade to min_interval
            interval = min_interval
            next_search_time = (prev_search_time + interval) // interval * interval
        if next_search_time > current_time:
            # no more than 1 hour, set to last_search_time
            next_search_time = prev_search_time
        return next_search_time

    def upload_summary_log(self):
        error_code = ErrorCode.success
        try:
            print("upload_summary_log start")
            last_index_time = self.get_cache(LAST_UPLOAD_INDEX_TIMESTAMP_KEY)
            current_time = time.time()
            if last_index_time == 0:
                # first run, update it
                last_index_time = current_time - DEFAULT_LAST_SEARCH_DAYS * 86400
                self.set_cache(LAST_UPLOAD_INDEX_TIMESTAMP_KEY, last_index_time)

            if (current_time - last_index_time) > DEFAULT_LAST_SEARCH_DAYS * 86400:
                # avoid huge delay on indexing
                last_index_time = current_time - DEFAULT_LAST_SEARCH_DAYS * 86400

            prev_search_time = last_index_time
            next_search_time = SplunkWrapper.next_search_time(last_index_time, current_time, MAX_SEARCH_INTERVAL,
                                                              MIN_SERRCH_INTERVAL)
            while (next_search_time > prev_search_time):
                logger.info("upload_summary_log -- last_search_time:{}, next_search_time:{}".format(last_index_time,
                                                                                                    next_search_time))
                search_str = 'search `default_index` tag=web OR tag=proxy _indextime > {} _indextime <= {} | eval indextime=_indextime, websites=coalesce(site,url,dest), eventhour=strftime(_time,"%Y-%m-%d:%H"), username=if(isnull(user),src,user) | stats count AS count1, max(indextime) AS last_index_time BY websites, src, eventhour, username | `extractfqdn` | stats sum(count1) AS count, max(last_index_time) AS last_index_time BY hostname, src, username, eventhour | rename hostname AS website | eval eventtime=strptime(eventhour, "%Y-%m-%d:%H")'.format(
                    last_index_time, next_search_time)
                if self.is_rdnslookup:
                    search_str += ' | lookup dnslookup clientip AS src OUTPUT clienthost AS hostname'
                logger.debug("search_str: {}".format(search_str))
                kwargs_export = {"search_mode": "normal", "preview": False, "index_earliest": last_index_time}
                ssl._create_default_https_context = ssl._create_unverified_context
                exportsearch_results = self.service.jobs.export(search_str, **kwargs_export)
                ssl._create_default_https_context = self.default_ssl_context
                logger.info("upload_summary_log -- search result success")

                reader = results.ResultsReader(exportsearch_results)
                filename = "{}_{}{}".format(LogUploader.LOG_PREFIX, current_time, LogUploader.LOG_SUFFIX)
                log_file = os.path.join(self.get_log_path(), filename)
                items = 0
                cur_last_search_time = last_index_time
                with open(log_file, 'w') as f:
                    for item in reader:
                        if isinstance(item, dict):
                            website = item.get('website', '')
                            src = item.get('src', '')
                            event_time = item.get('eventtime', '')
                            if not website or not src or not event_time:
                                # ignore 
                                continue

                            cur_search_time = int(item.get('last_index_time', 0))
                            # eventtime: '1604048400.000000'
                            event_time = int(event_time.split('.')[0])
                            count = int(item.get('count', 0))
                            user_name = item.get('username', '')
                            hostname = item.get('hostname', '')
                            if cur_search_time > cur_last_search_time:
                                cur_last_search_time = cur_search_time
                            f.write("{}\n".format(json.dumps(
                                {'eventtime': event_time, 'src': src, 'hostname': hostname, 'username': user_name,
                                 'website': website, 'count': count})))
                            items += 1
                        elif isinstance(item, results.Message):
                            logger.info("upload_summary_log Message is: %s" % item)
                        else:
                            logger.info("upload_summary_log Unknown result")

                # upload 
                logger.debug("upload_summary_log >> upload {} - {}".format(log_file, items))
                self.uploader.upload()

                if cur_last_search_time > last_index_time:
                    last_index_time = cur_last_search_time
                    self.set_cache(LAST_UPLOAD_INDEX_TIMESTAMP_KEY, last_index_time)

                # check the next search range
                prev_search_time = next_search_time
                next_search_time = SplunkWrapper.next_search_time(next_search_time, current_time, MAX_SEARCH_INTERVAL,
                                                                  MIN_SERRCH_INTERVAL)


        except Exception as e:
            logger.error(e)

        self.set_init_flag(1)

        return error_code


def sync_log(params):
    logger.info("crs_update start->")

    # Get parameter
    instance_id = "splunk_instance_id"
    splunk_id = ""
    http_proxy = None
    https_proxy = None
    command_parameter = {}

    for arg in params:
        para = arg.split("=")
        command_parameter[para[0]] = para[1]
    if all(p in command_parameter for p in ["username", "password", "type"]):
        logger.info("connect with username/password")
    elif all(p in command_parameter for p in ["token", "type"]):
        logger.info("connect with token")
    else:
        logger.error('Unsupport arguments')
        sys.exit()

    # get proxy
    try:
        http_proxy = command_parameter["http_proxy"]
        https_proxy = command_parameter["https_proxy"]
        logger.info(">> proxy setting: http_proxy:{}, https_proxy:{}".format(http_proxy, https_proxy))
    except:
        pass

    # get splunk home path

    SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '')
    if not SPLUNK_HOME:
        SPLUNK_HOME = "C:\\Program Files\\Splunk"
        if PLATFORM_STR == "Windows":
            SPLUNK_HOME = "C:\\Program Files\\Splunk"
        elif PLATFORM_STR == "Linux":
            SPLUNK_HOME = "/opt/splunk"
        else:
            sys.exit()

    # Get instance ID
    INC_FILE = os.path.join(SPLUNK_HOME, 'etc', 'instance.cfg')
    conf = ConfigParser.ConfigParser()
    conf.read(INC_FILE)
    instance_id = conf.get("general", "guid")
    logger.info("crs update set instance_id %s" % instance_id)

    # Get app version
    APP_CONF = os.path.join(SPLUNK_HOME, 'etc', 'apps', APP_NAME, 'default', 'app.conf')
    conf = ConfigParser.ConfigParser()
    conf.read(APP_CONF)
    app_version = conf.get("launcher", "version")
    logger.info("crs update app version %s" % app_version)

    mr2020_splunk = SplunkWrapper(splunk_id=splunk_id, instance_id=instance_id, http_proxy=http_proxy,
                                  https_proxy=https_proxy, app_version=app_version)

    # Check if has another task running
    task_status = -1

    if command_parameter["type"] == "1":
        task_status = mr2020_splunk.get_task_status(0)
    elif command_parameter["type"] == "2":
        task_status = mr2020_splunk.get_task_status(1)
    elif command_parameter["type"] == "3":
        task_status = mr2020_splunk.get_task_status(2)
    else:
        logger.error("Unsupport task type")

    if task_status == 0:
        try:
            mr2020_splunk.set_task_status(int(command_parameter["type"]) - 1, 1)
            if "token" in command_parameter:
                mr2020_splunk.connect(token=command_parameter["token"])
            else:
                mr2020_splunk.connect(username=command_parameter["username"], password=command_parameter["password"])

            if mr2020_splunk.check_config():
                if enable_upload_log:
                    if command_parameter["type"] == "3":
                        mr2020_splunk.upload_summary_log()
        except Exception as e:
            logger.error(e)
        finally:
            mr2020_splunk.set_task_status(int(command_parameter["type"]) - 1, 0)
    elif task_status == 1:
        if command_parameter["type"] == "1":
            logger.warning("there are another tasks update_newest_item running, exit this task")
        elif command_parameter["type"] == "2":
            logger.warning("there are another tasks update_expired_item running, exit this task")
        elif command_parameter["type"] == "3":
            logger.warning("there are another tasks upload_summary_log running, exit this task")

    logger.info("crs_update end->")


if __name__ == "__main__":
    logger.info("manual crs_update start->")
    command_parameter = {}

    for arg in sys.argv[1:]:
        para = arg.split("=")
        command_parameter[para[0]] = para[1]

    sync_log([f"{p}={command_parameter[p]}" for p in command_parameter])
    logger.info("manual crs_update end->")
