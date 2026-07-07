#!/usr/bin/env python3
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
import math
import os
import sys
import time
import urllib
import types

import requests
import splunk.entity as entity
from splunk.clilib import cli_common as cli

from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option

APP_PASSWORD_NAME = 'setup_page_realm:license_key:'


@Configuration(requires_preop=True)
class ReportMetricsCommand(ReportingCommand):
    appHomePath = os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), os.pardir))

    # logging set up
    logger = logging.getLogger("ReportMetricsCommand")
    logger.setLevel(logging.INFO)
    logFilePath = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ReportMetricsCommand.log'))
    handler = logging.FileHandler(logFilePath)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    projectName = Option(require=True)
    systemName = Option(require=False)
    instanceType = Option(require=False)
    insightAgentType = Option(require=False)
    serverUrl = Option(require=True)
    chunkSize = Option(require=False)
    sendRaw = Option(require=False)
    timeout = Option(require=False)
    samplingInterval = Option(require=False)

    # 2 Optional settings, which are only used when sending metrics
    # The nth value in each (semi-colon delimited) map to each other.
    # in the below example, valCol1 represents the column which maps to nameCol1 and nameCol2,
    #   whereas valCol2 maps to nameCol3 and nameCol4.
    # If a given row has valCol1=99 and nameCol1="countA", then countA[instance]=99 will be reported.
    # Otherwise, the column name is the metric name
    # valCol1;valCol2
    metricValCols = Option(require=False)
    # nameCol1,nameCol2;nameCol3,nameCol4
    metricNameCols = Option(require=False)

    mode = Option(require=True)  # LogStreaming, LogReplay, MetricReplay, MetricStreaming
    fileID = str(time.time())

    # access the credentials in /servicesNS/nobody/insightfinderapp/storage/passwords
    def getCredentials(self, session_key):
        username = ""
        license_key = ""
        try:
            config = cli.getConfStanza('appsetup', 'app_config')
            username = config.get('username')
        except Exception as e:
            raise Exception("please check app_config for correct configs")
        self.logger.debug("username: " + username)

        if username:
            myapp = 'insightfinderapp'
            try:
                entities = entity.getEntities(['admin', 'passwords'], namespace=myapp, owner='nobody',
                                              sessionKey=session_key)
                for i, c in entities.items():
                    if i == APP_PASSWORD_NAME:
                        license_key = c['clear_password']
            except Exception as e:
                raise Exception("Could not get %s credentials from splunk. Error: %s" % (myapp, str(e)))

        return username, license_key

    def getConfigValues(self):
        self.logger.debug("getConfigValues() - Loading Configuration Settings")
        self.logger.debug("python running enviroment: " + str(sys.version_info[0]))
        # read session key sent from splunkd
        session_key = self._metadata.searchinfo.session_key
        if session_key is None or len(session_key) == 0:
            self.logger.error("Did not receive a session key from splunkd.")
            sys.stderr.write("Did not receive a session key from splunkd. " +
                             "Please enable passAuth in inputs.conf for this " +
                             "script\n")
            exit(2)

        # now get insightfinder credentials - might exit if no creds are available
        ReportMetricsCommand.userName = None
        ReportMetricsCommand.licenseKey = None

        try:
            userName, licenseKey = self.getCredentials(session_key)
            ReportMetricsCommand.userName = userName
            ReportMetricsCommand.licenseKey = licenseKey
        except Exception:
            self.logger.warning("cannot get credentials from config, ignored")

        if not ReportMetricsCommand.userName or not ReportMetricsCommand.licenseKey:
            self.logger.debug("userName or licenseKey is not set")
            sys.stderr.write("The userName or licenseKey is empty. Please set it in the setting.")
            exit(2)

        # InsightFinder App data receiving url
        ReportMetricsCommand.serverUrl = str(self.serverUrl)

        if not self.timeout:
            ReportMetricsCommand.timeout = 10
        else:
            ReportMetricsCommand.timeout = int(self.timeout)

        if not self.samplingInterval:
            data_type = ReportMetricsCommand.determineTypeOfData(self.mode)
            ReportMetricsCommand.samplingInterval = 10 * 60 if data_type == 'log' else 5 * 60
        else:
            ReportMetricsCommand.samplingInterval = int(self.samplingInterval)

        if self.chunkSize is None:
            ReportMetricsCommand.chunkSize = 200
        else:
            ReportMetricsCommand.chunkSize = int(self.chunkSize)

        if self.sendRaw is None:
            ReportMetricsCommand.sendRaw = False
        else:
            ReportMetricsCommand.sendRaw = True

        ReportMetricsCommand.projectName = str(self.projectName)
        ReportMetricsCommand.systemName = str(self.systemName)
        ReportMetricsCommand.instanceType = str(self.instanceType)
        ReportMetricsCommand.insightAgentType = str(self.insightAgentType)
        ReportMetricsCommand.mode = str(self.mode)
        ReportMetricsCommand.metricValCols = self.metricValCols
        ReportMetricsCommand.metricNameCols = self.metricNameCols

    @Configuration(local=True)
    def map(self, records):

        self.getConfigValues()
        data_type = ReportMetricsCommand.determineTypeOfData(ReportMetricsCommand.mode)

        result = []
        records_list = list(records)  # Convert generator type into list
        self.logger.info('start processing %s %s records in map()' % (len(records_list), data_type))

        if len(records_list) > 0:
            if data_type == 'log':
                result = ReportMetricsCommand.extractLogData(records_list)
            else:
                result = records_list

        server_url = str(self.serverUrl) + '/api/v1/customprojectrawdata'
        is_valid_server_url = ReportMetricsCommand.urlIsValid(server_url)
        self.logger.info("verified server url: %s" % server_url)

        status = 'error'
        error = ''
        if not is_valid_server_url:
            self.logger.error("invalid command parameter: serverUrl")
            error = "invalid command parameter: serverUrl"
        else:
            is_valid_credentials = ReportMetricsCommand.verifyAccountDetails()
            if not is_valid_credentials:
                self.logger.error("incorrect credentials parameters: userName, licenseKey")
                error = "incorrect credentials parameters: userName, licenseKey"
            else:
                is_project_exist, err = ReportMetricsCommand.verifyProjectAndCreate()
                if not is_project_exist:
                    self.logger.error("project not exists or failed to create")
                    error = err
                else:
                    self.logger.info("begin sending data to %s" % server_url)
                    if data_type == 'log':
                        st = ReportMetricsCommand.analyzeLogData(result)
                    else:
                        st = ReportMetricsCommand.analyzeMetricData(result)

                    if st:
                        status = "success"
                        self.logger.info('finish sending data, records: %s/%s.' % (len(records_list), len(result)))
                    else:
                        self.logger.info('failed to sending data, records: %s/%s.' % (len(records_list), len(result)))
                        error = "sending data failed"

        yield {"count": len(result), "dataType": data_type, "status": status, "error": error}

    @Configuration(local=True)
    def reduce(self, records):
        if isinstance(records, dict):
            yield records
        elif isinstance(records, list):
            yield records
        elif isinstance(records, types.GeneratorType):
            for r in records:
                yield r
        else:
            yield {"status": "done"}

    @staticmethod
    def determineTypeOfData(_mode):
        ReportMetricsCommand.logger.info("Begin - determineTypeOfData()")
        if _mode == "MetricReplay" or _mode == "MetricStreaming":
            ReportMetricsCommand.logger.info("type is csv")
            return 'csv'
        elif _mode == "LogStreaming" or _mode == "LogReplay":
            ReportMetricsCommand.logger.info("type is log")
            return 'log'
        else:
            return ''

    @staticmethod
    def determineTypeOfData(_mode):
        if _mode == "MetricReplay" or _mode == "MetricStreaming":
            ReportMetricsCommand.logger.info("type is csv")
            return 'csv'
        elif _mode == "LogStreaming" or _mode == "LogReplay":
            ReportMetricsCommand.logger.info("type is log")
            return 'log'
        else:
            return ''

    @staticmethod
    def validateTimestamp(timestamp):
        timestamp_str = str(timestamp)

        # if timestamp is in milliseconds
        if len(timestamp_str) == 13:
            return int(timestamp_str)
        else:
            len_diff = 13 - len(timestamp_str)
            # if timestamp digit is less than 13, add 0s to the end
            if len_diff > 0:
                return int(timestamp_str + '0' * len_diff)
            # if timestamp digit is more than 13, trim the extra digits
            else:
                return int(timestamp_str[:13])


    # Funtion to check if a url is valid
    @staticmethod
    def urlIsValid(path):
        ReportMetricsCommand.logger.debug("Begin - urlIsValid()")
        result = None
        # require https
        if not path.startswith("https://"):
            ReportMetricsCommand.logger.error("Expect https but got: " + str(path))
            return False
        try:
            result = requests.head(path, timeout=10)
        except Exception as e:
            ReportMetricsCommand.logger.error(e)
            pass

        return result and (result.status_code == requests.codes.ok)

    @staticmethod
    def verifyAccountDetails():
        ReportMetricsCommand.logger.debug("Begin() - verifyAccountDetails()")
        alldata = {}
        alldata["userName"] = ReportMetricsCommand.userName
        alldata["operation"] = "verify"
        alldata["licenseKey"] = ReportMetricsCommand.licenseKey
        alldata["projectName"] = ReportMetricsCommand.projectName
        json_data = json.dumps(alldata)
        url = ReportMetricsCommand.serverUrl + "/api/v1/agentdatahelper"

        try:
            response = requests.post(
                url, data=json.loads(json_data), timeout=ReportMetricsCommand.timeout)
        except Exception as e:
            ReportMetricsCommand.logger.error("Got exception during API call: " + url)
            ReportMetricsCommand.logger.error(e)
            return False

        if response.status_code != 200:
            ReportMetricsCommand.logger.error("Expect 200 code, but got " + response.status_code)
            return False
        try:
            isValid = response.json()["success"]
        except ValueError as e:
            ReportMetricsCommand.logger.error("Got value error when parsing the response: " + response.text)
            return False
        if isValid:
            ReportMetricsCommand.logger.info("Account details verification succeed.")
        return isValid

    @staticmethod
    def verifyProjectAndCreate():
        ReportMetricsCommand.logger.debug("Begin() - verifyProjectAndCreate()")
        user_name = ReportMetricsCommand.userName
        license_key = ReportMetricsCommand.licenseKey
        project_name = ReportMetricsCommand.projectName

        params = {
            'operation': 'check',
            'userName': user_name,
            'licenseKey': license_key,
            'projectName': project_name,
        }
        url = urllib.parse.urljoin(ReportMetricsCommand.serverUrl, 'api/v1/check-and-add-custom-project')

        try:
            response = requests.post(url, data=params, timeout=ReportMetricsCommand.timeout)
        except Exception as e:
            ReportMetricsCommand.logger.error("Got exception check project: " + url)
            ReportMetricsCommand.logger.error(e)
            return False, str(e)

        is_project_exist = False
        try:
            result = response.json()
            if result['success'] is False or result['isProjectExist'] is False:
                ReportMetricsCommand.logger.error('Project not exist: ' + project_name)
            else:
                is_project_exist = True
                ReportMetricsCommand.logger.info('Check project success: ' + project_name)
        except ValueError as e:
            ReportMetricsCommand.logger.error("Got value error when parsing the response:" + response.text)
            return False, response.text

        if is_project_exist:
            return True, None

        create_project_success = False
        ReportMetricsCommand.logger.info('Starting add project: {}'.format(project_name))

        params = {
            'operation': 'create',
            'userName': user_name,
            'licenseKey': license_key,
            'projectName': project_name,
            'instanceType': 'Splunk',
            'projectCloudType': 'PrivateCloud',
            'dataType': 'Log' if ReportMetricsCommand.determineTypeOfData(
                ReportMetricsCommand.mode) == 'log' else 'Metric',
            'insightAgentType': 'Custom',
            'samplingInterval': ReportMetricsCommand.samplingInterval,
            'samplingIntervalInSeconds': ReportMetricsCommand.samplingInterval,
        }
        if ReportMetricsCommand.systemName:
            params['systemName'] = ReportMetricsCommand.systemName

        if ReportMetricsCommand.instanceType:
            params['instanceType'] = ReportMetricsCommand.instanceType

        if ReportMetricsCommand.insightAgentType:
            params['insightAgentType'] = ReportMetricsCommand.insightAgentType

        url = urllib.parse.urljoin(ReportMetricsCommand.serverUrl, 'api/v1/check-and-add-custom-project')
        try:
            response = requests.post(url, data=params, timeout=ReportMetricsCommand.timeout)
        except Exception as e:
            ReportMetricsCommand.logger.error("Got exception create project: " + url)
            ReportMetricsCommand.logger.error(e)
            return False, str(e)

        try:
            result = response.json()
            if result['success'] is False:
                ReportMetricsCommand.logger.error('Add project error: {}\n{}'.format(project_name, result))
                return False, response.text
            else:
                create_project_success = True
                ReportMetricsCommand.logger.info('Add project success: {}'.format(project_name))
        except Exception as e:
            ReportMetricsCommand.logger.error("Got value error when parsing the response: " + response.text)
            ReportMetricsCommand.logger.error(e)
            return False, response.text

        return create_project_success, None

    ###################################################
    ### FUNCTIONS SPECIFIC TO METRICREPLAY - START ####
    ###################################################

    @staticmethod
    def updateNumberOfRowsPerPacketMetric(metricDataArray):
        ReportMetricsCommand.logger.debug(
            "Begin updateNumberOfRowsPerPacket()")
        chunkSize = ReportMetricsCommand.chunkSize
        additionalPacketSize = 5000
        biggestRawData = max(metricDataArray, key=lambda x: len(json.dumps(x)))
        # Adding a padding of 100 bytes per metric object
        sizeSingleDataObject = len(json.dumps(biggestRawData)) + 100
        allowedPacketSize = chunkSize * 1000
        numberOfRowsPerPacket = int(int(allowedPacketSize - additionalPacketSize) / int(sizeSingleDataObject))
        return numberOfRowsPerPacket

    @staticmethod
    def has_valid_name_val_options():
        return ReportMetricsCommand.metricValCols is not None and ReportMetricsCommand.metricNameCols is not None and len(
            ReportMetricsCommand.metricValCols) > 0 and len(ReportMetricsCommand.metricNameCols) > 0

    @staticmethod
    def analyzeMetricData(stringListCompleteData):
        ReportMetricsCommand.logger.info("Begin - analyzeMetricData() " + str(len(stringListCompleteData)))
        json_data_list = []
        for record in stringListCompleteData:
            if isinstance(record, str):
                recordDict = json.loads(record)
            else:
                recordDict = record

            if '_time' in recordDict.keys():
                json_data_list.append(recordDict)
        # Check if we have any data or not
        if json_data_list:
            # sorting list by timestamp
            json_data_list = sorted(
                json_data_list, key=lambda record: record['_time'])
            numberOfRowsPerPacket = ReportMetricsCommand.updateNumberOfRowsPerPacketMetric(
                json_data_list)
            totalNumberOfChunks = int(math.ceil(float(len(json_data_list)) / float(numberOfRowsPerPacket)))
            # Convert EventId which is timestamp(integer) into string
            # initialize what we need later
            converted_data = []
            metric_val_cols = []
            metric_name_cols_list = []
            hosts_metrics = dict()
            # check name-val column options
            if ReportMetricsCommand.has_valid_name_val_options():
                metric_val_cols = ReportMetricsCommand.metricValCols.strip().split(';')
                metric_name_cols_list = ReportMetricsCommand.metricNameCols.strip().split(';')[:len(metric_val_cols)]
                metric_name_cols_flat = ReportMetricsCommand.metricNameCols.replace(',', ';').strip().split(';')[
                                        :len(metric_val_cols)]
                for i in range(len(metric_name_cols_list)):
                    metric_name_cols_list[i] = metric_name_cols_list[i].strip().split(',')
                # gather all hosts and metrics
                hosts_set = set()
                metrics_set = set()
                for record in json_data_list:
                    if 'host' in record.keys():
                        hosts_set.add(record['host'])
                    for metric_name in record.keys():
                        if metric_name in ['timestamp', '_time', 'host', 'resultData',
                                           'dataType'] or metric_name in metric_val_cols:
                            pass
                        elif metric_name in metric_name_cols_flat:
                            metrics_set.add(record[metric_name])
                        else:
                            metrics_set.add(metric_name)
                # map all metrics to all hosts
                for host in hosts_set:
                    hosts_metrics[host] = metrics_set.copy()

            # process each record and add to a data dict
            for record in json_data_list:
                record['timestamp'] = str(int(float(record['_time']) * 1000))
                host_name = 'default'
                if 'host' in record.keys():
                    host_name = record['host']
                record.pop('_time', None)
                record.pop('host', None)
                temp_data = {}
                temp_data['timestamp'] = record['timestamp']

                # handle separate name-val columns
                for i in range(len(metric_val_cols)):  # for each metric
                    metric_val_col = metric_val_cols[i]
                    metric_name_cols = metric_name_cols_list[i]
                    if metric_val_col in record.keys():  # if the metric is in the row
                        metric_val = record.pop(metric_val_col)
                        for metric_name_col in metric_name_cols:  # check each metric's name cols
                            if metric_name_col in record.keys():
                                metric_name = record.pop(metric_name_col)
                                if metric_name not in record.keys():  # for the first encountered name
                                    record[
                                        metric_name] = metric_val  # add the name-val to the record for later processing

                # name-val columns should all be popped and added back properly
                hosts_metrics_copy = hosts_metrics.copy()
                for metric_name in record.keys():
                    if metric_name in ['timestamp', '_time', 'host', 'resultData',
                                       'dataType'] or metric_name in metric_val_cols:
                        pass
                    else:
                        metric_val = record[metric_name]
                        new_metric_name = metric_name + '[' + host_name + ']'
                        temp_data[new_metric_name] = metric_val
                        # if this host hasn't been completed
                        if host_name in hosts_metrics_copy:
                            # if this metric hasn't been visited for this host, remove it
                            if metric_name in hosts_metrics_copy[host_name]:
                                hosts_metrics_copy[host_name].remove(metric_name)
                                # if this makes the list empty, remove the host
                                if len(hosts_metrics_copy[host_name]) == 0:
                                    hosts_metrics_copy.pop(host_name)

                # for each leftover metric per host
                for host_fill in hosts_metrics_copy:
                    for metric_fill in hosts_metrics_copy[host_fill]:
                        # set the value to zero
                        metric_key_fill = metric_fill + '[' + host_fill + ']'
                        temp_data[metric_key_fill] = '0'

                converted_data.append(temp_data)
            json_data_list = converted_data
            min_timestamp = json_data_list[0]["timestamp"]
            max_timestamp = json_data_list[len(json_data_list) - 1]["timestamp"]
            current_chunk_number = 0
            rows_per_chunk_counter = 0
            total_row_counter = 0
            data_list = []

            while total_row_counter < len(json_data_list):
                data_list.append(json_data_list[total_row_counter])
                total_row_counter += 1
                rows_per_chunk_counter += 1
                # Condition to send data satisfied
                if rows_per_chunk_counter == numberOfRowsPerPacket or total_row_counter == len(json_data_list):
                    current_chunk_number += 1
                    ReportMetricsCommand.sendMetricData(data_list, current_chunk_number,
                                                        totalNumberOfChunks, min_timestamp, max_timestamp)
                    rows_per_chunk_counter = 0
                    data_list = []
            return True
        else:
            ReportMetricsCommand.logger.info(
                "analyzeMetricData() - No Data to Report")
            return True

    @staticmethod
    def sendMetricData(metricDataList, currentChunkNumber, totalNumberOfChunks, minTimestamp, maxTimestamp):
        ReportMetricsCommand.logger.debug("Begin - sendMetricData() sending :: " + str(len(
            metricDataList)) + " rows :: Chunkinfo " + str(currentChunkNumber) + "/" + str(totalNumberOfChunks))
        licenseKey = ReportMetricsCommand.licenseKey
        url = ReportMetricsCommand.serverUrl + '/api/v1/customprojectrawdata'
        ifProject = ReportMetricsCommand.projectName
        userName = ReportMetricsCommand.userName
        alldata = {}
        alldata["projectName"] = ifProject
        alldata["metricData"] = json.dumps(metricDataList)
        alldata["instanceName"] = "localhost"
        alldata["licenseKey"] = licenseKey
        alldata["maxTimestamp"] = str(maxTimestamp)
        alldata["minTimestamp"] = str(minTimestamp)
        alldata["chunkSerialNumber"] = str(currentChunkNumber)
        alldata["chunkTotalNumber"] = str(totalNumberOfChunks)
        alldata["agentType"] = 'MetricFileReplay'
        if "MetricStreaming" == ReportMetricsCommand.mode:
            alldata["agentType"] = None
        alldata["userName"] = userName
        alldata["fileID"] = ReportMetricsCommand.fileID  # need to name a file id, maybe single file
        response = requests.post(url, data=alldata, timeout=ReportMetricsCommand.timeout)
        if int(response.status_code) >= 200 and int(response.status_code) < 300:
            pass
        else:
            ReportMetricsCommand.logger.info("Fail")

    ###################################################
    ##### FUNCTIONS SPECIFIC TO LOGREPLAY - START #####
    ###################################################

    @staticmethod
    def extractLogData(recordsList):
        ReportMetricsCommand.logger.debug("Begin - extractLogData()")
        result = []
        for record in recordsList:
            current_result = {}
            current_result["tag"] = 'insightfinder-log'
            try:
                current_result["tag"] = record['host']
            except Exception as e:
                pass
            if "_time" not in record.keys():
                continue
            timestamp = int(record["_time"].replace(".", ""))
            timestamp = ReportMetricsCommand.validateTimestamp(timestamp)
            current_result["eventId"] = timestamp
            if ReportMetricsCommand.sendRaw:
                current_result["data"] = record["_raw"]
            else:
                current_result["data"] = record["event_message"]
            result.append(current_result)
        return result

    @staticmethod
    def analyzeLogData(stringListCompleteData):
        ReportMetricsCommand.logger.info("analyzing %s log records" % len(stringListCompleteData))

        json_data_list = []
        for record in stringListCompleteData:
            if isinstance(record, str):
                json_data_list.append(json.loads(record))
            else:
                json_data_list.append(record)

        # Check if we have any data or not
        if json_data_list:
            # sorting list by timestamp
            json_data_list = sorted(
                json_data_list, key=lambda record: record['eventId'])
            numberOfRowsPerPacket = ReportMetricsCommand.updateNumberOfRowsPerPacketLog(
                json_data_list)
            if numberOfRowsPerPacket == 0:
                ReportMetricsCommand.logger.info(
                    "analyzeLogData() - No Data to Report")
                return True
            totalNumberOfChunks = int(
                math.ceil(float(len(json_data_list)) / float(numberOfRowsPerPacket)))
            # Convert EventId which is timestamp(integer) into string
            for record in json_data_list:
                if "LogReplay" == ReportMetricsCommand.mode:
                    record['eventId'] = str(record['eventId'])
                else:
                    record['timestamp'] = str(record['eventId'])

            minTimestamp = json_data_list[0]["eventId"]
            maxTimestamp = json_data_list[len(json_data_list) - 1]["eventId"]
            currentChunkNumber = 0
            rowsPerChunkCounter = 0
            totalRowCounter = 0
            dataList = []
            while totalRowCounter < len(json_data_list):
                if len(json_data_list[totalRowCounter]['data']) > ReportMetricsCommand.chunkSize * 1000:
                    continue
                else:
                    dataList.append(json_data_list[totalRowCounter])
                totalRowCounter += 1
                rowsPerChunkCounter += 1
                # Condition to send data satisfied
                if rowsPerChunkCounter == numberOfRowsPerPacket or totalRowCounter == len(json_data_list):
                    currentChunkNumber += 1
                    ReportMetricsCommand.sendLogData(dataList, currentChunkNumber, totalNumberOfChunks, minTimestamp,
                                                     maxTimestamp)
                    rowsPerChunkCounter = 0
                    dataList = []
            return True
        else:
            ReportMetricsCommand.logger.info("analyzeLogData() - No Data to Report")
            return True

    @staticmethod
    def sendLogData(log_data_list, current_chunk_number, total_number_of_chunks, min_timestamp, max_timestamp):
        ReportMetricsCommand.logger.info("sending log data:: " + str(len(
            log_data_list)) + " rows :: Chunkinfo " + str(current_chunk_number) + "/" + str(total_number_of_chunks))

        licenseKey = ReportMetricsCommand.licenseKey
        url = ReportMetricsCommand.serverUrl + '/api/v1/customprojectrawdata'
        ifProject = ReportMetricsCommand.projectName
        userName = ReportMetricsCommand.userName
        alldata = {}
        alldata["projectName"] = ifProject
        alldata["metricData"] = json.dumps(log_data_list)
        alldata["instanceName"] = "localhost"
        alldata["licenseKey"] = licenseKey
        alldata["maxTimestamp"] = str(max_timestamp)
        alldata["minTimestamp"] = str(min_timestamp)
        alldata["chunkSerialNumber"] = str(current_chunk_number)
        alldata["chunkTotalNumber"] = str(total_number_of_chunks)
        if "LogReplay" == ReportMetricsCommand.mode:
            alldata["agentType"] = 'LogFileReplay'
        else:
            alldata["agentType"] = 'LogStreaming'
        alldata["userName"] = userName
        ReportMetricsCommand.logger.info("Send data to url %s with project %s" % (url, ifProject))
        response = requests.post(url, data=alldata, timeout=ReportMetricsCommand.timeout)
        if 200 <= int(response.status_code) < 300:
            ReportMetricsCommand.logger.info("finish sending log data")
        else:
            ReportMetricsCommand.logger.error("Failed Sending Data")

    @staticmethod
    def updateNumberOfRowsPerPacketLog(logDataArray):
        chunkSize = ReportMetricsCommand.chunkSize
        additionalPacketSize = 5000
        biggestRawData = 1000
        allowedPacketSize = chunkSize * 1000
        biggestRawData = max(logDataArray, key=lambda x: len(x['data']) if len(x['data']) <= allowedPacketSize else 0)[
            'data']
        # Size of largest packet
        sizeSingleDataObject = len(biggestRawData) + 500
        numberOfRowsPerPacket = int(int(allowedPacketSize - additionalPacketSize) / int(sizeSingleDataObject))
        ReportMetricsCommand.logger.info("Number Of Rows Per Packet : " + str(numberOfRowsPerPacket))
        return numberOfRowsPerPacket


dispatch(ReportMetricsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
