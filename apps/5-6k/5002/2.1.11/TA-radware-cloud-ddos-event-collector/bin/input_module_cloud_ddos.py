# encoding = utf-8

import os
import sys
import time
import datetime
import json
import http.client, urllib.parse, urllib.request
import re

def validate_input(helper, definition):
    pass

def getSessionToken(helper,credentials):

    cookies={}
    
    connection = http.client.HTTPSConnection("ddos.radwarecloud.com",443)    
    payload = "{\"u\":\"" + credentials['username'] + "\",\"p\":\"" + credentials['password'] + "\"}"
    headers = {'Content-Type': "application/json",'Accept': 'application/json, text/plain, */*'}
    
    try:
        connection.request("POST", "/api/auth/", payload, headers)
        response = connection.getresponse()
    finally:
            connection.close()
            
    if response.status != 200:
        raise Exception("%d (%s) in Session Token" % (response.status, response.reason))
    
    SetCookie = response.getheader('Set-Cookie')

    try:
        cookies['sessionID'] = re.search('.*sessionid=(.+?);', SetCookie).group(1)
        cookies['csrftoken'] = re.search('.*csrftoken=(.+?);', SetCookie).group(1)
    except AttributeError:
        raise Exception("Session ID not found")
        
    return cookies

def getSecurityEvents(helper, Token, timelower, timeupper, account_id):

    events ={}
    
    hdrs = {
            'Cookie': 'sessionid='+Token['sessionID']+";csrftoken="+Token['csrftoken'],
            'Content-Type': 'application/json;charset=UTF-8'
            }
    
    url = "https://ddos.radwarecloud.com/api/alerts/security/?type=account&from="+str(timelower)+"&to="+str(timeupper)+"&severity=INFO,LOW,MEDIUM,HIGH,CRITICAL&id="+account_id
   
    req = urllib.request.Request(url,headers=hdrs, method="GET")
    
    try:
        response = urllib.request.urlopen(req)
        events = response.read().decode("utf8")
    finally:
            response.close()
    
    if response.code != 200:
        raise Exception(" %d (%s) in Security Events" % (response.code, response.msg))
    
    return events
    
def getOperationalEvents(helper, Token, timelower, timeupper, account_id):

    events ={}
    
    hdrs = {
            'Cookie': 'sessionid='+Token['sessionID']+";csrftoken="+Token['csrftoken'],
            'Content-Type': 'application/json;charset=UTF-8'
            }
    
    url = "https://ddos.radwarecloud.com/api/alerts/operational/?type=account&from="+str(timelower)+"&to="+str(timeupper)+"&severity=HIGH,CRITICAL&id="+account_id
   
    req = urllib.request.Request(url,headers=hdrs, method="GET")
    
    try:
        response = urllib.request.urlopen(req)
        events = response.read().decode("utf8")
    finally:
            response.close()
    
    if response.code != 200:
        raise Exception(" %d (%s) in Operational Events" % (response.code, response.msg))
    
    return events

def LogOut(helper, Token):

    uri = "/logout"
    hdrs = {
            'Cookie': 'sessionid='+Token['sessionID']+";csrftoken="+Token['csrftoken'],
            'Content-Type': 'application/json;charset=UTF-8'
            }
            
    connection = http.client.HTTPSConnection("ddos.radwarecloud.com",443,timeout=10)

    try:
        connection.request("GET", uri, " " ,hdrs)
        response = connection.getresponse()
    finally:
            connection.close()

    if response.status != 200:
        raise Exception(" %d (%s) in Log Out" % (response.status, response.reason))

def needed_items(key):
    switcher={
        'site_name':1,
        'policy_name':1,
        "sources":3,
        "attack_action":1,
        "account_name":1,
        "category":1,
        "targets":4,
        "bw_pps":1,
        "report_id":1,
        "type":1,
        "risk":1,
        "start_time":2,
        "name":1,
        "attack_bw_units":1,
        "end_time":2,
        "attack_bw":5
     }
    return switcher.get(key,0)

def getAccountID(cookies):

    hdrs = {
        'Cookie': 'sessionid=' + cookies['sessionID'] + ";csrftoken=" + cookies['csrftoken'],
        'Content-Type': 'application/json;charset=UTF-8'
    }

    url = "https://ddos.radwarecloud.com/api/accounts?tree"

    req = urllib.request.Request(url, headers=hdrs, method="GET")

    response = urllib.request.urlopen(req)
    accounts= json.loads(response.read().decode("utf8"))
    accountID = accounts["accounts"][0]["account_id"]
    response.close()

    if response.code != 200:
        raise Exception(" %d (%s) in Get Account ID" % (response.code, response.msg))

    return accountID
    
def get_unit_bw(key):
    switcher={
        'Kbps':1000,
        'Mbps':1000000,
        'Gbps':1000000000
     }
    return switcher.get(key,1)

