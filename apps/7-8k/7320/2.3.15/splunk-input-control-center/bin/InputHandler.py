import os
import sys
import logging 
import json
import base64
from splunk.rest import simpleRequest


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'splunk-input-control-center.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)
from splunk.persistconn.application import PersistentServerConnectionApplication

APP_NAME = "splunk-input-control-center"

def flatten_query_params(params):
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened

class InputHandler(PersistentServerConnectionApplication):
    
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        args = json.loads(in_string)
        LOCAL_URI = args["server"]["rest_uri"]
        AUTHTOKEN = args["session"]["authtoken"]
        
        try : 
            if args["method"] == "POST":
            
            
                form = dict(args.get("form", []))
                CtrlLink = form['ctrl_link']
                logging.debug("Arguments : %s", form)
                logging.debug("HIBP Input Manager: Enabling input")
                simpleRequest(
                            f"{LOCAL_URI}{CtrlLink}",
                            sessionKey=AUTHTOKEN,
                            method="POST",
                            raiseAllErrors=True,
                        )
                logging.debug("API HIT")
                return {"payload": form , "status": 200}
            else:
                return {"payload": "", "status": 500}
            

        except Exception as e:
            logging.error('Exception Occured %s', str(e))
            return {'payload': {'error': 'Exception Occured'}, 'status': 500}