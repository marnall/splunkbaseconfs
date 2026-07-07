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

# Append directory of this file to the Python path (sys.path) to be able to import app libs
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Get app name
app_name = 'cliauto'

# Import app endpoint lib
from cliautolib.cliauto_endpoint import endpoint

# Log file location /opt/splunk/var/log/splunk/<app_name>.log
# CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'cliauto.log'])
logconfpath = os.sep.join([os.environ['SPLUNK_HOME'], 'etc', 'apps', app_name, 'default', 'logger.conf'])
logging.config.fileConfig(logconfpath, defaults={'logfilename': logfile})

class cliautoHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        pass

    def handle(self, in_string):

        # Create endpoint object and return response
        try:

            logging.info('log_level=INFO script=cliauto.py method=handle, Starting cliautoHandler.handle method...')
            ppid = os.getpid()

            # Log parent pid
            logging.info('log_level=INFO script=cliauto.py method=handle, cliautoHandler.handle method: Parent pid:' + str(ppid))

            oep = endpoint(in_string, ppid)
            return oep.response

        except Exception as err:
            logging.error('log_level=ERROR script=cliauto.py method=handle, Create endpoint object and return response; err = ' + str(err))
            logging.error('log_level=ERROR script=cliauto.py method=handle, Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return json.dumps({ 'payload': 'Error, Create endpoint object and return response; err = ' + str(err),
                                         'status': 500  # HTTP status code
                                      })
