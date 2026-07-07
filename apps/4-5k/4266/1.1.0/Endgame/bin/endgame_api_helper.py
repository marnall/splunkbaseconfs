import os
import sys
import json
import requests
import time
import splunklib.client as client
import urllib3
import splunk.clilib.cli_common
import certifi

splunk_home = os.getenv("SPLUNK_HOME")
# get current management port of instance
mgmnt_port = splunk.clilib.cli_common.getMgmtUri().split(":")[-1]
# Append PYTHONPATH so script will load corresponding library
sys.path.append(splunk_home + "/etc/apps/Endgame/bin/")
sys.path.append(splunk_home + "/etc/apps/Endgame/bin/apputils")

from logger import setup_logging as create_logger
from config_reader import ConfigReader

logger = create_logger("endgame_logger", "endgame.log")

cached_config = {}
cached_pas = {}
last_updated_time = time.time()
cache_expires_in = 300


class APIHelper(object):
    def __init__(self, session_token, username):
        self.session_token = session_token
        self.username = username

    def invoke_api(self, request_method, endpoint_name, data=None, param_value=None):
        """
        urllib3 request helper method for Endgame API.
        """
        result = None
        cached_config = self.getconfigdata()
        BASE_URL = cached_config["base_url"]
        if BASE_URL.endswith("/"):
            BASE_URL = BASE_URL[:-1]
        API_URL = endpoint_name
        URL = BASE_URL + API_URL
        endpoint_response = None
        token = self.get_token()
        api_headers = {
            "content-type": "application/json",
            "Authorization": "JWT {0}".format(token),
        }
        try:
            if cached_config["disable_ssl_validation"].lower() in ["true", "1", "yes"]:
                http = urllib3.PoolManager()
            else:
                http = urllib3.PoolManager(
                    cert_reqs="CERT_REQUIRED", ca_certs=certifi.where()
                )
            endpoint_response = http.request(request_method, URL, headers=api_headers, body=data)
            result = endpoint_response.data
        except Exception as exp:
            logger.error(str(exp))
            result = json.dumps({"msg": str(exp)})

        return json.loads(result)

    def last_updated_time_dif(self):
        """
        Finds the last time cached_config was updated.
        """
        global last_updated_time
        return int(time.time() - last_updated_time)

    def get_token(self):
        """
        Gets token for making authorized api calls.
        """
        pswd = ""
        usname = ""
        app_realm = ""

        try:
            f = open(splunk_home + "/etc/apps/Endgame/local/passwords.conf")
            app_realm = f.readlines()[-2].split(":")[1]
        except Exception as exp:
            logger.error(str(exp))
        headers = {"content-type": "application/json"}
        SPLUNK_SERVER = "localhost"
        SPLUNK_DEST_APP = "Endgame"
        splunk_service = client.connect(
            host=SPLUNK_SERVER,
            token=self.session_token,
            app=SPLUNK_DEST_APP,
            port=mgmnt_port,
        )
        storage_passwords = splunk_service.storage_passwords

        for credential in storage_passwords:
            # case insensitive match between realms
            if credential.realm.lower() == app_realm.lower():
                pswd = credential.content.get("clear_password")
                usname = credential.content.get("username")

        cached_config = self.getconfigdata()
        BASE_URL = cached_config["base_url"]
        if BASE_URL.endswith("/"):
            BASE_URL = BASE_URL[:-1]
        LOGIN_URL = BASE_URL + "/api/auth/login"
        payload = {"username": usname, "password": pswd}
        try:
            if cached_config["disable_ssl_validation"].lower() in ["true", "1", "yes"]:
                http = urllib3.PoolManager()
            else:
                http = urllib3.PoolManager(
                    cert_reqs="CERT_REQUIRED", ca_certs=certifi.where()
                )
            response = http.request(
                "POST", LOGIN_URL, body=json.dumps(payload), headers=headers
            )
            if response.status == 200:
                json_response = json.dumps(response.data)
                req_val = json.loads(json_response)
                token = json.loads(req_val.encode("utf-8"))["metadata"]["token"]
            else:
                json_response = json.dumps(response.data)
                req_val = json.loads(json_response)
                token = req_val
        except Exception as exp:
            logger.error(
                "Failed to retrieve authorization token due to exception: " + str(exp)
            )
            token = ""

        return token

    def getconfigdata(self):
        """
        Returns appsetup conf data. It is updated after every 300 seconds. 
        """
        global cached_config
        global last_updated_time
        global cache_expires_in

        time_diff = int(self.last_updated_time_dif())
        if len(cached_config) < 1 or time_diff > cache_expires_in:
            logger.info(
                "Updating cached config. Last updated {0} second(s) ago.".format(
                    time_diff
                )
            )
            if time_diff > cache_expires_in:
                last_updated_time = time.time()
            configreader = ConfigReader(self.session_token, self.username)
            cached_config = configreader.readConfFile("appsetup", "app_config")
        return cached_config

    def getNativeAppBaseURL(self):
        """
        Returns native base url from the conf.
        """
        cached_config = self.getconfigdata()
        BASE_URL = cached_config["native_base_url"]
        if BASE_URL.endswith("/"):
            BASE_URL = BASE_URL[:-1]

        return {"url": BASE_URL}
