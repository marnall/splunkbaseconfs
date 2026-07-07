#!/usr/bin/env python

# It is in the public domain, so you can do what you like with it
# We referenced code written by Stephen C Phillipsv (http://scphillips.com)

import splunk.admin as admin
# import your required python modules
import splunk.rest
import json
from CMXRestAPIMAPImage import get_logger
import splunk.entity as entity
import datetime
import re
logger = get_logger('CMXSETUP')


class ConfigApp(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['RESTSERVER', 'RESTPORT', 'USERNAME', 'PASSWORD', 'ALLSSC', 'INDEX']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):

        conf_dict = self.readConf("cmximagemap")
        user_name = None
        password = None

        if None != conf_dict:

            '''
                Load password from the REST endpoint to be shown on Setup page.
            '''
            r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords?output_mode=json&search=CMX",
                                          self.getSessionKey(), method = 'GET')

            result_data = json.loads(r[1])

            if len(result_data["entry"]) > 0:
                for ele in result_data["entry"]:

                    if ele["content"]["realm"] == "CMX":
                        password = ele["content"]["clear_password"]
                        user_name = ele["content"]["username"]
                        break

        if None != conf_dict:
            for stanza, settings in conf_dict.items():
                for key, val in settings.items():

                    if key in ["PASSWORD"]:
                        val = password
                    elif key in ["USERNAME"]:
                        val = user_name

                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup screen, take updated parameters,
    normalize them, and save them somewhere
    '''

    def handleEdit(self, confInfo):

        if self.callerArgs.data['RESTSERVER'][0] is None:
            self.callerArgs.data['RESTSERVER'] = ''

        elif not re.match("^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$",
                        self.callerArgs.data['RESTSERVER'][0]) \
                and not re.match("^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$",
                        self.callerArgs.data['RESTSERVER'][0]):
            logger.exception("Invalid URL")
            raise Exception("Invalid URL")

        if self.callerArgs.data['USERNAME'][0] is None:
            self.callerArgs.data['USERNAME'] = ''
        elif not re.match("^[a-z0-9!@&-]+$", self.callerArgs.data['USERNAME'][0]):
            logger.exception("Invalid USERNAME")
            raise Exception("Invalid USERNAME")

        if self.callerArgs.data['PASSWORD'][0] is None:
            self.callerArgs.data['PASSWORD'] = ''
        elif not re.match("^[a-z0-9!@&-]{8}[a-z0-9!@&-]*$", self.callerArgs.data['PASSWORD'][0]):
            logger.exception("Invalid PASSWORD")
            raise Exception("Invalid PASSWORD")

        else:
            r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords?output_mode=json&search=CMX",
                                          self.getSessionKey(), method = 'GET')

            if 200 <= int(r[0]["status"]) <= 300:
                result_data = json.loads(r[1])
                user_name = ""

                if len(result_data["entry"]) > 0:
                    for ele in result_data["entry"]:
                        if ele["content"]["realm"] == "CMX":
                            user_name = ele["content"]["username"]
                            break

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
                realm = "CMX:" + user_name + ":"
                r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords/" + realm + "?output_mode=json",
                                              self.getSessionKey(), postargs = post_args, method = 'POST')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to update  password  for CMX App ")
                    raise Exception

            elif len(user_name) > 0 and user_name != self.callerArgs.data['USERNAME'][0]:
                realm = "CMX:" + user_name + ":"
                r = splunk.rest.simpleRequest(
                    "/servicesNS/nobody/CMX/storage/passwords/" + realm + "?output_mode=json", self.getSessionKey(),
                    method = 'DELETE')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to delete password  for CMX App ")
                    raise Exception

                post_args = {
                    "name": self.callerArgs.data['USERNAME'][0],
                    "password": self.callerArgs.data['PASSWORD'][0],
                    "realm": "TA-CMX"
                }
                r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords/?output_mode=json",
                                              self.getSessionKey(), postargs = post_args, method = 'POST')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to store  password  for CMX App ")
                    raise Exception

            else:

                post_args = {
                    "name": self.callerArgs.data['USERNAME'][0],
                    "password": self.callerArgs.data['PASSWORD'][0],
                    "realm": "CMX"
                }
                r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords/?output_mode=json",
                                              self.getSessionKey(), postargs = post_args, method = 'POST')

                if not (200 <= int(r[0]["status"]) <= 300):
                    logger.error("Unable to store  password  for CMX App ")
                    raise Exception

            '''
                Remove USERNAME and PASSWORD from custom configuration.
            '''
            del self.callerArgs.data['PASSWORD']
            del self.callerArgs.data['USERNAME']

        if self.callerArgs.data['RESTPORT'][0] is None:
            self.callerArgs.data['RESTPORT'] = ''

        elif not re.match("^[0-9]{1,4}[0-5]?$", self.callerArgs.data['RESTPORT'][0]):
            logger.exception("Invalid Port Number")
            raise Exception("Invalid Port Number")

        if self.callerArgs.data['INDEX'][0] is None:
            self.callerArgs.data['INDEX'] = ''
        elif not re.match("^[a-z0-9][a-z0-9_-]*$", self.callerArgs.data['INDEX'][0]):
            logger.exception("Invalid INDEX")
            raise Exception("Invalid INDEX")
        else:
            r = splunk.rest.simpleRequest(
                "/data/indexes?output_mode=json&search=" + self.callerArgs.data['INDEX'][0],
                self.getSessionKey(), method='GET')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.exception("Invalid INDEX defined")
                raise Exception("Invalid INDEX defined")
            else:
                result_index_search = json.loads(r[1])

                if len(result_index_search["entry"]) > 0 and result_index_search["entry"][0]["name"] == \
                        self.callerArgs.data['INDEX'][0]:
                    index = self.callerArgs.data['INDEX'][0]
                else:
                    logger.exception("Invalid INDEX defined")
                    raise Exception("Invalid INDEX defined")

            definition = ("(index = " + self.callerArgs.data['INDEX'][0] + ")")

            inputdata = {"definition": definition}

            self.writeConf("macros", "cmx_index", inputdata)

        self.writeConf('cmximagemap', 'imagemapentity', self.callerArgs.data)

        inputdata = entity.getEntities('data/inputs/script', namespace = "CMX", search = "CMXRestAPIMAPImage.py",
                                       sessionKey = self.getSessionKey(), owner = 'nobody')

        if inputdata:

            current_min = datetime.datetime.now().minute
            minutes = (current_min + 2) % 60

            map_cron = str(minutes) + " * * * *"

            r = splunk.rest.simpleRequest(
                "/servicesNS/nobody/CMX/data/inputs/script/%24SPLUNK_HOME%252Fetc%252Fapps%252FCMX%252Fbin%252FCMXRestAPIMAPImage.py",
                self.getSessionKey(), postargs = {"interval": map_cron, "disabled": 0}, method = 'POST')

            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to delete CMXRestAPIMAPImage ")
                raise Exception

    def handleReload(self, confInfo = None):
        """
        Handles refresh/reload of the configuration options
        """


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
