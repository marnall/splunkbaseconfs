import os
import shlex
from subprocess import Popen, DEVNULL
from abc import ABC

import toml

from constants import (
    SSE_CONNECTOR_FOLDER,
    SSE_CONNECTOR_CONFIG_FOLDER,
    SSE_CONNECTOR_CONFIG_FILE,
    SSE_CONNECTOR_FILE,
    SSE_CONNECTOR_RUNNING_COMMAND,
    SSE_CONNECTOR_CONF_ARG,
    SSE_CONNECTOR_ROOT_CERT_FILE,
    SSE_CONNECTOR_CERT_FOLDER,
    SSE_CONNECTOR_DATA_FOLDER,
    APP_FOLDER_NAME,
)
from errors import ShellError


class ShellCommand(ABC):
    separator = ' '

    def _join(self, *args):
        return self.separator.join(*args)

    @staticmethod
    def get_folder_path():
        return os.path.join(
            os.environ['SPLUNK_HOME'], 'etc', 'apps', APP_FOLDER_NAME, 'bin'
        )

    def get_path(self, name, folders=None):
        app_folder_path = self.get_folder_path()
        if not folders:
            file_path = self._join([app_folder_path, name])
        else:
            file_path = self._join([app_folder_path, *folders, name])
        return file_path

    def add_command(self, command):
        return NotImplemented

    def run(self, *args):
        return NotImplemented


class UnixShellCommand(ShellCommand):
    separator = '/'

    def __init__(self):
        self.command = None

    def _run_command(self, *args):
        command_args = []
        if self.command:
            command_args = shlex.split(self.command)
        if args:
            command_args.extend(args)
        if command_args:
            Popen(
                [*command_args],
                stdout=DEVNULL,
                stderr=DEVNULL,
                stdin=DEVNULL
            )
        else:
            raise ShellError(
                'Shell command not found'
            )

    def clean(self):
        self.command = None

    def add_command(self, command):
        if isinstance(command, str):
            if self.command:
                self.command = self._join([self.command, command])
            else:
                self.command = command
        elif isinstance(command, list):
            if self.command:
                self.command = self._join([self.command, *command])
            else:
                self.command = ' '.join(command)
        else:
            raise ShellError(
                'Unsupported command type'
            )

    def run(self, *args):
        try:
            self._run_command(*args)
        except Exception as err:
            raise ShellError(str(err))


class ConnectorShellClient:

    def __init__(self, shell_command):
        self.shell = shell_command()

    def _update_connector_config(self, section: str, **kwargs):
        config_file_path = self.get_connector_config_file()
        data = toml.load(config_file_path)
        data[section].update(**kwargs)

        with open(config_file_path, 'w') as f:
            toml.dump(data, f)

    def _get_connector_data_dir(self):
        return self.shell.get_path(
            SSE_CONNECTOR_DATA_FOLDER,
            [SSE_CONNECTOR_FOLDER, ]
        )

    def _get_connector_root_cert_file(self):
        return self.shell.get_path(
            SSE_CONNECTOR_ROOT_CERT_FILE,
            [SSE_CONNECTOR_FOLDER, SSE_CONNECTOR_CERT_FOLDER]
        )

    def _get_connector_file(self):
        return self.shell.get_path(
            SSE_CONNECTOR_FILE,
            [SSE_CONNECTOR_FOLDER, ]
        )

    def update_data_dir(self):
        self._update_connector_config(
            'Globals',
            **{'data_dir': self._get_connector_data_dir()}
        )

    def update_cert_store(self):
        self._update_connector_config(
            'Globals',
            **{'cert_store': self._get_connector_root_cert_file()}
        )

    def get_connector_config_file(self):
        return self.shell.get_path(
            SSE_CONNECTOR_CONFIG_FILE,
            [SSE_CONNECTOR_FOLDER, SSE_CONNECTOR_CONFIG_FOLDER]
        )

    def run_connector(self):
        self.update_data_dir()
        self.update_cert_store()
        self.shell.clean()
        self.shell.add_command(
            [
                self._get_connector_file(),
                SSE_CONNECTOR_RUNNING_COMMAND,
                SSE_CONNECTOR_CONF_ARG,
                self.get_connector_config_file()
            ]
        )
        self.shell.run()
