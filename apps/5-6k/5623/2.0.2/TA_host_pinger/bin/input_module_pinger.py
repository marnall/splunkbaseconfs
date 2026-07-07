# encoding = utf-8
import requests
import sys
import os
import json
import time
import datetime
from ping3 import ping, verbose_ping
import base64
import subprocess

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


def request_response(sid,auth,lookup_header):
    ssid=sid
    #b64_auth = base64.b64encode(auth.encode()).decode("utf-8")
    params = {'output_mode':'json','count':0}
    url = 'https://localhost:8089/services/search/jobs/{}/results/'.format(ssid)
    response = requests.get(url, params=params, verify=False, headers=auth)
    if response.status_code==200:
        output=json.loads(response.text)
        hosts=output["results"]
        length=len(hosts)
        host_list=[]
        for i in range(length):
            extract=hosts[i][lookup_header]
            host_list.append(extract)
        return host_list
    else:
        return False


def check_ping(hosts):
	hostname=hosts
    command=['timeout', "1", 'ping',"-c1",hostname]
    response=subprocess.call(command,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    if response == 0:
        pingstatus = "Network Active"
    else:
        pingstatus = "Network Error"
	curr_clock = str(datetime.datetime.now())
	data=curr_clock+","+hostname+","+pingstatus
	return data




def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # lookup_name = definition.parameters.get('lookup_name', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""
    opt_lookup_name = helper.get_arg('lookup_name')
    opt_lookup_file_header = helper.get_arg('lookup_file_header')
    global_account = helper.get_arg('account')
    global_authentication_token= global_account['password']
    token='Bearer '+ global_authentication_token
    auth={'Authorization' : token}
    ssid=request_search(auth,opt_lookup_name)
    if ssid!=False:
        hosts=request_response(ssid,auth,opt_lookup_file_header)
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
