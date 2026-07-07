from __future__ import print_function
import splunk.admin as admin
import re
import ssl
import splunk
import json
import http.client
import time, datetime
import logging
from tripwire_logging import setup_logger
from io import open
from six.moves import urllib



def getManagementURL():
    return f"https://{splunk.getDefault('host')}:{splunk.getDefault('port')}"


class ConfigApp(admin.MConfigHandler):
    appName = "TA-tripwire_IP360"
    setup_logger()
    logger = logging.getLogger('tripwire_ip360')


    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in [
                "db_name",
                "historic_days",
                "start_time",
                "dbconnect_1",
                "dbconnect_2",
                "dbconnect_3",
                "informational_start",
                "low_lower",
                "low_upper",
                "medium_lower",
                "medium_upper",
                "high_lower",
                "high_upper",
                "critical_start",
                "start_time_url",
            ]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
   
        confDict = self.readConf("ip360_settings")
        if None != confDict:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if key in [
                        "db_name",
                        "historic_days",
                        "start_time",
                        "dbconnect_1",
                        "dbconnect_2",
                        "dbconnect_3",
                        "informational_start",
                        "low_lower",
                        "low_upper",
                        "medium_lower",
                        "medium_upper",
                        "high_lower",
                        "high_upper",
                        "critical_start",
                        "start_time_url",
                    ] and val in [None, ""]:
                        val = ""
                    confInfo[stanza].append(key, val)

    def request(self, settings, stanza, check=False):
        try:
            self.logger.info("starting request")
            session_key = self.getSessionKey()
            headers = {"Authorization": ("Splunk %s" % session_key), 'Content-Type': 'application/json'}
            query = settings["query"]
            json_data = {
                "name": stanza,
                "query": query,
                "interval": settings["interval"],
                "index": settings["index"],
                "mode": "rising",
                "connection": settings["connection"],
                "rising_column_index": settings["rising_column_index"],
                "timestamp_column_index": settings["timestamp_column_index"],
                "timestampType": "dbColumn",
                "sourcetype": settings["sourcetype"],
                "ui_query_catalog": "ice",
                "checkpoint": json.loads(settings["checkpoint"]),
                "queryTimeout": settings["queryTimeout"],
            }
            targetApp = "splunk_app_db_connect"
            endpoint = "/servicesNS/nobody/" + targetApp + "/db_connect/dbxproxy/inputs"

            _context = ssl.create_default_context()
            _context.check_hostname = check
            _context.verify_mode = check

            conn = http.client.HTTPSConnection(splunk.getDefault('host'), splunk.getDefault('port'), context=_context)
            conn.request("POST", endpoint, body=json.dumps(json_data), headers=headers)

            res = conn.getresponse()
            data = res.read()

            self.logger.warning("status code:" + str(res.status))
            #logger.info("request text: " + data.decode("utf-8"))

        except Exception as e:
            import traceback
            self.logger.error(str(e))

            self.logger.warning("generic exception: " + traceback.format_exc())

    def handleEdit(self, confInfo):
        # modify ip360_settings.conf
        # set the start time for indexing
        self.logger.info("Value: " + self.callerArgs.data["historic_days"][0])
        if re.search(r"\d+", self.callerArgs.data["historic_days"][0]) is not None:
            days = re.search(r"\d+", self.callerArgs.data["historic_days"][0]).group(0)
            self.logger.info("historic_days: " + days)
            start_time = int(days) * 24 * 60 * 60
            now = datetime.datetime.now()
            self.logger.info("datetime: " + str(now))
            diff = datetime.timedelta(
                days=int(days),
                hours=now.hour,
                minutes=now.minute,
                seconds=now.second,
                microseconds=now.microsecond,
            )
            self.logger.info("timedelta: " + str(diff))
            start_time = now - diff
            self.logger.info("Start Time: " + str(start_time))
            self.callerArgs.data["historic_days"][0] = str(days)
            self.callerArgs.data["start_time"][0] = str(start_time)
            # url encode the start time for dbx query
            start_time_url = str(start_time)
            start_time_url = re.sub(r"\s", "%20", str(start_time_url), 1)
            start_time_url = re.sub(r":", "%3A", str(start_time_url), 2)
            self.callerArgs.data["start_time_url"][0] = str(start_time_url)
            self.logger.info("URL Encoded Start Time: " + str(start_time_url) )

        else:
            self.callerArgs.data.pop("historic_days")
            self.logger.info("No number found in historic_days")
        # drop any variables without data
        for key in self.callerArgs:
            if self.callerArgs.data[key][0] in [None, ""]:
                self.callerArgs.data.pop(key)
        # Write settings to file
        self.writeConf("ip360_settings", "settings", self.callerArgs.data)
        confInput = self.readConf("ip360_settings")
        for stanza, settings in list(confInput.items()):
            # Set Custom Severity Buckets
            if stanza == "ip360_distinct_audit":
                self.logger.info(str(list(settings.keys())))
                self.logger.info("replace strings")
                if "EVAL-severity" in settings:
                    self.logger.info("replace Informational Range")
                    settings["EVAL-severity"] = settings["EVAL-severity"].replace(
                        "INFO_REPLACE", self.callerArgs.data["informational_start"][0]
                    )
                    self.logger.info("replace Low Range")
                    settings["EVAL-severity"] = settings["EVAL-severity"].replace(
                        "LOW_REPLACE", self.callerArgs.data["low_upper"][0]
                    )
                    self.logger.info("replace Medium Range")
                    settings["EVAL-severity"] = settings["EVAL-severity"].replace(
                        "MEDIUM_REPLACE", self.callerArgs.data["medium_upper"][0]
                    )
                    self.logger.info("replace High Range")
                    settings["EVAL-severity"] = settings["EVAL-severity"].replace(
                        "HIGH_REPLACE", self.callerArgs.data["high_upper"][0]
                    )
                session_key = self.getSessionKey()
                headers = {"Authorization": ("Splunk %s" % session_key)}
                base_url = getManagementURL()
                try:
                    endpoint = (
                            "/servicesNS/nobody/" + self.appName + "/configs/conf-props/"
                    )
                    settings["name"] = stanza
                    self.logger.info("endpoint: " + endpoint)
                    self.logger.info("requesting")
                    r = urllib.request.Request(
                        base_url + endpoint,
                        data=urllib.parse.urlencode(settings).encode('utf-8'),
                        headers=headers,
                        )
                    self.logger.info("request made")
                    results = urllib.request.urlopen(r)
                    self.logger.info("results recieved")
                except:
                    self.logger.info("Stanza " + stanza + " already exists")
                    settings.pop("name")
                    endpoint = (
                            "/servicesNS/nobody/"
                            + self.appName
                            + "/configs/conf-props/"
                            + stanza
                    )
                    self.logger.info("endpoint: " + endpoint + "")
                    self.logger.info("requesting")
                    r = urllib.request.Request(
                        base_url + endpoint,
                        data=urllib.parse.urlencode(settings).encode('utf-8'),
                        headers=headers,
                        )
                    self.logger.info("request made")
                    results = urllib.request.urlopen(r)
                    self.logger.info("results recieved")

        self.logger.info("DBCONNECT VERSION: 3.X Selected ")

        # modify settings from custom configuration file
        confInput = self.readConf("ip360_settings")
        for stanza, settings in list(confInput.items()):
            self.logger.info("Original stanza: " + stanza)
            if stanza == "mi_input://ip360_distinct_audit_dbx3":
                name = "ip360_distinct_audit_dbx3"
                settings["connection"] = settings["connection"].replace(
                    "DATABASE_NAME_DBX3", self.callerArgs.data["db_name"][0]
                )
                self.logger.info("New stanza: " + stanza )
                # modify historical time stamp in query
                if "query" in settings:
                    self.logger.info("found timestamp to replace")
                    self.logger.info("Start Time: " + str(start_time) )
                    settings["query"] = settings["query"].replace(
                        "REPLACED_TIMESTAMP_DBX3", str(start_time)
                    )
                # write settings to specified file
                self.request(settings, name)
            # Add the second dbx3 query
            elif stanza == "mi_input://ip360_scan_status_dbx3":
                settings["connection"] = settings["connection"].replace(
                    "DATABASE_NAME_DBX3", self.callerArgs.data["db_name"][0]
                )
                self.logger.info("New stanza: " + stanza )
                # modify historical time stamp in query
                if "query" in settings:
                    self.logger.info("found timestamp to replace")
                    self.logger.info("Start Time: " + str(start_time) )
                    settings["query"] = settings["query"].replace(
                        "REPLACED_TIMESTAMP_DBX3", str(start_time)
                    )
                # write settings to specified file
                self.logger.info("starting writing")
                name = "ip360_scan_status_dbx3"
                self.request(settings, name)
            elif stanza == "ip360_scan_status_dbx3":
                self.logger.info(str(list(settings.keys())) )
                self.logger.info("replace strings")
                if "search" in settings:
                    self.logger.info("replace DB")
                    settings["search"] = settings["search"].replace(
                        "DATABASE_NAME_DBX3", self.callerArgs.data["db_name"][0]
                    )
                    self.logger.info("replace timestamp with URL encoded timestamp")
                    settings["search"] = settings["search"].replace(
                        "REPLACED_TIMESTAMP_DBX3",
                        self.callerArgs.data["start_time_url"][0],
                    )
                session_key = self.getSessionKey()
                headers = {"Authorization": ("Splunk %s" % session_key)}
                base_url = getManagementURL()
                try:
                    endpoint = (
                            "/servicesNS/nobody/"
                            + self.appName
                            + "/configs/conf-savedsearches/"
                    )
                    settings["name"] = stanza
                    self.logger.info("endpoint: " + endpoint )
                    self.logger.info("requesting")
                    r = urllib.request.Request(
                        base_url + endpoint,
                        data=urllib.parse.urlencode(settings).encode('utf-8'),
                        headers=headers,
                        )
                    self.logger.info("request made")
                    results = urllib.request.urlopen(r)
                    self.logger.info("results recieved")
                except:
                    self.logger.info("Stanza " + stanza + " already exists")
                    settings.pop("name")
                    endpoint = (
                            "/servicesNS/nobody/"
                            + self.appName
                            + "/configs/conf-savedsearches/"
                            + stanza
                    )
                    self.logger.info("endpoint: " + endpoint)
                    self.logger.info("requesting")
                    r = urllib.request.Request(
                        base_url + endpoint,
                        data=urllib.parse.urlencode(settings).encode('utf-8'),
                        headers=headers,
                        )
                    self.logger.info("request made")
                    results = urllib.request.urlopen(r)
                    self.logger.info("results recieved")
            else:
                self.logger.info("skip stanza" + stanza)


admin.init(ConfigApp, admin.CONTEXT_NONE)