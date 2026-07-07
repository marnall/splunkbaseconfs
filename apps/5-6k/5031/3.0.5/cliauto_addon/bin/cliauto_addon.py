from __future__ import absolute_import
from __future__ import print_function

import os
import re
import sys
import json
import logging
from logging.config import fileConfig
import time
from splunk.persistconn.application import PersistentServerConnectionApplication

# Append directory of this file to the Python path (sys.path) to be able to import cliauto_addon libs
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Get app name
app_name = 'cliauto_addon'

# Import cliauto_addon ao_endpoint lib
from cliauto_addonlib.cliauto_addon_endpoint import ao_endpoint

# Log file location /opt/splunk/var/log/splunk/cliauto_addon.log
# CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'cliauto.log'])
logconfpath = os.sep.join([os.environ['SPLUNK_HOME'], 'etc', 'apps', app_name, 'default', 'logger.conf'])
logging.config.fileConfig(logconfpath, defaults={'logfilename': logfile})

class cliauto_addonHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        pass

    def handle(self, in_string):

        # Create ao_endpoint object and return response
        try:

            logging.info('log_level=INFO script=cliauto_addon.py method=handle, Starting cliauto_addonHandler.handle method...')
            ppid = os.getpid()

            # Log parent pid
            logging.info('log_level=INFO script=cliauto_addon.py method=handle, cliauto_addonHandler.handle method: Parent pid:' + str(ppid))

            oep = ao_endpoint(in_string, ppid)
            return oep.response

        except Exception as err:
            logging.error('log_level=ERROR script=cliauto_addon.py method=handle, Create ao_endpoint object and return response; err = ' + str(err))
            logging.error('log_level=ERROR script=cliauto_addon.py method=handle, Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return json.dumps({ 'payload': 'Error, Create ao_endpoint object and return response; err = ' + str(err),
                                         'status': 500  # HTTP status code
                                      })
