from __future__ import absolute_import
from __future__ import print_function

import logging
from logging.config import fileConfig
import sys, os, datetime, json

# Append directory of this file to the Python path (sys.path) to be able to import snowtbl libs
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Import snowtbl endpoint lib
from snowtbllib.snowtbl_endpoint import endpoint

# Log file location /opt/splunk/var/log/splunk/snowtbl.log
# CRITICAL = 50, ERROR = 40, WARNING = 30, INFO = 20, DEBUG = 10, NOTSET = 0
logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'snowtbl.log'])
logconfpath = os.sep.join([os.environ['SPLUNK_HOME'], 'etc', 'apps', 'snowtbl', 'default', 'logger.conf'])
logfile = logfile.replace('\\','/')
logconfpath = logconfpath.replace('\\','/')
logging.config.fileConfig(logconfpath, defaults={'logfilename': logfile})

from splunk.persistconn.application import PersistentServerConnectionApplication

# For Splunk on MS Windows (possible future use)
if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

class run_query_Handler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        pass

    def handle(self, in_string):

        # Create endpoint object and return response
        try:

            logging.info('log_level=INFO script=snowtbl_rest_run_query.py method=run_query_Handler.handle, Starting run_query_Handler.handle method...')

            # Log parent pid
            ppid = os.getpid()
            logging.info('log_level=INFO script=snowtbl_rest_run_query.py method=run_query_Handler.handle, Parent pid=' + str(ppid))

            # Process in_string message
            oep = endpoint(in_string, "rest", "run_query", "rq_default")
            return oep.response

            logging.info('log_level=INFO script=snowtbl_rest_run_query.py method=create_ticket_Handler.handle, Ending run_query_Handler.handle method...')

        except Exception as err:
            logging.error('log_level=ERROR script=snowtbl_rest_run_query.py method=run_query_Handler.handle, Create endpoint object and return response; err=' + str(err))
            return json.dumps({'payload': json.dumps({'status': 'failure',
                               'error': {'detail': 'snowtbl app error - snowtbl_rest_run_query.run_query_Handler.handle',
                               'message': 'Create endpoint object and return response; err=' + str(err)}}),
                               'status': 200})
