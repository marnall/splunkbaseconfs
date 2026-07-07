#!/usr/bin/env python
"""
wrapper for the livedata api, mostly table.xml as csv or json whatever suits best.

parameter content specifies what content is pulled.

The PRTG API provides these contents:
content="sensortree"
content="sensors"
content="devices"
content="tickets"
content="messages"
content="values"
content="channels"
content="reports"
content="storedreports"
content="ticketdata"

Table Type	ID Required or Optional	Description	Object Types Allowed for the ID
content="sensortree"	optional	You will only get a part of the tree (the object with the given ID and all child objects below it).	Probe or group
content="sensors" or content="devices"	optional	You will only get the object with the given ID and all child objects below it.	Probe, group, or device
content="tickets" or content="messages"	optional	You will only get tickets or log file entries that are related to the object with the given ID or any child objects below it.	Any object
content="values" or content="channels"	required	You will get the data values (or channels, respectively) of the sensor selected by the ID.	Sensor
content="reports"	not used	This data table will always include all reports.	n/a
content="storedreports"	required	You will get a list of stored PDF files of the report selected by the ID.	Report
content="ticketdata"	required	You will get the history of the ticket selected by the ID.	Ticket

"""
from __future__ import print_function
import sys

def toSearchlog(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

import splunk.Intersplunk,os,ConfigParser
import time
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from ConfigParser import SafeConfigParser
import json
from json import JSONEncoder
import requests
import csv
import itertools
#import readconfig
from itertools import chain
import re

toSearchlog("port init")

@Configuration(local=True)
class prtgLiveData(GeneratingCommand):
    count = Option(require=False, validate=validators.Integer(0), default=500)
    id = Option(require=False, validate=validators.Integer(0), default=0)
    avg = Option(require=False, validate=validators.Integer(0), default=0)
    section_name = Option(require=False, default='default')
    content = Option(require=True)
    filter_status = Option(require=False)

    def generate(self):
        # Put your event  code here
        encoder = JSONEncoder(ensure_ascii=False, separators=(',', ':'))
        
        try:
            scriptDir = sys.path[0]
            configLocalFileName = os.path.join(scriptDir,'..','local','prtg.conf')
            parser = SafeConfigParser()
            parser.read(configLocalFileName)
            if not os.path.exists(configLocalFileName):
                exit(0)

        except Exception, e:
            import traceback
            stack =  traceback.format_exc()
            import splunk.Intersplunk
            splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

        # use user provided options or get [default] stanza options
        try:
            SERVER = parser.get(self.section_name, 'server')
            PROTOCOL = parser.get(self.section_name, 'protocol')
            USERNAME = parser.get(self.section_name, 'user')
            PASSWORD = parser.get(self.section_name, 'password')

        except Exception, e:
            import traceback
            stack =  traceback.format_exc()
            import splunk.Intersplunk
            splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

        #search_results = self.search_results_info
        #sdate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(search_results.search_et))))
        #edate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(search_results.search_lt))))

        if self.content == "sensordetails":
            url=PROTOCOL+"://"+SERVER+"/api/getsensordetails.json"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD,
                     'id': self.id}
            reply = requests.get( url, data=values, timeout=5, verify=False)
            mymsg = reply.content.decode('utf-8')
            returnvalue = json.loads(mymsg)
                        
            extrafields = {'_raw':mymsg,
                           '_time': time.time(),
                           'sourcetype':'prtg:livedata:sensordetails',
                           'host':SERVER,
                           'source':url+'?id='+str(self.id),
                           'id':self.id}

            yield dict(chain.from_iterable(d.iteritems() for d in (returnvalue['sensordata'], extrafields)))

        if self.content == "sensortypes":
            url=PROTOCOL+"://"+SERVER+"/api/sensortypesinuse.json"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD}
            reply = requests.get( url, data=values, timeout=5, verify=False)
            mymsg = reply.content.decode('utf-8')
            returnvalue = json.loads(mymsg)
            
            extrafields = {'_time': time.time(),
                           'sourcetype':'prtg:livedata:sensortypes',
                           'host':SERVER,
                           'source':url}

            for types in returnvalue['types']:
                for type in types:
                    yield dict(chain.from_iterable(d.iteritems() for d in ({'sensortype':type,'sensortype_description':types[type],'_raw': 'sensortype="'+type+'" sensortype_description="'+types[type]+'"',}, extrafields)))

        if self.content == "groups":
            url=PROTOCOL+"://"+SERVER+"/api/table.json"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD,
                     'content' : 'groups',
                     'output' : 'json',
                     'columns': 'objid,probe,group,name,downsens,partialdownsens,downacksens,upsens,warnsens,pausedsens,unusualsens,undefinedsens'
                     }
            reply = requests.get( url, data=values, timeout=5, verify=False)
            mymsg = reply.content.decode('utf-8')
            returnvalue = json.loads(mymsg)
            
            extrafields = {'sourcetype':'prtg:livedata:groups',
                           '_time': time.time(),
                           'treesize': returnvalue['treesize'],
                           'host':SERVER,
                           'source':url}

            for group in returnvalue['groups']:
                yield dict(chain.from_iterable(d.iteritems() for d in (group, extrafields, {'_raw': encoder.encode(group)})))

        if self.content == "messages":
            url=PROTOCOL+"://"+SERVER+"/api/table.json"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD,
                     'content' : 'messages',
                     'output' : 'json',
                     'count' : self.count,
                     'columns': 'objid,datetime,parent,type,name,status,message',
                     'id' : self.id
                     }
            reply = requests.get( url, data=values, timeout=60, verify=False) # might take a long while...
            mymsg = reply.content.decode('utf-8')
            returnvalue = json.loads(mymsg)
            
            extrafields = {'sourcetype':'prtg:livedata:messages',
                           'host':SERVER,
                           'source':url}

            for message in returnvalue['messages']:
                timestamp = (float(message["datetime_raw"]) - 25569)* 86400
                message['message'] = message['message'].split('>')[1].split('<')[0] # cryptic, cryptic. Text between first tag
                yield dict(chain.from_iterable(d.iteritems() for d in (message, extrafields, {'_raw': encoder.encode(message),'_time':timestamp})))

        if self.content == "status":
            url=PROTOCOL+"://"+SERVER+"/api/getstatus.htm"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD,
                     'id': '0'}
                     
            reply = requests.get( url, data=values, timeout=5, verify=False)
            
            extrafields = {'_raw':reply.content.decode('utf-8'),
                           '_time': time.time(),
                           'sourcetype':'prtg:livedata:status',
                           'host':SERVER,
                           'source':url+'?id='+str(self.id),
                           'id':self.id}
                           
            returnvalue = json.loads( reply.content.decode('utf-8') )
            
            yield dict(chain.from_iterable(d.iteritems() for d in (returnvalue, extrafields)))       

        #sensors limited to alarms: &columns=device,sensor&filter_status=5&filter_status=13&filter_status=14
        #filter_status values: Unknown=1, Collecting=2, Up=3, Warning=4, Down=5, NoProbe=6, PausedbyUser=7, PausedbyDependency=8, PausedbySchedule=9, Unusual=10, PausedbyLicense=11, PausedUntil=12, DownAcknowledged=13, DownPartial=14
        if self.content == "sensors":
            url=PROTOCOL+"://"+SERVER+"/api/table.json"
            values={ 'username' : USERNAME,
                     'password' : PASSWORD,
                     'content' : 'sensors',
                     'output' : 'json',
                     'count' : self.count,
                     'filter_status':self.filter_status,
                     'columns': 'objid,probe,group,device,sensor,status,message,lastvalue,priority,favorite,lastdown',
                     'id' : self.id
                     }
            reply = requests.get( url, data=values, timeout=60, verify=False) # might take a long while...
            mymsg = reply.content.decode('utf-8')
            returnvalue = json.loads(mymsg)
            
            extrafields = {'sourcetype':'prtg:livedata:sensors',
                           'host':SERVER,
                           'source':url,
                           '_time': time.time(),
                           'num_results': returnvalue['treesize']}

            for sensor in returnvalue['sensors']:
                timestamp = (float(sensor["lastdown_raw"]) - 25569)* 86400
                sensor['message'] = sensor['message'].split('>')[1].split('<')[0] # cryptic, cryptic. Text between first tag
                yield dict(chain.from_iterable(d.iteritems() for d in (sensor, extrafields, {'_raw': encoder.encode(sensor),'_time':timestamp})))

        pass

dispatch(prtgLiveData, sys.argv, sys.stdin, sys.stdout, __name__)
