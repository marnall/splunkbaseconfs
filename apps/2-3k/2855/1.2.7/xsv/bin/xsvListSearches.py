#
# Copyright 2012-2016 Scianta Analytics LLC   All Rights Reserved.  
# Reproduction or unauthorized use is prohibited. Unauthorized
# use is illegal. Violators will be prosecuted. This software 
# contains proprietary trade and business secrets.            
#
import fnmatch
import os
import re
import csv
import sys
import saUtils
import platform,time
import splunk.Intersplunk as si
from xml.dom.minidom import parseString
import splunk.rest

#import urllib
#import time
#import os
#import re
#import csv
#import sys
#import saUtils
#import splunk.Intersplunk as si
#from time import localtime,strftime
##from xml.dom import minidom
#import httplib2
#from xml.dom.minidom import parseString
#import json


def search_xsfindbestconcept(theApp, theSearch):
    skipfirst = 1;
    foundone = 0;
    it = re.finditer('xsfindbestconcept', theSearch, re.IGNORECASE)
    startidx = 0
    endidx = 0
    for match in it:
        foundone = 1;
        endidx = match.start()

        if (skipfirst == 0):
            if (startidx == endidx):
                startidx = len(theSearch)
            tmp = theSearch[int(startidx):int(endidx)]
            parse_xsfindbestconcept(theApp, tmp)
            startidx = endidx
        else:
            skipfirst = 0;
            startidx = endidx

    if (foundone == 1):
        endidx = len(theSearch)
        tmp = theSearch[int(startidx):int(endidx)]
        parse_xsfindbestconcept(theApp, tmp)
    return

