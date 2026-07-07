"""
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the
configuration page.

    handleList method: lists configurable parameters in the configuration page
    corresponds to handleractions = list in restmap.conf

    handleEdit method: controls the parameters and saves the values
    corresponds to handleractions = edit in restmap.conf
"""
import ta_rapidresponse_declare

import json
import splunk.clilib.cli_common as scc
import splunk.admin as admin


import solnlib.utils as utils
import solnlib.log as log
import solnlib.conf_manager as conf
import ta_rapidresponse_consts as setup_const
import modalert_rapid_response_action_helper
import requests
import socket
import ssl
import sys
from subprocess import Popen,PIPE,check_call
from urlparse import urlparse

log.Logs.set_context(namespace="ta_rapidresponse")
logger = log.Logs().get_logger("setup")

def get_or_create_conf_file(conf_mgr, file_name):
    try:
        conf_file = conf_mgr.get_conf(file_name)
        return conf_file
    except conf.ConfManagerException as cme:
        conf_mgr._confs.create(file_name)
        return conf_mgr.get_conf(file_name, refresh=True)

def filter_eai_property(stanza):
    if isinstance(stanza, dict):
        for k in list(stanza.keys()):
            if k.startswith('eai:'):
                del stanza[k]
            else:
                stanza[k] = filter_eai_property(stanza[k])
    return stanza

class ConfigApp(admin.MConfigHandler):
    valid_args = ("all_settings",)

    stanza_map = {
        setup_const.global_settings: True,
        setup_const.myta_customized_settings: True,
    }

    global_cred_fields = [setup_const.proxy_password, setup_const.password]
    cred_fields = [setup_const.password]
    encrypt_fields_customized = (setup_const.password,)

    def setup(self):
        """
        Set up supported arguments
        """
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.valid_args:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        logger.info("start list setup configure.")
        scheme, host, port = utils.extract_http_scheme_host_port(scc.getMgmtUri())
        conf_mgr = conf.ConfManager(self.getSessionKey(), self.appName, scheme=scheme, host=host, port=port)
        ta_conf_file = get_or_create_conf_file(conf_mgr, setup_const.myta_conf)
        # read globala and proxy settings
        all_settings = ta_conf_file.get_all()
        if not all_settings:
            all_settings = {}
        self._setNoneValues(all_settings.get(setup_const.global_settings, {}))
        # customized conf
        customized_conf_file = get_or_create_conf_file(conf_mgr, setup_const.myta_customized_conf)
        settings = customized_conf_file.get_all()
        all_settings[setup_const.myta_customized_settings] = settings
#        logger.info("*** settings from conf file are *** [%s] ", all_settings)
        self._clearPasswords(all_settings, self.cred_fields)
        all_settings = filter_eai_property(all_settings)
        all_settings = json.dumps(all_settings)
        all_settings = utils.escape_json_control_chars(all_settings)
        confInfo[setup_const.myta_settings].append(setup_const.all_settings, all_settings)
        logger.info("list setup configure is done.")

    def handleEdit(self, confInfo):
        logger.info("start edit setup configure.")
        scheme, host, port = utils.extract_http_scheme_host_port(scc.getMgmtUri())
        conf_mgr = conf.ConfManager(self.getSessionKey(), self.appName, scheme=scheme, host=host, port=port)
        ta_conf_file = get_or_create_conf_file(conf_mgr, setup_const.myta_conf)
        customized_conf_file = get_or_create_conf_file(conf_mgr, setup_const.myta_customized_conf)
        all_origin_settings = ta_conf_file.get_all()
        all_settings = utils.escape_json_control_chars(
        self.callerArgs.data[setup_const.all_settings][0])
        all_settings = json.loads(all_settings)
        doit = all_settings["customized_settings"]["importa"]["bool"]
        appSymUrl = all_settings["customized_settings"]["asrecovery_url"]["content"] + '/execution/execution/sync'
        splunkIndex = all_settings["customized_settings"]["string_label"]["content"]
        splunk_post_username = all_settings["customized_settings"]["asrecovery_username"]["content"]
        logger.info("************ splunk post username *** [%s] ", splunk_post_username)
        splunk_post_password= all_settings["customized_settings"]["password"]["password"]
