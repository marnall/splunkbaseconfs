from __future__ import print_function

import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *

import logging, logging.handlers

import splunklib.client as client
import six.moves.urllib.request, six.moves.urllib.error, six.moves.urllib.parse
from six.moves import urllib

import splunk
import base64
import json
import time
import splunk.Intersplunk
import splunk.auth
import splunk.search
import cherrypy
import splunk.entity
import requests

import xml.sax.saxutils

class MyScript(Script):

    # Define some global variables
    MASK           = 'xxxxxx'
    APP            = __file__.split(os.sep)[-3]
    LOGGER = None

    def __init__(self):
        self.LOGGER = self.setup_logger()

    def setup_logger(self):
        # Setup a logger for the REST handler.

        logger = logging.getLogger('splunk.appserver.%s.redsealModularInput' % self.APP)

        SPLUNK_HOME = os.environ['SPLUNK_HOME']
        LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
        LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
        LOGGING_STANZA_NAME = 'python'
        LOGGING_FILE_NAME = "redsealModInput.log"
        BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
        LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
        splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=20000000, backupCount=5 )
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        logger.addHandler(splunk_log_handler)
        splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

        return logger


    def get_scheme(self):

        scheme = Scheme("RedSeal")
        scheme.description = ("Get data from a RedSeal server via REST API.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        redsealServer_arg = Argument(
            name="redsealServer",
            title="RedSeal Server FQDN or IP Address",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(redsealServer_arg)

        port_arg = Argument(
            name="port",
            title="RedSeal Server Port Number",
            data_type=Argument.data_type_number,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(port_arg)

        username_arg = Argument(
            name="username",
            title="RedSeal Username",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(username_arg)

        password_arg = Argument(
            name="password",
            title="RedSeal password",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(password_arg)

        proxy_server_https_arg = Argument(
            name="proxy_server_https",
            title="Use https to connect to Proxy Server",
            data_type=Argument.data_type_boolean,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(proxy_server_https_arg)

        proxy_server_arg = Argument(
            name="proxy_server",
            title="Proxy Server FQDN or IP Address",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_server_arg)

        proxy_port_arg = Argument(
            name="proxy_port",
            title="Proxy Server Port Number",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_port_arg)

        proxy_username_arg = Argument(
            name="proxy_username",
            title="Proxy Username",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_username_arg)

        proxy_password_arg = Argument(
            name="proxy_password",
            title="Proxy password",
            data_type=Argument.data_type_string,
            required_on_create=False,
            required_on_edit=False
        )
        scheme.add_argument(proxy_password_arg)

        return scheme

    def validate_input(self, definition):
        inputName = definition.metadata["name"]
        session_key = definition.metadata["session_key"]
        username    = definition.parameters["username"]
        redsealServer = definition.parameters["redsealServer"]
        port        = definition.parameters["port"]
        password = definition.parameters["password"]

        # if the password is masked then get the unencrypted password.
        # if (password == self.MASK):
        # 	self.LOGGER.info("validate_input | **** ONLY FOR TESTING **** password is masked")
        # 	args = {'token':session_key}
        # 	session = client.connect(**args)
        # 	password = self.get_password(session_key, username, redsealServer, session.storage_passwords)

        try:
            self.LOGGER.info("validate_input | inputName:%s" % inputName)
            self.LOGGER.info("validate_input | username:%s" % username)
            self.LOGGER.info("validate_input | redsealServer:%s" % redsealServer)
            self.LOGGER.info("validate_input | port:%s" %port)

            # ToDo: Only for Testing displays password
            # self.LOGGER.info("validate_input | **** ONLY FOR TESTING **** password:%s" %password)

            portNum = int(port)
        except ValueError as ve:
            raise ValueError("Port number must be an integer: %s" % str(ve.args[0]))

        # if (self.loginCheck(redsealServer,port,username,password) == False):
        #     raise ValueError("Unable to connect to RedSeal server.")

        self.LOGGER.info("validate_input | END of validate_input")

    # def validDataInputCheck(self, session_key, redsealServer, inputName):
    #     result = False
    #     args = {'token':session_key}
    #
    #     try:
    #         # # Get the collection of data inputs
    #         self.LOGGER.info('validDataInputCheck | Before setting SERVICE')
    #         service = client.connect(**args)
    #
    #         self.LOGGER.info('validDataInputCheck | Before service inputs ')
    #
    #         inputs = service.inputs.list('redsealModInput')
    #
    #         self.LOGGER.info('validDataInputCheck | Before inputs length setting %s' % str(inputs.__len__()))
    #
    #         if (inputs != None) and (inputs.__len__()>0):
    #             # Check if updating existing data input
    #             servername = str((inputs[0].__getattribute__('content')).get('redsealServer'))
    #             self.LOGGER.info('validDataInputCheck | serverName:%s' % servername)
    #             self.LOGGER.info('validDataInputCheck | item.name:%s' % inputs[0].name)
    #             self.LOGGER.info('validDataInputCheck | redsealServer:%s' % redsealServer)
    #             self.LOGGER.info('validDataInputCheck | inputName:%s' % inputName)
    #             if (redsealServer == servername and inputName == str(inputs[0].name)):
    #                 result = True
    #     except Exception as e:
    #         self.LOGGER.error("validDataInputCheck | ERROR, Error validDataInputCheck: %s" % str(e))
    #     return result

    def encrypt_password(self, username, password, session_key, realm_value, password_store):
        args = {'token':session_key}
        service = client.connect(**args)

        self.LOGGER.info('encrypt_password | START encrypt_password')
        self.LOGGER.info('encrypt_password | username:%s' % username)
        # ToDo: Only used for testing
        # self.LOGGER.info('password:%s' % password)

        self.LOGGER.info('encrypt_password | realm_value:%s' % realm_value)

        try:
            # If the credential already exists, delete it.
            # for storage_password in service.storage_passwords:
            for storage_password in password_store:
                if (storage_password.username == username and storage_password.realm == realm_value):
                    self.LOGGER.info('encrypt_password | delete stored password:%s' % realm_value)
                    service.storage_passwords.delete(username=storage_password.username, realm=realm_value)
                    break

            # Create the credential and store in passwords.conf file.
            self.LOGGER.info('encrypt_password | Before call to encrypt password')
            service.storage_passwords.create(password, username, realm=realm_value)

        except Exception as e:
            self.LOGGER.error("encrypt_password | An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))


    def mask_password(self, session_key, username, port, redsealServer, proxy_server_https, proxy_server,
                        proxy_port, proxy_username):
        try:
            args = {'token':session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            self.LOGGER.info("mask_password | kind: %s, input_name %s" % (kind, input_name))
            item = service.inputs.__getitem__((input_name, kind))

            self.LOGGER.info("mask_password | proxy username: %s", print (proxy_username))
            proxy_password = self.MASK

            # Set empty string for the proxy values if None or the item.update
            # command will fail if value of None is passed.
            if (proxy_server_https is None):
                proxy_server_https = 0
                self.LOGGER.info("mask_password | set default proxy server https")
            if (proxy_username is None):
                proxy_username = str()
                self.LOGGER.info("mask_password | set default proxy username")
                # clear the masked characters since no password is required.
                proxy_password = str()
            if (proxy_server is None):
                proxy_server = str()
                self.LOGGER.info("mask_password | set default proxy server")
            if (proxy_port is None):
                proxy_port = str()
                self.LOGGER.info("mask_password | set default proxy port")

            # arguments need to match the what are defined in inputs.conf.spec
            kwargs = {
                "redsealServer": redsealServer,
                "port": port,
                "username": username,
                "password": self.MASK,
                "proxy_server_https" : proxy_server_https,
                "proxy_server" : proxy_server,
                "proxy_port" : proxy_port,
                "proxy_username" : proxy_username,
                "proxy_password" : proxy_password
            }

            self.LOGGER.info("mask_password | Before call to item.update to update with mask_password")

            item.update(**kwargs)
            # item.update(**kwargs).refresh()

            self.LOGGER.info("mask_password | After call to item.update to update with mask_password")

        except Exception as e:
            self.LOGGER.error("mask_password | Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, username, realm_value, password_store):
        args = {'token':session_key}
        service = client.connect(**args)

        self.LOGGER.info("get_password | Before password storage object loop")

        try:
            # for storage_password in service.storage_passwords:
            for storage_password in password_store:
                # self.LOGGER.info("get_password | **** ONLY FOR TESTING **** password username: %s" % storage_password.username)
                # self.LOGGER.info("get_password | **** ONLY FOR TESTING **** password clear password: %s" % storage_password.content.clear_password)
                # self.LOGGER.info("get_password | **** ONLY FOR TESTING **** password realm: %s" % storage_password.realm)
                if (storage_password.username == username and storage_password.realm == realm_value):
                    return storage_password.content.clear_password

            # No password found return None
            return None
        except Exception as e:
            self.LOGGER.error("get_password | Error retrieving and loop through password storage object: %s" % str(e))

    def get_source(self,s):
        return "redsealModInput:" + s

    def escape(self,s):
        """ A wrapper function to force conformity on xml escaping, and for ease of reading """
        return xml.sax.saxutils.escape(s)

    def login(self,serverName,port, username, password):
        # request = six.moves.urllib.request.Request("https://"+serverName+ ":"+ port +"/data/")
        base64string = self.getBase64String(username,password)

        # headers={'Authorization': 'Basic %s' % base64string, 'Accept': 'application/json'}
        # request.add_header("Authorization", "Basic %s" % base64string)
        # request.add_header("Accept", "application/json")
        # response = six.moves.urllib.request.urlopen(request)

        headers={'Authorization': 'Basic %s' % base64string, 'Accept': 'application/json'}
        url = "https://"+serverName+":"+ port +"/data/"
        res = requests.get(url,headers=headers, verify=False)
        # return(response.read())
        # return res.text
        return res.status_code, res.reason

    # def getHostMetrics(self, serverName, port, username, password):
    # 	request = six.moves.urllib.request.Request("https://"+serverName+ ":"+ port +"/data/metrics/host/all")
    # 	base64string = self.getBase64String(username,password)
    #
    # 	request.add_header("Authorization", "Basic %s" % base64string)
    # 	request.add_header("Accept", "application/json")
    # 	response = six.moves.urllib.request.urlopen(request)
    # 	return(response.read())

    def getSummaryData(self,serverName, port, username, password, proxy):
        base64string = self.getBase64String(username,password)
        headers={'Authorization': 'Basic %s' % base64string, 'Accept': 'application/json'}
        url = "https://"+serverName+":"+ port +"/data7/summary"

        try:
            if proxy is None:
                self.LOGGER.info("getSummaryData | proxy object is None")
                res = requests.get(url,headers=headers, verify=False)
            else:
                self.LOGGER.info("getSummaryData | proxy object is not None")
                res = requests.get(url,headers=headers, proxies=proxy, verify=False)

            self.LOGGER.info("getSummaryData | URL request response code:%s", res.status_code)
            if (res.status_code != 200):
                self.LOGGER.info("getSummaryData | URL request response message:%s", res.reason)

        except Exception as e:
            self.LOGGER.error("getSummaryData | Unable to retreive summaryData from RedSeal Server: %s", e.args[0])
            self.LOGGER.info("getSummaryData | RedSeal server :%s", serverName)
            self.LOGGER.info("getSummaryData | server port:%s", port)
            self.LOGGER.info("getSummaryData | RedSeal username:%s", username)
            raise Exception("Error getting summary data from RedSeal server.")

        return res.text

    def getBase64String(self, username, password):
        userpass = username+":"+password
        userpass = userpass.replace('\n','')
        if six.PY3:
            userpass = userpass.encode('utf-8')
        base64string = base64.b64encode(userpass).decode('utf-8')
        return base64string

    def processJSON(self, jsonResult):
        r =  json.loads(jsonResult)

        self.LOGGER.info('processJSON | get list array from JSON result')
        hostInfoList = []
        if (r.get('list') is None):
            # No analysis exists so no host metrics
            return hostInfoList

        hostList = r['list'][0]['Metrics']

        for val in hostList:

            parsedUrl = urllib.parse.urlparse(val['URL'])

            hostInfo = {'name':str(val['Name']), 'ipAddress':str(val['PrimaryIp']),
                        'serverName' : str(parsedUrl.netloc), 'attackDepth':str(val['AttackDepth']),'exposure': str(val['Exposure']),
                        'value':str(val['Value']), 'risk':str(val['Risk']), 'downstreamrisk':str(val['DownstreamRisk']),
                        'exploitable':str(val['Exploitable']), 'accessibleFromUntrusted': str(val['AccessibleFromUntrusted']),
                        'hasaccessToCritical':str(val['HasAccessToCritical'])}
            hostInfoList.append(hostInfo)
        return hostInfoList


    def processKVStore(self, hostList, session_key):
        self.LOGGER.info("processKVStore before processing host metric")
        args = {'token':session_key, 'owner':'nobody','app':self.APP }
        service = client.connect(**args)

        for val in hostList:
            data = json.dumps(val)
            collection = service.kvstore['host_metric_collection']
            key = collection.data.insert(data)

    def kvRemoveEntries(self, session_key, results, serverName):

        args = {'token':session_key, 'owner':'nobody'}
        service = client.connect(**args)

        # i = 0
        # for result in results:
            #self.LOGGER.info(serverName + " | " + str(i))
        #   i=i+1
        #   key = str(result['KeyID'])

        # 	self.LOGGER.info (serverName + '| Delete:' + key + '\n')

        collection = service.kvstore['host_metric_collection']
        #   result = collection.data.delete_by_id(key)
        query='{"serverName": "%s"}' % serverName
        result = collection.data.delete(query)
        self.LOGGER.info(serverName + ' | Removal complete')



    def kvSearchByServerName(self,sessionKey, serverName):
        #create search string
        server_search = "|inputlookup kv_host_metric_lookup where serverName = " + serverName + " | eval KeyID = _key"
        self.LOGGER.info("kvSearchByServerName str:"+ server_search)

        #dispatch search
        self.LOGGER.info("kvSearchByServerName: before search execution")
        my_job = splunk.search.dispatch( server_search, sessionKey=sessionKey, namespace=self.APP)
        self.LOGGER.info("kvSearchByServerName: after search execution")


        #while loop to wait for results to finish
        jobDone = my_job.isDone
        while jobDone == False :
            self.LOGGER.info("waiting for search job to finish")
            time.sleep(1)
            jobDone = my_job.isDone

        #Returned events
        self.LOGGER.info("assiging the search results to events")
        events = [ server_search ]

        # Display the search results now that the job is done
        resultCount = my_job.resultCount
        self.LOGGER.info("result count:" + str(resultCount))

        # Keep for debugging
        # i = 0
        # for result in my_job.results:
        # 	self.LOGGER.info(str(i))
        # 	i=i+1
        # 	self.LOGGER.info (str(result['KeyID']) + '\n')

        return my_job.results, resultCount

    def generateDashboardSummary(self,serverName, port, username, password, proxy):

        self.LOGGER.info("generateDashboardSummary | Before call to get Summary Data.")

        result = self.getSummaryData(serverName, port, username, password, proxy)
        r = json.loads(result)
        summary = {}
        if r is not None:
            # Check to see if Analysis is null that means no analysis has completed on the RedSeal server

            if ( r['srmStatus']['lastAnalysisBeginTime'] is not None):
                summary = {'AnalysisStartDate' : r['srmStatus']['lastAnalysisBeginTime'], 'ThreatSources': r['srmStatus']['untrustedSubnetCount'],
                           'DeviceCount':r['inventoryStatus']['numDevices'], 'HostCount':r['inventoryStatus']['numHosts'],'ModelIssues':r['modelIssues']['totalFailureCount'],
                           'ResilientScore':r['securitySummaryData']['networkSecurityScore']['networkSecurityScore'], 'CriticalVulns': r['securitySummaryData']['networkSecurityScore']['criticalVulnerabilities'],
                           'ConfigurationChecks':r['securitySummaryData']['networkSecurityScore']['failedConfigurationChecks'],'IncompleteModel':r['securitySummaryData']['networkSecurityScore']['missingNetworkInformation']}

        summaryResult  = {}
        self.LOGGER.info("generateDashboardSummary | summary results: " + str(summary))
        summaryResult = summary
        return summaryResult

    def redSealAPIComplete(self,serverName, summaryResults):

        serverMetaData = {'serverName' : serverName, 'api_call_complete' : 'true'}
        if (summaryResults.get('AnalysisStartDate') is None):
            summaryResults = {'comment' : 'No Analysis data found.  Analysis date from API call is empty.'}

        combineSummary = dict(list(serverMetaData.items()) + list(summaryResults.items()))
        self.LOGGER.info("redSealAPIComplete | combineSummary:" + str(combineSummary))
        return combineSummary

    def loginCheck(self,serverName, port, username, password):
        response = None
        try:
            self.LOGGER.info("loginCheck | Before login test.")
            # self.LOGGER.info("loginCheck | **** ONLY FOR TESTING **** username: %s" % username)
            # self.LOGGER.info("loginCheck | **** ONLY FOR TESTING **** password: %s" % password)
            response_code, reason = self.login(serverName,port,username,password)
            # self.LOGGER.info("loginCheck | **** ONLY FOR TESTING **** response code: %s" % str(response_code))

            if (response_code !=200):
                raise Exception ("Received error when trying to login to RedSeal Server.  Response Code: %s | Reason: %s"
                                 % (response_code, reason))
            else:
                return True
        except Exception as e:
            self.LOGGER.error("loginCheck | Unable to login to RedSeal Server: %s" % e.args[0])
            return False

    def configure_proxy(self, proxy_username, proxy_password, proxy_server_https , proxy_server, proxy_port):
        if (proxy_server_https == '1'):
            if (proxy_username is None):
                # No Authentication required for proxy server
                self.LOGGER.info("configure_proxy | https proxy no auth Before")
                proxy_configuration= { 'https' : 'https://'+proxy_server+':'+proxy_port }
                self.LOGGER.info("configure_proxy | https proxy no auth")
            else:
                self.LOGGER.info("configure_proxy | https proxy auth Before")
                self.LOGGER.info("proxy_username:%s", proxy_username)
                # self.LOGGER.info("**** ONLY FOR TESTING **** proxy_password:%s", proxy_password)
                proxy_configuration= { 'https' : 'https://'+proxy_username+':'+proxy_password+'@'+proxy_server+':'+proxy_port }
                self.LOGGER.info("configure_proxy | https proxy auth")
        else:
            if (proxy_username is None):
                # No Authentication required for proxy server
                self.LOGGER.info("configure_proxy | http proxy no auth Before")
                proxy_configuration= { 'http' : 'http://'+proxy_server+':'+proxy_port }
                self.LOGGER.info("configure_proxy | http proxy no auth")
            else:
                self.LOGGER.info("configure_proxy | http proxy  auth Before")
                proxy_configuration= { 'http' : 'http://'+proxy_username+':'+proxy_password+'@'+proxy_server+':'+proxy_port }
                self.LOGGER.info("configure_proxy | http proxy  auth")

        return proxy_configuration

    def get_pasword_store(self,session_key):
        # Retrieve the password from the storage/passwords endpoint
        args = {'token':session_key}
        service = client.connect(**args)
        password_store = service.storage_passwords
        return password_store


    def stream_events(self, inputs, ew):
        self.LOGGER.info("Start of stream_events")
        self.input_name, self.input_items = inputs.inputs.popitem()

        clear_proxy_password = None

        session_key = self._input_definition.metadata["session_key"]
        username = self.input_items["username"]
        password   = self.input_items['password']
        redsealServer = self.input_items['redsealServer']
        port = self.input_items['port']
        self.LOGGER.info("stream_events | Before proxy info pull ")
        proxy_server_https = self.input_items['proxy_server_https']

        self.LOGGER.info("stream_events | Before proxy server info pull ")
        proxy_server = self.input_items.get('proxy_server')
        proxy_username = self.input_items.get('proxy_username')
        proxy_password = self.input_items.get('proxy_password')
        proxy_port = self.input_items.get('proxy_port')

        source_type = self.input_items['sourcetype']
        stanza = self.input_name
        source = self.get_source(stanza[(stanza.rfind("/")+1):])

        password_store = self.get_pasword_store(session_key)

        try:

            # kind, inputName = self.input_name.split("://")
            # result = self.validDataInputCheck(session_key, redsealServer, inputName)
            # self.LOGGER.info('stream_events | Result value:%s' % result)

            # If the password is not masked, encrypt it.
            self.LOGGER.info("stream_events | Check if Password is masked")
            self.LOGGER.info("stream_events | mask value to check:%s", self.MASK)
            self.LOGGER.info("stream_events | password:%s", password)
            if password != self.MASK:
                self.LOGGER.info("stream_events | Password NOT masked")
                self.encrypt_password(username, password, session_key, redsealServer, password_store)

            self.LOGGER.info("stream_events | Get the unmasked password")
            clear_password = self.get_password(session_key, username, redsealServer, password_store)

            self.LOGGER.info("stream_events | Before proxy check")
            proxy = None

            if((proxy_username is not None) and (len(proxy_username)>1) and proxy_password is not None):
                self.LOGGER.info("stream_events | proxy username:%s", proxy_username)
                # self.LOGGER.info("stream_events | **** ONLY FOR TESTING **** proxy password:%s", proxy_password)
                self.LOGGER.info("stream_events | Check if Proxy Password is masked")
                # If the proxy_password is not masked, encrypt it.
                if proxy_password != self.MASK:
                    self.LOGGER.info("stream_events | Proxy Password NOT masked")
                    self.encrypt_password(proxy_username, proxy_password, session_key, proxy_server, password_store)

                self.LOGGER.info("stream_events | Get the unmasked Proxy Password")
                clear_proxy_password = self.get_password(session_key, proxy_username, proxy_server, password_store)

                if (clear_proxy_password is None):
                    raise Exception ("Proxy password could not be found for proxy username:"+ proxy_username)

                self.LOGGER.info("stream_events | proxy username:%s", proxy_username)
                # self.LOGGER.info("stream_events | **** ONLY FOR TESTING **** proxy clear password:%s", clear_proxy_password)
                self.LOGGER.info("stream_events | Auth required for proxy server")
                proxy = self.configure_proxy(proxy_username, clear_proxy_password, proxy_server_https ,
                                             proxy_server, proxy_port)

                self.LOGGER.info("stream_events | proxy username:%s", proxy_username)

                # ToDo: Only for Testing displays password
                # self.LOGGER.info("stream_events | **** ONLY FOR TESTING **** proxy password:%s", clear_proxy_password)

                self.LOGGER.info("stream_events | proxy server https:%s", proxy_server_https)
                self.LOGGER.info("stream_events | proxy server:%s", proxy_server)
                self.LOGGER.info("stream_events | proxy server port:%s", proxy_port)

            if (((proxy_server is not None) and len(proxy_server)>1) and ((proxy_username is None) or
                    len(proxy_username)==0)):
                self.LOGGER.info("stream_events | No Auth required for proxy server")
                proxy = self.configure_proxy(None, None, proxy_server_https , proxy_server, proxy_port)

                self.LOGGER.info("stream_events | proxy server https:%s", proxy_server_https)
                self.LOGGER.info("stream_events | proxy server:%s", proxy_server)
                self.LOGGER.info("stream_events | proxy server port:%s", proxy_port)

            # ToDo: Only for Testing displays password
            # if proxy is not None:
            #     for keys,value in list(proxy.items()):
            #         self.LOGGER.info("stream_events | **** ONLY FOR TESTING **** proxy key:%s",keys)
            #         self.LOGGER.info("stream_events | **** ONLY FOR TESTING **** proxy value:%s",value)

            if password != self.MASK or (proxy_password is not None and proxy_password != self.MASK):
                # Mask the passwords that appear in the Data Input Listing view.
                self.mask_password(session_key, username, port, redsealServer, proxy_server_https,
                                   proxy_server, proxy_port, proxy_username)

        # results, resultCount = self.kvSearchByServerName(session_key, redsealServer)
            # self.LOGGER.info("stream_events | Number of host to RedSeal server mapping count resultCount:%s | RedSeal Server:%s" % (str(resultCount), redsealServer))


            # self.kvRemoveEntries(session_key, results, redsealServer)
            # self.LOGGER.info("stream_events | Remove kvRemoveEntries")

            # hostlist = self.processJSON(self.getHostMetrics(redsealServer, port ,username,self.CLEAR_PASSWORD))
            # if (hostlist is not None):
            # 	self.LOGGER.info("stream_events | Generated hostlist size:%s" % str(len(hostlist)))

            # self.LOGGER.info("stream_events | Generated hostlist")

            # self.processKVStore(hostlist,session_key)
            # self.LOGGER.info("stream_events | Completed processKVStore")

            # Generate summary run results from the RedSeal server
            self.LOGGER.info("stream_events | Get DashboardSummary Results")
            summaryResult = self.generateDashboardSummary(redsealServer, port, username, clear_password, proxy)
            self.LOGGER.info("stream_events | Completed DashboardSummary Results")

            # Add a Summary event to signal end of RedSeal API call
            # Create an Event object, and set its data fields
            event = Event()
            event.stanza = self.input_name
            event.data = json.dumps(self.redSealAPIComplete(redsealServer, summaryResult))
            event.source = self.escape(source)
            event.sourceType = self.escape(source_type)
            # Tell the EventWriter to write this event
            ew.write_event(event)
            self.LOGGER.info("stream_events | Completed DashboardSummary event.")

        except Exception as e:
            self.LOGGER.error("ERROR, stream_events | Unable to complete DashboardSummary event.")
            self.LOGGER.error("ERROR, stream_events | Unable to complete DashboardSummary event. | %s", e.args[0])
            ew.log("ERROR", "Error: %s" % str(e))


    # def unit_test(self):
    #     serverUri = 'localhost:8089'
    #     cherrypy.tools.sessions.on = True
    #     self.LOGGER = self.setup_logger()
    #     class FakeSession(dict):
    #         def __init__(self):
    #             self.id = 5
    #             self.sessionKey = splunk.auth.getSessionKey('admin', '1redSeal1')
    #     cherrypy.session = FakeSession()
    #     sessionKey = splunk.auth.getSessionKey('admin', '1redSeal1')
    #     cherrypy.session['sessionKey'] = sessionKey
    #     cherrypy.session['user'] = { 'name': 'admin' }
    #     cherrypy.session['id'] = 12345
    #     cherrypy.config['module_dir'] = '/'
    #     cherrypy.config['build_number'] = '123'
    #     cherrypy.request.lang = 'en-US'
    #     #ToDo: Remove values
    #     serverName = ''
    #     port = ''
    #     username = ''
    #     password = ''
    #
    #     try:
    #         # results, resultCount = self.kvSearchByServerName(sessionKey,serverName)
    #         # self.kvRemoveEntries(serverUri, sessionKey, results, serverName)
    #         # hostlist = self.processJSON2(self.getHostMetrics(serverName,username,password))
    #         # self.processKVStore(serverUri,hostlist,sessionKey)
    #         # result = self.getSummaryData(serverName,'443',username,password)
    #         # result2 =  self.generateDashboardSummary(serverName,username,password)
    #         # print (str(result))
    #         # print (str(result2))
    #
    #         # args = {'token':sessionKey,'username':'admin','password':''}
    #         args = {'token':sessionKey}
    #         service = client.connect(**args)
    #         # Get the collection of data inputs
    #         inputs = service.inputs.list('redsealModInput')
    #
    #         # List the inputs and kind
    #         for item in inputs:
    #             print("%s (%s)" % (item.name, item.kind))
    #
    #         # self.loginCheck(serverName,port,username,password)
    #         # self.encrypt_password(username,password,sessionKey,serverName)
    #         # self.mask_password(sessionKey,username,port,serverName)
    #         # self.get_password(sessionKey,username,serverName)
    #         print ('Completed calls')
    #
    #     except Exception as e:
    #         # print_error(e)
    #         # self.LOGGER.info(e.message)
    #         sys.stdout.write("ERROR:" + e.args[0])
    #     sys.stdout.write('Completed UNIT TEST')

    def getSummaryDataTEST(self,serverName, port, username, password):
        request = six.moves.urllib.request.Request("https://"+serverName+":"+ port +"/data7/summary")
        base64string = self.getBase64String(username,password)

        try:
            # url = "https://"+serverName+":"+ port +"/data7/summary"
            url = "https://www"
            headers={'Authorization': 'Basic %s' % base64string, 'Accept': 'application/json'}
            # headers={'Authorization': 'Basic %s' % base64string}
            # request.add_header("Authorization", "Basic %s" % base64string, )
            # request.add_header("Accept", "application/json")
            # response = six.moves.urllib.request.urlopen(request)
            # return(response.read())
            # res = requests.post(url,header, verify=False)
            # Auth not required
            proxies = { 'https' : 'https://10.xx.xx.xx:4128' }
            res = requests.get(url,headers=headers, proxies=proxies, verify=False)
            print(res.status_code)
            print (res.text)
        except Exception as e:
            print ('error message caught: ',e.args[0])

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test" :
            print('stand alone test')
            ms = MyScript()
            # ms.getSummaryDataTEST('172.x.x.x','443','xxx','xxxx')
    else:
        exitcode = MyScript().run(sys.argv)
        sys.exit(exitcode)
