from logging import getLogger

from splunklib import client
from splunktaucclib.rest_handler.handler import RestHandler, RestError
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from solnlib.splunkenv import get_splunkd_uri

from connect import connect, ConnectError
from settings import Settings, CONFIGURATION_FILE, STANZA
from constants import ADDON_NAME

logger = getLogger()


class ConnectRestHandler(RestHandler):
    """ Checks input settings for connection to CTR on save. """

    def __init__(self, splunkd_uri, session_key, endpoint, *args, **kwargs):
        super(
            ConnectRestHandler, self
        ).__init__(splunkd_uri, session_key, endpoint, *args, **kwargs)

    def check_connection(self, data):
        settings = Settings(data, self._client.storage_passwords)
        try:
            connect(settings, logger)
        except ConnectError as error:
            raise RestError(400, str(error))

    def check_index(self):
        """
        Connect to Splunk instance and
        Check the index of exist.
        """
        conn = client.connect(
            token=self._session_key,
            app=ADDON_NAME,
            port=self._client.port
        )
        index_name = \
            self._client \
                .confs[CONFIGURATION_FILE][STANZA]['index_name']
        if index_name not in conn.indexes:
            message = "A '{index}' index does not exist. " \
                      "Please go to Manage Indexes " \
                      "and create the index." \
                .format(index=index_name)
            raise RestError(400, message)

    def update(self, name, data):
        self.check_connection(data)
        self.check_index()
        return super(ConnectRestHandler, self).update(name, data)

    def create(self, name, data):
        self.check_connection(data)
        self.check_index()
        return super(ConnectRestHandler, self).create(name, data)


class ConnectConfigMigrationHandler(ConfigMigrationHandler):
    def __init__(self, *args, **kwargs):
        super(ConnectConfigMigrationHandler, self).__init__(*args, **kwargs)

        self.handler = ConnectRestHandler(
            get_splunkd_uri(),
            self.getSessionKey(),
            self.endpoint,
        )
