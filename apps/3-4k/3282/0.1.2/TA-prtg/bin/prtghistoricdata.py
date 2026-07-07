#!/usr/bin/env python

import sys,splunk.Intersplunk,os,ConfigParser
import time
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from ConfigParser import SafeConfigParser
import json
from json import JSONEncoder
import requests
import csv
import itertools
#import readconfig

@Configuration(local=True)
class prtgHistoricData(GeneratingCommand):
    count = Option(require=False, validate=validators.Integer(0), default=500)
    id = Option(require=False, validate=validators.Integer(0), default=0)
    avg = Option(require=False, validate=validators.Integer(0), default=0)
    section_name = Option(require=False, default='default')

    def generate(self):
        # Put your event  code here
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

        # use user provided options or get [default] stanza options
        try:
            SERVER = parser.get(self.section_name, 'server')
            PROTOCOL = parser.get(self.section_name, 'protocol')
            USERNAME = parser.get(self.section_name, 'user')
            PASSWORD = parser.get(self.section_name, 'password')

        except Exception, e:
            import traceback
            stack =  traceback.format_exc()
            #splunk.Intersplunk.generateErrorResults("Error : Traceback: '%s'. %s" % (e, stack))

        search_results = self.search_results_info
        
        sdate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(search_results.search_et))))
        edate = str(time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(float(search_results.search_lt))))

        url=PROTOCOL+"://"+SERVER+"/api/historicdata.csv"
        values={ 'username' : USERNAME,
                 'password' : PASSWORD,
                 'id': self.id,
                 'sdate' : sdate,
                 'edate' : edate,
                 'avg' : self.avg,
                 'count': self.count}

        reply = requests.get( url, data=values, timeout=5, verify=False)
        mydictreader = csv.DictReader( reply.text.splitlines(), delimiter=',', quotechar='"' )
        from itertools import chain
        for row in mydictreader:
            # remove some fields, formate a proper _time by calculating epoch using this formula(row[Date Time (RAW)] - 25569)* 86400)
            try:
                extrafields = {'_raw':row
                               ,'sourcetype':'prtg:historicdata'
                               ,'host':SERVER
                               ,'source':url
                               ,'_time':(float(row["Date Time(RAW)"]) - 25569)* 86400 }
            except Exception, e:
                #import traceback
                #stack =  traceback.format_exc()
                return #just hide it...
            #clean up
            row.pop("Date Time(RAW)", None)
            row.pop("Date Time", None)
            #push out
            yield dict(chain.from_iterable(d.iteritems() for d in (row, extrafields)))       
        pass

dispatch(prtgHistoricData, sys.argv, sys.stdin, sys.stdout, __name__)
