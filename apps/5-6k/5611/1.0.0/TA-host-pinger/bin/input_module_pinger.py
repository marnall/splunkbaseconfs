
# encoding = utf-8
import requests
import sys
import os
import json
import time
import datetime

def request_search(auth,opt_lookup_name):
    lookup="| inputlookup "+opt_lookup_name
    data = {'search': lookup,'output_mode': 'json'}
    response = requests.post('https://localhost:8089/services/search/jobs', data=data, verify=False, headers=auth)
    if (response.status_code == 201):
        output=json.loads(response.content.decode("utf-8"))
        sid=output["sid"]
        status=request_status(sid,auth)
        if status==True :
            return sid
        elif status=="Failed":
            exit()
        else:
            for i in range(10):
                time.sleep(0.5*i)
                status=request_status(sid,auth)
                if status == True:
                    return sid
                else:
                    continue
            return False
    else:
        return False

def request_status(sid,auth):
    params = {'output_mode':'json'}
    url='https://localhost:8089/services/search/jobs/'+sid
    response = requests.get(url, params=params, verify=False, headers=auth)
    if (response.status_code==200):
        output=json.loads(response.content.decode("utf-8"))
        stat=output["entry"][0]["content"]["isDone"]
        return stat
    else:
        return "Failed"


def request_response(sid,auth):
    ssid=sid
    params = {'output_mode':'json'}
    url = 'https://localhost:8089/services/search/jobs/{}/results/'.format(ssid)
    response = requests.get(url, params=params, verify=False, headers=auth)
    if response.status_code==200:
        output=json.loads(response.text)
        hosts=output["results"]
        length=len(hosts)
        host_list=[]
        for i in range(length):
            extract=hosts[i]["pingable"]
            host_list.append(extract)
        return host_list
    else:
        return False


def check_ping(hosts):
	hostname=hosts
	response = os.system("ping -c 1 " + hostname + ">/dev/null 2>&1")
	if response == 0:
	    pingstatus = "Network Active"
	else:
	    pingstatus = "Network Error"
	curr_clock = str(datetime.datetime.now())
# 	print(curr_clock+","+hostname+","+pingstatus)
	data=curr_clock+","+hostname+","+pingstatus
	return data


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

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # lookup_name = definition.parameters.get('lookup_name', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_lookup_name = helper.get_arg('lookup_name')
    # In single instance mode, to get arguments of a particular input, use
    #opt_lookup_name = helper.get_arg('lookup_name', stanza_name)

    # get input type
    #helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    #helper.get_input_stanza()
    # get specific input stanza with stanza name
    #helper.get_input_stanza(stanza_name)
    # get all stanza names
    #helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    #loglevel = helper.get_log_level()
    # get proxy setting configuration
    #proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    #account = helper.get_user_credential_by_username("username")
    #account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    #global_username = helper.get_global_setting("username")
    #global_password = helper.get_global_setting("password")
    global_authentication_token = helper.get_global_setting("authentication_token")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    #helper.log("log message")
    # write to the log using specified log level
    #helper.log_debug("log message")
    #helper.log_info("log message")
    #helper.log_warning("log message")
    #helper.log_error("log message")
    #helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    #helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.

    #auth=(global_username,global_password)
    token='Bearer '+ global_authentication_token
    auth={'Authorization' : token}
    ssid=request_search(auth,opt_lookup_name)
    #count=1
    #status=request_status(ssid,count,auth)
    if ssid!=False:
        hosts=request_response(ssid,auth)
        if hosts!=False:
            length=len(hosts)
            for ho in range(length):
                res=check_ping(hosts[ho])
                back=check_dedup(helper,res)
                if back == True:
            	    event=helper.new_event(res, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
            	    ew.write_event(event)
                else:
            	    pass
        else:
            exit()
    else:
        exit()


def check_dedup(helper,result):
    state = helper.get_check_point(result)
    if state is None:
        #final_result.append(my_key)
        helper.save_check_point(result,"Indexed")
        return True
    else:
        return False

    """ ends here"""

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
