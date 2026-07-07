# !/usr/bin/env python

import splunk.admin as admin
# import your required python modules
import splunk.entity as entity
import splunk.rest
import re
from CMXUtil import *
import platform

logger = get_logger("CMXSETUP")


class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['HTTPECKEY', 'HTTPECPORT', 'RESTSERVER', 'RESTPORT', 'HTTPSPEC', 'SSL', 'NOOFTHREADS',
                        'USERNAME', 'PASSWORD', 'INDEX', 'ALLSSC']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):

        conf_dict = self.readConf("cmxsetup")
        if conf_dict:
            '''
                Load password from the REST endpoint to be shown on Setup page.
            '''

            user_name, password = get_credentials(self.getSessionKey())
            http_ec_token = get_hec_credentials(self.getSessionKey())

            for stanza, settings in conf_dict.items():
                for key, val in settings.items():

                    if key in ["PASSWORD"]:
                        val = password

                    elif key in ["USERNAME"]:
                        val = user_name

                    elif key in ["HTTPECKEY"]:
                        val = http_ec_token

                    confInfo[stanza].append(key, val)

    '''
        If user changes index, we need to delete the existing scripted input.
    '''

    def check_entity_exist(self, script_name):

        inputdata = entity.getEntities('data/inputs/script', namespace = "TA-CMX", search = script_name,
                                       sessionKey = self.getSessionKey(), owner = 'nobody')


        return inputdata

    '''
        Create New Scripted inputs.
    '''

    def create_new_scripted_inputs(self, data):

        inputdata = entity.getEntity('data/inputs/script', '_new', sessionKey = self.getSessionKey())

        inputdata[
            "name"] = '$SPLUNK_HOME\\etc\\apps\\TA-CMX\\bin\\Server.py' \
            if platform.system().lower() == 'windows' else '$SPLUNK_HOME/etc/apps/TA-CMX/bin/Server.py'

        inputdata["interval"] = ["0"]
        inputdata["disabled"] = ["false"]
        inputdata["passAuth"] = ["splunk-system-user"]
        inputdata.namespace = "TA-CMX"
        entity.setEntity(inputdata, sessionKey = self.getSessionKey())

        index = data["INDEX"][0] if data["INDEX"] else "main"

        inputdata = entity.getEntity('data/inputs/script', '_new', sessionKey = self.getSessionKey())
        inputdata[
            "name"] = '$SPLUNK_HOME\\etc\\apps\\TA-CMX\\bin\\CMXRestAPIMAP.py' \
            if platform.system().lower() == 'windows' else '$SPLUNK_HOME/etc/apps/TA-CMX/bin/CMXRestAPIMAP.py'
        inputdata["interval"] = ["86400"]
        inputdata["disabled"] = ["false"]
        inputdata["index"] = [index]
        inputdata["sourcetype"] = ["cmxmap"]
        inputdata["passAuth"] = ["splunk-system-user"]
        inputdata.namespace = "TA-CMX"
        entity.setEntity(inputdata, sessionKey = self.getSessionKey())

        inputdata = entity.getEntity('data/inputs/script', '_new', sessionKey = self.getSessionKey())
        inputdata[
            "name"] = '$SPLUNK_HOME\\etc\\apps\\TA-CMX\\bin\\CMXRestAPIAnalytics.py' \
            if platform.system().lower() == 'windows' else '$SPLUNK_HOME/etc/apps/TA-CMX/bin/CMXRestAPIAnalytics.py'
        inputdata["interval"] = ["540"]
        inputdata["disabled"] = ["false"]
        inputdata["index"] = [index]
        inputdata["sourcetype"] = ["cmxanalytics"]
        inputdata["passAuth"] = ["splunk-system-user"]
        inputdata.namespace = "TA-CMX"
        entity.setEntity(inputdata, sessionKey = self.getSessionKey())

        inputdata = entity.getEntity('data/inputs/script', '_new', sessionKey = self.getSessionKey())
        inputdata[
            "name"] = '$SPLUNK_HOME\\etc\\apps\\TA-CMX\\bin\\CMXRestAPIActive.py' \
            if platform.system().lower() == 'windows' else '$SPLUNK_HOME/etc/apps/TA-CMX/bin/CMXRestAPIActive.py'
        inputdata["interval"] = ["960"]
        inputdata["disabled"] = ["false"]
        inputdata["index"] = [index]
        inputdata["sourcetype"] = ["cmxactive"]
        inputdata["passAuth"] = ["splunk-system-user"]
        inputdata.namespace = "TA-CMX"
        entity.setEntity(inputdata, sessionKey = self.getSessionKey())


    '''
        Update index in existing scripted input
    '''

    def update_scripted_inputs(self, data):

        inputdata = entity.getEntities('data/inputs/script', namespace = "TA-CMX",
                                       search = "$SPLUNK_HOME/etc/apps/TA-CMX/bin/CMXRestAPIActive.py",
                                       sessionKey = self.getSessionKey(), owner = 'nobody')

        if inputdata:

            self.deleteEntity('Server.py')

            self.deleteEntity('CMXRestAPIMAP.py')

            self.deleteEntity('CMXRestAPIAnalytics.py')

            self.deleteEntity('CMXRestAPIActive.py')

        else:
            self.delete_scripted_inputs()

        self.create_new_scripted_inputs(data)

    '''
        To delete existing scirpted input.
    '''

    def deleteEntity(self, script_name):
        inputdata = entity.getEntities('data/inputs/script', namespace = "TA-CMX", search = script_name,
                                       sessionKey = self.getSessionKey(), owner = 'nobody')

        if inputdata:
            entity.deleteEntity('data/inputs/script', inputdata.keys()[0], namespace = "TA-CMX",
                                sessionKey = self.getSessionKey(), owner = 'nobody')

    '''
        Delete existing scripted inputs
    '''

    def delete_scripted_inputs(self):

        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-CMX/data/inputs/script/.%252Fbin%252FCMXRestAPIMAP.py?output_mode=json",
            self.getSessionKey(),
            method = 'DELETE')
        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to delete CMXRestAPIMAP ")
            raise Exception

        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-CMX/data/inputs/script/.%252Fbin%252FCMXRestAPIActive.py?output_mode=json",
            self.getSessionKey(),
            method = 'DELETE')
        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to delete CMXRestAPIActive ")
            raise Exception

        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-CMX/data/inputs/script/.%252Fbin%252FCMXRestAPIAnalytics.py?output_mode=json",
            self.getSessionKey(),
            method = 'DELETE')
        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to delete CMXRestAPIAnalytics ")
            raise Exception

        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-CMX/data/inputs/script/.%252Fbin%252FServer.py?output_mode=json",
            self.getSessionKey(),
            method = 'DELETE')
        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to delete CMXRestAPIMAP ")
            raise Exception

    '''
        Store HEC token with storage/password REST endpoint
    '''

    def store_hec_token(self, hec_token):
        password = get_hec_credentials(self.getSessionKey())
        user_name = "hec-token"

        if not (not password):

            postArgs = {
                "password": hec_token
            }

            realm = "TA-CMX-HEC:" + user_name + ":"
            splunk.rest.simpleRequest(
                "/servicesNS/nobody/" + self.appName + "/storage/passwords/" + realm + "?output_mode=json",
                self.getSessionKey(), postargs = postArgs, method = 'POST')

        else:
            postArgs = {
                "name": user_name,
                "password": hec_token,
                "realm": "TA-CMX-HEC"
            }
            r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords/?output_mode=json",
                                          self.getSessionKey(), postargs = postArgs, method = 'POST')
            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to create  password for HEC")

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''

    def handleEdit(self, confInfo):

        '''
            Load current configuration file data from REST endpoint.
        '''

        conf_dict = get_cmx_conf(self.getSessionKey())

        enable_ssl_for_http(self.getSessionKey())

        if not re.match("^[0-9]{1,4}[0-5]?$", self.callerArgs.data['HTTPECPORT'][0]):
            logger.exception("Invalid Event Collection Port Number")
            raise Exception("Invalid Event Collection Port Number")

        if not re.match("^[0-9]{1,4}[0-5]?$", self.callerArgs.data['HTTPSPEC'][0]):
            logger.exception("Invalid Splunk EC Port Number")
            raise Exception("Invalid Splunk EC Port Number")

        if not conf_dict["HTTPSPEC"] or int(conf_dict["HTTPSPEC"]) != int(self.callerArgs.data['HTTPSPEC'][0]):
            self.update_http_event_collector_settings(self.getSessionKey())

        '''
            If user doesn't provide HTTP Event Collection Key, generate new one
        '''
        http_ec_token = get_hec_credentials(self.getSessionKey())

        if not conf_dict["HTTPECKEY"]:
            self.store_hec_token(self.get_auth_token())
        elif conf_dict["HTTPECKEY"] and not http_ec_token:
            self.store_hec_token(conf_dict["HTTPECKEY"])

        if self.callerArgs.data['RESTSERVER'][0] is None:
            self.callerArgs.data['RESTSERVER'] = ''

        elif not re.match("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",
                        self.callerArgs.data['RESTSERVER'][0]) \
                and not re.match("^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$",
                        self.callerArgs.data['RESTSERVER'][0]):
            logger.exception("Invalid URL")
            raise Exception("Invalid URL")

        if self.callerArgs.data['RESTPORT'][0] is None:
            self.callerArgs.data['RESTPORT'] = ''
        elif not re.match("^[0-9]{1,4}[0-5]?$", self.callerArgs.data['RESTPORT'][0]):
            logger.exception("Invalid Port Number")
            raise Exception("Invalid Port Number")

        if self.callerArgs.data['USERNAME'][0] is None:
            self.callerArgs.data['USERNAME'] = ''

        index = "main"

        if self.callerArgs.data['INDEX'][0] is None:
            self.callerArgs.data['INDEX'] = ''
        else:
            index = self.callerArgs.data['INDEX'][0]

        if self.callerArgs.data['PASSWORD'][0] is None:
            self.callerArgs.data['PASSWORD'] = ''

        else:
            user_name, password = get_credentials(self.getSessionKey())

            '''
            Store password into passwords.conf file. Following are different scenarios
            1. Enters credentials for first time, use REST call to store it in passwords.conf
            2. Updates password. Use REST call to update existing password.
            3. Upadates Username. Delete existing User entry and insert new entry.
            '''
            if len(user_name) > 0 and user_name == self.callerArgs.data['USERNAME'][0]:
                post_args = {
                    "password": self.callerArgs.data['PASSWORD'][0]
                }
                realm = "TA-CMX:" + user_name + ":"
                r = splunk.rest.simpleRequest(
                    "/servicesNS/nobody/TA-CMX/storage/passwords/" + realm + "?output_mode=json", self.getSessionKey(),
                    postargs = post_args, method = 'POST')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to update password")

            elif len(user_name) > 0 and user_name != self.callerArgs.data['USERNAME'][0]:
                realm = "TA-CMX:" + user_name + ":"
                r = splunk.rest.simpleRequest(
                    "/servicesNS/nobody/TA-CMX/storage/passwords/" + realm + "?output_mode=json", self.getSessionKey(),
                    method = 'DELETE')
                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to delete password")
                else:
                    post_args = {
                        "name": self.callerArgs.data['USERNAME'][0],
                        "password": self.callerArgs.data['PASSWORD'][0],
                        "realm": "TA-CMX"
                    }
                    r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords/?output_mode=json",
                                                  self.getSessionKey(), postargs = post_args, method = 'POST')
                    if not (200 <= int(r[0]["status"]) <= 300):
                        logger.error("Unable to create new password")
            else:
                post_args = {
                    "name": self.callerArgs.data['USERNAME'][0],
                    "password": self.callerArgs.data['PASSWORD'][0],
                    "realm": "TA-CMX"
                }
                r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords/?output_mode=json",
                                              self.getSessionKey(), postargs = post_args, method = 'POST')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to create new password")

            '''
                Remove USERNAME and PASSWORD from custom configuration.
            '''
            del self.callerArgs.data['PASSWORD']
            del self.callerArgs.data['USERNAME']
            del self.callerArgs.data['HTTPECKEY']

        '''
            This code is required only in case of Upgrade scenario
        '''

        if self.check_entity_exist('CMXRestAPIActive.py') and (not conf_dict["INDEX"] or conf_dict["INDEX"] != index):
            self.update_scripted_inputs(self.callerArgs.data)
        elif not conf_dict["INDEX"] and not self.check_entity_exist('Server.py'):
            self.create_new_scripted_inputs(self.callerArgs.data)

        '''
            Remove  if scripts are already configured.
        '''

        self.writeConf('cmxsetup', 'setupentity', self.callerArgs.data)

    '''
        This method is used to update HTTP Event Collector port.
    '''

    def update_http_event_collector_settings(self, session_key):
        post_args = {
            "enableSSL": self.callerArgs.data['SSL'],
            "port": self.callerArgs.data['HTTPSPEC']
        }
        r = splunk.rest.simpleRequest("/servicesNS/admin/splunk_httpinput/data/inputs/http/http/", self.getSessionKey(),
                                      postargs = post_args, method = 'POST')

        if 200 <= int(r[0]["status"]) <= 300:
            r = splunk.rest.simpleRequest("/servicesNS/admin/splunk_httpinput/data/inputs/http/http/enable",
                                          self.getSessionKey(), method = 'POST')
            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to enable HTTP Event Collector ")
        else:
            logger.error("Unable to set HTTP Event Collector settings")

    '''
        This method is used to create new HTTP Event Collector token if none is provided.
    '''

    def get_auth_token(self):
        try:
            r = splunk.rest.simpleRequest("/servicesNS/admin/splunk_httpinput/data/inputs/http/cmxtoken/enable",
                                          self.getSessionKey(), method = 'POST')

        except:
            postargs = {'name': 'cmxtoken', 'description': 'Token created for HTTP event collection by TA-CMX'}
            r = splunk.rest.simpleRequest("/servicesNS/admin/splunk_httpinput/data/inputs/http", self.getSessionKey(),
                                          method = 'POST', postargs = postargs)


        p = re.compile('<s:key name="token">(.*)<\/s:key>')
        auth_key = p.findall(str(r))
        return auth_key[0]

    def handleReload(self, confInfo = None):
        """
        Handles refresh/reload of the configuration options
        """

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
