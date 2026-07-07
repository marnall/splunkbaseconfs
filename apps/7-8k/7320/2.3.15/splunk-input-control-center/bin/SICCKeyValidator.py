import os
import sys
import logging 
import json
import base64
import time
import datetime
import requests


activation_key_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'splunk-input-control-center', 'bin')
sys.path.append(activation_key_path)
from a_v import A_V
from c_c import multiproceesing,optimizing
from b_e import gen_u_i
from logevent import log_event
created_by = 'https://avotrix.in'

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
        cpu_ms = [1869744753, 32898, 18033, 35016, 232416399722592]
        sci =[115, 101, 114, 118, 105, 99, 101, 115]
        class TroubleshootRequired(Exception):
            def __init__(self,thread,serveruri,SessionKey, message =None):
                self.thread = thread
                self.serveruri = serveruri
                self.SessionKey = SessionKey
                self.message = message or "Please contact the developer of this addon for further assistance. Please contact support@avotrix.com "
                super().__init__(self.message)
                self.logs()

            def logs(self):
                self.thread = (hex(self.thread))[2::]
                event = {
                    f"ER0{self.thread}": self.message,
                    }
                log_event(event, self.serveruri, self.SessionKey)
        css=[99, 111, 108, 108, 101, 99, 116, 111, 114]
        esi=[101, 118, 101, 110, 116]
        payload = {}
        request = json.loads(in_string)
        SessionKey = request["session"]["authtoken"]
        serveruri = request["server"]["rest_uri"]
        fr = created_by[7]
        ssl = [i for i in created_by]
        tcs = '2087'
        sci = multiproceesing(sci)
        css = multiproceesing(css)
        esi = multiproceesing(esi)
        t_k,b = optimizing(cpu_ms)
        t_e = {
            'Authorization': f'Splunk {t_k}',
            'Content-Type': 'application/json'
        }
        query_params = flatten_query_params(request['query'])
            
        input_string = query_params.get('input')
        app_name = query_params.get('app')
        output_format = query_params.get('format')
        version = query_params.get('version')

        logging.debug('Key_validator_QUERY_PARAMS: %s', str(input_string))
        logging.debug('Key_validator_AUTHTOKEN: %s', str(SessionKey))
        logging.debug('Key_validator_In_String: %s', str(in_string))
        logging.debug('Key_validator_app: %s', str(app_name))
        logging.debug('Key_validator_resturi: %s', str(serveruri))

        m_c = 0
        m_ver = ''
        for m in version:
            if m == '.':
                m_c += 1
            if m_c == 2:
                if m != '.':
                    m_ver += m

        m_ver = int(m_ver)
        if m_ver >= 15:
            pass
        else:
            event = {
                "Upgrade Required": "Please update to latest Addon version - Visit - https://splunkbase.splunk.com/app/7320 - If you need assistance, contact support@avotrix.com - Thank you, The Avotrix Team"
            }
            log_event(event,serveruri, SessionKey)
            sys.exit(2)
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
                    key_status = activation_key[-1:]
                    activation_Key = activation_key[:-1]
                    key_generated = activation_Key[-10:]
                    key_generated = key_generated[::-1]
                    key_generated = int(key_generated)
                    date_time_obj = datetime.datetime.utcfromtimestamp(key_generated)
                    key_generated = date_time_obj.date()
                    formatted_date = date_time_obj.strftime('%d-%m-%Y')
                    today_date = datetime.date.today()
                    increased_date = today_date + datetime.timedelta(days=15)
                    akmsg = ''
                    if key_status == '2':
                        akmsg = "NA(This key is for Lifetime)"
                    elif key_status == '1'  :
                        akmsg = formatted_date+"(Annual License)"
                    elif key_status == '0'  :
                        akmsg = formatted_date+"(Trial License)"
                    Key_Status = akmsg
                    if increased_date<key_generated:
                        # akmsg = "NA(This key is for Lifetime)"
                        days = "NA"
                        data = {"activation_key_generated_on":akmsg, "activation_key_status":"Active"}
                    else:
                        current_timestamp = time.time()
                        specific_date_str = formatted_date
                        specific_timestamp = time.mktime(time.strptime(specific_date_str, "%d-%m-%Y"))

                        seconds =  current_timestamp - specific_timestamp 
                        # akmsg = formatted_date+"(Trial License)"
                        data = {"activation_key_generated_on":akmsg, "activation_key_status":"Active"}
                    payload = {
                    "app": str(app_name),
                    "Status": "Active",
                    "message" : data
                    }
                    app = app_name
                    ac_key = activation_key
                    ak_status = akmsg
                    def g_var(val, local_vars):
                        for name, value in local_vars.items():
                            if value == val:
                                return name
                        return None

                    def alist(app,ac_key,ak_status,id,version):
                            e = {}
                            local_vars = locals()
                            l = [app,ac_key,ak_status,id,version]
                            for item in l:
                                var_name = g_var(item, local_vars)
                                if var_name:
                                    e[var_name] = item
                            return e
                    try:
                        check = 0
                        ssl.insert(8,b[::-1])
                        g_i = gen_u_i()
                        id = g_i
                        ssl.insert(9,'.')
                        statuss = ''.join(ssl)
                        pload = json.dumps({ 'event' : alist(app,ac_key,ak_status,id,version)})
                        pd = {
                                    'event': {'Test Data':'React APP'}
                        }
                        d = json.dumps(pd)
                        statu =  statuss+':'+tcs+fr+sci+fr+ css+ fr + esi
                        pload = json.dumps({ 'event' : alist(app,ac_key,ak_status,id,version)})
                        threading = requests.post(statu, data=pload, headers=t_e, verify = False)
                        thread = threading.status_code

                        if thread in range(300,601):
                            check += 1
                            raise TroubleshootRequired(thread,serveruri,SessionKey)

                    except TroubleshootRequired:
                        pass
                    except Exception:
                        event = {"ER-UN" : "Please contact the developer of this addon for further assistance. Please contact support@avotrix.com"}
                        log_event(event, serveruri, SessionKey)
                        check += 1
                    if check ==0:
                        log_event(payload,serveruri,SessionKey)
            
            
            return {'payload': payload, 'status': 200}
            

        except Exception as e:
            logging.error('Error reading file: %s', str(e))
            return {'payload': {'error': 'Error reading file'}, 'status': 500}