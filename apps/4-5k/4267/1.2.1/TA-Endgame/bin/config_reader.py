import os
import json
from splunk.clilib import cli_common as cli

from logger import setup_logging as create_logger

logger = create_logger('ta_endgame_logger', 'TA-Endgame.log')


class ConfigReader(object):

    def readConfFile(self, filename, stanza=None):
        obj = None
        dict = {}
        appdir = os.path.dirname(os.path.dirname(__file__))
        defaultconfpath = os.path.join(appdir, "default", filename)
        localconfpath = os.path.join(appdir, "local", filename)
        logger.info('Default app path: {}, {}'.format(defaultconfpath, stanza))
        logger.info('Local app path: {}, {}'.format(localconfpath, stanza))
        if os.path.exists(localconfpath):
            confFileObj = cli.readConfFile(localconfpath)
        elif os.path.exists(defaultconfpath):
            confFileObj = cli.readConfFile(defaultconfpath)
        else:
            logger.info('Config file {0} does not exist'.format(filename))
            return None
        if stanza is None:
            obj = json.loads(json.dumps(confFileObj).encode('utf-8'))
            for key, value in obj.items():
                key = str(key)
                dict[key] = str(value)
        else:
            obj = json.loads(json.dumps(confFileObj).encode('utf-8'))
            for key, value in obj.items():
                key = str(key)
                if stanza in key:
                    for key1, value1 in value.items():
                        dict[str(key1)] = str(value1)

        return dict

    def writeToStanza(self, _key, _value, _stanza, _conf_file_name):
        _path = None
        appdir = os.path.dirname(os.path.dirname(__file__))
        defaultconfpath = os.path.join(appdir, "default", _conf_file_name)
        localconfpath = os.path.join(appdir, "local", _conf_file_name)
        logger.info('Default app path: {}, {}'.format(
            defaultconfpath, _stanza))
        logger.info('Local app path: {}, {}'.format(localconfpath, _stanza))
        if os.path.exists(localconfpath):
            _path = localconfpath
        elif os.path.exists(defaultconfpath):
            _path = defaultconfpath
        else:
            logger.info(
                'Config file {0} does not exist'.format(_conf_file_name))
            pass
        logger.info('localconfpath: {}, stanza: {}, key:{}, value: {}'.format(
            localconfpath, _stanza, _key, _value))
        stanza = {_stanza: {_key: _value}}
        cli.writeConfFile(_path, stanza)
