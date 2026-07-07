import splunk
import os
import sys
import json
import cherrypy


import logging as logger
from io import open
logger.basicConfig(level=logger.INFO, format='%(asctime)s %(levelname)s  %(message)s',datefmt='%m-%d-%Y %H:%M:%S.000 %z',
     filename=os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk','vo_sess_key.log'),
     filemode='a')

splunkHome=os.environ.get('SPLUNK_HOME')

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

class Key(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):

        try:

            python3 = sys.version_info[0] >= 3
            if python3:
                in_string = str(in_string, 'utf-8')

            filename = "default"
            content = "none"

            data = json.loads(str(in_string))
            auth_token = data['system_authtoken']

            return {'payload': auth_token, 'status': 200 }

        except Exception as e:
            logger.info(e)
            resp = "Exception Occurred";
            return {'payload': resp,  # Payload of the request.
                    'status': 403          # HTTP status code
            }

