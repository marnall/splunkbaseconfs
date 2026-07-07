import os
import sys
import json
import logging
import re
import splunk

cur_dir = os.path.dirname(os.path.abspath(__file__))
lib_path = os.path.abspath(os.path.join(cur_dir, 'libs'))
sys.path.append(cur_dir)
sys.path.append(lib_path)

import splunk.rest
from splunklib import client
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

class IndexHandler(PersistentServerConnectionApplication):
    index_name_pattern = re.compile("^[a-zA-z]([\w-*]*)$")

    def __init__(self, commandLine, commandArg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, inString):
        request = json.loads(inString)
        authToken = request['session']['authtoken']
        if request['method'] == 'GET':
            return self.getHandler(authToken,request['query'])
        elif request['method'] == 'PUT':
            return self.putHandler(authToken, request['payload'])
        else:
            return {'payload':{}, 'status':405}

    # Get custom index
    def getHandler(self, authToken, params):
        try:
            confs = client.Service(token = authToken, app=APP_NAME, autologin=True).confs
            macros = confs['macros']

            for stanza in macros:
                if stanza.name == 'jenkins_statistics_index':
                    statistics = stanza.content
                elif stanza.name == 'jenkins_console_index':
                    console = stanza.content
                elif stanza.name == 'jenkins_index':
                    jenkins = stanza.content

            payload={
                'payload':{
                    'content':{
                        'entry':{
                            'statistics':statistics,
                            'consoleIdx':console,
                            'jenkins':jenkins
                        }
                    }
                },
                'status':200
            }

            return json.dumps(payload)
        except Exception as e:
            logging.error(str(e))
            payload={
                'payload':{
                    'error':str(e),
                },
                'status':500
            }
            return json.dumps(payload)

    def _validate_user_input(self, content):
        # only alphbet, digits and under score is allowd
        valid = content and self.index_name_pattern.match(content.strip('"'))
        if not valid:
            raise ValueError("Index name " + content + " is not valid. "
                            + "Index name must start with alphabet letters and"
                            + " can only contains alphabet letters, digits and underscores.")

    # Change custom index
    def putHandler(self, authToken, in_string):
        try:
            confs = client.Service(token = authToken, app=APP_NAME, autologin=True).confs
            macros = confs['macros']

            data = json.loads(in_string)
            jenkins = data['jenkins']
            statistics = data['jenkinsStatistics']
            console = data['jenkinsConsole']
            self._validate_user_input(jenkins)
            self._validate_user_input(statistics)
            self._validate_user_input(console)
            for stanza in macros:
                if stanza.name == 'jenkins_statistics_index':
                    stanza.update(**{'definition':'index='+statistics})
                elif stanza.name == 'jenkins_console_index':
                    stanza.update(**{'definition':'index='+console})
                elif stanza.name == 'jenkins_index':
                    stanza.update(**{'definition':'index='+jenkins})

            payload={
                'payload':{
                    'content':{
                        'entry':{
                            'statistics':statistics,
                            'jenkins':jenkins,
                            'consoleIdx':console
                        }
                    }
                },
                'status':200
            }
            return json.dumps(payload)
        except Exception as e:
            logging.error(str(e))
            payload={
                'payload':{
                    'error':str(e)
                },
                'status':500
            }
            return json.dumps(payload)