#        logger.info("************ splunk post password*** [%s] ", splunk_post_password)
        myUrl=all_settings["customized_settings"]["asrecovery_url"]["content"]
        host2=urlparse(myUrl).hostname
        port2=urlparse(myUrl).port
        # this function gets splunk server address as will be viewed from the appsymphony server by opening a socket to appsymphony but not actually sending anything
        splunk_server_address=([l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect((host2, port2)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0])
#        logger.info("************ splunk ip address as seen from appsym server should be *** [%s] ", splunk_server_address)

        #handle credentials the Splunk way
        currentPassword=self._handleCredentials(self.getSessionKey(),splunk_post_username,splunk_post_password)
        #will return a valid password or throw exception
#        logger.info("************password returned from handleCredentials *** [%s] ", currentPassword)
        # obfuscate the password stored the old way - this is for user display purposes only
        all_settings["customized_settings"]["password"]["password"] = "**********"

        # write global and proxy settings
        self._updateGlobalSettings(setup_const.global_settings, all_settings,
                all_origin_settings, ta_conf_file)
        # write customized settings
        customized_conf_file = get_or_create_conf_file(conf_mgr, setup_const.myta_customized_conf)
        self._updateConfStanzas(all_settings.get(setup_const.myta_customized_settings, {}), customized_conf_file, self.encrypt_fields_customized)
        logger.info("edit setup configure is done")

        logger.info("starting postrapidresponseappstosplunk call to AppSymphony")
        myUrl=all_settings["customized_settings"]["asrecovery_url"]["content"]
        if doit==1:
            logger.info("Get recovery apps checkbox is checked - requesting certificate and response apps from rapid response services")
            if urlparse(myUrl).scheme == "https":
                keytoolUrl = urlparse(myUrl).hostname
                logger.info("rapidresponse url is [%s] - requesting rapidresponse service certificate",myUrl)
                logger.info("rapidresponse hostname is [%s]",keytoolUrl)
                try:
                    certfile = open("../local/current_appsymcert.pem","w+")
                    cert = ssl.get_server_certificate((keytoolUrl, 8080))
                    certfile.write(str(cert))
                    certfile.close()
                    logger.info("Return from certificate request is [%s]",cert)
                    logger.info("Successfully retrieved https certificate from rapid response service")
                    verify_cert="../local/current_appsymcert.pem"
                except:
                    logger.error("Exception retrieving https certificate from rapid response service: [%s]",sys.exc_info()[0])
                    raise ValueError('Unable to retrieve rapid response certificate')
                    verify_cert=False
            else:
                logger.error("rapidresponse Service URL must be https")
                verify_cert=False
                raise ValueError('rapidresponse Service URL must be https')
            try:
                logger.info("AppSym URL is [%s] ",appSymUrl)
                logger.info("verify_cert is [%s] ",verify_cert)
                POSTdata=json.dumps({
                    'coordinate': 'com.optensity:rapidresponse-artifacts-applications-postAlertActionAppsToSplunk:3.2.6-RELEASE',
                    'name': 'postAlertActionAppsToSplunk',
                    'parameters': {'entry':[{'key':'splunkIndex','value': splunkIndex},{'key':'splunkHostIP','value':splunk_server_address},{'key':'splunkCredentials','value':(splunk_post_username+":"+currentPassword)}]}})
#                logger.info("AppSym POST data is [%s] ", POSTdata)
                dialog_return = requests.post(
                    url=appSymUrl,
                    data=json.dumps({
                        'coordinate': 'com.optensity:rapidresponse-artifacts-applications-postAlertActionAppsToSplunk:3.2.6-RELEASE',
                        'name': 'postAlertActionAppsToSplunk',
                        'parameters': {'entry':[{'key':'splunkIndex','value': splunkIndex},{'key':'splunkHostIP','value':splunk_server_address},{'key':'splunkCredentials','value':(splunk_post_username+":"+currentPassword)}]}
                        }),
                    headers={'Content-Type': 'application/json'},
                    verify=verify_cert)
                new_content=dialog_return.text
                post_status_code=dialog_return.status_code
                logger.info("postAlertActionApps status code is [%s] ",post_status_code)
                logger.info("postAlertActionApps response is [%s] ",new_content)
                dialog_return.raise_for_status()
            except OSError:
                logger.error("Connection Error exception retrieving response apps from rapid response service")
                raise ValueError('Unable to retrieve response apps')
        else:
            logger.info("Get recovery apps checkbox is unchecked - not requesting certificate or response apps from rapid response services")
            logger.info("completed call to postrapidresponseappstosplunk call to AppSymphony")

    def _updateGlobalSettings(self, stanza, all_settings,
                              all_origin_settings, conf_file):
        if not self.stanza_map[stanza]:
            return
        global_settings = all_settings.get(stanza, {})
        if self._configChanges(global_settings, all_origin_settings.get(stanza, {})):
            logger.info("global setting stanza [%s] changed", stanza)
            conf_file.update(stanza, global_settings, self.global_cred_fields)

    def _updateConfStanzas(self, all_settings, conf_file, encrypt_fields):
        all_origin_settings = conf_file.get_all()
        if not all_origin_settings:
            all_origin_settings = {}
        for stanza, settings in all_settings.iteritems():
            conf_file.update(stanza, settings, encrypt_fields)
        updated_stanzas = all_settings.keys()
        to_be_deleted_stanzas = [ s for s in all_origin_settings if s not in updated_stanzas ]
        for stanza in to_be_deleted_stanzas:
            conf_file.delete(stanza)

    def _handleCredentials(self,currentSessionKey,saved_username,saved_password):
        headers = {'Authorization': ('Splunk '+ currentSessionKey)}
        retrievedPassword='no password retrieved'
        # try to retrieve user creds from splunk realm
        try:
            r=requests.get("https://localhost:8089/services/authentication/users/"+saved_username+"?output_mode=json", headers=headers, verify=False)
        except requests.ConnectionError:
            logger.error("TA-rapidresponse setup encountered a connection error exception while connecting to authentication/user to verify [%s] ", saved_username)
            raise requests.ConnectionError('TA-rapidresponse Connection Error exception verifying Splunk username')
        # if user creds exist in splunk realm
        if r.status_code==200:
            # try to retrieve user creds from TA-rapidresponse realm
            try:
                r=requests.get("https://localhost:8089/servicesNS/nobody/TA-rapidresponse/storage/passwords/TA-rapidresponse:"+saved_username+":?output_mode=json", headers=headers, verify=False)
            except requests.ConnectionError:
                logger.error("TA-rapidresponse setup encountered a connection error exception while connecting to TA-rapidresponse/storage/passwords service ****** ")
                raise requests.ConnectionError('TA-rapidresponse Connection Error exception retrieving user credentials from TA-rapidresponse service')
            # if user creds exist in splunk realm, get the password
            if r.status_code==200:
                retrievedPassword=r.json()['entry'][0]['content']['clear_password']
                logger.info("TA-rapid response successfully retrieved existing creds for user [%s] ", saved_username)
            else:
                #create TA-rapidresponse user creds
                try:
                    r=requests.post('https://localhost:8089/servicesNS/nobody/TA-rapidresponse/storage/passwords?output_mode=json',headers=headers,verify=False,data={'name': saved_username,'password': saved_password,'realm': 'TA-rapidresponse'})
                    logger.info("TA-rapidreponse created new creds for user= [%s] in TA-rapidresponse realm ***", saved_username)
                    retrievedPassword=saved_password
                except requests.ConnectionError:
                    logger.error("TA-rapidresponse setup encountered a connection error while connecting to TA-rapidresponse/storage/passwords to create creds for user= [%s] in TA-rapidresponse realm ***", saved_username)
                    raise requests.ConnectionError('TA-rapidresponse Connection Error exception creating creds in TA-rapidresponse realm***')
        else:
            logger.info("TA-rapidresponse received a [%s] response code from authentication/users service - username [%s] may not exist", r.status_code,saved_username)
            raise ValueError('TA-rapidresponse - not a valid Splunk user')
        return retrievedPassword

    @staticmethod
    def _clearPasswords(settings, cred_fields):
        for k, val in settings.iteritems():
            if isinstance(val, dict):
                return ConfigApp._clearPasswords(val, cred_fields)
            elif isinstance(val, (str, unicode)):
                if k in cred_fields:
                    settings[k] = ""

    @staticmethod
    def _setNoneValues(stanza):
        for k, v in stanza.iteritems():
            if v is None:
                stanza[k] = ""

    @staticmethod
    def _configChanges(new_config, origin_config):
        for k, v in new_config.iteritems():
            if k in ConfigApp.cred_fields and v == "":
                continue
            if v != origin_config.get(k):
                return True
        return False


admin.init(ConfigApp, admin.CONTEXT_APP_ONLY)

