######################################
# File: osc_query.py                 #
# Author: OSC                        #
# Version: 1.3                       #
# Date: 29AUG2019                    #
# Purpose: Connect Splunk to OSC API #
######################################

import argparse, re
from datetime import datetime
import sys
import ipcalc
import splunk.Intersplunk
import splunklib.client as splclient

#This is the top level calss for building an OSC Query object. This oscq_b top
#level object class should not be used by itself. This class as a whole builds
#the object that will be given to the query execution class.
class oscq_b:

    def __init__(self):
        pass
#This sub class is all about validating the query to be turned into
#an object for the execution class.
class qa:

    def __init__(self, o_args):
        self.args = qa.parseArgs(self, o_args)
        self = qa.valSearch(self)
        self = qa.buildQ(self)
        self = qa.getAPI(self)

    #I think this one is pretty self explanatory
    def getAPI(self):
        results,dummyresults,my_settings = splunk.Intersplunk.\
                getOrganizedResults()
        session_key = str(my_settings.get('sessionKey'))
        splunkService = splclient.connect(token=session_key, app=\
                "Splunk_TA_OSContext")
        storage_passwords = splunkService.storage_passwords
        for credential in storage_passwords:
            if credential.content.get('username') == "OSC_API_KEY":
                self.token = str(credential.content.get('clear_password'))
        return self
        

    #There is nothing particularly special about this - it is a standard
    #argument parser - but it was put here in the validator to clean up
    #the main function and lessen the burden of compilation at runtime
    def parseArgs(self, input):
        temp = argparse.ArgumentParser()
        temp.add_argument('-d', help='Domain to Query')
        temp.add_argument('-i', help='IP Value to Query')
        temp.add_argument('-w', help="Use this to specify a CIDR")
        temp.add_argument('-s', default="2010-01-01T00:00:00", help='Start\
                Time in UTC ISO Format')
        temp.add_argument('-e', default=datetime.utcnow().replace\
                (microsecond=0).isoformat(), help='End Time in UTC ISO\
                Format')
        temp.add_argument('-n', default=100, help='Number of results')
        temp.add_argument('-o', default="last_seen:desc", help="sort order")
        temp.add_argument('-r', default="last_seen", help="Date Range: date\
                OR last_seen")
        temp.add_argument('-k', help='API Key')
        temp.add_argument('-m', help='Only used for gui_workflow')
        temp.add_argument('-l', help='Lucene Syntax query')
        temp.add_argument('-t', help='Record Type')
        temp.add_argument('-f', default="ALL", help='Fields')
        temp.add_argument('-y', help='start_time in epoch')
        temp.add_argument('-z', help='end_time in epoch')
        return temp.parse_args()
    
    #This is the main search validator. The search is going to be
    #checked to ensure that there is actually something the user
    #is searching for. It will also make sure the search is not
    #contain conflicting values that would lead to a search failure.
    #The GUI led search takes care of making sure
    #the necessary values are filled out - this is more focused on
    #the power users who launch from the spl-line
    def valSearch(self):
        valzero = qa.valSearch0(self)
        valone = qa.valSearch1(self)
        if valzero != "valid":
            print(valzero)
            sys.exit(3)
        elif valone != "valid":
            print(valone)
            sys.exit(3)
        else:
            self = qa.time_and_flow(self)
            return self
    

    #Are we actually searching for something?
    def valSearch0(self):
        if (self.args.d, self.args.i, self.args.w, self.args.m,\
                self.args.l) == (None, None, None, None, None):
            return "What are you serching for?"
        else:
            return "valid"
    
    #You can only do one thing at a time...
    def valSearch1(self):
        if (self.args.d and self.args.i):
            return "You may only ue one of -d, -i, or -w simultaneously"
        elif (self.args.d and self.args.w):
            return "You may only ue one of -d, -i, or -w simultaneously"
        elif (self.args.i and self.args.w):
            return "You may only ue one of -d, -i, or -w simultaneously"
        elif (self.args.d and self.args.l):
            return "You may not use lucene syntax with -d, -i, or -w\
                    options"
        elif (self.args.i and self.args.l):
            return "You may not use lucene syntax with -d, -i, or -w\
                    options"
        elif (self.args.w and self.args.l):
            return "You may not use lucene syntax with -d, -i, or -w\
                    options"
        else:
            return "valid"
    
    #Splunk deals in epochs - so we will convert time to ISO8601 as well
    #as make sure the search can be run if being executed as a workflow
    #action
    def time_and_flow(self):
        self = qa.convTime(self)
        if self.args.m:
            self = qa.convWorlflow(self)
        return self

    #If launched from a GIU workflow action this will
    #interpret the type of action and set the right
    #flag for the search
    def convWorkflow(self):
        (st,ss) = qa.searchValType(self)
        if "i" in st:
            self.args.i = ss
        elif "w" in st:
            self.args.w = ss
        elif "d" in st:
            self.args.d = ss
        return self

    #This will convert epoch to ISO 8601 if neccessary
    def convTime(self):
        if self.args.y:
            temp = float(self.args.y.split(".", 1)[0])
            self.args.s = datetime.utcfromtimestamp(temp).isoformat()
        if self.args.z:
            temp = float(self.args.z.split(".", 1)[0])
            self.args.e = datetime.utcfromtimestamp(temp).isoformat()
        return self

    #This builds the "q" portion of the query string (lucene syntax)
    def buildQ(self):
        if self.args.l:
            self.q = self.args.r+":["+str(self.args.s)+"Z TO "+\
                   str(self.args.e)+"Z] AND "+self.args.l
        if self.args.d:
            self.q = self.args.r+":["+str(self.args.s)+"Z TO "+\
                    str(self.args.e)+"Z] AND qname.right:"+self.args.d
        if self.args.i:
            #ALL IPv6 is handled as if it were a network
            if ":" in self.args.i:
                p = prep6(self.args.i+'/128')
                self.q=self.args.r+":["+str(self.args.s)+"Z TO "+\
                        str(self.args.e)+"Z] AND value_ip:["+p.sip+" TO "\
                        +p.eip+"]"
            else:
                self.query=self.args.r+":["+str(self.args.s)+"Z TO "\
                        +str(self.args.e)+"Z] AND value_ip:"+self.args.i
        if self.args.w:
            if ":" in self.args.w:
                p = prep6(self.args.w)
                self.q=self.args.r+":["+str(self.args.s)+"Z TO "+\
                        str(self.args.e)+"Z] AND value_ip:["+p.sip+" TO "+\
                        p.eip+"]"
            else:
                p = prep4(self.args.w)
                self.q=self.args.r+":["+str(self.args.s)+"Z TO "+\
                        str(self.args.e)+"Z] AND value_ip:["+p.sip+" TO "+\
                        p.eip+"]"
        return self

    def searchValType (self):
        ss = self.args.m
        iv4=re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")
        iv6=re.compile("([A-f0-9:]+:+)[A-f0-9]+")
        if iv4.match(ss):
            if '/' in ss:
                return ("w", ss)
            else:
                return ("i", ss)
        elif iv6.match(ss):
            if '/' in ss:
                return("w", ss)
            else:
                return("i", ss)
        else:
            return ("d", ss)

    
