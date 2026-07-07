import sys, os
import logging, logging.handlers
import splunk
#import io
import base64
import requests
#import json
#import ast

class neo4jenvironment:
    #def __init__(self, account="", service="", logger="", username=""):
    def __init__(self, outerclass="", account="", scriptname="", debug=True, statsonly=False):
        self.debug = bool(debug)
        self.outerclass = outerclass
        self.account = account
        self.conf_loglevel = ""
        self.statsonly = bool(statsonly)

        try:
            if debug:
                self.conf_loglevel = "DEBUG"
            else:
                self.conf_loglevel= outerclass.service.confs['itmip_neo4j_commands_splunk_settings']['logging']['loglevel']
            #if self.debug: self.logger2.debug("The configured loglevel for the account {0} is {1}".format(account,self.conf_loglevel))
        except Exception as e:
            #if self.debug: self.logger2.debug("No loglevel is specified for the requested account: \"{0}\". Following is the error: {1}".format(account, e))
            outerclass.write_error("No loglevel is specified for the requested account: \"{0}\".".format(account))

        try: 
            self.setup_logging(outerclass, scriptname)
        except Exception as e:
            outerclass.write_error("Not possible to setup logging. The following is the error: {0}".format(e))
        
        #self.logger2.error("this is a test")

        self.searchusername = outerclass._metadata.searchinfo.username
        if self.debug: 
            self.logger2.debug("This {0} command is executed with python version: {1}, and user: {2}.".format(scriptname, sys.version_info, self.searchusername))
            #outerclass.write_error("The value of debug is: {0}".format(scriptname))
        
        try:
            self.conf_allowedroles = outerclass.service.confs['itmip_neo4j_commands_splunk_account'][account]['allowedroles']
            if self.debug: self.logger2.debug("The configured allowedroles for the account {0} are {1}".format(account,self.conf_allowedroles))
        except Exception as e:
            if self.debug: self.logger2.debug("No allowedroles are specified for the requested account: \"{0}\". Following is the error: {1}".format(account, e))
            outerclass.write_error("No allowedroles are specified for the requested account: \"{0}\".".format(account))

        
        try:
            self.conf_fullurl= outerclass.service.confs['itmip_neo4j_commands_splunk_account'][account]['transaction_full_url']
            if self.debug: self.logger2.debug("The configured transaction_full_url for the account {0} is {1}".format(account,self.conf_fullurl))
        except Exception as e:
            if self.debug: self.logger2.debug("No transaction_full_url is specified for the requested account: \"{0}\". Following is the error: {1}".format(account, e))
            outerclass.write_error("No transaction_full_url is specified for the requested account: \"{0}\".".format(account))

        
        if "https" in self.conf_fullurl.lower()[0:5]:
            pass
        else:
            if self.debug: self.logger2.debug("Only HTTPs URLs may be used. Now it is: \"{0}\".".format(self.conf_fullurl))
            outerclass.write_error("Only HTTPs URLs may be used. Now it is: \"{0}\".".format(self.conf_fullurl))
            exit()

        try:
            self.conf_username= outerclass.service.confs['itmip_neo4j_commands_splunk_account'][account]['username']
            if self.debug: self.logger2.debug("The configured username for the account {0} is {1}".format(account,self.conf_username))
        except Exception as e:
            if self.debug: self.logger2.debug("No username is specified for the requested account: \"{0}\". Following is the error: {1}".format(account, e))
            outerclass.write_error("No username is specified for the requested account: \"{0}\".".format(account))


        #if not logger is None: logger2.info("The specified database name is: {0}".format(self.conf_dbname))
        conf_lallowedroles = self.conf_allowedroles.split(',')
        self.lconfroles = []
        for roles in conf_lallowedroles:
            role = roles.strip()
            self.lconfroles.append(role)
        if self.debug: self.logger2.debug("The configured allowedroles is: {0}".format(self.lconfroles))
        #if not logger is None: logger2.info("The configured allowedroles is: {0}".format(lconfroles))

        self.rolevalid = 0
        userroles = outerclass.service.roles
        for role in userroles:
            if self.debug: self.logger2.debug("logging all roles the current user {0} has: {1}".format(account, role.name))
            if role.name in self.lconfroles:
                self.rolevalid = 1
                break

        if not self.rolevalid:
            if self.debug: self.logger2.debug("This user {0} is not having valid roles for executing this command.".format(self.searchusername))
            outerclass.write_error("This user {0} is not having valid roles for executing this command.".format(self.searchusername))
            exit()

        long_account = "__REST_CREDENTIAL__#itmip_neo4j_commands_splunk#configs/conf-itmip_neo4j_commands_splunk_account:" + account + "``splunk_cred_sep``1:"
        clearpassword = None
        try:
            clearpassword = eval(outerclass.service.storage_passwords[long_account]['clear_password'])
            clearpassword = clearpassword['password']
        except Exception as e:
            if self.debug: self.logger2.debug("This account {0} is not having a password defined. The error is the following: {1}".format(account, e))
            outerclass.write_error("This account {0} is not having a password defined.".format(account))

        #authorizemsg = self.conf_username+":"+clearpassword['password']
        encoded_credentials = base64.b64encode(bytes(f'{self.conf_username}:{clearpassword}',encoding='ascii')).decode('ascii')
        
        #message_bytes = authorizemsg.encode('ascii')
        #if self.debug: self.logger2.debug("Authorize msgb: {0}".format(encoded_credentials))
        authorize = f'Basic {encoded_credentials}'
        if self.debug: self.logger2.debug("Authorize header: {0}".format(authorize))
        self.headers = {
            'Accept': "application/json;charset=UTF-8",
            'Content-Type': "application/json",
            'Authorization': authorize,
            'user-agent': "itmip_neo4j_commands_splunk_common",
            'cache-control': "no-cache",
            'charset': "UTF-8",
            }
        if self.debug: self.logger2.debug("All headers: {0}".format(self.headers))

 
        return
    
    def __del__(self):
        return

    def setup_logging(self, outerclass, scriptname):
        self.logger2 = logging.getLogger('splunk.foo')
        SPLUNK_HOME = os.environ['SPLUNK_HOME']
        LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
        LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
        LOGGING_STANZA_NAME = 'python'
        LOGGING_FILE_NAME = "neo4jcommands_%s.log" % scriptname
        BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
        LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
        splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
        splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        self.logger2.addHandler(splunk_log_handler)
        splunk.setupSplunkLogger(self.logger2, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
        self.logger2.setLevel(self.conf_loglevel)  
        self.logger2.debug("The logging is initialized.")
        return
 
    def execute_query(self, query="", data=""):
        testfordot = "."
        if query and data: query="UNWIND $splunkraw AS splunk "+query
        if query and not data: query=query
        if self.debug: self.logger2.debug("Query is {0}".format(query))
        if data:
            payload = {
                "statements": [
                    {
                        "statement": query,
                        "includeStats": False,
                        "parameters": {
                            "splunkraw": data
                        }
                    }
                ]
            }
        else:
            payload = {
                "statements": [
                    {
                        "statement": query,
                        "includeStats": False
                    }
                ]
            }
        try:
            fullautocommiturl = self.conf_fullurl+"/commit"
            if self.debug: self.logger2.debug("Fullcommiturl is {0}".format(fullautocommiturl))
            r = requests.post(fullautocommiturl, headers = self.headers, json = payload, timeout=300)
            if self.debug: self.logger2.debug("Request status code is {0}".format(r.status_code))
            #if self.debug: self.logger2.debug("Response headers are {0}".format(payload))
            if self.debug: self.logger2.debug("Response data is {0}".format(r.json()))
        except Exception as e:
            if self.debug: self.logger2.debug("Following {0} account is throwing connection with error: {1}".format(self.account, e))
            self.outerclass.write_error("Following {0} account is throwing connection with error: {1}".format(self.account, e))
            exit()

        try:
            output = r.json()
        except Exception as e:
            if self.debug: self.logger2.debug("Json decode request is throwing connection with error: {0}".format(e))
            self.outerclass.write_error("Json decode request is throwing connection with error: {0}".format(e))
        if self.debug and output['errors']:
            self.logger2.debug("Neo4j errors: {0}".format(output['errors'][0]['message']))
            self.outerclass.write_error("There where errors with the Neo4j search: {0}.".format(output['errors'][0]['message']))

        resulttosplunk = []
        if self.statsonly:
            statsonly = bool(0)
        if not self.statsonly:
            statsonly = bool(1)
        if self.debug: self.logger2.debug("Statsonly is {0}".format(self.statsonly))
        if self.statsonly:
            #self.outerclass.write_error("with stats but no results")
            for result in output['results']:
                self.logger2.debug("The following stats are there: {0}".format(result['stats']))
                datadict = result['stats']
                resulttosplunk.append(datadict)
        
        if not self.statsonly:
            for result in output['results']:
                if result['data']:
                    for datarow in result['data']:
                        row = {}
                        self.logger2.debug("datarow.....: {0}".format(datarow))
                        for idx, val in enumerate(datarow['row']):
                            
                            self.logger2.debug("datarow.row....: {0}, {1}".format(idx, val))
                            
                            if testfordot in result['columns'][idx]:
                                row[result['columns'][idx]] = val
                                #keypair = {result['columns'][idx]: val}
                            else:
                                if isinstance(val, dict):
                                    for key, value in val.items():
                                        newkey = result['columns'][idx]+"."+key
                                        row[newkey] = value
                                else:
                                    row[result['columns'][idx]] = val
                            
                        resulttosplunk.append(row)
        return resulttosplunk

    def execute_path_query(self, query="", data=""):
        testfordot = "."
        if query and data: query="UNWIND $splunkraw AS splunk "+query
        if query and not data: query=query
        if self.debug: self.logger2.debug("Query is {0}".format(query))
        if data:
            payload = {
                "statements": [
                    {
                        "statement": query,
                        "includeStats": False,
                        "parameters": {
                            "splunkraw": data
                        }
                    }
                ]
            }
        else:
            payload = {
                "statements": [
                    {
                        "statement": query,
                        "includeStats": False,
                        "resultDataContents": ["graph"]
                    }
                ]
            }
        try:
            fullautocommiturl = self.conf_fullurl+"/commit"
            if self.debug: self.logger2.debug("Fullcommiturl is {0}".format(fullautocommiturl))
            r = requests.post(fullautocommiturl, headers = self.headers, json = payload, timeout=300)
            if self.debug: self.logger2.debug("Request status code is {0}".format(r.status_code))
            #if self.debug: self.logger2.debug("Response headers are {0}".format(payload))
            if self.debug: self.logger2.debug("Response data is {0}".format(r.json()))
        except Exception as e:
            if self.debug: self.logger2.debug("Following {0} account is throwing connection with error: {1}".format(self.account, e))
            self.outerclass.write_error("Following {0} account is throwing connection with error: {1}".format(self.account, e))
            exit()

        try:
            output = r.json()
        except Exception as e:
            if self.debug: self.logger2.debug("Json decode request is throwing connection with error: {0}".format(e))
            self.outerclass.write_error("Json decode request is throwing connection with error: {0}".format(e))
        if self.debug and output['errors']:
            self.logger2.debug("Neo4j errors: {0}".format(output['errors'][0]['message']))
            self.outerclass.write_error("There where errors with the Neo4j search: {0}.".format(output['errors'][0]['message']))

        resulttosplunk = []
        if self.statsonly:
            statsonly = bool(0)
        if not self.statsonly:
            statsonly = bool(1)
        if self.debug: self.logger2.debug("Statsonly is {0}".format(self.statsonly))
        if self.statsonly:
            #self.outerclass.write_error("with stats but no results")
            for result in output['results']:
                self.logger2.debug("The following stats are there: {0}".format(result['stats']))
                datadict = result['stats']
                resulttosplunk.append(datadict)
        
        if not self.statsonly:
            if output['results'][0]['data']:
                return output['results'][0]['data']

        return resulttosplunk
