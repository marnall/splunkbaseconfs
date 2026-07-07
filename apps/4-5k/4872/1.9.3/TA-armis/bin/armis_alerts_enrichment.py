"""This file if for data collection logic."""
import ta_armis_declare

import time
import traceback
from datetime import datetime
import json
import copy
import requests
import logging
import splunklib.client as splunkClient
import splunklib.results as results

from requests.compat import quote_plus
from splunklib.modularinput import *
from proxy_config import read_proxies_from_conf
from log_manager import setup_logging

import armis_constants as constants

logging.getLogger("urllib3").propagate = False


class ArmisAlert(object):
    """A class for all the alerts related data collection."""

    def __init__(self, helper, ew, logger):
        """Initialize an object."""
        self.account = helper.get_arg("global_account")
        self.input_name = helper.get_input_stanza_names()
        self.armis_host = self.account["armis_hostname"]
        self.secret = self.account["armis_api_key"]
        self.armis_index = helper.get_arg("armis_index")
        self.session_key = helper.context_meta["session_key"]
        self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
        self.endpoint_url = "https://{}/api/v1/access_token/".format(self.armis_host)
        self.headers = None
        self.params = {
            "fields": "tags,biosType,biosVendor,biosVersion,category,firmwareVersion,firstSeen,fqdn,id,imei,ipAddress,ipv6,lastSeen,macAddress,manufacturer,meid,model,name,operatingSystem,operatingSystemVersion,osBuildNumber,osEdition,osKernelType,osKernelVersion,osLastLoginTime,osServicePack,osTcpIpStack,phoneNumber,publicIp,riskLevel,serialNumber,site,tcpIpStack,type,udid"
        }
        self.total_devices_count = 0
        self.helper = helper
        self.ew = ew
        self.logger = logger

    def get_access_token(self):
        """Get Access Token."""
        data = {"secret_key": self.secret}
        self.logger.debug("TA-armis - url=%s" % (self.endpoint_url))
        try:
            session_key = self.helper.context_meta["session_key"]
            proxy_settings = read_proxies_from_conf(session_key)
            if proxy_settings:
                self.logger.info("input_name={} | message=proxy_enabled | Alerts:Proxy is Enabled".format(self.input_name))
            else:
                self.logger.info("input_name={} | message=proxy_disabled | Alerts:Proxy is Disabled".format(self.input_name))
            r = requests.post(self.endpoint_url, data=data, proxies=proxy_settings)
            token = r.json().get("data").get("access_token")
            headers = {
                "Authorization": token,
            }
            return headers

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.logger.error(
                "input_name={} | message=http_or_connection_error"
                "ArmisError: HTTPError or ConnectionError occurred while fetching access token"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error: {}".format(self.input_name, quote_plus(str(e)))
            )
            self.logger.debug(
                "input_name={} | message=http_or_connection_error"
                "ArmisDebug: HTTPError or ConnectionError occurred while fetching access token"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " Error trace: {}".format(self.input_name, traceback.format_exc())
            )
            return False

        except Exception as e:
            self.logger.error("input_name={} | message=token_error | ArmisError: Could not retrieve token. Error: {}"
                .format(self.input_name, str(e))
            )
            return False

    def write_devices(self, device, url):
        """Fetch and write data to splunk."""
        try:
            session_key = self.helper.context_meta["session_key"]
            proxy_settings = read_proxies_from_conf(session_key)
            if proxy_settings:
                self.logger.info("input_name={} | message=proxy_enabled | Writing Alerts Data to Splunk:Proxy is Enabled"
                    .format(self.input_name)
                )
            else:
                self.logger.info("input_name={} | message=proxy_disabled | Writing Alerts Data to Splunk:Proxy is Disabled"
                    .format(self.input_name)
                )
            response = requests.get(url, headers=self.headers, params=self.params, proxies=proxy_settings)
            status_code = response.status_code
            if status_code == 200:
                device_count = response.json().get("data")["count"]
                if device_count > 0:
                    device_data = response.json().get("data").get("data")[0]
                    device_data["alert_id"] = device.get("alert_id")
                    device_data["_time"] = device.get("alert_time")
                    raw_event = Event()
                    raw_event.stanza = "%s" % (self.input_name)
                    raw_event.sourceType = "armis:alert:device"
                    raw_event.host = self.armis_host
                    raw_event.data = json.dumps(device_data, separators=(",", ":"))
                    self.ew.write_event(raw_event)
                    self.total_devices_count += 1
                else:
                    self.logger.info("input_name={} | message=data_not_found | No data found for device id - {}"
                        .format(self.input_name, device.get("device_id"))
                    )
            elif status_code in [400, 401, 405] or status_code in constants.STATUS_FORCELIST:
                self.logger.error(
                    "input_name={} | message=fetching_error"
                    "Armis Error: Error occurred while fetching device data."
                    " Status code: {} ".format(self.input_name, status_code)
                )

                self.logger.info(
                    "input_name={} | message=retry_mechanism_started."
                    "Armis Info: Started retry mechanism as API rate limit exceeded"
                    .format(self.input_name)
                )
                # Retry Mechanism
                if self.retry_count == constants.RETRY_COUNT:
                    while self.retry_count > 0:
                        self.logger.debug(
                            "input_name={} | message=retry_mechanism_started"
                            "Armis Debug: Started retry mechanism and retry count is {} "
                            .format(self.input_name, (constants.RETRY_COUNT - self.retry_count) + 1)
                        )
                        time.sleep(3)
                        self.retry_count -= 1
                        headers = self.get_access_token()
                        self.headers = headers
                        self.write_devices(device, url)
                        if headers:
                            break
                    self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
            else:
                self.logger.error(
                    "input_name={} | message=fetching_error"
                    "ArmisError: Error occurred while fetching device data. "
                    " Status code: {} and "
                    " DeviceId: {}".format(self.input_name, status_code, device.get("device_id"))
                )

        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            self.logger.error(
                "input_name={} | message=http_or_connection_error"
                "ArmisError: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " DeviceId: {}, Error: {}".format(self.input_name, device.get("device_id"), quote_plus(str(e)))
            )
            self.logger.debug(
                "input_name={} | message=http_or_connection_error"
                "ArmisDebug: HTTPError or ConnectionError occurred while fetching device data"
                " or Invalid Proxy Credentials. Please verify Proxy settings"
                " or Please verify Armis Credentials."
                " DeviceId: {}, Error trace: {}".format(self.input_name, device.get("device_id"), traceback.format_exc())
            )

        except Exception as e:
            self.logger.error(
                "input_name={} | message=fetching_error"
                "ArmisError: Exception occurred while fetching device data. "
                "DeviceId: {}, Error: {}".format(self.input_name, device.get("device_id"), str(e))
            )
            self.logger.debug(
                "input_name={} | message=fetching_error"
                "ArmisDebug: Unexpected error occured. "
                "DeviceId: {}, Error trace: {}".format(self.input_name, device.get("device_id"), traceback.format_exc())
            )

    def fetch_devices_not_found(self, devices):
        """Method to fetch devices data through api call."""
        self.logger.info("input_name={} | message=collecting_devices_data | Collecting {} devices info through API call and writing to splunk ."
            .format(self.input_name, len(devices))
        )
        self.headers = self.get_access_token()
        for device in devices:
            url = "https://%s/api/v1/devices/?id=%s" % (self.armis_host, device.get("device_id"))
            self.logger.debug("input_name={} | message=query_url | TA-armis: Device URL to query {}".format(self.input_name, url))
            self.write_devices(device, url)

    def get_devices_data(self, alerts_list, serviceobj):
        """To search device data for which alert is generated and index it. Return a list of devices not found in search."""
        devices_not_found = []
        for device in alerts_list:
            device_ids = device.get("device_ids")
            alert_id = device.get("alert_id")
            alert_time = device.get("alert_time")
            try:
                for device_id in device_ids:
                    try:
                        device_query = "search index={} sourcetype=armis:device id={} | head 1".format(
                            self.armis_index, device_id
                        )
                        device_result = serviceobj.jobs.oneshot(device_query, count=0)
                        device_reader = results.ResultsReader(device_result)
                        device_flag = False
                        for device in device_reader:
                            device_flag = True
                            device = dict(device).get("_raw")
                            device = json.loads(device)
                            device["alert_id"] = alert_id
                            device["_time"] = alert_time
                            device = json.dumps(device)
                            raw_event = Event()
                            raw_event.stanza = "%s" % (self.input_name)
                            raw_event.sourceType = "armis:alert:device"
                            raw_event.host = self.armis_host
                            raw_event.data = device
                            self.ew.write_event(raw_event)
                            self.total_devices_count += 1
                        if not device_flag:
                            device_to_add = {"device_id": device_id, "alert_id": alert_id, "alert_time": alert_time}
                            devices_not_found.append(device_to_add)
                    except Exception as e:
                        self.logger.error("input_name={} | message=fetching_error | Error occured while fetching specific "
                                          "device data.\n Error {}".format(self.input_name, str(e)))
                        continue
            except Exception as e:
                self.logger.error(
                    "input_name={} | message=fetching_error"
                    "ArmisError: Error occurred while fetching device data for id - {} \n Error {}"
                    .format(self.input_name, device_id, str(e))
                )
        return devices_not_found

    def get_alerts_list(self, alert_reader):
        """To extract the alert_id, device_id and alert_time from syslog alerts data and return list."""
        alerts_list = []
        alerts_count = 0
        for alert in alert_reader:
            try:
                alert_dict = {}
                alert = dict(alert).get("_raw")
                alert = json.loads(alert)
                alert_dict["alert_id"] = alert.get("id")
                alert_dict["alert_time"] = alert.get("_time")
                related_devices = alert.get("relatedDevices")
                devices_list = []
                for device in related_devices:
                    devices_list.append(device.get("id"))
                alert_dict["device_ids"] = devices_list
                alerts_list.append(alert_dict)
                alerts_count += 1
            except Exception as e:
                self.logger.error("input_name={} | message=fetching_error | Error occured while fetching specific "
                                  "alert data.\n Error {}".format(self.input_name, str(e)))
                continue
        self.logger.info("input_name={} | message=total_alerts_found | Total alerts found are {}."
            .format(self.input_name, alerts_count)
        )
        return alerts_list

    def get_alerts(self):
        """To collect device data for which alerts are generated."""
        start_time = time.time()
        try:
            # Getting checkpoint
            checkpoint = self.helper.get_check_point(self.input_name)
            if checkpoint:
                self.logger.debug(
                    "input_name={} | message=checkpoint_found"
                    "Found an existing checkpoint {}".format(self.input_name, checkpoint)
                )
                current_time = datetime.now()
                current_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%f")
                kwargs_oneshot = {"earliest_time": checkpoint, "latest_time": current_time, "count": 0}
            else:
                self.logger.debug("input_name={} | message=checkpoint_not_found | No old checkpoint found."
                    .format(self.input_name)
                )
                kwargs_oneshot = {"count": 0}
            serviceobj = splunkClient.connect(token=self.session_key, owner="nobody")
            # Fetch syslog alerts data
            self.logger.info("input_name={} | message=fetching_data |TA-armis: Fetching syslog alerts data..."
                .format(self.input_name)
            )
            alert_query = 'search index={} sourcetype="armis:alert" id=*'.format(self.armis_index)
            alert_results = serviceobj.jobs.oneshot(alert_query, **kwargs_oneshot)
            alert_reader = results.ResultsReader(alert_results)
            alerts_list = self.get_alerts_list(alert_reader)

            # Fetch and ingest devices data
            self.logger.info("input_name={} | message=fetching_devices_data | TA-armis: Fetching and ingesting devices data for which alerts are generated..."
                .format(self.input_name)
            )
            list_of_devices_not_found = self.get_devices_data(alerts_list, serviceobj)
            self.logger.info("input_name={} | message=total_devices_data | Found {} devices using search"
                .format(self.input_name, self.total_devices_count)
            )

            # Fetch devices data using api if not found using search
            if (len(list_of_devices_not_found)) > 0:
                self.fetch_devices_not_found(list_of_devices_not_found)

        except Exception as e:
            self.logger.error(
                "input_name={} | message=fetching_error"
                "ArmisError : Error occurred while fetching devices data for which alerts are generated. \nError: - {}".format(
                    self.input_name, str(e)
                )
            )
            self.logger.debug(
                "input_name={} | message=fetching_error"
                "ArmisError : Error occurred while fetching devices data for which alerts are generated. \nError trace : - {}".format(
                    self.input_name, traceback.format_exc()
                )
            )
        else:
            # Storing checkpoint
            checkpoint_time = datetime.now()
            checkpoint_time = checkpoint_time.strftime("%Y-%m-%dT%H:%M:%S.%f")
            self.helper.save_check_point(self.input_name, checkpoint_time)
            self.logger.debug("input_name={} | message=checkpoint_stored | Checkpoint stored {}"
                .format(self.input_name, self.helper.get_check_point(self.input_name))
            )
            self.logger.info("input_name={} | message=total_devices_found | Total devices found are {}"
                .format(self.input_name, self.total_devices_count)
            )
            elapsed_time_data_collection = time.time() - start_time
            self.logger.info("input_name={} | message=time_taken | Time elapsed in data collection is {}"
                .format(self.input_name, elapsed_time_data_collection)
            )
