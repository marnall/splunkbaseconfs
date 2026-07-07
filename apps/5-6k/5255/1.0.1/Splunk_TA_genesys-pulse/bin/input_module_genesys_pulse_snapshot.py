
# encoding = utf-8

import os
import sys
import time
import datetime

import requests
import pickle
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import json 
from hashlib import md5

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''
def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z
    
def parse_pulse(o):
    output = list()
    stage = dict()
    header = dict()
    header["timestamp"] = o["generator_info"]["timestamp"]
    header["layout_guid"] = o["layout_guid"]
    for k,v in o["generator_info"].items():
        if k.startswith("cme_"):
            header[k] = v
    for i in o["col"]:
        _key = (i["col"]["id"].lstrip("_").replace("$","_"))
        _val = (i["v"])
        stage[_key] = _val
    for i, val in enumerate(stage["Object_ID"]):
        record = dict() 
        for _k, _v in stage.items():
            record[_k] = _v[i]
        final_record = merge_two_dicts(header,record)
        output.append(final_record)
    return output
    
def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # username = definition.parameters.get('username', None)
    # password = definition.parameters.get('password', None)
    # pulse_base = definition.parameters.get('pulse_base', None)
    # pulse_port = definition.parameters.get('pulse_port', None)
    pass

def collect_events(helper, ew):
    
    ## GET url
    pulse_base = helper.get_arg('pulse_base')
    pulse_port = helper.get_arg('pulse_port')
    pulse_subbase = pulse_base + ":" + pulse_port
    pulse_url = pulse_subbase + "/gax/api"
    
    # GET SOURCE metadata field
    source = helper.get_input_type() + ":" + pulse_base.split("//")[-1].split(".")[0]
    
    ## GET credentials
    username = helper.get_arg('username')
    password = helper.get_arg('password')
    
    ## MAKE cookie/pickle jar
    splunkhome = os.environ['SPLUNK_HOME']
    cookie_name = pulse_url.encode('utf-8') + username.encode('utf-8')
    cookie_name_md5 = md5(cookie_name).hexdigest() + ".pkl"
    session_file = os.path.join(splunkhome, 'etc', 'apps', 'Splunk_TA_genesys-pulse', 'bin', cookie_name_md5)

    ## Load/Create the session
    try:
        with open(session_file, 'rb') as f:
            s = pickle.load(f)
    except (IOError,EOFError):
        s = requests.session()
        
    ## log me in, uses the existing cookie if it exists
    data = {"username":username, "password":password, "isPasswordEncrypted":"false"}
    r = s.post(pulse_url + '/session/login', data=data, verify=False)

    ## just a test call
    r = s.get(pulse_url + "/user/info", data=data, verify=False)
    if r.status_code != 200:
        print("Authentication failed.")
        sys.exit()
        
    ## lets get all layouts
    layouts = list()
    r = s.get(pulse_url + "/wbrt/layouts", data=data, verify=False)
    if r.status_code != 200:
        print("Authentication failed.")
        sys.exit()
        
    for i in r.json():
        layouts.append(i["definition"]["guid"])
    layouts = list(set(layouts))
        
    ## loop through the layouts and get some datas
    for i in layouts:                   
        r = s.get(pulse_url + "/wbrt/layouts/{}/snapshot".format(i), data=data, verify=False)
        if r.status_code == 200:
            o = r.json()
            for r in parse_pulse(o):
                
                data = json.dumps(r)
                event = helper.new_event(source=source, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
                ew.write_event(event)
                    
    # At this point, the session might contain cookies, session variables, etc.
    # Persist the session through program runs
    with open(session_file, 'wb') as f:
        pickle.dump(s, f)
