import os
import sys
import json
import logging

cur_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(cur_dir, 'libs'))
sys.path.append(cur_dir)
sys.path.append(lib_path)

import splunk.rest
from constants import APP_NAME

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', APP_NAME+'.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)

class UserHandler(PersistentServerConnectionApplication):

    def __init__(self, commandLine, commandArg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, inString):
        request = json.loads(inString)
        authToken = request['session']['authtoken']
        final_url = "/services/authentication/current-context?output_mode=json"
        try:
            server_response, server_content = splunk.rest.simpleRequest(
                final_url, sessionKey=authToken,
                method='GET', raiseAllErrors=True
            )
            roles = json.loads(server_content)['entry'][0]['content']['roles']
            if 'admin' not in roles:
                payload = {
                    'payload':{
                        'entry':{
                            'content':'invalid'
                        }
                    }
                }
            else:
                payload = {
                    'payload':{
                        'entry':{
                            'content':'valid'
                        }
                    }
                }
            logging.info(payload)
            return json.dumps(payload)
        except Exception as e:
            payload = {
                'payload':{
                    'entry':{
                        'content':str(e)
                    }
                }
            }
            return json.dumps(payload)
