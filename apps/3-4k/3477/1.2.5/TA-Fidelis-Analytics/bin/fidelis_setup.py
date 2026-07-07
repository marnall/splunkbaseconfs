#!/usr/bin/env python

import json
import platform
import re

import splunk.admin as admin
import splunk.rest
import splunk.entity as entity

from fidelis_utility import get_logger, get_credentials, get_fidelis_conf, is_app_configured


logger = get_logger("FIDELIS_SETUP")


class ConfigApp(admin.MConfigHandler):
    def get_input(self):
        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-Fidelis-Analytics/data/inputs/all?search=fidelis:xps&output_mode=json",
            self.getSessionKey(), method = 'GET')

        dict = json.loads(r[1])
        port = ""
        protocol = ""
        if len(dict["entry"]) > 0:
            for ele in dict["entry"]:
                if ele["content"]["sourcetype"] == "fidelis:xps":
                    port = ele["name"]
                    protocol = "TCP" if ele["content"]["eai:type"] == "raw" else ele["content"]["eai:type"].upper()
                    break
        return port, protocol

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['ECPORT', 'USERNAME', 'PASSWORD', 'RESTSERVER', 'INPUT_CONFIG', 'INDEX',
                        'ALLOW_SSL', 'SSL_CERT_LOC']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):

        conf_dict = self.readConf("fidelissetup")

        password, user_name = get_credentials(self.getSessionKey(), "FIDELIS_SETUP")

        for stanza, settings in conf_dict.items():
            for key, val in settings.items():
                confInfo[stanza].append(key, val)

            port, protocol = self.get_input()

            confInfo[stanza].append("ECPORT", port)
            confInfo[stanza].append("USERNAME", user_name)
            confInfo[stanza].append("PASSWORD", password)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''

    def handleEdit(self, confInfo):
        conf_dict = get_fidelis_conf(self.getSessionKey())

        if self.callerArgs.data['RESTSERVER'][0] is None:
            self.callerArgs.data['RESTSERVER'] = ''

        elif not re.match('https:\/\/', self.callerArgs.data["RESTSERVER"][0]):
            logger.exception("Invalid URL")
            raise Exception("Invalid URL")

        if self.callerArgs.data['SSL_CERT_LOC'][0] is None:
            self.callerArgs.data['SSL_CERT_LOC'] = ''

        if self.callerArgs.data['ECPORT'][0] is None:
            self.callerArgs.data['ECPORT'] = ''
        elif not re.match("^[0-9]{1,4}[0-5]?$", self.callerArgs.data['ECPORT'][0]):
            logger.exception("Invalid Port Number")
            raise Exception("Invalid Port Number")

        if self.callerArgs.data['INPUT_CONFIG'][0] is None:
            input_config = False
        else:
            input_config = bool(int(self.callerArgs.data['INPUT_CONFIG'][0]))

        index = "main"
        if self.callerArgs.data['INDEX'][0] is None:
            self.callerArgs.data['INDEX'] = ''
        else:
            logger.info("Validate index")
            r = splunk.rest.simpleRequest(
                "/data/indexes?output_mode=json&search="+self.callerArgs.data['INDEX'][0],
                self.getSessionKey(), method = 'GET')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.exception("Invalid index defined")
                raise Exception
            else:
                result_index_search = json.loads(r[1])

                if len(result_index_search["entry"]) >0 and result_index_search["entry"][0]["name"] == self.callerArgs.data['INDEX'][0]:
                    index = self.callerArgs.data['INDEX'][0]
                else:
                    logger.exception("Invalid index defined")
                    raise Exception

        password, user_name = get_credentials(self.getSessionKey(), "FIDELIS_SETUP")
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
            realm = "TA-Fidelis-Analytics:" + user_name + ":"
            r = splunk.rest.simpleRequest(
                "/servicesNS/nobody/TA-Fidelis-Analytics/storage/passwords/" + realm + "?output_mode=json",
                self.getSessionKey(), postargs = post_args, method = 'POST')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to update password")
                raise Exception

        elif len(user_name) > 0 and user_name != self.callerArgs.data['USERNAME'][0]:
            realm = "TA-Fidelis-Analytics:" + user_name + ":"
            r = splunk.rest.simpleRequest(
                "/servicesNS/nobody/TA-Fidelis-Analytics/storage/passwords/" + realm + "?output_mode=json",
                self.getSessionKey(), method = 'DELETE')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to delete password")
                raise Exception

            post_args = {
                "name": self.callerArgs.data['USERNAME'][0],
                "password": self.callerArgs.data['PASSWORD'][0],
                "realm": "TA-Fidelis-Analytics"
            }
            r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-Fidelis-Analytics/storage/passwords/?output_mode=json",
                                          self.getSessionKey(), postargs = post_args, method = 'POST')
            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to create new password")
                raise Exception

        else:
            post_args = {
                "name": self.callerArgs.data['USERNAME'][0],
                "password": self.callerArgs.data['PASSWORD'][0],
                "realm": "TA-Fidelis-Analytics"
            }
            r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-Fidelis-Analytics/storage/passwords/?output_mode=json",
                                          self.getSessionKey(), postargs = post_args, method = 'POST')
            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to create new password ")
                raise Exception
        '''
            Remove USERNAME and PASSWORD from custom configuration.
        '''
        del self.callerArgs.data['PASSWORD']
        del self.callerArgs.data['USERNAME']
        configured = is_app_configured(self.getSessionKey(), "TA-Fidelis-Analytics")

        if not conf_dict.get('INDEX') and input_config and not configured:
            self.delete_raw_input()
            self.create_input(index, "tcp")

        elif not conf_dict.get('INDEX') and input_config and configured:
            self.delete_raw_input()
            self.delete_script_input()
            self.create_script_input(index)
            self.create_input(index, "tcp")

        elif conf_dict.get('INDEX') and conf_dict.get('INDEX') != index:
            self.delete_raw_input()
            self.delete_script_input()
            self.create_script_input(index)
            self.create_input(index, "tcp")

        elif ((conf_dict.get('ECPORT') and int(conf_dict.get('ECPORT')) != int(self.callerArgs.data["ECPORT"][0]))):
            self.delete_raw_input()
            self.delete_script_input()
            self.create_script_input(index)
            self.create_input(index, "tcp")

        if not configured:
            self.create_script_input(index)
        else:
            self.delete_script_input()
            self.create_script_input(index)

        if conf_dict.get('INDEX') != index:
            defination = ("(index = " + index + " sourcetype=\"fidelis:xps\")")

            inputdata = {"definition": defination}

            self.writeConf("macros", "fidelis_get_xps_event", inputdata)

            defination = ("(index = " + index + " sourcetype=\"fidelis:xps:api\")")

            inputdata = {"definition": defination}

            self.writeConf("macros", "fidelis_get_alert_events", inputdata)

        self.writeConf('fidelissetup', 'setupentity', self.callerArgs.data)

    def create_script_input(self, index):
        inputdata = entity.getEntity('data/inputs/script', '_new', sessionKey = self.getSessionKey())
        inputdata[
            "name"] = '$SPLUNK_HOME\\etc\\apps\\TA-Fidelis-Analytics\\bin\\fidelis_api.py' \
            if platform.system().lower() == 'windows' else '$SPLUNK_HOME/etc/apps/TA-Fidelis-Analytics/bin/fidelis_api.py'

        inputdata["index"] = [index]
        inputdata["sourcetype"] = ["fidelis:xps:api"]
        inputdata["interval"] = ["600"]
        inputdata["source"] = ["RESTAPI"]
        inputdata["disabled"] = ["false"]
        inputdata["passAuth"] = ["splunk-system-user"]
        inputdata.namespace = "TA-Fidelis-Analytics"
        entity.setEntity(inputdata, sessionKey = self.getSessionKey())

    def create_input(self, index, protocol = "tcp"):

        inputdata = {}
        inputdata["index"] = [index]
        inputdata["sourcetype"] = ["fidelis:xps"]
        inputdata["source"] = ["fidelis"]
        inputdata["connection_host"] = ["ip"]
        inputdata["disabled"] = ["false"]
        stanza = protocol + '://' + self.callerArgs.data['ECPORT'][0]
        inputdata["name"] = stanza

        r = splunk.rest.simpleRequest(
            "/servicesNS/nobody/TA-Fidelis-Analytics/configs/conf-inputs",
            self.getSessionKey(), postargs = inputdata, method = 'POST')

        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to delete CMXRestAPIMAPImage ")
            raise Exception


        r = splunk.rest.simpleRequest(
                "/admin/raw/_reload",
                self.getSessionKey(), method = 'POST')

        if not (200 <= int(r[0]["status"]) <= 300):
            logger.error("Unable to reload TCP endpoint ")
            raise Exception


                # self.writeConf('inputs', stanza, inputdata)

    def delete_raw_input(self):
        port, protocol = self.get_input()

        if port and protocol:
            path = "/servicesNS/nobody/TA-Fidelis-Analytics/data/inputs/" + protocol.lower() + \
                   "/raw/" + port if protocol == "TCP" \
                else "/servicesNS/nobody/TA-Fidelis-Analytics/data/inputs/" + protocol.lower() + "/" + port

            r = splunk.rest.simpleRequest(path, self.getSessionKey(), method = 'DELETE')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to delete Raw input ")
                raise Exception

    def delete_script_input(self):
        inputdata = entity.getEntities('data/inputs/script', namespace = "TA-Fidelis-Analytics", search = "fidelis_api",
                                       sessionKey = self.getSessionKey(), owner = 'nobody')

        if inputdata:
            entity.deleteEntity('data/inputs/script', inputdata.keys()[0], namespace = "TA-Fidelis-Analytics",
                                sessionKey = self.getSessionKey(), owner = 'nobody')


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
