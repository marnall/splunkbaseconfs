
# encoding = utf-8

import os
import sys
import time
import datetime
import pexpect
import re
import json


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # address = definition.parameters.get('address', None)
    # email = definition.parameters.get('email', None)
    # secret_key = definition.parameters.get('secret_key', None)
    # password = definition.parameters.get('password', None)
    pass

def collect_events(helper, ew):
    
    # Get inputs
    opt_op_binary = helper.get_arg('path_to_op_binary')
    opt_address = helper.get_arg('address')
    opt_email = helper.get_arg('email')
    opt_user_id = helper.get_arg('user_id')
    opt_secret_key = helper.get_arg('secret_key')
    opt_password = helper.get_arg('password')
    
    # Set environment variables from proxy settings if Proxy set
    proxy_dict = helper.get_proxy()
    
    if proxy_dict != {}:
        if "proxy_username" in proxy_dict:
            proxy_string = proxy_dict["proxy_type"]+"://"+proxy_dict["proxy_username"]+":"+proxy_dict["proxy_password"]+"@"+proxy_dict["proxy_url"]+":"+proxy_dict["proxy_port"]
        elif "proxy_url" in proxy_dict:
            proxy_string = proxy_dict["proxy_type"]+"://"+proxy_dict["proxy_url"]+":"+proxy_dict["proxy_port"]
        
        os.environ["http_proxy"] = proxy_string
        os.environ["https_proxy"] = proxy_string
    
    # Set secret key in environment
    os.environ["OP_SECRET_KEY"] = opt_secret_key
    
    # Get base path to the onepassword cli binary
    base_cmd = opt_op_binary

    # First add the account to the cli account profiles
    addacc_cmd = base_cmd+" account add --address "+opt_address+" --email "+opt_email
    addacc_1password = pexpect.run(addacc_cmd, events={'(?i)password': '%s\n' % opt_password})
    
    # Run the signin command and pass the password
    signin_command = base_cmd+" signin -f --raw"
    addacc_1password = pexpect.run(signin_command, events={'(?i)password': '%s\n' % opt_password})
    
    # Grab the onepass token from the result of the previous command 
    regex_get_onep_token = r"\\n([^\\]+)'$"
    onep_session_token = re.findall(regex_get_onep_token,str(addacc_1password))[0]
    
    os.environ["OP_SESSION_"+opt_user_id] = onep_session_token
    
    # Get the list of users
    listusers_command = base_cmd+" users list --format=json"
    listusers_1p = pexpect.run(listusers_command,encoding='utf-8')
    
    # Remove the Ansi escape characters
    # From: https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    ansi_escape_8bit = re.compile(r'(?:\x1B[@-Z\\-_]|[\x80-\x9A\x9C-\x9F]|(?:\x1B\[|\x9B)[0-?]*[ -/]*[@-~])')
    listusers_1p = ansi_escape_8bit.sub('', listusers_1p)
    
    l_json = json.loads(listusers_1p)
    
    # Write each user json entry as an event
    for u in l_json:
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(u, ensure_ascii=False))
        ew.write_event(event)
    
    
    