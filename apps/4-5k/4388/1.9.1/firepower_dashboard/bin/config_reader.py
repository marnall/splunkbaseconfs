import os
import sys
import json
from splunk.clilib import cli_common as cli
import sys
import splunklib.client as client

splunk_home = os.getenv('SPLUNK_HOME')
sys.path.append(splunk_home + '/etc/apps/firepower_dashboard/bin')
from logger import setup_logging as create_logger

logger = create_logger('firepower_logger', 'firepower.log')

class ConfigReader(object):

        def readConfFile(self, filename, stanza = None):
            obj = None
            dict = {}
            appdir = os.path.dirname(os.path.dirname(__file__))
            defaultconfpath = os.path.join(appdir, "default", filename)
            localconfpath = os.path.join(appdir, "local", filename)
            logger.info('Default app path: {}, {}'.format(defaultconfpath,stanza))
            logger.info('Local app path: {}, {}'.format(localconfpath, stanza))
            if os.path.exists(localconfpath):
                confFileObj = cli.readConfFile(localconfpath)
            elif os.path.exists(defaultconfpath):
                confFileObj = cli.readConfFile(defaultconfpath)
            else:
                logger.info('Config file {0} does not exist'.format(filename))
                pass
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