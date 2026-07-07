#!/usr/bin/env python
# just glueing snippets together, Dominique Vocat 2017

import sys,splunk.Intersplunk,os,ConfigParser
import time
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from ConfigParser import SafeConfigParser
import json
from json import JSONEncoder
import requests
from readability.readability import Document
from lxml import html
import pyteaser

@Configuration(local=True)
class readability(StreamingCommand):
    input = Option(require=False, default='url')
    outputraw = Option(require=False, default='False')
    fieldforraw = Option(require=False, default='_raw')
    def stream(self, records):
        #auth = HTTPBasicAuth( self.parser.get(self.section_name, 'user'), self.parser.get(self.section_name, 'password'))
        for record in records:
            for fieldname in record.keys():
                if fieldname == self.input:                    
                    #get the page
                    r = requests.get(record[self.input], timeout=15, verify=False, headers={'User-Agent': 'Mozilla/5.0 (X11; OpenBSD i386) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'}) #cheeky? yeah.
                    #record["should_output_raw"] = self.outputraw #was useful while debuging
                    if self.outputraw != "False":
                        record[self.fieldforraw] = r.text # raw answer
                    
                    #make it readable using readability
                    doc = Document(r.text)
                    record["readable_html"] = doc.summary()
                    record["readable_short_title"] = doc.short_title()
                    record["readable_title"] = doc.title()
                    #record["readable_content"] = doc.content()
                    
                    #extract plain text with lxml
                    htmldoc = html.fromstring(doc.summary())
                    record["readable_plaintext"] = str(htmldoc.text_content())
                    
                    #summarize with pyteaser
                    summaries = pyteaser.Summarize(record["readable_title"], record["readable_plaintext"])
                    record["readable_summary"] = summaries
                    record["readable_summary_length"] = sum(len(s) for s in summaries) #do it here because its easier in python then spl
            yield record
        
dispatch(readability, sys.argv, sys.stdin, sys.stdout, __name__)
