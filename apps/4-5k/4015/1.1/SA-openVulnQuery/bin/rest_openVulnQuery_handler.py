import sys
from splunk import admin, entity
from splunklib.client import connect
import ovquery_consts as c

CONF_FILE = 'ovquery_settings'
APP_NAME = 'SA-openVulnQuery'
STANZA = 'ovquery_settings'

class OpenVulnQueryHandler(admin.MConfigHandler):
    valid_args = [
        c.ovquery_username,
        c.ovquery_password,
        c.ovquery_debug,
    ]

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in self.valid_args:
                self.supportedArgs.addOptArg(arg)

    def _decrypt_username_password(self, confDict):
        entities = entity.getEntities(
            ['admin', 'passwords'],
            namespace=APP_NAME,
            owner='nobody',
            sessionKey=self.getSessionKey()
        )
        for i, c in entities.items():
            return c['username'], c['clear_password']


    def handleList(self, confInfo):
        # reads settings from CONF_FILE except for username and password (which are decrypted from storage)
        confDict = self.readConf(CONF_FILE)
        if confDict is not None:
            try:
                username, password = self._decrypt_username_password(confDict)
            except:
                username = None
                password = None
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key in self.valid_args and val is None:
                        val = ''
                    if username and key == c.ovquery_username:
                        val = username
                    if password and key == c.ovquery_password:
                        val = len(password) * '*'

                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        edit_data = self.callerArgs.data
        for arg in self.valid_args:
            if edit_data.get(arg, None) and edit_data[arg][0] is None:
                edit_data[arg][0] = ""
        if ( edit_data.get(c.ovquery_username, None)
                 and edit_data.get(c.ovquery_password, None)
                 and edit_data[c.ovquery_password][0] != (len(edit_data[c.ovquery_password][0]) * '*')
           ):
            service = connect(host='localhost', port=8089, app=APP_NAME, token=self.getSessionKey())
            storage_passwords = service.storage_passwords
            #create the storage password, delete the old on first if it exists
            try:
                storage_password = storage_passwords.delete(edit_data[c.ovquery_username][0])
                storage_password = storage_passwords.create(edit_data[c.ovquery_password][0], edit_data[c.ovquery_username][0], APP_NAME)
            except:
                storage_password = storage_passwords.create(edit_data[c.ovquery_password][0], edit_data[c.ovquery_username][0], APP_NAME)
            edit_data[c.ovquery_password][0] = len(edit_data[c.ovquery_password][0]) * '*'

        self.writeConf(CONF_FILE, STANZA, edit_data)

# initialize the handler
admin.init(OpenVulnQueryHandler, admin.CONTEXT_NONE) 

