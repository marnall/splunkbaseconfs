#!/usr/bin/env python
# just glueing snippets together, Dominique Vocat 2017

import sys,splunk.Intersplunk,os,ConfigParser
import time
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from ConfigParser import SafeConfigParser
from cssselect import GenericTranslator, SelectorError
from lxml.etree import fromstring

@Configuration(local=True)
class cssselector(StreamingCommand): 
    input = Option(require=False, default='_raw')
    output = Option(require=False, default='cssselectorresults')        
    item = Option(require=True, default='href')
    selector = Option(require=True, default='')
    def stream(self, records):
        print >> sys.stderr, "looking for items in field "+self.input
        for record in records:
            for fieldname in record.keys():
                if fieldname == self.input:
                    try:
                        expression = GenericTranslator().css_to_xpath(self.selector)
                        record['expression'] = expression
                        document = fromstring(record[self.input]) # content we filter
                        count = 0
                        items = []
                        for e in document.xpath(expression):
                            items.append( e.get(self.item) )
                            count += 1
                            #print >> sys.stderr, e.get(self.item)
                        record['numresults'] = count
                        record[self.output] = items
                    except SelectorError:
                        record['error'] ='Invalid selector.'
                    
                    #get the page
                    #r = requests.get(record['url'], timeout=15, verify=False, headers={'User-Agent': 'Mozilla/5.0 (X11; OpenBSD i386) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'}) #cheeky? yeah.

            yield record
        
dispatch(cssselector, sys.argv, sys.stdin, sys.stdout, __name__)
