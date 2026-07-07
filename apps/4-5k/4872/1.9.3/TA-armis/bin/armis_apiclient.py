"""This file if for data collection logic."""
import ta_armis_declare

import os
import sys
import requests
import copy
import json
import time
from datetime import datetime,timedelta
import traceback
import armis_constants as constants
import logging
import re
import signal

import splunklib.client as splunkClient
import splunk.rest as rest
from requests.compat import quote_plus

from armis_device_kvstore import ApplicationCheckpoint
from splunklib.modularinput import *
from proxy_config import read_proxies_from_conf
from splunk.auth import getSessionKey
from log_manager import setup_logging
import armis_utils as ar_utils
from solnlib.utils import is_true

logging.getLogger("urllib3").propagate = False
vuln_id_list = set()

class APIClient(object):
    """A Client for all IntSights API related transactions."""

    def __init__(self, helper, ew, logger):
        """Initialize an object."""
        self.account = helper.get_arg("global_account")
        self.input_name = helper.get_input_stanza_names()
        self.key = "armis_alerts_{}-{}".format(self.account["name"], self.input_name)
        self.armis_host = self.account["armis_hostname"]
        self.secret = self.account["armis_api_key"]
        self.armis_fetch_applications = helper.get_arg("inventory")
        self.visibility_device = helper.get_arg("visibility_device")
        self.aql_query = helper.get_arg("aql_query")
        self.index_vuln_match_data = helper.get_arg("index_vuln_match_data")
        self.vulnerabilities_chunk = int(helper.get_arg("vulnerabilities_chunk")) if helper.get_arg("vulnerabilities_chunk") else None
        self.lookback_days = helper.get_arg("lookback_days")
        if self.lookback_days and int(self.lookback_days) > 90:
            logger.info("Lookback days value is greater than 90 : {}. defaulting to 90 days".format(self.lookback_days))
            self.lookback_days = "90"
        self.backfill_days = None
        self.backfill_type = None
        # self.headers = None
        self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
        self.endpoint_url = "https://{}/api/v1/access_token/".format(self.armis_host)
        self.helper = helper
        self.ew = ew
        self.logger = logger

    def send_to_kvstore(self, session_key, helper, data):
        '''Send to kvstore.'''
        
        class KVStoreClient:
            def __init__(
                self,
                splunk_server,
                splunk_server_port,
                splunk_app,
                splunk_collection,
                session_key,
                splunk_server_verify,
            ):
                self.splunk_server = splunk_server
                self.splunk_server_port = splunk_server_port
                self.splunk_app = splunk_app
                self.splunk_collection = splunk_collection
                self.session_key = session_key

            def chunk_data(self, data, chunk_size=1000):
                for i in range(0, len(data), chunk_size):
                    yield data[i:i + chunk_size]
            
            def write_data_to_kvstore(self, data):
                headers = {
                    "Content-type": "application/json",
                    "Accept": "text/plain",
                    "Authorization": "Splunk {}".format(self.session_key),
                }
                splunk_url = "".join(
                            [
                                "https://",
                                self.splunk_server,
                                ":",
                                self.splunk_server_port,
                                "/servicesNS/nobody/",
                                self.splunk_app,
                                "/storage/collections/data/",
                                self.splunk_collection,
                                "/",
                                "batch_save",
                            ]
                        )
                try:
                    response = requests.post(
                        splunk_url, verify=splunk_server_verify, headers=headers, data=json.dumps(data),
                    )
                    return response
                except Exception as e:
                    self.logger.error(
                        "input_name = {}"
                        " message=write_data_to_kvstore_error | Error while performing kvstore operations,"
                        " Error: {}".format(self.input_name, str(e))
                    )

        self.logger.debug(
            "input_name = {} "
            "| message=posting_to_kvstore "
            "| Posting the data to kvstore".format(self.input_name)
        )
        splunkserver = helper.get_global_setting("splunk_rest_host_url") or 'localhost'
        destappname = "armis"
        destcollection = "affected_devices_lookup"
        local_session_key = helper.context_meta.get("session_key")
        splunk_account_info = ar_utils.get_splunk_credentials(local_session_key)
        splunk_server_verify = is_true(splunk_account_info["splunk_verify_cert"])

        if splunkserver in ['127.0.0.1', 'localhost']:
            splunk_server_verify = False
        self.logger.debug("input_name = {} | message=verify_splunk_server | splunk_server_verify={}"
            .format(self.input_name, splunk_server_verify)
        )
        splunk_server_port = splunk_account_info.get("splunk_rest_port") or "8089"
        self.logger.debug("input_name = {} | message=splunk_server_port | splunk_server_port={}"
            .format(self.input_name, splunk_server_port)
        )
        dest_splunk_service = splunkClient.connect(
            host=splunkserver,
            port=splunk_server_port,
            token=session_key,
            owner="nobody",
            app=destappname,
        )

        if destcollection not in dest_splunk_service.kvstore:
            self.logger.error(
                "message=send_to_kvstore_collection_error |"
                " KVStore collection {0} not on {1} Splunk instance".format(destcollection, splunkserver)
            )
            raise Exception(
                "KVStore collection {0} not on {1} Splunk instance".format(destcollection, splunkserver)
            )

        dest_kvstore = KVStoreClient(
            splunkserver,
            splunk_server_port,
            destappname,
            destcollection,
            session_key,
            splunk_server_verify,
        )
        try:
            chunked_data = (list(dest_kvstore.chunk_data(data)))
            for chunk in chunked_data:
                response = dest_kvstore.write_data_to_kvstore(chunk)
                if not response.status_code == requests.codes.ok:
                    if response.status_code == 401:
                        session_key = ar_utils.get_session_key(helper)
                        if session_key:
                            self.session_key = session_key
                            response = dest_kvstore.write_data_to_kvstore(chunk)
                    else:
                        self.logger.error(
                            "input_name = {}"
                            "message=data_post_batch_save_error | API POST response:"
                            " status_code={} response={}".format(self.input_name, response.status_code, response.text)
                        )
        except Exception:
            self.logger.error(
                "input_name = {}"
                "message=batch_thread_post_error | Error while writing to the collection"
                .format(self.input_name)
                )
        self.logger.debug("input_name = {} | message=posted_to_kvstore | Successfully Posted the data to kvstore."
            .format(self.input_name)
        )
    
    def get_token(self):
        """Get Access Token."""
        try:
            # To get session key
            session_key = self.helper.context_meta["session_key"]
            proxy_settings = read_proxies_from_conf(session_key)
            data_for_access_token = {"secret_key": self.secret}
            user_agent = ar_utils.get_user_agent(session_key)
            if proxy_settings:
                self.logger.debug(
                    "input_name = {} | message=Proxy_enabled | Access Token(api client):Proxy is Enabled"
                    .format(self.input_name)
                )
            else:
                self.logger.debug(
                    "input_name = {} | message=Proxy_disabled | Access Token(api client):Proxy is Disabled"
                    .format(self.input_name)
                )
            headers = {
                "User-Agent": user_agent
            }
            response = requests.post(self.endpoint_url, data=data_for_access_token, headers=headers, proxies=proxy_settings)
            if response.status_code == 400:
                self.logger.error('input_name = {} | message = invalid_key | Invalid Armis API Key. The API Key is expired. Please regenerate it.'
                    .format(self.input_name)
                )
                return False
            token = response.json().get("data").get("access_token")
            headers = {
                "Authorization": token,
                "User-Agent": user_agent
            }
            return headers

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.logger.error(
                "input_name = {}"
                "message=http_or_connection_error"
                "ArmisError: HTTPError or ConnectionError occurred while fetching data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error: {}".format(self.input_name, quote_plus(str(e)))
            )
            self.logger.debug(
                "input_name = {}"
                "message=http_or_connection_error"
                "ArmisDebug: HTTPError or ConnectionError occurred while fetching data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error trace: {}".format(self.input_name, traceback.format_exc())
            )
            return False

        except Exception as e:
            self.logger.error("input_name = {} | message=token_error | ArmisError: Could not retrieve token. Error: {}"
                .format(self.input_name, str(e))
            )
            return False

    def make_request_call(self, url, headers, params):
        """Make Rest Call to URL."""
        try:
            session_key = self.helper.context_meta["session_key"]
            proxy_settings = read_proxies_from_conf(session_key)
            if proxy_settings:
                self.logger.debug("input_name = {} | message=proxy_enabled | Request Call:Proxy is Enabled"
                .format(self.input_name)
                )
            else:
                self.logger.debug("input_name = {} | message=proxy_disabled | Request Call:Proxy is Disabled"
                .format(self.input_name)
                )

            self.logger.debug("input_name = {} | message=api_call | url: {}, params: {}".format(self.input_name, url, params))
            response = requests.get(url, params=params, headers=headers, proxies=proxy_settings)
            status_code = response.status_code
            text = response.text

            if status_code == 200:
                response = response.json()
                return response, headers
            elif status_code == 504 and params.get("vulnerability_ids"):
                self.logger.info(
                    "input_name = {} | message=updating_vulnerability_chunk |"
                    " Updating vulnerability chunk size to minimum(5) as 504 error occured while fetching"
                    " vulnerability-devices data.".format(self.input_name)
                )
                self.logger.info(
                    "input_name = {} | message=data_collection_terminated |"
                    " Current data collection is terminated. Updated chunk size (5)" 
                    " will be used on the next invocation.".format(self.input_name)
                )
                value = {"vulnerabilities_chunk":"5"}
                stanza = "armis_vulnerability://{}".format(self.input_name)
                encoded_stanza = quote_plus(stanza, safe="")
                response = rest.simpleRequest(
                    "/servicesNS/nobody/TA-armis/configs/conf-inputs/{}"
                    .format(encoded_stanza),
                    method='POST',
                    postargs=value,
                    sessionKey=session_key,
                    raiseAllErrors=True,
                )
                raise Exception(text)
            elif status_code == 504:
                self.logger.error(
                    "input_name = {} | message=api_call_error"
                    "Armis Error: Error occurred while making api call."
                    "Status code: {} and "
                    "Response: {}".format(self.input_name, status_code, text)
                )
                raise Exception(text)
            elif status_code in [400, 401, 405] or status_code in constants.STATUS_FORCELIST:
                self.logger.error(
                    "input_name = {} | message=fetching_error"
                    "Armis Error: Error occurred while fetching data."
                    "Status code: {} and "
                    "Response: {}".format(self.input_name, status_code, text)
                )
                self.logger.info(
                    "input_name = {} | message=retry_mechanism "
                    "| Armis Info: Started retry mechanism as API rate limit exceeded"
                    .format(self.input_name)
                )

                # Retry Mechanism
                if self.retry_count == constants.RETRY_COUNT:
                    while self.retry_count > 0:
                        self.logger.debug(
                            "input_name = {} | message=retry_mechanism "
                            "| Armis Debug: Started retry mechanism and retry count is {} "
                            .format(self.input_name, (constants.RETRY_COUNT - self.retry_count) + 1)
                        )
                        time.sleep(3)
                        self.retry_count -= 1
                        headers = self.get_token()
                        if headers:
                            res, headers = self.make_request_call(url, headers, params)
                            if res:
                                break
                    self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
                    return res, headers

            else:
                self.logger.error(
                    "input_name = {} | message=fetching_error "
                    "| ArmisError: Error occurred while fetching data. "
                    "| Status code: {} and "
                    "Response: {}".format(self.input_name, status_code, text)
                )

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.logger.error(
                "input_name = {} | message=http_or_connection_error "
                "| ArmisError: HTTPError or ConnectionError occurred while fetching data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials. "
                "| Error: {}".format(self.input_name, quote_plus(str(e)))
            )
            self.logger.debug(
                "input_name = {} | message=http_or_connection_error "
                "| ArmisDebug: HTTPError or ConnectionError occurred while fetching data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials. "
                "| Error trace: {}".format(self.input_name, traceback.format_exc())
            )

        except Exception as e:
            self.logger.error(
                "input_name = {} | message=fetching_error"
                " | ArmisError: Exception occurred while fetching data. "
                "| Error: {}".format(self.input_name, str(e))
            )
            self.logger.debug(
                "input_name = {} | message=unexpected_error "
                "| ArmisDebug: Unexpected error occured. "
                "| Error trace: {}".format(self.input_name, traceback.format_exc())
            )

        return None, None

    def fetch_device(self, headers):
        """Fetch Devices from the response."""
        self.logger.info("input_name={} | message=fetching_devices_data | TA-armis: Fetching devices...".format(self.input_name))

        if self.backfill_days:
            pattern = 'timeFrame:("[0-9]*\s*\S*)'
            self.aql_query = re.sub(
                pattern, 'timeFrame:"{} {}"'.format(self.backfill_days, self.backfill_type), self.aql_query
            )
        offset = 0
        length = constants.DEVICE_PARAMS_LENGTH
        device_fields = ""
        if not self.helper.get_arg('device_fields'):
            device_fields = constants.DEFAULT_DEVICE_FIELDS
        else:
            device_fields = self.helper.get_arg('device_fields').strip()
            device_fields += ",lastSeen"
            if self.armis_fetch_applications:
                device_fields += ",ipAddress,macAddress,id"
        
        self.logger.debug("input_name={} | message=fetching_devices_data | Device Fields: {}".format(self.input_name, device_fields))

        url = "https://{}/api/v1/search/".format(self.armis_host)
        params = {
            "aql": self.aql_query,
            "fields": device_fields,
            "from": str(offset),
            "length": str(length),
            "orderBy": "lastSeen",
        }
        self.logger.info("input_name={} | message=AQL_query | TA-armis: AQL to query: {}"
            .format(self.input_name, params["aql"])
            )
        response, headers = self.make_request_call(url, headers, params)
        if response is None:
            self.logger.error("input_name={} | message=no_response | Exited from the program due to no response."
                .format(self.input_name)
                )
            sys.exit(1)
        return response, params, offset, length, url

    def fetch_vulnerability(self, headers):
        """Fetch vulnerability from the response."""
        self.logger.info("input_name={} | message=fetching_vulnerability_data | TA-armis: Fetching vulnerabilities...".format(self.input_name))

        offset = 0
        length = constants.VULNERABILITIES_PARAMS_LENGTH
        url = "https://{}/api/v1/search/".format(self.armis_host)
        params = {
            "aql": "in:vulnerabilities",
            "fields": "affectedDevicesCount,attackComplexity,attackVector,availabilityImpact,confidentialityImpact,cveUid,cvssScore,description,exploitabilityScore,id,impactScore,integrityImpact,latestExploitUpdate,numOfExploits,orgPriority,orgPriorityChangeReason,orgPriorityChangedBy,orgPriorityUpdateTime,privilegesRequired,publishedDate,scope,score,severity,status,userInteraction",
            "from": str(offset),
            "length": str(length),
            "orderBy": "id",
        }
        self.logger.info("input_name={} | message=AQL_query | TA-armis: AQL to query: {}"
            .format(self.input_name, params["aql"])
            )
        response, headers = self.make_request_call(url, headers, params)
        if response is None:
            self.logger.error("input_name={} | message=no_response | Exited from the program due to no response."
                .format(self.input_name)
                )
            sys.exit(1)
        return response, params, offset, length, url

    def fetch_activities(self, url, headers, id):
        """To fetch activities per alert."""
        try:
            offset = 0
            length = 1000
            params = {
                "aql": 'in:activity alert:(alertId:({}))'.format(id),
                "from": str(offset),
                "length": str(length),
                "orderBy": 'time',
            }
            self.logger.info("input_name={} | message=AQL_query | TA-armis: AQL to query: {}"
                .format(self.input_name, params["aql"])
                )
            response_activity, headers = self.make_request_call(url, headers, params)
            if response_activity is None:
                raise Exception
        
            _response_activity = []
            while len(response_activity["data"]["results"]) > 0:
                _response_activity.extend(response_activity["data"]["results"])
                if not response_activity["data"]["next"]:
                    break
                else:
                    offset = offset + length
                    params['from'] = offset
                    response_activity, headers = self.make_request_call(url, headers, params)
            return _response_activity, headers
        except Exception as e:
            self.logger.info("input_name={} | message=fetching_error | Error occured while fetching activities data: {}"
                .format(self.input_name, str(e))
                )
            return None

    def get_checkpoint(self):
        """Get checkpoint."""
        try:
            checkpoint = json.loads(self.helper.get_check_point(self.key) or "{}")
            if checkpoint and checkpoint.get("time") and checkpoint.get("alert_ids"):
                self.logger.info("input_name={} | message=checkpoint_found | Checkpoint found : {}"
                    .format(self.input_name, checkpoint)
                )
                return 'in:alerts after:{}'.format(checkpoint.get("time")), checkpoint.get("alert_ids"), checkpoint.get("time")
            else:
                self.logger.info("input_name={} | message=checkpoint_not_found | Checkpoint not found. starting data collection from {} days"
                    .format(self.input_name, self.lookback_days)
                )
                return 'in:alerts timeFrame:"{} days"'.format(self.lookback_days), None, None
        except Exception as e:
            self.logger.info("input_name={} | message=checkpoint_error | Error occured while fetching checkpoint: {}"
                .format(self.input_name, str(e))
            )
            self.logger.debug("input_name={} | message=checkpoint_error | Error occured while fetching checkpoint: {}"
                .format(self.input_name, traceback.format_exc())
            )

    def save_checkpoint(self, checkpoint_time, alert_id):
        """Save checkpoint."""
        try:
            
            checkpoint = {}
            checkpoint["time"]  = checkpoint_time
            checkpoint["alert_ids"] = alert_id   
            self.helper.save_check_point(self.key, json.dumps(checkpoint))
            self.logger.info("input_name={} | message=checkpoint_saved | Checkpoint saved successfully. Checkpoint : {}"
                .format(self.input_name, checkpoint)
            )
        except Exception as e:
            self.logger.info("input_name={} | message=checkpoint_error | Error occured while saving checkpoint: {}"
                .format(self.input_name, str(e))
            )
            self.logger.debug("input_name={} | message=checkpoint_error | Error occured while saving checkpoint: {}"
                .format(self.input_name, traceback.format_exc())
            )

    def fetch_alerts_activities(self, headers):
        """Fetch vulnerability from the response."""
        self.logger.info("input_name={} | message=fetching_alerts_data | TA-armis: Fetching Alerts...".format(self.input_name))
        try:

            def termination_signal_handler(sig, frame):
                """Handle termination signal sent by Splunk."""
                self.logger.info(
                    "input_name={} | message=termination_signal_received"
                    " | Received the termination signal."
                    " | Initializing the termination process."
                    .format(self.input_name)
                )
                raise Exception
            signal.signal(signal.SIGTERM, termination_signal_handler)
            
            offset = 0
            length = 1000
            counter = 0

            url = "https://{}/api/v1/search/".format(self.armis_host)
            aql, alert_ids, _time = self.get_checkpoint()
            params = {
                "aql": aql,
                "from": str(offset),
                "length": str(length),
                "orderBy": 'time',
            }
            self.logger.info("input_name={} | message=AQL_query | TA-armis: AQL to query: {}"
                .format(self.input_name, params["aql"])
            )
            response, headers = self.make_request_call(url, headers, params)
            if response is None:
                raise Exception
            alert_id=[]
            checkpoint_time = None
            while len(response["data"]["results"]) > 0:
                
                for res in response["data"]["results"]:
                    event_time = res.get("time")[:19]
                    # Handling Timestamp format
                    if len(event_time) != 19:
                        if len(event_time) == 10:
                            # eg. 2022-04-02T
                            event_time += "T00:00:00"
                            res["time"] += "T00:00:00.000000+00:00"
                            self.logger.info(
                                "input_name={} | message=time_added_with_T "
                                "| 'T:00:00:00' added as only date is available.".format(self.input_name)
                            )
                        elif len(event_time) == 11:
                            # eg. 2022-04-02T
                            event_time += "00:00:00"
                            res["time"] += "00:00:00.000000+00:00"
                            self.logger.info(
                                "input_name={} | message=time_added "
                                "| '00:00:00' added as only date and 'T' is available.".format(self.input_name) 
                            )
                        elif len(event_time)  == 16 and "+" in event_time:
                            # eg. 2022-04-02+00:00
                            event_time = event_time.split("+")[0] + "T00:00:00"
                            res["time"] = event_time + ".000000+00:00"
                        elif len(event_time)  == 17 and "+" in event_time:
                            # eg. 2022-04-02T+00:00
                            event_time = event_time.split("+")[0] + "00:00:00"
                            res["time"] = event_time + ".000000+00:00"
                        else:
                            splited_time = event_time.split('T')
                            if len(splited_time[1]) == 5:
                                # eg. 2022-04-02T02:22
                                splited_time[1] += ":00"
                                res["time"] += ":00.000000+00:00"
                                self.logger.info(
                                    "input_name={} | message=second_added "
                                    "| ':00' added as only hour and minute is available.".format(self.input_name)                              )
                            elif len(splited_time[1]) == 2:
                                # eg. 2022-04-02T02
                                splited_time[1] += ":00:00"
                                res["time"] += ":00:00.000000+00:00"
                                self.logger.info(
                                    "input_name={} | message=minute_and_second_added "
                                    "| ':00:00' added as only hour is available.".format(self.input_name) 
                                )
                            event_time = "T".join(splited_time)
        
                    elif len(event_time) == 19 and len(res.get("time")) == 25:
                        # eg. 2022-04-02T02:22:24+00:00
                        res["time"] = event_time + ".000000+00:00"
                    elif (len(event_time)) == 19 and "+" in event_time:
                        temp_list = event_time.split("+")
                        if len(temp_list[0]) == 13:
                            # eg. 2022-04-02T02+00:00
                            res["time"] = temp_list[0] + ":00:00.000000+00:00"
                            event_time = temp_list[0] + ":00:00"
                        elif len(temp_list[0]) == 16:
                            # eg. 2022-04-02T02:22+00:00
                            res["time"] = temp_list[0] + ":00.000000+00:00"
                            event_time = temp_list[0] + ":00"
                    elif len(res.get("time")) == 19:
                        # eg. 2022-04-02T02:22:24
                        res["time"] += ".000000+00:00"
                    elif len(res.get("time")) == 26:
                        # eg. 2022-04-02T02:22:24.000000
                        res["time"] += "+00:00"
                    
                    if alert_ids  and event_time == _time and res.get("alertId") in alert_ids:
                        continue
                    else:
                        alert_ids = None  
                        del res['activityUUIDs']
                        id = res.get("alertId")
                        res["activities"], headers = self.fetch_activities(url, headers, id)
                        self.write_alert_event(res)
                        counter = counter + 1
                        if checkpoint_time and checkpoint_time is res["time"][:19]:
                            alert_id.append(id)
                        else:
                            checkpoint_time = res["time"][:19]
                            alert_id = []
                            alert_id.append(id)
    
                if counter > 0:
                    self.save_checkpoint(checkpoint_time, alert_id)
                if not response["data"]["next"]:
                    break
                else:
                    offset = offset + length
                    params['from'] = offset
                    response, headers = self.make_request_call(url, headers, params)

            self.logger.info(
                "input_name={} | message=total_events_collected " 
                "| Total {} events are collected for armis alerts"
                .format(self.input_name, counter)
            )
        except Exception as e:
            self.logger.info(
                "input_name={} | message = alert_activities_fetching_error "
                "| Error occured while fetching alert and activities event: {}"
                .format(self.input_name, str(e))
            )
            self.logger.debug(
                "input_name={} | message = alert_activities_fetching_error "
                "| Error occured while fetching alert and activities event: {}"
                .format(self.input_name, traceback.format_exc()))
        finally:
            if counter > 0:
                self.save_checkpoint(checkpoint_time, alert_id)
    
    def write_alert_event(self, response):
        """write events."""
        try:
            event = self.helper.new_event(
                    source=self.helper.get_input_type(),
                    index=self.helper.get_arg('index'),
                    sourcetype="armis:api:alerts",
                    data=json.dumps(response, ensure_ascii=False)
                )
            self.ew.write_event(event)
        except Exception as e:
            self.logger.info(
                "input_name={} | message=writing_alert_error "
                "| Error occured while writing an alert event: {}"
                .format(self.input_name, str(e))
            )
            self.logger.debug(
                "input_name={} | message=writing_alert_error "
                "| Error occured while writing an alert event: {}"
                .format(self.input_name, traceback.format_exc())
            )
            raise Exception
            

    def write_event(self, response, ew, params, offset, length, url, headers, start_time, sourcetype):
        """Write Events to Splunk."""
        type_data = "vulnerabilities"
        if sourcetype == "armis:device":
            type_data = "devices"
        devices = []
        while len(response["data"]["results"]) > 0:
            devices.extend(response["data"]["results"])
            for device in response["data"]["results"]:
                ts = time.time()
                raw_event = Event()
                raw_event.stanza = "%s" % (self.input_name)
                raw_event.sourceType = sourcetype
                raw_event.time = ts
                raw_event.host = self.armis_host
                raw_event.data = json.dumps(device, separators=(",", ":"), sort_keys=True)
                ew.write_event(raw_event)

            offset = offset + length
            params["from"] = offset
            time.sleep(0.5)
            self.logger.info("input_name = {} | message=query_url | TA-armis: {} URL to query: {} with offset ({})"
                .format(self.input_name, type_data, url, offset)
            )

            try:
                if not response["data"]["next"]:
                    break
                response, headers = self.make_request_call(url, headers, params)
            except Exception as e:
                self.logger.error("input_name = {} | message=exception | Exception occured: {}".format(self.input_name, e))
                sys.exit(1)
            if response is None:
                self.logger.error("input_name = {} | message=no_response | Exited from the program due to no response."
                    .format(self.input_name)
                )
                sys.exit(1)

        if sourcetype == "armis:device":
            if len(devices) > 0:
                self.helper.save_check_point(self.input_name, devices[-1].get("lastSeen"))
                self.logger.debug("input_name={} | message=checkpoint_stored | Checkpoint stored {}"
                    .format(self.input_name, self.helper.get_check_point(self.input_name))
                )

        self.logger.info("input_name={} | message=total_events_collected | Total events collected for {} are {}"
            .format(self.input_name, type_data, len(devices))
        )
        self.logger.info(
            "input_name = {} | message=time_taken | Total time taken to fetch {}: {} minutes"
            .format(self.input_name, type_data, (time.time() - start_time) / 60)
        )
        self.logger.info("input_name = {} | message=devices_written | TA-armis: Done for Armis {}"
            .format(self.input_name, type_data)
        )
        return devices


    def fetch_device_ids(self, devices):
        """Fetch device ids."""
        device_ids = []
        for device in devices:
            device_ids.append(device.get("id") if device.get("_key") is None else device.get("_key"))
        return device_ids


    def ingest_application_data(self, application_response, device, ew):
        """Ingest application data."""
        count_events = 0
        for application in application_response["data"]["items"]:
            deviceId = application["deviceId"]
            for individual_device in device:
                individual_device_id = individual_device.get("id") if individual_device.get("_key") is None else individual_device.get("_key")
                if str(deviceId) == str(individual_device_id):
                    ts = time.time()
                    application["ipAddress"] = individual_device["ipAddress"]
                    application["macAddress"] = individual_device["macAddress"]
                    application_event = Event()
                    application_event.stanza = self.input_name
                    application_event.sourceType = "armis:application"
                    application_event.host = self.armis_host
                    application_event.time = ts
                    application_event.data = json.dumps(application, separators=(",", ":"), sort_keys=True)
                    ew.write_event(application_event)
                    count_events = count_events + 1
                    break
            
        return count_events

    
    def fetch_application_inventory(self, devices, length, url, headers, ew, start_time):
        """Fetch Applications from devices."""
        no_of_application_events = 0
        # instead of looping on each device, do it on a batch of 100 devices
        devices = [devices[i : i + 100] for i in range(0, len(devices), 100)]
        for device in devices:
            device_ids = self.fetch_device_ids(device)
            str_device_ids = ",".join(device_ids)

            offset = 0
            application_params = {
                "device_ids": str_device_ids,
                "from": str(offset),
                "length": str(length),
            }

            self.logger.info("input_name = {} | message=getting_applications | Getting Applications for {} devices."
                .format(self.input_name, len(device_ids))
            )
            self.logger.debug("input_name = {} | message=getting_applications | Getting Applications for devices {}."
                .format(self.input_name, device_ids)
            )
            
            application_response, headers = self.make_request_call(url, headers, application_params)
            if application_response is None:
                self.logger.error("input_name = {} | message=no_response | Exited from the program due to no response."
                    .format(self.input_name)
                )
                sys.exit(1)

            count = len(application_response.get("data", {}).get("items", []))
            while count > 0:
                count_events = 0
                count_events += self.ingest_application_data(application_response, device, ew)

                no_of_application_events = no_of_application_events + count_events
                if not application_response.get("data", {}).get("next"):
                    break
                else:
                    application_params['from'] = application_response.get("data", {}).get("next")
                    application_response, headers = self.make_request_call(url, headers, application_params)

        self.logger.info("input_name = {} | message=applications_fetched | TA-Armis: Done for Armis Application from devices."
            .format(self.input_name)
        )
        self.logger.info("input_name = {} | message=count_of_applications_collected | Total Application Events Collected are {}"
            .format(self.input_name, no_of_application_events)
        )
        self.logger.info(
            "input_name={} | message=time_taken | Total time taken to fetch applications: {} minutes"
            .format(self.input_name, (time.time() - start_time) / 60)
        )

    def get_backfill_days(self, last_seen):
        """Method to get the timeFrame value."""
        try:
            start_time = last_seen
            start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%f+00:00")
            # Get current utc time
            end_time = datetime.utcnow()
            # Get the difference
            time_frame = end_time - start_time
            # Convert into seconds
            days, seconds = time_frame.days, time_frame.seconds
            total_seconds = days * constants.PER_DAY_SECONDS + seconds + 2
            if total_seconds > constants.NO_OF_SECONDS_ALLOWED:
                total_seconds = constants.NO_OF_SECONDS_ALLOWED
            return total_seconds
        except Exception:
            raise Exception("Some error occured while getting the timeFrame value.")
        
    def write_vuln_match_data(self, data_returned):
        '''Writes vuln-match data'''
       
        final_list = []
        dict_of_all_id = {}         
        # Make a dictionary of all vulnerability IDs and corresponding affected devices, firstDetected and lastDetected in form of list                        
        for each in data_returned:      
            if each["cveUid"] in dict_of_all_id.keys():
                dict_of_all_id[each["cveUid"]][0].append(each["deviceId"])
                dict_of_all_id[each["cveUid"]][1].append(each["firstDetected"])  
                dict_of_all_id[each["cveUid"]][2].append(each["lastDetected"])    
            else:
                dict_of_all_id[each["cveUid"]] = [ [each["deviceId"]], [each["firstDetected"]], [each["lastDetected"]] ]
        for k,v in dict_of_all_id.items():
            fd = {}
            fd["_key"] = k
            fd["vuln_id"] = k
            fd["deviceId"] = v[0]
            fd["firstDetected"] = v[1]
            fd["lastDetected"] = v[2]
            final_list.append(fd)
        if not self.index_vuln_match_data:
            self.logger.debug("Ingesting the vuln-device mapping data into kvstore lookup as Index Vuln-Device Mappings is not selected.")      
            session_key = self.helper.context_meta["session_key"]
            session_key = ar_utils.get_session_key(self.helper, session_key)
            self.send_to_kvstore(session_key, self.helper, final_list)
        else:
            self.logger.debug("Ingesting the vuln-device mapping data into splunk index as Index Vuln-Device Mappings is selected.")
            try:
                for response in final_list:
                    if response["vuln_id"] in vuln_id_list:
                        continue
                    else:
                        event = self.helper.new_event(
                                source=self.helper.get_input_type(),
                                index=self.helper.get_arg('index'),
                                sourcetype="armis:vuln:match",
                                data=json.dumps(response, ensure_ascii=False)
                        )
                        self.ew.write_event(event)
                        vuln_id_list.add(response["vuln_id"])
            except Exception as e:
                self.logger.info(
                    "input_name={} | message=writing_vuln_match_data_error "
                    "| Error occured while writing an vuln match event: {}"
                    .format(self.input_name, str(e))
                )
                self.logger.debug(
                    "input_name={} | message=writing_vuln_match_error "
                    "| Error occured while writing an vuln match event: {}"
                    .format(self.input_name, traceback.format_exc())
                )
                raise Exception    

    def get_list_of_all_vuln_id(self, cve_content):
        """Returns list of all vulnerabilities IDs"""
        list_of_vuln_ids = []
        for x in range(len(cve_content)):
            list_of_vuln_ids.append(cve_content[x]["cveUid"])
        self.logger.info("input_name = {} | message=total_vulnerability_count | length of total vulnerability count = {}"
            .format(self.input_name, len(list_of_vuln_ids))
        )
        return list_of_vuln_ids

    def vul_to_string(self, list_of_vul):
        """Converts Vuln-ids to strings for not more than 1000 chars"""
        param_string = ""
        list_of_all_vul_strings = []
        for i in list_of_vul:
            if (len(param_string) + len(str(i)) + 1) < self.vulnerabilities_chunk * 14:
                param_string = param_string + str(i) + ","
            else:
                param_string = param_string.rstrip(param_string[-1])
                list_of_all_vul_strings.append(param_string)
                param_string = ""
                param_string = str(i) + ","
        param_string = param_string.rstrip(param_string[-1])
        list_of_all_vul_strings.append(param_string)
        return list_of_all_vul_strings

    def get_match_vuln(self, cve_data):
        """To collect Armis Vulnerability-match data"""
        try:
            vul_id_list = self.get_list_of_all_vuln_id(cve_data)    
            list_of_vul_strings = self.vul_to_string(vul_id_list) 
            headers = self.get_token()
            for st in list_of_vul_strings:
                offset = 0
                length = constants.VULN_MATCH_PARAMS_LENGTH
                requestURL = constants.URL_FOR_VULN_MATCH.format(self.armis_host)
                params = {
                    "vulnerability_ids": "{}".format(str(st)), 
                    "from": str(offset),
                    "length": str(length),
                    "orderBy": "firstDetected",
                }                                  
                response, headers = self.make_request_call(requestURL, headers, params)    
                while (
                    response is not None and 
                    response["data"] is not None and 
                    response["data"]["sample"] is not None and 
                    len(response["data"]["sample"])>0
                ): 
                    data_returned = response["data"].get("sample")
                    
                    self.write_vuln_match_data(data_returned)
        
                    offset = offset + length
                    params["from"] = str(offset)
                    if not response["data"]["paging"]["next"]:
                        break
                    response, headers = self.make_request_call(requestURL, headers, params)
                else:
                    raise Exception("Exited From match-vuln API Calls due to no response")
            self.logger.info(
                "input_name = {} | message=fetched_data_from_vulnmatch_api | Successfully fetched all the vuln-match data from API"
                .format(self.input_name)
            )     

        except Exception as e:
            self.logger.error("input_name={} | message=fetching_error | Armis Error:{}".format(self.input_name, e))
            self.logger.error(
                "input_name={} | message=fetching_error | Armis Error: Error Occured While getting match-vulnerability data collection"
                .format(self.input_name)
            )
            self.logger.debug(
                "input_name={} | message=fetching_error | Armis Debug: Error Occured While getting match-vulnerability data collection : {}"
                .format(self.input_name, traceback.format_exc())
            )
            return None
    
    def get_vulnerabilities(self, helper, ew):
        """To collect Armis Vulnerabilities and Vulnerability-match data."""
        start_time = time.time()

        self.logger.info("input_name={} | message=access_token_url | TA-armis - url={}".format(self.input_name, self.endpoint_url))
        # Get access key and set it into header.
        headers = self.get_token()
        if headers:
            response, params, offset, length, url = self.fetch_vulnerability(headers)
            self.logger.info("input_name={} | message=writing_to_splunk | Collects and write vulnerabilities events to splunk."
                .format(self.input_name)
            )
            cves = self.write_event(response, ew, params, offset, length, url, headers, start_time, "armis:cve")
    
        # Vulnerability-match logic
        self.logger.info("input_name = {} | message=data_collection_started | Data collection for vulnerability-match started"
            .format(self.input_name)
        )

        self.get_match_vuln(cves)

    def get_alerts(self, ew):
        """To collect Armis Alerts data."""
        start_time = time.time()

        self.logger.info("input_name={} | message=access_token_url | TA-armis - url={}".format(self.input_name, self.endpoint_url))
        # Get access key and set it into header.
        headers = self.get_token()
        if headers:
            self.fetch_alerts_activities(headers)

    def get_data(self, ew):
        """To collect Armis Devices data."""
        start_time = time.time()
        try:
            checkpoint = self.helper.get_check_point(self.input_name)
            if checkpoint:
                self.logger.debug(
                    "input_name = {} | message=checkpoint_found | Found an existing checkpoint {}"
                    .format(self.input_name, checkpoint)
                )
                self.backfill_days = self.get_backfill_days(checkpoint)
                self.backfill_type = "seconds"
            else:
                self.logger.debug("input_name = {} | message=checkpoint_not_found | No old checkpoint found."
                    .format(self.input_name)
                )
        except Exception as e:
            self.logger.error("input_name = {} | message=device_error | Error - {}".format(self.input_name, str(e)))

        self.logger.info(
            "TA-armis - url=%s fetch_applications=%s backfill_time=%s %s"
            % (self.endpoint_url, self.armis_fetch_applications, self.backfill_days, self.backfill_type)
        )
        # Get access key and set it into header.
        headers = self.get_token()
        if headers:
            response, params, offset, length, url = self.fetch_device(headers)
            self.logger.info("input_name = {} | message=writing_to_splunk | Collects and write events to splunk."
                .format(self.input_name)
            )
            devices = self.write_event(response, ew, params, offset, length, url, headers, start_time, "armis:device")

        # If Fetch Application Inventory checkbox selected, then below method will run
        if self.armis_fetch_applications:
            self.logger.info(
                "input_name = {} | message=inserting_in_lookup | Inserting devices records in application checkpoint lookup."
                .format(self.input_name)
            )
            # Initializing object of ApplicationCheckpoint
            application_checkpoint = ApplicationCheckpoint(self.helper, self.logger, self.input_name)
            # Calling kvstore_insert method for inserting devices data in collection
            application_checkpoint.kvstore_insert(devices)
            self.logger.info("input_name = {} | message=querying_lookup | Querying kvstore checkpoint lookup to fetch device records."
                .format(self.input_name)
            )
            response = application_checkpoint.query_kv_store()
            url = constants.URL_FOR_APPLICATION.format(self.armis_host)
            length = constants.APPLICATION_PARAMS_LENGTH
            if response is None:
                self.logger.warning(
                    "input_name = {} | message=kvstore_not_ready | KVStore is not ready. Please make sure that KVStore is enabled if not then there could be chances of application data loss."
                    .format(self.input_name)
                )
                self.fetch_application_inventory(devices, length, url, headers, ew, start_time)
            else:
                devices = sorted(response, key=lambda d: int(d["_key"]))
                self.logger.info("input_name = {} | message=fetching_application_devices | Fetches Application devices."
                    .format(self.input_name)
                )
                self.fetch_application_inventory(devices, length, url, headers, ew, start_time)
                self.logger.info("input_name = {} | message=deleting_records | Deleting devices records from application checkpoint lookup."
                    .format(self.input_name)
                )
                application_checkpoint.kvstore_delete()
