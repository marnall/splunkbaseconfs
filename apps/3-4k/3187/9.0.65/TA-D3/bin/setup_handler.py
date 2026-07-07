import splunk.admin as admin
import splunk.entity as en
import splunk
import re
import requests
import json
import logging, logging.handlers

def setup_logging():
    logger = logging.getLogger('Splunk.tad3')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "tad3.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

class ConfigApp(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['host_1', 'uname', 'upassword']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf("appsetup")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in ['host_1'] and val in [None, '']:
                        val = ''
                    if key in ['uname']:
                        val = ''
                    if key in ['upassword']:
                        val = ''
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        logger = setup_logging()
        try:
            name = self.callerArgs.id
            args = self.callerArgs

            if self.callerArgs.data['host_1'][0] in [None, '']:
                self.callerArgs.data['host_1'][0] = ''
            if self.callerArgs.data['uname'][0] in [None, '']:
                self.callerArgs.data['uname'][0] = ''
            if self.callerArgs.data['upassword'][0] in [None, '']:
                self.callerArgs.data['upassword'][0] = ''

            #validate input
            if self.callerArgs.data['host_1'][0] == '' or self.callerArgs.data['uname'][0] == '' or self.callerArgs.data['upassword'][0] == '':
                raise Exception('Missing host and credentials information')

            if not self.callerArgs.data['host_1'][0].startswith('https://'):
                raise Exception('We can only accept https host URL.')

            # deal with username and password
            username = self.callerArgs.data['uname'][0] + "_d3tad3"    #important: to make username unique in splunk
            password = self.callerArgs.data['upassword'][0]

            # save config without username and password details
            self.callerArgs.data['upassword'][0] = ''
            self.callerArgs.data['uname'][0] = ''
            self.writeConf('appsetup', 'setupentity', self.callerArgs.data)

            # Use splunk password endpoint to save and encrypt password
            #check username exists
            url = splunk.getLocalServerInfo()+'/servicesNS/nobody/TA-D3/storage/passwords/%3A' + username + '%3A?search=TA-D3&output_mode=json'
            r = requests.get(url = url, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)

            if r.status_code == 200:
                #if username exists update passwords
                url = splunk.getLocalServerInfo()+'/servicesNS/nobody/TA-D3/storage/passwords/%3A' + username + '%3A?search=TA-D3&output_mode=json'
                r = requests.post(url=url, data={'password': password}, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)
            else:
                #if username not exists, search only TA-D3 credentials
                url = splunk.getLocalServerInfo()+'/servicesNS/nobody/TA-D3/storage/passwords?search=TA-D3&output_mode=json'
                r = requests.get(url = url, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)
                if r.status_code != 200:
                    raise Exception('Failed to update username and password')
                    
                data = r.json()
                #logger.error(json.dumps(data, indent=4, sort_keys=True))

                #if TA-D3 old user exists, replace the old user with new username and password
                if(len(data['entry'])>0):
                    for ent in data["entry"]:
                        if(ent['acl']['app']=='TA-D3'):
                            removeLink = ent['links']['remove']
                            url = splunk.getLocalServerInfo()+removeLink
                            requests.delete(url = url, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)

                    url = splunk.getLocalServerInfo()+'/servicesNS/nobody/TA-D3/storage/passwords?search=TA-D3&output_mode=json'
                    requests.post(url = url, data = {'name': username, 'password': password, 'realm':'TA-D3'}, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)

                #if TA-D3 old user not exists, create new user
                else: 
                    url = splunk.getLocalServerInfo()+'/servicesNS/nobody/TA-D3/storage/passwords?search=TA-D3&output_mode=json'
                    requests.post(url = url, data = {'name': username, 'password': password, 'realm':'TA-D3'}, headers={'Authorization': 'Splunk ' + self.getSessionKey()}, verify=False)

        except Exception, e:
            logger.error(str(e))
            logger.exception("Fatal error when saving config")
            raise Exception("Error: %s" % (str(e)))

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
