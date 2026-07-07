import re
from time import sleep
from contextlib import suppress

from errors import (
    NotSupportedAction,
    ConnectorAlreadyLaunched,
    DeviceAlreadyExists,
    ConnectorNotFound
)
from constants import CONFIG_PORT_REGEX


def write_new_port_to_config(conf_file, port):
    with open(conf_file, 'rt') as file:
        config = file.read()

    if config:
        with open(conf_file, 'wt') as file:
            old_port = re.findall(CONFIG_PORT_REGEX, config)
            if old_port != port:
                file.write(config.replace(old_port[0], port))


class SSEConnectorClient:

    def __init__(self, data, api_client_instance, shell_client_instance):
        self.action = data.get('action')
        self.port = data.get('sse_connector_port')
        self.token = data.get('activation_token')
        self.api = api_client_instance
        self.shell = shell_client_instance

    def run_action(self):
        supported_commands = {
            'start': self.start,
            'stop': self.stop,
            'deregister': self.deregister
        }
        if self.action in supported_commands:
            supported_commands[self.action]()
        else:
            raise NotSupportedAction(self.action, supported_commands.keys())

    def start(self):
        if self.api.check_connection():
            raise ConnectorAlreadyLaunched
        write_new_port_to_config(
            self.shell.get_connector_config_file(), self.port
        )
        self.shell.run_connector()
        sleep(5)
        try:
            self.api.create_context()
        except DeviceAlreadyExists:
            pass
        else:
            self.api.activate(self.token)

    def stop(self):
        if not self.api.check_connection():
            raise ConnectorNotFound
        with suppress(ConnectorNotFound):
            self.api.shutdown()

    def deregister(self):
        if not self.api.check_connection():
            raise ConnectorNotFound
        self.api.remove_context()
        sleep(5)
        with suppress(ConnectorNotFound):
            self.api.reset()
