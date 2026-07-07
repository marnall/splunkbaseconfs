from logging import getLogger
from http import HTTPStatus

from splunktaucclib.rest_handler.handler import RestHandler, RestError
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from solnlib.splunkenv import get_splunkd_uri

from shell_client import ConnectorShellClient, UnixShellCommand
from api_client import ConnectorApiClient
from sse_connector_client import SSEConnectorClient
from errors import (
    ShellError,
    ConnectorClientError,
    ApiClientError
)

logger = getLogger()


class SSERestHandler(RestHandler):
    """ Checks input settings for connection to CTR on save. """

    def __init__(self, splunkd_uri, session_key, endpoint, *args, **kwargs):
        super(
            SSERestHandler, self
        ).__init__(splunkd_uri, session_key, endpoint, *args, **kwargs)

    def start_connector(self, data):
        api_client = ConnectorApiClient(
            data['sse_connector_port'],
            self._client.port,
            self._client.host,
            data['region']
        )
        shell_client = ConnectorShellClient(UnixShellCommand)
        client = SSEConnectorClient(data, api_client, shell_client)

        try:
            client.run_action()
        except ShellError as err:
            raise RestError(
                int(HTTPStatus.INTERNAL_SERVER_ERROR),
                err.message
            )
        except ConnectorClientError as err:
            raise RestError(
                int(HTTPStatus.BAD_REQUEST),
                err.message
            )
        except ApiClientError as err:
            raise RestError(
                int(err.status_code),
                err.message
            )
        except Exception as err:
            raise RestError(
                int(HTTPStatus.INTERNAL_SERVER_ERROR),
                str(err)
            )

    def update(self, name, data):
        self.start_connector(data)
        return super(SSERestHandler, self).update(name, data)

    def create(self, name, data):
        self.start_connector(data)
        return super(SSERestHandler, self).create(name, data)


class SSEConfigMigrationHandler(ConfigMigrationHandler):
    def __init__(self, *args, **kwargs):
        super(SSEConfigMigrationHandler, self).__init__(*args, **kwargs)

        self.handler = SSERestHandler(
            get_splunkd_uri(),
            self.getSessionKey(),
            self.endpoint,
        )