#For IPv4 obviously
class prep4:

    def __init__(self, cidrString):
        self.cidrString = cidrString
        prep4.Cidr2Range(self)

    #Takes CIDR notation and uses the network and broadcast for
    #building the start and end range for the lucene query
    def Cidr2Range (self):
        (addrString, cidrString) = self.cidrString.split('/')
        addr = addrString.split('.')
        cidr = int(cidrString)
        nmask = [0, 0, 0, 0]
        for i in range(cidr):
            nmask[i/8] = nmask[i/8] + ( 1 << (7-i %8))
        net=[]
        for i in range(4):
            net.append(int(addr[i]) & nmask [i])
        broad = list(net)
        brange = 32 - cidr
        for i in range(brange):
            broad[3- i/8] = broad[3 - i/8] + (1 << (i %8))
        self.sip = (".".join(map(str, net)))
        self.eip = (".".join(map(str, broad)))
        return self

# I think this might be IPv6 focused.
class prep6:

    def __init__(self, cidrString):
        self.cidrString = cidrString
        prep6.Cidr2Range(self)

    #Takes v6 CIDR notation and uses the network and broadcast for building
    #the start and end range for the lucene query
    def Cidr2Range (self):
        my_sub = ipcalc.Network(self.cidrString)
        self.sip = str(my_sub.network())
        self.eip = str(my_sub.broadcast())
        return self
