import os
import sys

import splunk.admin as admin
from constants import (ADDRESS_FIELD, PORT_FIELD, LIMIT_FIELD, LICENSE_FIELD,
                       CONFIGURATION_NAME, CONFIGURATION_STANZA, REALM)
from utils import string

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "lib"))
import splunklib.client as client


class SonarConfigurationHandler(admin.MConfigHandler):
    handledActions = [admin.ACTION_LIST, admin.ACTION_EDIT]
    conf_fields = [ADDRESS_FIELD, PORT_FIELD, LIMIT_FIELD]
    secret_fields = [LICENSE_FIELD]

    def setup(self):
        if self.requestedAction not in self.handledActions:
            raise admin.BadActionException(
                "This handler does not support this action (%d)." % self.requestedAction)

        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.conf_fields + self.secret_fields:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        for field in self.secret_fields:
            value = self.get_secret_field(field)
            confInfo[CONFIGURATION_STANZA].append(field, value if value is not None else '')

        settings = self.get_conf_stanza_settings()
        if not settings:
            return

        for field in self.conf_fields:
            value = settings[field] if settings[field] is not None else ''
            confInfo[CONFIGURATION_STANZA].append(field, value)

    def get_conf_stanza_settings(self):
        conf_dict = self.readConf(CONFIGURATION_NAME)
        if not conf_dict:
            return

        return conf_dict[CONFIGURATION_STANZA]

    def handleEdit(self, confInfo):
        for field in self.secret_fields:
            value = self.callerArgs.data[field][0] if self.callerArgs.data[field][0] is not None else ''
            self.save_secret_field(field, value)

        stanza_settings = {}
        for field in self.conf_fields:
            value = self.callerArgs.data[field][0] if self.callerArgs.data[field][0] is not None else ''
            stanza_settings[field] = value

        self.writeConf(CONFIGURATION_NAME, CONFIGURATION_STANZA, stanza_settings)

    def get_secret_field(self, field):
        if SonarConfigurationHandler.is_blank_string(field):
            return ''

        splunk_service = client.connect(token=self.getSessionKey(), app=self.appName)
        password_storage = splunk_service.storage_passwords

        for credential in password_storage:
            if credential.username == field and credential.realm == REALM:
                return credential.clear_password

        return ''

    def save_secret_field(self, field, value):
        splunk_service = client.connect(token=self.getSessionKey(), app=self.appName)
        password_storage = splunk_service.storage_passwords

        for credential in password_storage:
            if credential.username == field and credential.realm == REALM:
                if SonarConfigurationHandler.is_blank_string(value):
                    credential.delete()
                    return None

                return credential.update(password=value).refresh()

        if SonarConfigurationHandler.is_blank_string(value):
            return None

        return password_storage.create(value, field, REALM)

    @staticmethod
    def is_blank_string(value):
        return not (value and isinstance(value, string) and value.strip())


# initialize the handler
admin.init(SonarConfigurationHandler, admin.CONTEXT_NONE)
