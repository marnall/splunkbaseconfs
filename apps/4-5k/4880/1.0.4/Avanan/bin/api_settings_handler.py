# See https://dev.splunk.com/enterprise/docs/developapps/setuppage/setupxmlexamples/
import splunk.admin as admin
import splunk.entity as en

from constants import (
    FIELD_CLIENT_ID, FIELD_CLIENT_SECRET, FIELD_POLLING_INTERVAL,
    OWNER, NAMESPACE, STANZA_NAME)
from utils import get_encrypted_value, store_encrypted_value


INPUT_STANZA_NAME = 'script://$SPLUNK_HOME/etc/apps/Avanan/bin/poll_avanan_api.py'


class ConfigApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addOptArg(FIELD_CLIENT_ID)
            self.supportedArgs.addOptArg(FIELD_CLIENT_SECRET)
            self.supportedArgs.addOptArg(FIELD_POLLING_INTERVAL)

    def handleList(self, confInfo):
        session_key = self.getSessionKey()
        client_id = get_encrypted_value(FIELD_CLIENT_ID, session_key)
        client_secret = get_encrypted_value(FIELD_CLIENT_SECRET, session_key)
        polling_interval_seconds = self.readConf('inputs')[INPUT_STANZA_NAME]['interval']
        confInfo[STANZA_NAME].append(
            FIELD_CLIENT_ID,
            client_id,
        )
        confInfo[STANZA_NAME].append(
            FIELD_CLIENT_SECRET,
            client_secret,
        )
        confInfo[STANZA_NAME].append(
            FIELD_POLLING_INTERVAL,
            polling_interval_seconds,
        )

    def handleEdit(self, confInfo):
        client_id = self.callerArgs.data[FIELD_CLIENT_ID][0]
        client_secret = self.callerArgs.data[FIELD_CLIENT_SECRET][0]
        polling_interval = self.callerArgs.data[FIELD_POLLING_INTERVAL][0]
        session_key = self.getSessionKey()
        store_encrypted_value(FIELD_CLIENT_ID, client_id, session_key)
        store_encrypted_value(FIELD_CLIENT_SECRET, client_secret, session_key)
        self.writeConf(
            'inputs',
            INPUT_STANZA_NAME,
            {'interval': polling_interval},
        )
        # Reload inputs config
        en.getEntity(
            'data/inputs/script',
            '_reload',
            owner=OWNER,
            namespace=NAMESPACE,
            sessionKey=session_key,
        )


admin.init(ConfigApp, admin.CONTEXT_NONE)