def parse_xsfindbestconcept(theApp, commandString):
    theCommand = "xsFindBestConcept"

    # get the field
    theField = ""
    p = re.compile("xsfindbestconcept ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(commandString)
    if m:
       theField  = m.group(1)

    # check for container
    theContainer = ""
    p = re.compile("xsfindbestconcept .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(commandString)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsfindbestconcept .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(commandString)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsfindbestconcept .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(commandString)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsfindbestconcept .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(commandString)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xswhere(theApp, theSearch):
    p = re.compile("xswhere", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xswhere(theApp, theSearch)
    return

def parse_xswhere(theApp, theSearch):
    theCommand = "xsWhere"

    # get the field
    theField = ""
    p = re.compile("xswhere ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xswhere .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xswhere .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xswhere .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xswhere .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xscreateudcontext(theApp, theSearch):
    p = re.compile("xscreateudcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xscreateudcontext(theApp, theSearch)
    return

def parse_xscreateudcontext(theApp, theSearch):
    theCommand = "xsCreateUDContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xscreateudcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xscreateudcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xscreateudcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xscreateudcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return


def search_xscreateddcontext(theApp, theSearch):
    p = re.compile("xscreateddcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xscreateddcontext(theApp, theSearch)
    return

def parse_xscreateddcontext(theApp, theSearch):
    theCommand = "xsCreateDDContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xscreateddcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xscreateddcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xscreateddcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xscreateddcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theScope  = ""
    else:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xscreateadcontext(theApp, theSearch):
    p = re.compile("xscreateadcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xscreateadcontext(theApp, theSearch)
    return
def parse_xscreateadcontext(theApp, theSearch):
    theCommand = "xsCreateADContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xscreateadcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xscreateadcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xscreateadcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xscreateadcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theScope  = ""
    else:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xscreatecdcontext(theApp, theSearch):
    p = re.compile("xscreatecdcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xscreatecdcontext(theApp, theSearch)
    return

def parse_xscreatecdcontext(theApp, theSearch):
    theCommand = "xsCreateCDContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xscreatecdcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xscreatecdcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xscreatecdcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xscreatecdcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theScope  = ""
    else:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsupdateudcontext(theApp, theSearch):
    p = re.compile("xsupdateudcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsupdateudcontext(theApp, theSearch)
    return

def parse_xsupdateudcontext(theApp, theSearch):
    theCommand = "xsUpdateUDContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xsupdateudcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsupdateudcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsupdateudcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsupdateudcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsupdateddcontext(theApp, theSearch):
    p = re.compile("xsupdateddcontext", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsupdateddcontext(theApp, theSearch)
    return

def parse_xsupdateddcontext(theApp, theSearch):
    theCommand = "xsUpdateDDContext"
    theField = ""

    # check for container
    theContainer = ""
    p = re.compile("xsupdateddcontext.*container=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsupdateddcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    theContext = ""
    p = re.compile("xsupdateddcontext.*name=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)
       if (theContext is None):
           p = re.compile("xsupdateddcontext.*name=([\'\"])([a-zA-Z0-9_.-]+)(\1)*", re.IGNORECASE);
           m  = p.search(theSearch)
           if m:
               theContext  = m.group(2)

    # check for class
    theClass = ""
    p = re.compile("xsupdateddcontext.*class=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsupdateddcontext.*scope=([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsgetcompatibility(theApp, theSearch):
    p = re.compile("xsgetcompatibility", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsgetcompatibility(theApp, theSearch)
    return

def parse_xsgetcompatibility(theApp, theSearch):
    theCommand = "xsGetCompatibility"

    # get the field
    theField = ""
    p = re.compile("xsgetcompatibility ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsgetcompatibility .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsgetcompatibility .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsgetcompatibility .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsgetcompatibility .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope

def search_xsdiscovertrend(theApp, theSearch):
    p = re.compile("xsdiscovertrend", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsdiscovertrend(theApp, theSearch)
    return

def parse_xsdiscovertrend(theApp, theSearch):
    theCommand = "xsDiscoverTrend"

    # get the field
    theField = ""
    p = re.compile("xsdiscovertrend ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsdiscovertrend .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsdiscovertrend .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsdiscovertrend .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsdiscovertrend .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsdisplaywhere(theApp, theSearch):
    p = re.compile("xsdisplaywhere", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsdisplaywhere(theApp, theSearch)
    return

def parse_xsdisplaywhere(theApp, theSearch):
    theCommand = "xsDisplayWhere"

    # get the field
    theField = ""
    p = re.compile("xsdisplaywhere ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsdisplaywhere .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsdisplaywhere .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsdisplaywhere .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsdisplaywhere .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsgetwherecix(theApp, theSearch):
    p = re.compile("xsgetwherecix", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsgetwherecix(theApp, theSearch)
    return

def parse_xsgetwherecix(theApp, theSearch):
    theCommand = "xsGetWhereCIX"

    # get the field
    theField = ""
    p = re.compile("xsgetwherecix ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsgetwherecix .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsgetwherecix .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsgetwherecix .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsgetwherecix .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsnormalize(theApp, theSearch):
    p = re.compile("xsnormalize", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsnormalize(theApp, theSearch)
    return

def parse_xsnormalize(theApp, theSearch):
    theCommand = "xsNormalize"

    # get the field
    theField = ""
    p = re.compile("xsnormalize ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsnormalize .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsnormalize .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsnormalize .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsnormalize .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

def search_xsfindmembership(theApp, theSearch):
    p = re.compile("xsfindmembership", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
        parse_xsfindmembership(theApp, theSearch)
    return

def parse_xsfindmembership(theApp, theSearch):
    theCommand = "xsFindMembership"

    # get the field
    theField = ""
    p = re.compile("xsfindmembership ([a-zA-Z0-9_.-]+) *", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theField  = m.group(1)

    theContainer = ""
    # check for container
    p = re.compile("xsfindmembership .* in ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContainer  = m.group(1)

    # check for context
    theContext = ""
    p = re.compile("xsfindmembership .* from ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theContext  = m.group(1)

    # check for class
    theClass = ""
    p = re.compile("xsfindmembership .* by ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if (m is None):
       theClass=""
    else:
      if (m.group(1) is None):
        theClass = ""
      else:
        theClass  = m.group(1)

    # check for scope
    theScope = ""
    p = re.compile("xsfindmembership .* scoped ([a-zA-Z0-9_.-]+)*", re.IGNORECASE);
    m  = p.search(theSearch)
    if m:
       theScope  = m.group(1)

    print title + "," + theApp + "," + theSearch + "," + theCommand + "," + theContainer + "," + theContext + "," + theClass + "," + theField + "," + theScope
    return

if __name__ == '__main__':

    settings = saUtils.getSettings(sys.stdin)
    endpoint = '/services/saved/searches?count=0'
    response, content = splunk.rest.simpleRequest(endpoint, method='GET', sessionKey=settings['sessionKey'], raiseAllErrors=False)

    if response.status != 200:
        print response.status

    dom = parseString(content)
    entries = dom.getElementsByTagName('entry')
    print "Title, App, Search, Command, Container, Context, Class, Field, Scope"
    #print "Title"
    for entry in entries:
        #
        # Get the Title
        #
        titleXML = entry.getElementsByTagName('title')[0].toxml()
        title=titleXML.replace('<title>','').replace('</title>','')

        #
        # Get the app
        #
        content = entry.getElementsByTagName('content')[0].toxml()
        p = re.compile("name=\"app\"\>([^\<]+)\<")
        theApp = p.search(content).group(1)


        #
        # Get the search - problem with commas in search
        #
        p = re.compile("name=\"search\"\>([^\<]+)\<")
        m  = p.search(content)
        theSearch = ""

        if m:
           dummy = ""
        else:
            p = re.compile("name=\"search\"\><!\[CDATA\[(.*?)\]\]>\<")
            #p = re.compile("name=\"search\"\>(<!\[CDATA\[(.*?)\]\]>)\<")
            m  = p.search(content)


        if m:
           # "search" can contain quote, commas, or newline
           # Wrap "search" in quotes and escape any embedded quotes
           #theSearch = '"' + m.group(1).replace('"','\"') + '"'
           #theSearch = m.group(1).replace('"','\"').replace(',','\"\,\"')
           #theSearch = '"' + m.group(1).replace('"','\"').replace(',','\"\,\"') + '"'
           #theSearch = '"' + m.group(1).replace('"','\"').replace(',','.') + '"'
           #print theSearch
           #theSearch = '"' + m.group(1) + '"'

           theSearch = m.group(1).replace(',','.')

           search_xswhere(theApp, theSearch)
           search_xsfindbestconcept(theApp, theSearch)
           search_xscreateudcontext(theApp, theSearch)
           search_xscreateddcontext(theApp, theSearch)
           search_xscreateadcontext(theApp, theSearch)
           search_xscreatecdcontext(theApp, theSearch)
           search_xsupdateudcontext(theApp, theSearch)
           search_xsupdateddcontext(theApp, theSearch)
           search_xsgetcompatibility(theApp, theSearch)
           search_xsdiscovertrend(theApp, theSearch)
           search_xsdisplaywhere(theApp, theSearch)
           search_xsgetwherecix(theApp, theSearch)
           search_xsnormalize(theApp, theSearch)
           search_xsfindmembership(theApp, theSearch)

        if platform.system() == 'Windows':
            sys.stdout.flush()
            time.sleep(1.0)

