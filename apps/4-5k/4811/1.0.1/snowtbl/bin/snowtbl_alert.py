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

try:

    alert_action_name = ''
    logging.info('log_level=INFO script=snowtbl_alert.py method=main, Starting snowtbl_alert.py...')

    # Log parent pid
    ppid = os.getpid()
    logging.info('log_level=INFO script=snowtbl_alert.py method=main, parent_pid=' + str(ppid))
    print('INFO parent_pid=' + str(ppid), file=sys.stderr)

    # Get payload
    in_string = json.loads(sys.stdin.read())

    # Try to get snowtbl_stanza name
    try:
        snowtbl_stanza = str(sys.argv[1])
    except:

        print('ERROR missing alert action argument(s), alert_result=unknown', file=sys.stderr)

        # Exit script (exit_code=1 is Fail)
        sys.exit(1)

    # Try to get alert_action name
    try:
        alert_action_name = str(sys.argv[2])
    except:
        alert_action_name = 'not set in conf file'

    # Create endpoint object
    oep = endpoint(in_string, "alert", "create_ticket", snowtbl_stanza)
    print('INFO alert_result=' + str(oep.alert_result), file=sys.stderr)
    logging.info('log_level=INFO script=snowtbl_alert.py method=main action=' + alert_action_name + ', alert_result=' + str(oep.alert_result))

    logging.info('log_level=INFO script=snowtbl_alert.py method=main action=' + alert_action_name + ', Ending create_ticket.py...')

    # Exit script (exit_code=0 is Success)
    sys.exit(oep.exit_code)


except Exception as err:
    logging.error('log_level=ERROR script=snowtbl_alert.py method=main action=' + alert_action_name + ', err=' + str(err))
    logging.error('log_level=ERROR script=snowtbl_alert.py method=main action=' + alert_action_name + ', Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
    print('ERROR err=' + str(err), file=sys.stderr)
    print('ERROR Error on line {}'.format(sys.exc_info()[-1].tb_lineno), file=sys.stderr)
    sys.exit(1)
