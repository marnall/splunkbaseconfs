#!/usr/bin/env python
# Dominique Vocat, 13.01.2017
# apply xslt to xml data

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
import splunk.Intersplunk
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import lxml.etree as ET

@Configuration(local=True)
class xslt_command(StreamingCommand):
    try:
        input = Option(require=False, default='_raw')
        transform = Option(require=False, default='') #either
        stylesheet = Option(require=False, default='') # or
        output = Option(require=False, default='transform')

    except Exception as e:
        import traceback
        stack =  traceback.format_exc()
        sys.stderr.write(str(e)+"\n"+str(stack))
        exit(0)
        
    def stream(self, records):
        for record in records:
            for fieldname in record.keys():
                if fieldname == self.input:
                    try:
                        print >> sys.stderr, "data we got passed to work on " + record[self.input] #just dump some generic infor blurb
                        dom = ET.fromstring(record[self.input])
                        if self.transform!="":
                            xslt = ET.fromstring(self.transform)
                        elif self.stylesheet!="":
                            scriptDir = sys.path[0]
                            stylesheetFileName = os.path.join(scriptDir,'..','stylesheet',self.stylesheet)
                            xslt = ET.parse(stylesheetFileName)
                        transform = ET.XSLT(xslt)
                        newdom = transform(dom)
                        record[self.output] = ET.tostring(newdom, pretty_print=True) # raw answer
                    except Exception as e:
                        sys.stderr.write(str(e))
                        #returnvalue = "returnvalue"
                        record["returnvalue"] = str(e)
            yield record
        
dispatch(xslt_command, sys.argv, sys.stdin, sys.stdout, __name__)
