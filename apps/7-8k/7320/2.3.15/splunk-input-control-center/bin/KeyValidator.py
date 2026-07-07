import os
import sys
import logging 
import json
import base64
import time
import datetime

activation_key_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'splunk-input-control-center', 'bin')
sys.path.append(activation_key_path)
from logevent import log_event
from a_v import A_V

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)
    

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'splunk-input-control-center.log'])
logging.basicConfig(filename=logfile, level=logging.DEBUG)
from splunk.persistconn.application import PersistentServerConnectionApplication




def flatten_query_params(params):
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened

class EchoHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        payload = {}
        request = json.loads(in_string)
        SessionKey = request["session"]["authtoken"]
        serveruri = request["server"]["rest_uri"]
        query_params = flatten_query_params(request['query'])
            
        input_string = query_params.get('input')
        app_name = query_params.get('app')
        output_format = query_params.get('format')

        logging.debug('Key_validator_QUERY_PARAMS: %s', str(input_string))
        logging.debug('Key_validator_AUTHTOKEN: %s', str(SessionKey))
        logging.debug('Key_validator_In_String: %s', str(in_string))
        logging.debug('Key_validator_app: %s', str(app_name))
        logging.debug('Key_validator_resturi: %s', str(serveruri))
        
        try : 
            activation_key = str(input_string)
            v = A_V(app_name, activation_key)
            key_validator = v.v_a_k()
            if key_validator:
                    logging.debug('activation_key_status : %s', str(key_validator))
                    payload = {
                    "app": str(app_name),
                    "Status": "Inactive",
                    "message" : key_validator
                    }
                    log_event(payload,serveruri,SessionKey)
            else:
                    logging.debug('activation_key_status : %s', str(key_validator))
                    key_generated = activation_key[-10:]
                    key_generated = key_generated[::-1]
                    key_generated = int(key_generated)
                    date_time_obj = datetime.datetime.utcfromtimestamp(key_generated)
                    key_generated = date_time_obj.date()
                    formatted_date = date_time_obj.strftime('%d-%m-%Y')
                    today_date = datetime.date.today()
                    increased_date = today_date + datetime.timedelta(days=10)
                    if increased_date<key_generated:
                        akmsg = "NA(This key is for Lifetime)"
                        days = "NA"
                        data = {"activation_key_generated_on":akmsg, "activation_key_status":"Active"}
                    else:
                        current_timestamp = time.time()
                        specific_date_str = formatted_date
                        specific_timestamp = time.mktime(time.strptime(specific_date_str, "%d-%m-%Y"))

                        seconds =  current_timestamp - specific_timestamp 
                        akmsg = formatted_date+"(Trial License)"
                        data = {"activation_key_generated_on":akmsg, "activation_key_status":"Active"}
                    payload = {
                    "app": str(app_name),
                    "Status": "Active",
                    "message" : data
                    }
                    log_event(payload,serveruri,SessionKey)
            
            
            return {'payload': payload, 'status': 200}
            

        except Exception as e:
            logging.error('Error reading file: %s', str(e))
            return {'payload': {'error': 'Error reading file'}, 'status': 500}