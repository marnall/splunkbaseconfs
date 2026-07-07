import json
# import logging as logger
import math
import base64
import os
import sys
import time
import datetime
import requests
import re
import glob
import gzip
from zipfile import ZipFile
import uuid
import configparser
from random import randint
from event_name_filter import event_name_filter
from constants import PAGE_SIZE, MAX_TIME, RETRY_COUNT, JWT_STATE_FILE, JWT_EXPIRY_FILE, FALLBACK_API_MESSAGE
import platform
import traceback
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import certifi


_APP_NAME = 'CybereasonAddOnForSplunk'

log_location = make_splunkhome_path(['var', 'log', 'splunk', _APP_NAME])
server_conf_location = make_splunkhome_path(['etc', 'system', 'default'])
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''
class CybereasonClient:
    def __init__(self, helper, ew, base_url=None, cyb_account=None, auth_type=None, proxy=None, utils=None, cred_realm=None, **kwargs):
        try:
            t = base_url.split(":")
            # Setting default port as 443 if no port is provided in the url
            self.port = t[1] if len(t) > 1 and len(t[1]) > 0 else "443"
            self.server = t[0]
            self.base_url = "https://{}:{}".format(self.server, self.port)
            self.login_url = self.base_url + "/login.html"
            self.password = cyb_account.get('password')
            self.username= cyb_account.get('username')
            self.proxies = proxy
            self.helper = helper
            self.ew = ew
            self._useproxy = False
            # self._log = log
            self.verify = True
            self.child_processes = dict()
            self.auth_type = auth_type
            self.is_first_poll = True
            self.jwt_auth_token = None
            self.jwt_expiry_minutes = 0
            self.utils = utils
            self.cred_realm = cred_realm
            self.headers = {"Content-Type": "application/json", "User-Agent": "CybereasonSplunkIntegration/1.5.3 (target="+self._get_server_address()+")"}
            if proxy is not None  and proxy:
                pconfig = proxy
                if "proxy_url" not in pconfig or "proxy_port" not in pconfig:
                    self.helper.log_error(
                        "component=proxy action=get_proxy_config status=failed step='host_or_port'")
                    raise AttributeError("Failed to find Hostname or Port in Configuration Object")
                protocol = "http"
                if "proxy_type" in pconfig:
                    protocol = pconfig["proxy_type"]
                authentication = ""
                hostname = pconfig["proxy_url"]
                proxyport = pconfig["proxy_port"]
                if "proxy_username" not in pconfig or "proxy_password" not in pconfig:
                    self.helper.log_error("component=proxy action=get_proxy_authentication_config status=failed")
                    raise AttributeError("Failed to find Username or password in Configuration Object")
                authentication = "{0}:{1}@".format(pconfig["proxy_username"], pconfig["proxy_password"])
                proxy = {"http": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport),
                         "https": "{0}://{1}{2}:{3}/".format(protocol, authentication, hostname, proxyport)}
                self.proxies = proxy
                self._useproxy = True
            self._create_session()
                                                   
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "file={} line={} error={}".format(fname, exc_tb.tb_lineno, e)
            raise e
        
    def _create_session(self, counter=0):
        counter = counter + 1
        self.helper.log_debug("action=create_session counter={}".format(counter))
        if counter > 10:
            self.helper.log_debug("action=create_session counter={} over_10".format(counter))
            return
        try:
            if self.auth_type == 'jwt_token':
                self.session = requests
                self.__add_jwt_to_header()
            else:
                self.session = requests.session()
            if self.helper.get_arg("ssl_certificate_path"):
                self.session.verify = str(self.helper.get_arg("ssl_certificate_path"))
                self.helper.log_info("Input Configuration Specifies Server path for Valid SSL Certificates. Default won't be used!")
                self.helper.log_debug(f"Specified Certificate Path on Server: {self.session.verify}")
            self.helper.log_debug(f"Default Certificate Path on Server: {certifi.where()}")
            self.helper.log_debug("action=create_session ssl_verify={}".format(self.verify))
            self.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
            if self._useproxy:
                response = self.session.post(self.login_url,
                                             data={"username": self.username, "password": self.password},
                                             proxies=self.proxies, verify=self.verify,
                                             headers=self.headers)
            else:
                response = self.session.post(self.login_url,
                                             data={"username": self.username, "password": self.password},
                                             verify=self.verify,
                                             headers=self.headers)
            self.headers.update({"Content-Type": "application/json"})

            code = response.status_code
            if code == 200 and "error" in response.url:
                raise Exception(
                    "type='login error' url='{}' code=200 possible_reason='check for bad credentials'".format(
                        response.url))

            if code == 200 and "reset.html" in response.url:
                raise Exception(
                    "type='login_error' url='{}' code=200 possible_reason='password reset required'".format(
                        response.url))

            if code == 200 and "Authentication Code" in response.text:
                raise Exception(
                    "type='login error' url='{}' code=200 possible_reason='check for TWO FACTOR enabled'".format(
                        response.url))

            # log.debug("action=create_session code={} resp='{}'".format(code, response))
            if code == 500:
                raise Exception("Server error", response.json())

            if code == 410:
                raise Exception("Item no longer exists", response.json())

            if code == 400:
                raise Exception("Malformed query", response.json())

            if code != 200:
                raise Exception("Query failed", response.json())

            if 'input type="password"' in response.text or "<app-login>" in response.text:
                [self.helper.log_debug(
                    "action=login subsection=history code={} url={}".format(x.status_code,
                                                                            x.url
                                                                            ))
                    for x in response.history]
                self.helper.log_debug("action=login msg='Cookie expired, performing login again'")
                return self._create_session(counter=counter)
            self.helper.log_debug("action=login code={} status=end_of_session session={}".format(code, self.session))

            # if "<app></app>" in response.text:
            #     log.info(f"action=login msg='assuming good login, resuming operations for server: {self.server} and user: {self.username}'")

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "action=login file={} exception_line={} error_type={} {}".format(fname, exc_tb.tb_lineno,
                                                                                    type(e),
                                                                                    e)
            self.helper.log_error("{}".format(addl))
            raise e
        
    def __set_jwt_expiry_mins(self):
        res = self.jwt_auth_token.split('.')
        data = res[1] + '===='
        decoded_token = base64.b64decode(data)
        decoded_token = json.loads(decoded_token)
        created_timestamp = decoded_token.get('iat',0)
        expiry_timestamp = decoded_token.get('exp',0)
        # Calulating expiry minutes with a buffer
        expiry_mins = int((expiry_timestamp-created_timestamp)/60 - 5)
        self.jwt_expiry_minutes = expiry_mins
        self.helper.log_info('JWT token will be renewed after {} minutes'.format(self.jwt_expiry_minutes))
        
    def __check_jwt_expiry(self, jwt_creation_timestamp):
        expired_flag = False
        latest = int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))
        duration = latest - jwt_creation_timestamp
        if duration > (self.jwt_expiry_minutes*60):
            expired_flag = True
        return expired_flag
        
    def __new_jwt_token(self, jwt_state_file, jwt_expiry):
        # Reset the token to handle token expiry
        self.jwt_auth_token = None
        self.__fetch_jwt()
        if self.jwt_auth_token:
            latest = int(math.ceil(time.mktime(datetime.datetime.now().timetuple())))
            with open(jwt_state_file, 'w') as checkpoint:
                checkpoint.write(str(latest))
            with open(jwt_expiry, 'w') as checkpoint:
                checkpoint.write(str(self.jwt_expiry_minutes))
            
    def __fetch_jwt(self):
        self.helper.log_info('Generating new JWT token')
        url = self._build_endpoint("auth/token")
        res = requests.post(url=url,auth=(self.username,self.password))
        self.jwt_auth_token = res.content.decode("utf-8")
        if self.jwt_auth_token:
            self.__set_jwt_expiry_mins()
        else:
            self.helper.log_error('JWT token not received')
            
    def __add_jwt_to_header(self):
        jwt_state_dir = log_location + '/jwt_token_state/{}-{}-{}'.format(self.cred_realm, self.server, self.username)
        jwt_state_file = jwt_state_dir + JWT_STATE_FILE
        jwt_expiry = jwt_state_dir + JWT_EXPIRY_FILE
        if not os.path.exists(jwt_state_dir):
            os.makedirs(jwt_state_dir)
        if self.jwt_auth_token and os.path.exists(jwt_state_file):
            with open(jwt_state_file, 'r') as file:
                jwt_creation_timestamp = int(file.read())
            with open(jwt_expiry, 'r') as file:
                self.jwt_expiry_minutes = int(file.read())
            expired = self.__check_jwt_expiry(jwt_creation_timestamp)
            if expired:
                self.helper.log_info('JWT token has expired, generating new one')
                self.__new_jwt_token(jwt_state_file, jwt_expiry)
            else:
                self.helper.log_debug('Using saved JWT token')
        else:
            self.__new_jwt_token(jwt_state_file, jwt_expiry)
        if self.jwt_auth_token:
            self.headers["Authorization"] = 'Bearer ' + self.jwt_auth_token
    
    def _get_server_address(self):
        target = 'unknown'
        try:
            server_conf_path = os.path.join(server_conf_location, 'server.conf')
            if os.path.exists(server_conf_path):
                config = configparser.ConfigParser()
                config.read(server_conf_path)
                target = str(config['dfs']['spark_master_host'])
        except Exception as exc:
            self.helper.log_warning(f'Exception occured while reading server name. Proceeding with default target as {target}\n')
        return target
                       
    def _build_endpoint(self, endpoint="visualsearch/query/simple", **kwargs):
        return "https://{}:{}/rest/{}".format(self.server, self.port, endpoint)
    
    def _call(self, data=None, url=None, **kwargs):
        
        self.helper.log_debug("calling use_proxy={} url={} data={}".format(self._useproxy, url, data))
        ret = None
        
        if self.auth_type == 'jwt_token':
            self.__add_jwt_to_header()
            self.helper.log_debug("calling __add_jwt_to_header function")
        try:
            attempt = 0
            if data is None:
                if self._useproxy:
                    self.helper.log_debug("action=call_get use_proxy=true")
                    # This section of the code implements a rate limiting mechanism to control the number of
                    # requests a user can make to the API within a specified time window.
                    while attempt < RETRY_COUNT:
                        ret = self.session.get(url=url, headers=self.headers, verify=self.verify, proxies=self.proxies)
                        if ret.status_code == 429:
                            wait_time = min(2 ** attempt, MAX_TIME)
                            self.helper.log_info(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            attempt+=1
                        elif ret.status_code == 200:
                            return ret
                        else:
                            error_message = f"Status code received {ret.status_code} while calling {url}"
                            self.helper.log_info(error_message)
                            raise Exception(error_message)
                    self.helper.log_error("Max tries exceeded.")
                else:
                    self.helper.log_debug("action=call_get use_proxy=false")
                    # This section of the code implements a rate limiting mechanism to control the number of
                    # requests a user can make to the API within a specified time window.
                    while attempt < RETRY_COUNT:
                        ret = self.session.get(url=url, headers=self.headers, verify=self.verify)
                        if ret.status_code == 429:
                            wait_time = min(2 ** attempt, MAX_TIME)
                            self.helper.log_info(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            attempt+=1
                        elif ret.status_code == 200:
                            return ret
                        else:
                            error_message = f"Status code received {ret.status_code} while calling {url}"
                            self.helper.log_info(error_message)
                            raise Exception(error_message)
                    self.helper.log_error("Max tries exceeded.")
                return ret
            else:
                if self._useproxy:
                    self.helper.log_debug("action=call_post use_proxy=true")
                    # This section of the code implements a rate limiting mechanism to control the number of
                    # requests a user can make to the API within a specified time window.
                    while attempt < RETRY_COUNT:
                        ret = self.session.post(url=url, headers=self.headers, verify=self.verify, data=data, proxies=self.proxies)
                        if ret.status_code == 429:
                            wait_time = min(2 ** attempt, MAX_TIME)
                            self.helper.log_info(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                            time.sleep(wait_time)
                            attempt+=1
                        elif ret.status_code == 200:
                            return ret
                        else:
                            error_message = f"Status code received {ret.status_code} while calling {url}"
                            self.helper.log_info(error_message)
                            raise Exception(error_message)
                    self.helper.log_error("Max tries exceeded.")
                else:
                    self.helper.log_debug("action=call_post use_proxy=false url={} data={} headers={}".format(url, data, self.headers))
                    try:
                        # This section of the code implements a rate limiting mechanism to control the number of
                        # requests a user can make to the API within a specified time window.
                        while attempt < RETRY_COUNT:
                            ret = self.session.post(url=url, headers=self.headers, verify=self.verify, data=data)
                            if ret.status_code == 400 and 'rest/mmng/v2/malops' in url:
                                self.helper.log_info(f"Status code received 400 while calling rest/mmng/v2 API")
                                return {"message": FALLBACK_API_MESSAGE}
                            elif ret.status_code == 429:
                                wait_time = min(2 ** attempt, MAX_TIME)
                                self.helper.log_info(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                                time.sleep(wait_time)
                                attempt+=1
                            elif ret.status_code == 200:
                                return ret
                            else:
                                error_message = f"Status code received {ret.status_code} while calling {url}"
                                self.helper.log_info(error_message)
                                raise Exception(error_message)
                        self.helper.log_error("Max tries exceeded.")
                    except Exception as e:
                        self.helper.log_debug("action=call_post step=error_caught_on_post e={} ret={}".format(e, ret))
                        raise Exception(e)
                return ret
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            addl = "file={} line={} error={}".format(fname, exc_tb.tb_lineno, e)

            if ret is not None:
                if "unauthorized" in ret.content:
                    self.helper.log_error("func=_call condition=unauthorized {} ret={}".format(addl, ret.text))
                    raise Exception("code=403 error_message=\"unauthorized user\" {}".format(e))
                elif "HTTP Status 500" in ret.text:
                    self.helper.log_error("func=_call condition=server_error {} req={}".format(addl, data))
                    raise Exception("code=500 error_message=\"SERVER_ERROR\" {}".format(e))
                else:
                    self.helper.log_error("func=_call condition=unknown {} ret={}".format(addl, ret.text))
                    raise Exception("unknown Exception {}: {}".format(e, ret.text))
            else:
                self.helper.log_error("func=_call condition=unspecified_error {} ret={}".format(addl, ret.text))
                raise Exception(
                    "code=400 error_message=\"Unspecified Error\" {} ret_content=\"{}\"".format(e, ret))

    def get_last_sent_items(self, file_type):
        try:
            base_url = self.helper.get_arg('base_url')
            username = self.helper.get_arg('username')
            host = "malicious-"+base_url.split(":")[0]+"-"+username
            file_dir = os.path.join(log_location, 'malicious_data_input', host) 
            filepath = os.path.join(file_dir, f'last_sent_{file_type}_file.json')
            last_sent_dict = {}
            if not os.path.exists(file_dir):
                    os.makedirs(file_dir)
            elif os.path.exists(filepath) and os.stat(filepath).st_size != 0:
                last_sent_file = open(filepath, "r")
                last_sent_dict = json.loads(last_sent_file.read())
                last_sent_file.close()
            else:
                self.helper.log_info(f"Returning empty file{file_type}")
            return last_sent_dict
        except:
            self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
            self.helper.log_info(f"Unable to read file{file_type}")
            return {}

    def save_last_sent_items(self, file_type, last_sent_dict):
        try:
            base_url = self.helper.get_arg('base_url')
            username = self.helper.get_arg('username')
            host = "malicious-"+base_url.split(":")[0]+"-"+username
            file_dir = os.path.join(log_location, 'malicious_data_input', host) 
            filepath = os.path.join(file_dir, f'last_sent_{file_type}_file.json')
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            with open(filepath, "w") as last_sent_file:
                last_sent_file.write(json.dumps(last_sent_dict))
        except:
            self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
            self.helper.log_info(f"Could not update the last_sent_file {file_type}")
 
    def _get_detection_inbox_data(self, start_time, end_time, group_info):
        detection_inbox_response = []
        try:
            #Converting string to list to pass it to malops API query
            if group_info:
                group_ids = [item['group_id'] for item in group_info]
                query = {"startTime":start_time,"endTime":end_time,"groupIds": group_ids}
            else:
                query = {"startTime":start_time,"endTime":end_time}
            detection_inbox_response = self._call(data=json.dumps(query), url=self._build_endpoint(endpoint='detection/inbox'))
            self.helper.log_info(f"Query sent to detection/inbox : {query} response status code for detection/inbox : {detection_inbox_response.status_code}")
            if 'message' in detection_inbox_response:
                return detection_inbox_response.get('message')
            detection_inbox_response = json.loads(detection_inbox_response.content)
            return detection_inbox_response
        except Exception as error_details:
            self.helper.log_error(f"Exception while getting detection_inbox_response. Exception details : {error_details}")
    
    def _get_malop_management_data(self, start_time, end_time, malop_status, group_info, offset):
        malop_management_response = []
        try:
            #Converting string to list to pass it to malops API query
            group_ids = []
            self.helper.log_info(f"group_info in _get_malop_management_data: {group_info}")
            if group_info:
                group_ids = [item['group_id'] for item in group_info]
                self.helper.log_info(f"group_ids in _get_malop_management_data: {group_ids}")
            if malop_status[0] == '[]':
                self.helper.log_info("Malop Status is not selected, Setting empty Array")
                malop_status = []
            query = self.build_query(start_time, end_time, malop_status, group_ids, offset)
            malop_management_response = self._call(data=json.dumps(query), url=self._build_endpoint(endpoint='mmng/v2/malops'))
            if 'message' in malop_management_response:
                return malop_management_response.get('message')
            malop_management_response = json.loads(malop_management_response.content)
            return malop_management_response
        except Exception as error_details:
            self.helper.log_error(f"Exception while getting mmng/v2 response. Exception details : {error_details}")
    
    def _get_detection_details_data(self, malop_id):
        """
            Retrieves the detection details for a given Non-EDR Malop ID
        """
        detection_details_response = []
        try: 
            query = json.dumps({"malopGuid":malop_id})
            detection_details_response = self._call(data=query, url=self._build_endpoint(endpoint='detection/details'))
            self.helper.log_info(f'Detection/details response status code: {detection_details_response.status_code}')
            detection_details_response = json.loads(detection_details_response.content)
        except Exception as error_details:
            self.helper.log_error(f"Exception while getting detection/details response. Exception details : {error_details}")
        return detection_details_response
    
    def build_query(self, start_time, end_time, malop_status, group_ids, offset):
        """
            Constructs a query JSON object for the Malop management API.
        """
        query_json = {
            "search": {},
            "range": {
                "from": start_time,
                "to" : end_time
            },
            "pagination": {
                "pageSize": PAGE_SIZE,
                "offset": offset
            },
            "filter": {
                "malop": {
                    "status":malop_status
                },
            },
            "federation": {
                "groups": group_ids
            },
            "sort":[{
                "field": "LastUpdateTime",
                "order": "desc"
            }]
        }
        self.helper.log_info(f"Query for Malop Management API: {query_json}")
        return query_json

    def get_offset(self):
        """
            Retrieves the offset value from a JSON file.
        """
        try:
            base_url = self.helper.get_arg('base_url')
            username = self.helper.get_arg('username')
            host = "malicious-"+base_url.split(":")[0]+"-"+username
            file_dir = os.path.join(log_location, 'malicious_data_input', host) 
            filepath = os.path.join(file_dir, 'offset.json')
            offset_dict = {}
            if not os.path.exists(file_dir):
                    os.makedirs(file_dir)
            elif os.path.exists(filepath) and os.stat(filepath).st_size != 0:
                offset_file = open(filepath, "r")
                offset_dict = json.loads(offset_file.read())
                offset_file.close()
            else:
                self.helper.log_info(f"Returning empty offset dictionary")
        except:
            self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
            self.helper.log_info(f"Unable to read the offset file")
        return offset_dict

    def save_offset(self, offset):
        """
            Saves the provided offset value to a JSON file for persistence.
        """
        try:
            base_url = self.helper.get_arg('base_url')
            username = self.helper.get_arg('username')
            host = "malicious-"+base_url.split(":")[0]+"-"+username
            file_dir = os.path.join(log_location, 'malicious_data_input', host) 
            filepath = os.path.join(file_dir, f'offset.json')
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            with open(filepath, "w") as offset_file:
                offset_file.write(json.dumps(offset))
        except Exception as exc:
            self.helper.log_error(f'Could not update the offset file error: {exc}')
            self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
    
    def update_state(self, malop_count_per_poll, offset=0):
        """
            Updates and saves the offset state for the next Malop polling query.
        """
        #  Save the current time as last poll timestamp
        self.helper.log_info(f"Processed {malop_count_per_poll} malops per paginated call")
        offset_state = {'offset': offset}
        self.helper.log_info(f"Saving the offset : {offset_state}")
        self.save_offset(offset_state)
    
    def get_malop_offset(self):
        """
            Retrieves the offset value for the Malop polling query.
        """
            # Get offset for Malop polling query
        offset = 0
        offset_state = self.get_offset()
        if offset_state and 'offset' in offset_state:
            offset = offset_state['offset']
        if not offset:
            # This is the first poll (Historical poll)
            offset = 0
        return offset

    def get_time_bound_malops(self, ew, earliest, latest, sensor_group_name, malop_status):
        """
            Fetching the time bound malops from the server on basis of earliest and latest timestamp
        """
        self.helper.log_debug("within the get_time_bound_malops function")
       
        try:
            start_time = earliest*1000
            end_time = latest*1000
            sensor_group_name_list=[]
            if sensor_group_name:
                sensor_group_name_list = sensor_group_name.split(',')
            all_groups, group_info = self._get_sensor_group_info(sensor_group_name_list)
            self.helper.log_debug("action=get_time_bound_malops startTime={} endTime={}".format(start_time, end_time))
            offset = self.get_malop_offset()
            has_more_results = True
            total_malops_available = 0
            total_malops_fetched = 0
            while has_more_results:
                total_events = []
                malop_management_response = self._get_malop_management_data(start_time, end_time, malop_status, group_info, offset)
                if malop_management_response == FALLBACK_API_MESSAGE:
                    detection_inbox_response = self._get_detection_inbox_data(start_time, end_time, all_groups)
                    has_more_results = False
                    total_events = self._process_detection_inbox_data(detection_inbox_response, all_groups, offset, start_time, end_time)
                    continue
                if malop_management_response == [] or malop_management_response == None:
                    has_more_results = False
                    continue
                total_malops_available = malop_management_response["data"]["totalHits"]
                malop_management_response = malop_management_response["data"]["data"]
                malop_count_per_poll = len(malop_management_response)
                self.helper.log_info(f"Malop stats: Malop per paginated call {malop_count_per_poll}. Malops per polling cycle {total_malops_available}")
                total_malops_fetched += malop_count_per_poll
                last_sent_malops_dict = self.get_last_sent_items("malop")
                edr_malop_data, non_edr_list, last_sent_malops_dict = self.classify_malop_types(malop_management_response, last_sent_malops_dict, all_groups)
                self.helper.log_info(f"For mmng/v2 last_sent_malops_dict: {last_sent_malops_dict}")
                if non_edr_list:
                    self.helper.log_info(f'Sending {len(non_edr_list)} Non-EDR malops to Splunk....')
                    self.print_multiple_events(non_edr_list)

                for malop in edr_malop_data:
                    processed_malop_obj = self._process_edr_malop(malop, start_time, end_time)
                    if processed_malop_obj:
                        total_events.append(processed_malop_obj)
                if total_malops_fetched < total_malops_available:
                    has_more_results = True
                    offset += malop_count_per_poll
                else:
                    has_more_results = False
                    offset = 0
                self.update_state(malop_count_per_poll, offset)

                if total_events:
                    self.helper.log_info(f'Sending {len(total_events)} EDR malops to Splunk....')
                    self.print_multiple_events(total_events)
                [self.process_malop_elements(x) for x in total_events]
                self.update_buffer(last_sent_malops_dict, end_time)
            return [self._api_return(operation="time_bound_malops", total_results=len(total_events))]

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_time_bound_malops")
            self.helper.log_error("{}".format(myJson))
            raise e
        
    def _process_detection_inbox_data(self, detection_inbox_response, group_info, offset, start_time, end_time):
        total_events = []
        last_sent_malops_dict = self.get_last_sent_items("malop")
        detection_inbox_response = detection_inbox_response["malops"]
        edr_malop_data, non_edr_list, last_sent_malops_dict = self.classify_malop_types(detection_inbox_response, last_sent_malops_dict, group_info)
        self.helper.log_info(f"_process_detection_inbox_data last_sent_malops_dict: {last_sent_malops_dict}")
        if non_edr_list:
            self.helper.log_info(f'Sending {len(non_edr_list)} detection/inbox Non-EDR malops to Splunk....')
            self.print_multiple_events(non_edr_list)

        for malop in edr_malop_data:
            processed_malop_obj = self._process_edr_malop(malop, start_time, end_time)
            if processed_malop_obj:
                total_events.append(processed_malop_obj)
        self.helper.log_info(f"Processed {len(detection_inbox_response)} malops")

        if total_events:
            self.helper.log_info(f'Sending {len(total_events)} EDR malops to Splunk....')
            self.print_multiple_events(total_events)
        [self.process_malop_elements(x) for x in total_events]
        self.update_buffer(last_sent_malops_dict, end_time)
        return total_events

    def update_buffer(self, last_sent_malops_dict, end_time):
        """
            Updates the buffer dictionary by removing entries older than a specified time frame and saves the updated buffer to a file.
        """
        try:
            # Trim the Buffer dict of older Guid's and save to file
            self.helper.log_info(f"update_buffer last_sent_malops_dict: {last_sent_malops_dict}")
            last_sent_malops_dict_new = {}
            opt_interval = int(self.helper.get_arg('interval'))
            opt_buffer_time = int(self.helper.get_arg('buffer_time'))
            if opt_interval*2 > opt_buffer_time:
                time_diff = opt_interval*2 
            else:
                time_diff = opt_buffer_time
            buffer_time = end_time - (time_diff*1000)
            for malop in last_sent_malops_dict.keys():
                #Keep only the Guid's for which the lastUpdateTime is greater than the start_Time
                if buffer_time < last_sent_malops_dict[malop]:
                    last_sent_malops_dict_new[malop] = last_sent_malops_dict[malop]
            self.helper.log_info(f'MalopBuffer: Saving the buffer dict: {last_sent_malops_dict_new}')
            self.save_last_sent_items("malop", last_sent_malops_dict_new)
            last_sent_malops_dict_new = {}
            last_sent_malops_dict = {}
        except Exception as error_details:
            self.helper.log_error(f'Exception occurred while updating the buffer: {error_details}')


    def classify_malop_types(self, malop_management_response, last_sent_malops_dict, group_info):
        try:
            edr_malop_data = list()
            non_edr_list = list()
            for malop in malop_management_response:
                malop_guid = malop.get('guid', '')
                malop_detection_types = malop.get('detectionTypes', [])
                malop_status = malop.get('status','')
                malop_investigation_status = malop.get('investigationStatus','')
                if not (malop_guid in last_sent_malops_dict.keys() and last_sent_malops_dict[malop_guid] == malop['lastUpdateTime']):
                    group_id = ""
                    if 'group' in malop:
                        group_id = malop["group"]
                    elif (len(malop.get('groups')) > 0):
                        group_id =  malop['groups'][0]
                    sensor_group_name = self._get_group_name(group_info, group_id)
                    if malop.get('isEdr') or malop.get('edr'):
                        self.helper.log_info(f"malop is EDR")
                        edr_malop_data.append(
                            {
                                "malop_guid": malop_guid,
                                "detection_types": malop_detection_types,
                                "sensor_group_name": sensor_group_name,
                                "group_name": sensor_group_name,
                                "malop_status": malop_status,
                                "group": group_id,
                                "investigation_status": malop_investigation_status
                            }
                        )
                    else:
                        detection_malop = self._get_detection_details_data(malop_guid)
                        updated_malop = detection_malop
                        updated_malop['group_name'] = sensor_group_name
                        updated_malop['group'] = group_id
                        non_edr_list.append(updated_malop)
                else:
                    self.helper.log_debug(f"Skipping Malop,because it is already polled. Malop Guid:{malop['guid']}")

                # Add/Update the Buffer Dict with latest malops
                last_sent_malops_dict[malop['guid']] = malop['lastUpdateTime']
                self.helper.log_debug(f"Added malop guid {malop['guid']} to buffer")
            self.helper.log_info(f'Polled {len(edr_malop_data)} EDR malops and {len(non_edr_list)} Non-EDR malops')
        except Exception as e:
            self.helper.log_error(f"Exception while classifying the malop types. Error details: {e}")
            raise Exception(e)
        return edr_malop_data, non_edr_list, last_sent_malops_dict

    def _process_edr_malop(self, malop, start_time, end_time):
        guid = malop['malop_guid']
        detection_types = malop['detection_types']
        group_name = malop['sensor_group_name']
        malop_status = malop['malop_status']
        group_id = malop['group']
        malop_investigation_status = malop["investigation_status"]
        query = {"queryPath": [{
                "requestedType": "MalopProcess",
                "guidList": ["{}".format(guid)],
                "isResult": True}], "totalResultLimit": 75000,
                "perGroupLimit": 75000, "perFeatureLimit": 75000, "templateContext": "MALOP"}
        ret = self._call(data=json.dumps(query), url=self._build_endpoint(endpoint='crimes/unified'))
        self.helper.log_debug("after the EDR MalOps crimes/unified _call")
        my_obj = json.loads(ret.content)
        severity_dict = self._get_mapped_severities(start_time, end_time)
        for guid in my_obj["data"]["resultIdToElementDataMap"]:
            try:
                self.helper.log_debug("processing EDR MalOp {}".format(guid))
                self.child_processes.clear()
                base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                base_obj["malop_guid"] = guid
                base_obj["severity"] = self.get_malop_severity(guid, severity_dict)
                # The malopLastUpdateTime is 13 digits which is an issue so only pull the 1st 10 digits
                for idx, item in enumerate(base_obj["simpleValues"]["malopLastUpdateTime"]["values"]):
                    new_malop_last_update_time = int(
                        str(base_obj["simpleValues"]["malopLastUpdateTime"]["values"][idx])[0:10])
                    base_obj["timestamp"] = str(new_malop_last_update_time).encode("utf-8").decode("utf-8")
                    base_obj["simpleValues"]["malopLastUpdateTime"]["values"][idx] = base_obj["timestamp"]
                    # print(self.is_webshell_malop(guid, my_obj))
                    # Code for webshell_malop has been revmoed since the API response has changed for the malops: CYB-641
                single_malop = self.get_single_malop(malop_guid=guid)
                if single_malop is not None:
                    guid_detail = json.loads(single_malop)
                    for idx, item in enumerate(guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"][
                                                "malopLastUpdateTime"]["values"]):
                        new_malop_last_update_time = int(str(
                            guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"][
                                "malopLastUpdateTime"]["values"][idx])[0:10])
                        guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"]["malopLastUpdateTime"][
                            "values"][idx] = str(new_malop_last_update_time).encode("utf-8").decode("utf-8")
                    gd = guid_detail["data"]["resultIdToElementDataMap"][guid]["simpleValues"]
                    self.helper.log_debug("processing base simpleValues for EDR MalOp")
                    [self._process_detail(x, base_obj["simpleValues"], base_obj,
                                        parent_function="get_time_bound_malops_base") for x in gd]
                    self.helper.log_debug("processing detail simpleValues for EDR MalOp")
                    [self._process_detail(x, gd, base_obj, parent_function="get_time_bound_malops_detail") for x in gd]
                    if "iconBase64" in base_obj["simpleValues"]:
                        base_obj["simpleValues"]["iconBase64"] = "removed_for_size"
                    if "iconBase64" in base_obj:
                        base_obj["simpleValues"] = "removed_for_size"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["detectionTypes"] = detection_types
                    my_obj["data"]["resultIdToElementDataMap"][guid]["groupName"] = group_name
                    my_obj["data"]["resultIdToElementDataMap"][guid]["malopStatus"] = malop_status
                    my_obj["data"]["resultIdToElementDataMap"][guid]["group"] = group_id
                    my_obj["data"]["resultIdToElementDataMap"][guid]["managementStatus"] = malop_investigation_status
                    my_obj["data"]["resultIdToElementDataMap"][guid]["edr"] = "true"
                    return my_obj["data"]["resultIdToElementDataMap"][guid]
            except Exception as e:
                self.helper.log_info(f'Exception occured while processing malop id {guid}. Exception details: {e}')
                self.helper.log_error(f'Traceback:\n{traceback.format_exc()}') 


    def _get_group_name(self, group_info, group_id):
        group_name = ""
        try:
            for info in group_info:
                if info['group_id'] == group_id:
                    group_name = info['group_name']
                    break
        except Exception as error_details:
            self.helper.log_info(f'Exception occured while getting group name . Exception details: {error_details}')
        return group_name

    
    def _get_mapped_severities(self, earliest, latest):
        '''
        Fetches severity of malops using rest/detection/inbox API
        Parameters:
                earliest (int)
                latest (int)
        Returns:
                severities (dict)
        '''
        self.helper.log_debug("within the _get_mapped_severities")
        severities = dict()
        query = {"startTime":earliest,"endTime":latest}
        self.helper.log_debug("severity query={}".format(query))
        ret = self._call(data=json.dumps(query), url=self._build_endpoint("detection/inbox"))
        if ret is None:
            self.helper.log_debug("severity query={}".format(query))
            return None
        if not ret.status_code == 200:
            raise Exception(ret.content)
        res_json = ret.json()
        for malop in res_json["malops"]:
            if malop.get("severity"):
                severities[malop.get("guid")] = malop.get("severity")
            else:
                severities[malop.get("guid")] = "Unknown"
        return severities

    def get_malop_severity(self, malop_guid, severity_dict):
        '''
        Gets malop severity from the severity_dict object
        Parameters:
                malop_guid (string)
                severity_dict (dict)
        Returns:
                severity (string)
        '''
        self.helper.log_debug("get_malop_severity")
        if malop_guid in severity_dict:
            return severity_dict[malop_guid]
        else:
            return "Unknown"

    def is_webshell_malop(self, guid, my_obj):
        '''
        Checks if the malop type is Webshell
        Parameters:
                guid (string)
                my_obj (dict)
        Returns:
                flag (Boolean)
        '''
        try:
            flag = False
            decision_feature = my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"]["decisionFeature"]["values"][0]
            if decision_feature == "Process.maliciousWebShellExecution(Malop decision)":
                flag = True
            return flag
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "is_webshell_malop")
            self.helper.log_error(myJson)
            raise e
    def get_child_process(self, process_id_list):
        '''
        Makes API call to fetch child processes for Webshell type malops process
        Parameters:
                process_id_list (list)
        Returns:
                childs (dict)
        '''
        ret = None
        element_values = None
        childs = dict()
        try:
            query = {
                "queryPath": [
                    {
                        "requestedType": "Process",
                        "guidList": process_id_list,
                        "result": True
                    }
                ],
                "totalResultLimit": 1000,
                "perGroupLimit": 1000,
                "perFeatureLimit": 100,
                "templateContext": "DETAILS",
                "customFields": [
                    "children"
                ]
            }
            ret = self._call(data=json.dumps(query), url=self._build_endpoint("visualsearch/query/simple"))
            if ret is None:
                # log.debug("query={}".format(query))
                return None
            if not ret.status_code == 200:
                raise Exception(ret.content)
            res_json = ret.json()
            processes = res_json["data"]["resultIdToElementDataMap"]
            if len(processes) > 0:
                for guid, process in processes.items():
                    element_values = process.get("elementValues")
                    if element_values and "children" in element_values:
                        _child_proceses = element_values.get("children")["elementValues"]
                        if _child_proceses:
                            for child in _child_proceses:
                                childs[child["guid"]] = child
            
            return childs
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_child_process")
            # self._log.error(myJson)
            raise e
    def set_child_processes(self, parent_process_id_list):
        '''
        Fetches child processes for Webshell type malop parent and child processes
        Parameters:
                parent_process_id_list (list)
        Returns:
                None
        '''
        childs = self.get_child_process(parent_process_id_list)
        if childs:
            process_id_list = list(childs.keys())
            for key, value in childs.items():
                self.child_processes[key] = value
            self.set_child_processes(process_id_list)
        else:
            self.helper.log_debug("No child process for the process : {}".format(parent_process_id_list))
    def handle_child_processes(self, malop_guid, timestamp, child_processes, parent_process_name):
        '''
        Ingests child processes for Webshell type malop parent and child processes.
        Parameters:
                malop_id (string)
                timestamp (string)
                child_processes (list)
        Returns:
                None
        '''
        for process in child_processes:
            process["elementType"] = "Child processes"
            process["malop_guid"] = malop_guid
            process["timestamp"] = int(timestamp)
            process_name = process["name"]
            if process["name"] == parent_process_name:
                process["rootCauseElementNames"] = process_name + '(parent process)'
            else:
                process["rootCauseElementNames"] = process_name + '(child process)'
            # log.debug("CHILD PROCESS : {}".format(process))
            # self.mi.sourcetype("cybereason:malops:rootCauseElements")
            # self.mi.print_event(json.dumps(process))
            # print(json.dumps(process))
            sourcetype = "cybereason:malops:rootCauseElements"
            data = str(json.dumps(process))
            event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
            self.ew.write_event(event)

    def get_single_malop(self, malop_guid=None):
        self.helper.log_debug("within the get_single_malop")
        if malop_guid is None:
            return None, None
        query = {"queryPath": [
            {"requestedType": "MalopProcess", "guidList": ["{}".format(malop_guid)],
             "isResult": "true"}],
            "totalResultLimit": 75000, "perGroupLimit": 75000, "perFeatureLimit": 75000,
            "templateContext": "OVERVIEW"}
        ret = self._call(data=json.dumps(query), url=self._build_endpoint("crimes/unified"))
        if ret is None:
            return None, None
        if not ret.status_code == 200:
            raise Exception(ret.content)
        return ret.content

    def _process_detail(self, detail, obj_values, base_object, parent_function="not_defined"):
        try:
            self.helper.log_debug("func=_process_detail pf={} action=start object=_process_detail".format(parent_function))
            if detail in obj_values:
                self.helper.log_debug("func=_process_detail pf={} is_detail_in_obj_values={}".format(parent_function,
                                                                                               detail in obj_values))
                if obj_values[detail]["values"] is None or obj_values[detail]["values"] == []:
                    self.helper.log_debug(
                        "func=_process_detail pf={} obj_values[{}]['values'] is None".format(parent_function, detail))
                    base_object[detail] = ""
                else:
                    self.helper.log_debug(
                        "func=_process_detail pf={} obj_values[{}]['values']={}".format(parent_function, detail,
                                                                                        obj_values[detail]["values"]))
                    whasup = obj_values[detail]["values"].pop()
                    self.helper.log_debug("func=_process_detail pf={} whasup={}".format(parent_function, whasup))
                    obj_values[detail]["values"].append("{}".format(whasup))
                    self.helper.log_debug(
                        "func=_process_detail pf={} action=assigning detail={} to base_object".format(parent_function,
                                                                                                      detail))
                    if detail != "comments":
                        base_object[detail] = ",".join(obj_values[detail]["values"])
                        self.helper.log_debug("func=_process_detail pf={} base_object[{}]={}".format(parent_function, detail,
                                                                                               base_object[detail]))
                    else:
                        comments = str(obj_values[detail]["values"])
                        if comments:
                            if len(comments) < 3000:
                                base_object[detail] = comments
                            else:
                                base_object[detail] = comments[:2997] + '....'

                self.helper.log_debug("func=_process_detail pf={} action=returning base_object".format(parent_function))
                return base_object
        except Exception as e:
            self.helper.log_error("{}".format(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "func=_process_detail pf={} message=\"{}\" " \
                     "exception_type=\"{}\" exception_arguments=\"{}\" " \
                     "filename=\"{}\" line=\"{}\" section=\"{}\"".format(parent_function,
                                                                         str(e), type(e).__name__, e, fname,
                                                                         exc_tb.tb_lineno, "process_detail")
            self.helper.log_error("{}".format(myJson))
            raise e
        finally:
            return base_object
            
    def print_multiple_events(self, total_events):
        for malop in total_events:
            sourcetype = "cybereason:malops"
            if malop.get("edr") is False:
                # Non-EDR MalOp Details URL
                malop["malopDetailUrl"] = f"{self.base_url}/#/detection-malop/{malop['guid']}"
            else:
                # EDR MalOp Details URL
                malop["malopDetailUrl"] = f"{self.base_url}/#/malop/{malop['malop_guid']}"
            self.helper.log_debug("Printing MalOp into Splunk Storage")
            data = str(json.dumps(malop))
            event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
            self.ew.write_event(event)

    def process_malop_elements(self, malop):
        for elem in malop["elementValues"]:
            # self.mi.sourcetype("cybereason:malops:{}".format(elem))
            self.helper.log_debug("parsing elementValues {}".format(elem))
            if not malop["elementValues"][elem]["elementValues"] is None:
                for elem_indv in malop["elementValues"][elem]["elementValues"]:
                    elem_indv["malop_guid"] = malop["malop_guid"]
                    elem_indv["timestamp"] = int(str(malop["malopLastUpdateTime"])[0:10])
                    elem_indv["rootCauseElementNames"] = malop["rootCauseElementNames"]
                    if elem == "affectedMachines":
                        try:
                            query = {"limit":1000,"offset":0,"filters":[{"fieldName":"guid","operator":"Equals","values":[elem_indv["guid"]]}]}
                            ret = self._call(data=json.dumps(query), url=self._build_endpoint(endpoint="sensors/query"))
                            ret_content = json.loads(ret.content)
                            if len(ret_content["sensors"]) != 0:
                                ext_ipaddress = ret_content["sensors"][0]["externalIpAddress"]
                                elem_indv["ExternalIpAddress"]=ext_ipaddress
                        except Exception as e:
                            self.helper.log_error(f"Skipping fetching of External IP Address for Machine {elem_indv['guid']}. Error: {e}")
                    sourcetype = "cybereason:malops:{}".format(elem)
                    data = str(json.dumps(elem_indv))
                    event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
                    self.helper.log_debug(f"Writing an event : {event.data}")
                    try:
                        self.ew.write_event(event)
                    except Exception as e:
                        self.helper.log_error(f"Could not write the event : {event.data}. Error : {e}")
                    
    def get_time_bound_suspicious(self, requested_type, earliest, latest):
        try:
            self.helper.log_debug("within the get_time_bound_suspicious")
            self.helper.log_debug("action=get_time_bound_suspicious earliest={} latest={} requestedType={}".format(earliest, latest,
                                                                                                      requested_type))
            ltr = 25000
            query = {"queryPath": [
                {"requestedType": "{}".format(requested_type),
                 "filters": [{"facetName": "hasSuspicions", "values": [True]}],
                 "isResult": "true"}
            ],
                "totalResultLimit": ltr, "perGroupLimit": ltr, "perFeatureLimit": ltr,
                "templateContext": "SPECIFIC",
                "startTime": "{}000".format(earliest),
                "endTime": "{}000".format(latest),
                "customFields": ["elementDisplayName", "creationTime", "endTime", "commandLine",
                                 "isImageFileSignedAndVerified", "imageFile.maliciousClassificationType",
                                 "productType", "children", "parentProcess", "ownerMachine", "calculatedUser",
                                 "imageFile", "imageFile.sha1String", "imageFile.md5String",
                                 "imageFile.companyName",
                                 "imageFile.productName", "iconBase64", "ransomwareAutoRemediationSuspended",
                                 "executionPrevented", "isWhiteListClassification", "matchedWhiteListRuleIds"]}
            ret = self._call(url=self._build_endpoint(), data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            total_events = []
            my_obj = json.loads(ret.content)
            if my_obj["data"]:
                self.helper.log_info("Time Bound Suspicious Events Polled.")
            for guid in my_obj["data"]["resultIdToElementDataMap"]:
                try:
                    base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                    base_obj["guid"] = guid
                    base_obj["requestedType"] = requested_type
                    gd = base_obj["simpleValues"]
                    [self._process_detail(x, gd, base_obj, parent_function="get_time_bound_suspicous") for x in gd]
                    base_obj["simpleValues"] = "moved_to_root_object"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                    total_events.append(my_obj["data"]["resultIdToElementDataMap"][guid])
                except Exception as e:
                    self.helper.log_info(f'Exception occured while processing suspicion for malop id {guid}. Exception details: {e}')
                    self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
            self.helper.log_debug("AnyFriendOfRicks total_events={} data_length={}".format(len(total_events), len(my_obj)))
            # self.mi.sourcetype("cybereason:suspicious")
            # self.mi.print_multiple_events(total_events)
            
            if total_events:
                self.helper.log_info("Sending Suspicious events to Splunk...")
                for each in total_events:
                    sourcetype = "cybereason:suspicious"
                    data = str(json.dumps(each))
                    event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
                    self.ew.write_event(event)
            return [self._api_return(operation="get_time_bound_suspicious", total_results=len(total_events),
                                     result_limit=ltr)]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\" requested_type={}".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_time_bound_suspicious", requested_type)
            # self._log.error(myJson)
            raise e

    def _get_175_malware(self, starttime=0, limit=1000):
        try:
            now = round(datetime.datetime.now().timestamp())*1000
            self.helper.log_info(f"Starting to Poll Malware from {starttime}")
            url = self._build_endpoint("malware/query")
            query = {"filters": [
                {"fieldName": "needsAttention", "operator": "Is", "values": [True, False]},
                {"values": [(int(starttime) * 1000)], "fieldName": "timestamp", "operator": "GreaterThan"}],
                "sortingFieldName": "timestamp", "sortDirection": "DESC", "limit": limit, "offset": 0}
            self.helper.log_debug("action=calling_malware url={} query={}".format(url, json.dumps(query)))

            last_sent_malwares_dict = self.get_last_sent_items("malware")
            self.helper.log_info(f"MalwareBuffer: Malware Buffer: {last_sent_malwares_dict}")

            ret = self._call(url=url, data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            my_obj = json.loads(ret.content)
            if my_obj is None:
                self.helper.log_debug("action=none_my_obj _get_175_malware function Malware Call returned None")
                return [self._api_return(operation="malware", total_results=0, msg="Object Returned is None")]
            if my_obj.get("data") is None:
                self.helper.log_debug("action=returned_events status={} {}".format(ret.status_code, json.dumps(my_obj)))
                return [self._api_return(operation="malware", total_results=0, msg="Data Object Returned is None")]
            malware_list=[]
            for malware in my_obj['data']['malwares']:
                malware_guid = malware['guid']
                if not (malware_guid in last_sent_malwares_dict.keys() and last_sent_malwares_dict[malware_guid] == malware['timestamp']):
                    malware_list.append(malware)
                else:
                    self.helper.log_debug(f"Skipping malware, because it is already polled. Malware Guid:{malware['guid']}")
                last_sent_malwares_dict[malware['guid']] = malware['timestamp']
            my_obj['data']['malwares']=malware_list
            
            # Do Pagination, sending events as found by limit
            # self.mi.sourcetype("cybereason:malware")
            data = my_obj.get("data", {})
            if data.get("malwares"):
                self.helper.log_debug("action=printing_events length={}".format(len(data.get("malwares"))))
                self.helper.log_info(f"Polled {len(data.get('malwares'))} Malwares")
            ######
            # self.mi.print_multiple_events(data.get("malwares", []))
            ######
            self.print_malware_events(data.get("malwares", []))
            self.helper.log_debug("action=show_object obj={}".format(json.dumps(my_obj)))
            total_results = int(data.get("totalResults", 0))
            self.helper.log_debug("action=show_total_results total_results={} hasMoreResults={}".format(total_results,
                                                                                            data.get("hasMoreResults",
                                                                                                     False)))
            while data.get("hasMoreResults", False):
                self.helper.log_debug("action=continue_results hasMoreResults={}".format(data.get("hasMoreResults", False)))
                query.update({"offset" : query["offset"] + 1})
                self.helper.log_debug(
                    "action=calling_malware offset: {} url={} query={}".format(query["offset"], url, json.dumps(query)))
                ret = self._call(url=url, data=json.dumps(query))
                my_obj = json.loads(ret.content)
                if my_obj is None:
                    my_obj = {"hasMoreResults": False}
                else:
                    if my_obj.get("data") is not None:
                        data = my_obj.get("data", {})
                        if data.get("malwares"):
                            malware_list=[]
                            for malware in data['malwares']:
                                malware_guid = malware['guid']
                                if not (malware_guid in last_sent_malwares_dict.keys() and last_sent_malwares_dict[malware_guid] == malware['timestamp']):
                                    malware_list.append(malware)
                                else:
                                    self.helper.log_debug(f"Skipping malware, because it is already polled. Malware Guid:{malware['guid']}")
                                last_sent_malwares_dict[malware['guid']] = malware['timestamp']
                            data['malwares']=malware_list
                            self.helper.log_debug("action=printing_events length={}".format(len(data.get("malwares"))))
                        ######
                        # self.mi.print_multiple_events(data.get("malwares", []))
                        ######
                        self.print_malware_events(data.get("malwares", []))
                        total_results = total_results + int(data.get("totalResults", 0))
                        self.helper.log_debug("action=show_total_results total_results={}".format(total_results))
                    
            last_sent_malwares_dict_new = {}
            opt_interval = int(self.helper.get_arg('interval'))
            opt_buffer_time = int(self.helper.get_arg('buffer_time'))
            if opt_interval*2 > opt_buffer_time:
                time_diff = opt_interval*2 
            else:
                time_diff = opt_buffer_time
            buffer_time = now-(time_diff*1000)
            for malware in last_sent_malwares_dict.keys():
                #Keep only the Guid's for which the timestamp is greater than the start_Time
                if buffer_time < last_sent_malwares_dict[malware]:
                    last_sent_malwares_dict_new[malware] = last_sent_malwares_dict[malware]
            self.helper.log_info(f'MalwareBuffer: Saving the buffer dict: {last_sent_malwares_dict_new}')
            self.save_last_sent_items("malware", last_sent_malwares_dict_new)
            last_sent_malwares_dict_new = {}
            last_sent_malwares_dict = {}
            return [self._api_return(operation="malware", total_results=total_results)]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_175_malware")
            self.helper.log_error(myJson)

    def _api_return(self, **kwargs):
        return {"api_operation": kwargs.get("operation", "unknown"), "total_results": kwargs.get("total_results", 0),
                "message": kwargs.get("msg", "no_message_sent")}

    def get_all_malware(self, starttime=0, limit=1000):
        try:
            return self._get_175_malware(starttime=starttime, limit=limit)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" exception_line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_malware")
            self.helper.log_error(myJson)
                    
    def print_malware_events(self, malwares):
        if malwares:
            self.helper.log_info("Sending Malwares to Splunk...")
            sourcetype = "cybereason:malware"
            for each in malwares:
                data = str(json.dumps(each))
                event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
                self.ew.write_event(event)

    def _fetch_all_sensor_groups(self):
        sensor_groups = []
        try:
            sensor_group_response = self._call(url=self._build_endpoint(endpoint='groups'))
            sensor_groups = json.loads(sensor_group_response.content)
        except Exception as error_details:
            self.helper.log_error(f"Exception while getting sensor group API response. Exception details: {error_details}")
        return sensor_groups

    def _get_sensor_group_info(self, group_name):
        group_info = []
        all_groups = []
        try:
            sensor_groups = self._fetch_all_sensor_groups()
            for single_group in sensor_groups:
                all_groups.append({'group_name': single_group['name'], 'group_id': single_group['id']})
                if (single_group['name'] in group_name) or (single_group['id'] in group_name):
                    group_info.append({'group_name': single_group['name'], 'group_id': single_group['id']})
        except Exception as error_details:
            self.helper.log_error(f"Exception while getting sensor group info. Exception details : {error_details}")
        return all_groups, group_info


    def pull_latest_comments(self, earliest, latest, sensor_group_name):
        last_poll_timestamp = earliest*1000
        end_time = latest*1000
        start_time = 0
        sensor_group_name_list=[]
        if sensor_group_name:
            sensor_group_name_list = sensor_group_name.split(',')
        all_groups, sensor_group_info = self._get_sensor_group_info(sensor_group_name_list)
        malop_management_response = self._get_detection_inbox_data(start_time, end_time, sensor_group_info)
        self.helper.log_debug(f"action=pull_latest_comments malop_management_response count after applying group filter {len(malop_management_response)}")
        self.helper.log_debug("action=pull_latest_comments startTime={} endTime={}".format(last_poll_timestamp, end_time))
        total_events = []
        edr_malop_data = list()
        count = 0
        for malop in malop_management_response['malops']:
            malop_guid = malop.get('guid', "")
            self.helper.log_info(f"Processing malop {malop_guid}. Count: {count}")
            comments = self.get_comments(malop_guid)
            is_new_comment_present = self.process_comments(comments, last_poll_timestamp)
            if is_new_comment_present:
                self.helper.log_debug(f"New comment found for Malop with guid {malop_guid}")
                malop_detection_types = malop.get('detectionTypes', [])
                if malop['edr']:
                    edr_malop_data.append(
                    {
                        "malop_guid": malop_guid,
                        "detection_types": malop_detection_types
                    }
                )
                else:
                    total_events.append(malop)
                self.helper.log_debug(f"total_events count: {len(total_events)}")
                for malop in edr_malop_data:
                    processed_malop_obj = self._process_edr_malop(malop, last_poll_timestamp, end_time)
                    total_events.append(processed_malop_obj)
            count = count + 1
        self.helper.log_debug(f"action=pull_latest_comments Total malops to be sent: {len(total_events)}")
        if total_events:
            self.helper.log_debug('Sending malops to Splunk....')
            self.print_multiple_events(total_events)
        [self.process_malop_elements(x) for x in total_events]
        return [self._api_return(operation="malop", total_results=len(total_events))]


    def get_comments(self, malop_guid):
        comments = []
        try:
            query = malop_guid
            comments_raw_response = self._call(data=query, url=self._build_endpoint(endpoint='crimes/get-comments'))
            if comments_raw_response is None:
                self.helper.log_info(f'Empty Response received from Comments API for {malop_guid}')
            else:
                comments_raw_response_content = comments_raw_response.content
                self.helper.log_info(f"comments response: {comments_raw_response_content}")
                if comments_raw_response_content == b'' or comments_raw_response_content == b'[]':
                    self.helper.log_info(f'Empty Array/Body received from Comments API for {malop_guid}')
                else:
                    comments = json.loads(comments_raw_response_content)
            return comments
        except Exception as error_details:
            self.helper.log_info(f'Exception occured while getting comments. Exception details: {error_details}')
            return comments
    
    def process_comments(self, comments, last_poll_timestamp):
        is_new_comment_found = False
        for comment in comments:
            comment_timestamp = comment.get("timestamp", 0)
            if comment_timestamp > last_poll_timestamp:
                is_new_comment_found = True
                break 
        return is_new_comment_found

    def get_all_users(self):
        # rest / investigation / columns / undefined / User
        ret = None
        try:
            self.helper.log_debug("within the get_all_users")
            ret = self._call(url=self._build_endpoint(endpoint="investigation/columns/undefined/User"))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            myar = json.loads(ret.content)
            myar.append("elementDisplayName")
            query = {"queryPath": [{"requestedType": "User", "filters": [], "isResult": "true"}],
                     "totalResultLimit": 75000,
                     "perGroupLimit": 75000, "perFeatureLimit": 75000, "templateContext": "SPECIFIC",
                     "queryTimeout": 120000,
                     "customFields": myar}
            ret = self._call(url=self._build_endpoint(), data=json.dumps(query))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            my_obj = json.loads(ret.content)
            total_events = []
            if my_obj["data"]:
                self.helper.log_info("Polled User Details")
            for guid in my_obj["data"]["resultIdToElementDataMap"]:
                try:
                    base_obj = my_obj["data"]["resultIdToElementDataMap"][guid]
                    base_obj["guid"] = guid
                    gd = base_obj["simpleValues"]
                    [self._process_detail(x, gd, base_obj, parent_function="get_all_users") for x in gd]
                    base_obj["simpleValues"] = "moved_to_root_object"
                    my_obj["data"]["resultIdToElementDataMap"][guid]["simpleValues"] = "moved_to_root"
                    total_events.append(my_obj["data"]["resultIdToElementDataMap"][guid])
                except Exception as e:
                    self.helper.log_info(f'Exception occured while processing user data for malop id {guid}. Exception details: {e}')
                    self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
            ######
            # self.mi.sourcetype("cybereason:users")
            # self.mi.print_multiple_events(total_events)
            ######
            events_count = 0
            if total_events:
                self.helper.log_info("Getting Checkpoint else Sending User Details to Splunk...")
                for user in total_events:
                    # get checkpoint
                    state = self.helper.get_check_point(user['guid'])
                    if state is None:
                        sourcetype = "cybereason:users"
                        data = str(json.dumps(user))
                        event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
                        self.ew.write_event(event)
                        events_count += 1
                        # save checkpoint
                        self.helper.save_check_point(user['guid'], "Indexed")
                    # delete checkpoint
                    # self.helper.delete_check_point(user['guid'])   # enable this to delete the check pointing
            return [self._api_return(operation="users", total_results=events_count)]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_users")
            self.helper.log_error(myJson)
            raise e

    def get_logon_sessions(self, start_time, end_time):
        '''
        Fetches logon sessions using rest/visualsearch/query/simple API
        Parameters:
                None
        Returns:
                dict
        '''
        ret = None
        try:
            self.helper.log_debug("within the get_logon_sessions")
            # start_time = round((datetime.datetime.now() + datetime.timedelta(days=-1)).timestamp())
            # end_time = round(datetime.datetime.now().timestamp())
            query = {"queryPath": [{"requestedType": "LogonSession", "filters":
                            [{"facetName": "creationTime", "filterType": "Between", "values": [start_time*1000, end_time*1000]}], "isResult":True}],
             "totalResultLimit": 1000, "perGroupLimit": 100, "perFeatureLimit": 100, "templateContext": "SPECIFIC", "queryTimeout": 120000,
             "customFields": ["processes", "ownerMachine", "user", "remoteMachine", "logonType", "creationTime", "endTime", "elementDisplayName"]}
            self.helper.log_debug("logon query={}".format(query))
            ret = self._call(data=json.dumps(query), url=self._build_endpoint())
            if ret is None:
                self.helper.log_debug("logon sessions query={}".format(query))
                return None
            if not ret.status_code == 200:
                raise Exception(ret.content)
            res_json = ret.json()
            total_events = []
            for guid, data in res_json["data"]["resultIdToElementDataMap"].items():
                try:
                    base_obj = dict()
                    if "guidString" in data:
                        base_obj["guid"] = data["guidString"]
                    if "elementDisplayName" in data["simpleValues"]:
                        base_obj["element_name"] = data["simpleValues"]["elementDisplayName"]["values"][0]
                    if "ownerMachine" in data["elementValues"]:
                        base_obj["owner_machine"] = data["elementValues"]["ownerMachine"]["elementValues"][0]["name"]
                    if "user" in data["elementValues"]:
                        base_obj["user"] = data["elementValues"]["user"]["elementValues"][0]["name"]
                    if "remoteMachine" in data["elementValues"]:
                        base_obj["remote_machine"] = data["elementValues"]["remoteMachine"]["elementValues"][0]["name"]
                    if "logonType" in data["simpleValues"]:
                        base_obj["logon_type"] = data["simpleValues"]["logonType"]["values"][0]
                    if "creationTime" in data["simpleValues"]:
                        base_obj["created"] = round(int(data["simpleValues"]["creationTime"]["values"][0])/1000)
                    if "processes" in data["elementValues"]:
                        base_obj["processes"] = data["elementValues"]["processes"]["totalValues"]
                    base_obj["tag"] = "authentication"
                    base_obj["action"] = "success"
                    base_obj["app"] = "win:local"
                    base_obj["dest"] = "dest_host"
                    if "remote_machine" not in base_obj:
                        base_obj["remote_machine"] = "Unknown"
                    if "logon_type" not in base_obj:
                        base_obj["logon_type"] = "Unknown"
                    if "user" not in base_obj:
                        base_obj["user"] = "Unknown"
                    total_events.append(base_obj)
                except Exception as e:
                    self.helper.log_info(f'Exception occured while processing logon session for malop id {guid}. Exception details: {e}')
                    self.helper.log_error(f'Traceback:\n{traceback.format_exc()}')
                    
            ########
            # self.mi.sourcetype("cybereason:logon_sessions")
            # self.mi.print_multiple_events(total_events)
            ########
            for each in total_events:
                sourcetype = "cybereason:logon_sessions"
                data = str(json.dumps(each))
                event = self.helper.new_event(host=self.server, source=self.helper.get_arg('name'), index=self.helper.get_output_index(), sourcetype=sourcetype, data=data)
                self.ew.write_event(event)
            return [self._api_return(operation="logon_sessions", total_results=len(total_events))]
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_logon_sessions")
            self.helper.log_error(myJson)
            raise e
    
    def get_all_action_logs(self):
        '''
        Fetches user action logs from monitor/global/userAuditLog endpoint
        Parameters: self (object)
        Returns: dict
        '''
        try:
            self.helper.log_debug("within the get_all_action_logs")
            log_reader = LogReader(self.server)
            last_action_time = None
            user_action_logs_path = log_location + '/user_action_logs/{}-{}'.format(self.cred_realm, self.server)
            parent_zip = user_action_logs_path + '/action_logs.zip'
            extracted_files_path = user_action_logs_path + '/extracted_data'
            checkpoint_file = user_action_logs_path + '/last_polled_timestamp.txt'
            
            self.helper.log_info("os.path.exists(checkpoint_file) {}".format(str(os.path.exists(checkpoint_file))))
            if os.path.exists(checkpoint_file):
                with open(checkpoint_file, 'r') as file:
                    str_timestamp = file.read()
                    last_polled_timestamp = datetime.datetime.strptime(str_timestamp, '%Y-%m-%d %H:%M:%S')
                self.is_first_poll = False
            else:
                last_polled_timestamp = None
                
            
            ret = self._call(url=self._build_endpoint(endpoint="monitor/global/userAuditLog"))
            if not ret.status_code == 200:
                raise Exception(ret.content)
            
           
            log_reader.unzip_file(user_action_logs_path, extracted_files_path, parent_zip, ret.content)
            self.helper.log_info("last polled timestamp {}".format(str(last_polled_timestamp)))
            # Process the log (already unzip) file if it exist
            action_logs_path = extracted_files_path + '/userAuditSyslog.log'
            
            if os.path.exists(action_logs_path):
                self.helper.log_info("if os.path.exists for userAuditlog")
                last_action_time = log_reader.read_cef_events(self.helper, self.ew, action_logs_path, self.is_first_poll, last_polled_timestamp, contains_last_log=True)
                os.remove(action_logs_path)
            
            # Process all the zip files after extracting the main zip file
            file_count = 1
            zips_count = len(glob.glob1(extracted_files_path, '*.gz'))
            while file_count <= zips_count:
                file_to_process = action_logs_path + '.' + str(file_count)
                file_to_extract = file_to_process +  '.gz'
                if os.path.exists(file_to_extract):
                    f_out = open(file_to_process, 'w')
                    with gzip.open(file_to_extract, 'rb') as input_file:
                        f_out.write(input_file.read().decode("utf-8"))
                    f_out.close()
                    log_reader.read_cef_events(self.helper, self.ew, file_to_process, self.is_first_poll, last_polled_timestamp)
                    file_count = file_count + 1
                    os.remove(file_to_extract)
                    os.remove(file_to_process)

            # updating last polled time
            if last_action_time:
                timestamp_str = last_action_time
                res = re.sub('UTC', '', timestamp_str).strip()
                log_timestamp = datetime.datetime.strptime(
                    res, '%b %d %Y, %H:%M:%S')
            else:
                log_timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            self.helper.log_info('Saving the last polled timestamp for Action Logs : {} '.format(log_timestamp))
            with open(checkpoint_file, 'w') as checkpoint:
                checkpoint.write(str(log_timestamp))
            
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            myJson = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\" section=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, "get_all_action_logs")
            self.helper.log_error(myJson)
            raise e
    
    
class LogReader:
    '''
    Read CEF events received from the endpoint
    '''
    def __init__(self, server):
        self.server = server

    def unzip_file(self, user_action_logs_path, extracted_files_path, parent_zip, content):
        '''
        Parameters: self (object), user_action_logs_path (str), extracted_files_path (str), parent_zip (str), content (bytes)
        Returns: None
        '''
        if not os.path.exists(user_action_logs_path):
            os.makedirs(user_action_logs_path)
        with open(parent_zip, 'wb') as file:
            file.write(content)
        # Extract the downloaded script
        if not os.path.exists(extracted_files_path):
            os.makedirs(extracted_files_path)
        with ZipFile(parent_zip, 'r') as myzip:
            myzip.extractall(path=extracted_files_path)
        os.remove(parent_zip)
        
    def read_cef_events(self,helper, ew, path, is_first_poll, last_polled_timestamp=None, contains_last_log=False):
        '''
        Reads the CEF formatted event returned from API
        Parameters: self (object), path (str), modular_input (object), is_first_poll (Boolean), last_polled_timestamp (timestamp), contains_last_log (Boolean)
        Return: last_polled_timestamp (timestamp)
        '''
        last_log_timestamp = None
        with open(path, 'r') as file:
            
            cef_events = file.readlines()
            for cef_event in cef_events:
                last_log_timestamp = self._process_cef_events(helper, ew, path, is_first_poll, last_polled_timestamp, cef_event, contains_last_log)

                #Removing this line since we are seeing lot of lsat timestamp logs in the internal index - CYB-644
                #helper.log_debug("last log timestamp {}".format(str(last_log_timestamp)))
                #
        if last_log_timestamp:
            helper.log_info("returning last log_time stamp")
            return last_log_timestamp

    def _filter_action_log(self, device_name):
        '''
        Parameters: device_name (string)
        Returns: is_filtered_event (Boolean)
        '''
        event_name = device_name.strip().split('/')[1]
        if event_name in event_name_filter:
            return True

    def _process_cef_events(self, helper, ew, path, is_first_poll, last_polled_timestamp, cef_event, contains_last_log=False):
        '''
        Parameters: self (object), path (str), modular_input (object), is_first_poll (Boolean), contains_last_log (Boolean)
        Return: last_polled_timestamp (timestamp)
        '''
        helper.log_debug("within the process cef events")
        is_filtered_event = False
        log_parser = LogParser()
        log_printer = LogPrinter()
        user_action = log_parser.parse(cef_event.strip())
        
        user_action = {k: None if not v else v for k, v in user_action.items()}
        # adding a uuid to event
        user_action['uuid'] = str(uuid.uuid4())
        # adding validations
        action_status = user_action['actionSuccess']
        user_action['actionSuccess'] = False
        if 'DeviceName' in user_action:
            is_filtered_event = self._filter_action_log(user_action['DeviceName'])
        if is_filtered_event:
            if action_status == "1":
                user_action['actionSuccess'] = True
            if user_action and is_first_poll:
                log_printer.print_log("cybereason:action_logs", helper, ew, user_action, self.server)
            elif user_action:
                timestamp_str = user_action.get('userActionTime')
                res = re.sub('UTC', '', timestamp_str).strip()
                
                log_timestamp = datetime.datetime.strptime(res, '%b %d %Y, %H:%M:%S')
                if log_timestamp > last_polled_timestamp:
                    log_printer.print_log("cybereason:action_logs", helper, ew, user_action, self.server)
       
        if contains_last_log and user_action:
            return user_action.get('userActionTime')
    
class LogParser:
    '''
    Parse the CEF event and return a dict with the syslog, header values and the extension
    '''
    def parse(self, str_input):
        '''
        Parameters: self (object), str_input (cef event to parse)
        Returns: values (dict) 
        '''
        values = dict()
        # This regex separates the string into the CEF header and the extension
        syslog_chunk = r'(.*)((CEF:\d+)([^=\\]+\|){,7})'
        header_re = r'((CEF:\d+)([^=\\]+\|){,7})(.*)'
        res_syslog = re.search(syslog_chunk, str_input)
        res = re.search(header_re, str_input)
        if res_syslog:
            syslog = res_syslog.group(1).split(' ')
            values["ServerName"] = syslog[3]
            values["LoggerName"] = syslog[4]
        if res:
            header = res.group(1)
            extension = res.group(4)
            # Split the header on the "|" char.
            spl = re.split(r'(?<!\\)\|', header)
            values["DeviceVendor"] = spl[1]
            values["DeviceProduct"] = spl[2]
            values["DeviceEventClassID"] = spl[4]
            values["DeviceName"] = spl[5]
            if len(spl) > 6:
                values["Severity"] = spl[6]
            cef_start = spl[0].find('CEF')
            if cef_start == -1:
                return None
            (cef, version) = spl[0][cef_start:].split(':')
            values["CEFVersion"] = version
            # The regex here finds a single key=value pair
            spl = re.findall(r'([^=\s]+)=((?:[\\]=|[^=]|)+)(?:\s|$)', extension)
            for i in spl:
                values[i[0]] = i[1]
            # Process custom field labels
            for key in list(values.keys()):
                if key[-5:] == "Label":
                    customlabel = key[:-5]
                    for customfield in list(values.keys()):
                        if customfield == customlabel:
                            values[values[key]] = values[customfield]
                            del values[customfield]
                            del values[key]
        else:
            # log.info('Could not parse record. Is it valid CEF format?')
            return None
        if (values.get('cs2Label',"")=="userFields"):
            text = str_input[str_input.find("cs2=username=")+13:]
            values["addedUser"] = text.split(',')[0]
            del values['cs2Label']
        return values


class LogPrinter:
    '''
    Prints the log as splunk events
    '''
    def print_log(self, source_type, helper, ew, log, hostname):
        '''
        Parameters: self (object), source_type (str), modular_input (object), log(str)
        Returns: None
        '''
        #######
        # modular_input.sourcetype(source_type)
        # modular_input.print_event(json.dumps(log))
        ############
        # helper.log_info("each log {}".format(str(log)))
        sourcetype = source_type
        data = str(json.dumps(log))
        event = helper.new_event(host=hostname, source=helper.get_arg('name'), index=helper.get_output_index(), sourcetype=sourcetype, data=data)
        ew.write_event(event)
