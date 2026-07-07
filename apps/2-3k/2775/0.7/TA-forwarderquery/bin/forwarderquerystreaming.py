#!/usr/bin/env python

import sys,splunk.Intersplunk,os,ConfigParser
import time
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from ConfigParser import SafeConfigParser
import json
from json import JSONEncoder
import requests
import csv
import itertools
import ast
from requests.auth import HTTPBasicAuth

@Configuration(local=True)
class forwarderquerystreaming(StreamingCommand):
    try:
        section_name = Option(require=False, default='default')
        data = Option(require=False, default='')
        api = Option(require=True, default='')
        method = Option(require=False, default='GET')

        scriptDir = sys.path[0]
        configLocalFileName = os.path.join(scriptDir,'..','local','forwarderquery.conf')
        parser = SafeConfigParser()
        parser.read(configLocalFileName)
        if not os.path.exists(configLocalFileName):
            exit(0)

    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        sys.stderr.write(str(e)+"\n"+str(stack))
        exit(0)
        
    def stream(self, records):
        auth = HTTPBasicAuth( self.parser.get(self.section_name, 'user'), self.parser.get(self.section_name, 'password'))
        for record in records:
            for fieldname in record.keys():
                if fieldname == "host":
                    print >> sys.stderr, "HTTP Method used: " + self.method #um, something is up with the url encoded parameters, need to test some.
                    try:
                        if self.method.upper() == 'GET':
                            print >> sys.stderr, "https://"+record['host']+":8089"+self.api+" - "+self.data
                            if self.data != "":
                                r = requests.get("https://"+record['host']+":8089"+self.api, timeout=1, data=json.dumps(self.data), verify=False, auth=auth)
                            else:
                                r = requests.get("https://"+record['host']+":8089"+self.api, timeout=1, verify=False, auth=auth)
                        if self.method.upper() == 'POST':
                            print >> sys.stderr, "https://"+record['host']+":8089"+self.api+" - "+self.data
                            if self.data != "":
                                r = requests.post("https://"+record['host']+":8089"+self.api, timeout=1, data=self.data, verify=False, auth=auth)
                            else:
                                r = requests.post("https://"+record['host']+":8089"+self.api, timeout=1, verify=False, auth=auth)
                        if self.method.upper() == 'DELETE':
                            print >> sys.stderr, "https://"+record['host']+":8089"+self.api+" - "+self.data
                            if self.data != "":
                                r = requests.delete("https://"+record['host']+":8089"+self.api, timeout=1, data=self.data, verify=False, auth=auth)
                            else:
                                r = requests.delete("https://"+record['host']+":8089"+self.api, timeout=1, verify=False, auth=auth)
                        returnvalue = "returnvalue"
                        record[returnvalue] = r.text # raw answer
                    except Exception, e:
                        sys.stderr.write(str(e))
                        returnvalue = "returnvalue"
                        record[returnvalue] = str(e)
            yield record
        
dispatch(forwarderquerystreaming, sys.argv, sys.stdin, sys.stdout, __name__)