def format_event(helper, ew,dict_events):
    item=1
    build_event=""
    
    while item < len(dict_events['security']):
        build_event="_time="+str(dict_events['security'][item]['timestamp']['_date_time'])+","
        build_event=build_event+"type="+dict_events['security'][item]['type']+","
        
        build_event=build_event+"site_name="+str(dict_events['security'][item]['metadata']['site_name'])+","
        build_event=build_event+"policy_name="+str(dict_events['security'][item]['metadata']['policy_name'])+","
        
        if dict_events['security'][item]['metadata']['sources'] != "Unknown":
            sources=re.search('^(.+?):(.+?)$', dict_events['security'][item]['metadata']['sources'])
            build_event=build_event+"srcIP="+sources.group(1)+",srcPort="+sources.group(2)+","
        else:
                    build_event=build_event+"srcIP="+"Multiple"+",srcPort="+"Multiple"+","
        
        build_event=build_event+"attack_action="+str(dict_events['security'][item]['metadata']['attack_action'])+","
        build_event=build_event+"account_name="+str(dict_events['security'][item]['metadata']['account_name'])+","
        build_event=build_event+"category="+str(dict_events['security'][item]['metadata']['category'])+","
        
        if dict_events['security'][item]['metadata']['targets'] != "0.0.0.0":
            targets=re.search('^(.+?):(.+?)$', dict_events['security'][item]['metadata']['targets'])
            build_event=build_event+"dstIP="+targets.group(1)+",dstPort"+targets.group(2)+","
        else:
            build_event=build_event+"dstIP=Multiple,dstPort=Multiple,"
        
        build_event=build_event+"bw_pps="+str(dict_events['security'][item]['metadata']['bw_pps'])+","
        build_event=build_event+"report_id="+str(dict_events['security'][item]['metadata']['report_id'])+","
        build_event=build_event+"type="+str(dict_events['security'][item]['metadata']['type'])+","
        build_event=build_event+"risk="+str(dict_events['security'][item]['metadata']['risk'])+","
        
        if re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+.*", dict_events['security'][item]['metadata']['start_time']['_date_time']):
            begins=(int(time.mktime(datetime.datetime.strptime(dict_events['security'][item]['metadata']['start_time']['_date_time'], "%Y-%m-%dT%H:%M:%S%z").timetuple()))*1000)
        else:
            begins=(int(time.mktime(datetime.datetime.strptime(dict_events['security'][item]['metadata']['start_time']['_date_time'], "%Y-%m-%dT%H:%M:%S.%f%z").timetuple()))*1000)
        
        build_event=build_event+"name="+str(dict_events['security'][item]['metadata']['name'])+","
        build_event=build_event+"attack_bw_units="+str(dict_events['security'][item]['metadata']['attack_bw_units'])+","    
        
        if re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+.*", dict_events['security'][item]['metadata']['end_time']['_date_time']):
            ends=(int(time.mktime(datetime.datetime.strptime(dict_events['security'][item]['metadata']['end_time']['_date_time'], "%Y-%m-%dT%H:%M:%S%z").timetuple()))*1000)
        else:
            ends=(int(time.mktime(datetime.datetime.strptime(dict_events['security'][item]['metadata']['end_time']['_date_time'], "%Y-%m-%dT%H:%M:%S.%f%z").timetuple()))*1000)
        duration=round((ends-begins)/1000)
        bandwidth_unit=get_unit_bw(dict_events['security'][item]['metadata']['attack_bw_units'])
        bw_log=int(dict_events['security'][item]['metadata']['attack_bw'])*bandwidth_unit
        
        build_event=build_event+"attack_bw="+str(bw_log)+',duration='+str(duration)
                
        event=helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=build_event)
        ew.write_event(event)
        item+=1
    
    item=0
    build_event=""    
    
    while item < len(dict_events['operational']):
        build_event="_time="+str(dict_events['operational'][item]['timestamp']['_date_time'])+","
        build_event=build_event+"type="+dict_events['operational'][item]['type']+","
        build_event=build_event+"origin="+dict_events['operational'][item]['origin']+","
        build_event=build_event+"code="+dict_events['operational'][item]['code']+","
        build_event=build_event+"id="+dict_events['operational'][item]['_id']['_oid']+","
        build_event=build_event+"severity="+str(dict_events['operational'][item]['severity'])+","
        if 'site_name' in dict_events['operational'][item]['metadata']:
            build_event=build_event+"site_name="+dict_events['operational'][item]['metadata']['site_name']+","
        build_event=build_event+"description="+dict_events['operational'][item]['metadata']['description']
                
        event=helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=build_event)
        ew.write_event(event)
        item+=1

def collect_events(helper, ew):
    
    stanza=helper.get_input_stanza()
    
    for key in stanza:
        interval=int(stanza[key]['interval'])
        pass
    now=int(round(time.time() * 1000))
    past=now-(interval*1000)
    
    credentials={}
    dict_events={}
    credentials['username']=helper.get_arg('username')
    credentials['password'] = helper.get_arg('password')
    
    cookies = getSessionToken(helper,credentials)
    credentials['account_id']=getAccountID(cookies)
 
    security_events=getSecurityEvents(helper,cookies,past,now,credentials['account_id'])
    
    dict_events['security']=json.loads(security_events)['reply']
    
    operational_events=getOperationalEvents(helper,cookies,past,now,credentials['account_id'])
    dict_events['operational']=json.loads(operational_events)['reply']
    
    format_event(helper, ew,dict_events)
