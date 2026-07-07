#!/usr/bin/env python

import os
from splunk.clilib import cli_common as cli

APP_NAME = __file__.split(os.sep)[-3]


class Config:

    def __init__(self, config_name):
        self.config_name = config_name

    def get(self, stanza, key):
        stanza_dict = self._read_config()
        if stanza in stanza_dict:
            return stanza_dict[stanza].get(key)

    def set(self, stanza, key, value):
        stanza_dict = self._read_config()
        if stanza not in stanza_dict:
            stanza_dict[stanza] = {}

        stanza_dict[stanza][key] = value
        self._write_config(stanza_dict)

    def delete(self, stanza, key):
        stanza_dict = self._read_config()
        if stanza in stanza_dict:
            stanza_dict[stanza].pop(key, None)
            self._write_config(stanza_dict)

    @staticmethod
    def _build_path(*paths):
        splunk_home = os.environ['SPLUNK_HOME']
        relative_path = os.path.normpath(os.path.join(*paths))
        full_path = os.path.normpath(os.path.join(splunk_home, relative_path))
        return full_path

    @staticmethod
    def _build_config_file_name(file_name):
        return file_name + '.conf'

    def _full_config_path(self):
        config_path = self._build_path(
            'etc',
            'apps',
            APP_NAME,
            'local',
            self._build_config_file_name(self.config_name)
        )
        return config_path

    def _write_config(self, stanza_dict):
        file_name = self._full_config_path()
        cli.writeConfFile(file_name, stanza_dict)

    def _read_config(self):
        file_name = self._full_config_path()
        cli.touch(file_name)
        stanza_dict = cli.readConfFile(file_name)
        return stanza_dict
