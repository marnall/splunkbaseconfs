#!/usr/bin/env python
# coding=utf-8


from __future__ import absolute_import, division, print_function, unicode_literals
#mport app

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
import random
import csv
import sys
import json
import re
try:
    # for Python 2.x
    from StringIO import StringIO
except ImportError:
    # for Python 3.x
    from io import StringIOO
import time
import requests
#reverse whois, ip and whois

@Configuration()

class SimulateCommand(GeneratingCommand):
    def save_api_key(self,key):
        r = requests.post("https://www.domainiq.com/api",data={"key":key,"service":"whois","domain":"google.com","output_mode":"json"})
        if "<error>Invalid key" in r.text:
            return "json",{"Error":"The API key you entered doesn't match our records"}
        
        with open("api.key","w") as f:
            f.write(key)
        return "json",{"Success":"Your key has been verified and successfully updated"}
    def get_api_key(self):
        try:
            with open("api.key","r") as f:
                key=f.readline()
            return key
        except:
            return "error"
    def isValidEmail(self,email):
        if len(email) > 7:
            if re.match("^.+@[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$", email) != None:
                return True
        return False
    """
        Generate whois data from DIQ database
    """
    def api(self, key, service, data):
        """
            Query DIQ
        """
        query_type=""

        if (service=="api"):
            #Cut the domain part of user has entered it
            if "?" in data: data=data[data.index("?")+1:]
            #Parse POST variables
            post={}
            while True:
                
                    #I know, regex is more readable, but I'm 
                    key=data[:data.index("=")]
                    data=data[data.index("=")+1:]
                    if "&" in data:
                        value=data[:data.index("&")]
                        data=data[data.index("&")+1:]
                        post[key]=value
                    else:
                        value=data
                        post[key]=value
                        break
            if "key" not in post: post["key"]=key 
            post["output_mode"]="json"
            r = requests.post("https://www.domainiq.com/api",data=post)
            return "xml", {"xml":json.loads(r.text)}

        if (service=="ip"):
            query = "ip"
            service = "whois"
            self.service = "whois"
            #data=data.encode("idna")
            #return "json",{"Error": data}
        elif (service=="bulk_whois"): 
            query = "domains"
            data=">>".join(data)
        elif (service=="email_report"):
            query = "email"
            if not self.isValidEmail(data):
                return "json", {"Error":"Please, enter a valid email"}
        elif (service=="name_report"):
            query = "name"
        elif (service=="whois"):
            query = "domain"
            service = "domain_report"
            self.service = "domain_report"
            data=data.encode("idna")
        elif (service=="domain_report"):
            query = "domain"
        elif (service=="reverse_dns"):
            query= "domain"
        elif (service=="reverse_ip")|(service=="reverse_mx"):
            query="data"
            if "-" in data:
                query_type = "range"
            elif re.match("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", data) != None:
                #We have a full ip. Check whether it's a block/subnet
                if data[:-4] == ".0.0":
                    query_type = "block"
                elif data[:-2] == ".0":
                    query_type = "subnet"
                else:
                    query_type = "ip"
            elif re.match("[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", data)!=None:
                query_type="subnet"
            elif re.match("[0-9]{1,3}\.[0-9]{1,3}", data)!=None:
                query_type="block"
            elif service=="reverse_mx":
                query_type="hostname"
            else:
                return "json",{"Error":"IP not recognized"}

        elif (service=="snapshot_hist"):
            service="snapshot_history"
            query="domain"
        elif "history" in service:
            service="custom_domain_history"
            query="domain"
        elif (service=="reverse_analytics"):
            if "." in data:
                query_type = "domain"
            else:
                query_type = "id"
            query = "data"
        elif (service=="save_api"):
            return self.save_api_key(data)
        else:
            return "json",{"Error":"Unsupported input mode"}
        #Try to get output
        try:
            if "history" in service:
                r = requests.post("https://www.domainiq.com/api",data={"key":key,"service":service,query:data,"mode":"dates","output_mode":"json"})
            
            elif query_type=="":
                r = requests.post("https://www.domainiq.com/api",data={"key":key,"service":service,query:data,"output_mode":"json"})
            else:
                r = requests.post("https://www.domainiq.com/api",data={"key":key,"service":service,query:data,"type":query_type,"output_mode":"json"})
        except:
            return "json",{"Error":"Internet connection error"}
        #API error handling module

        if "<error>Invalid key" in r.text:
            return "json",{"Error":"The API key you entered doesn't match our records"}
        if "<title>domainIQ - Not Found</title>" in r.text:
            return "json",{"Error":"Nothing was found"}
        #By default parse json. If it fails, fall down to parsing csv
        try:
            return "json",json.loads(r.text)
        except:
            f = StringIO(r.text)
            output = list(list(rec) for rec in csv.reader(f, delimiter=str(",").encode('utf-8'),quotechar=str('"').encode('utf-8')))
            return "csv",output 

    service = Option(
        doc='''**Syntax:** **input=***<string>*
        **Description:** API service to call''',
        name='input',require=True)
    query = Option(
        doc='''**Syntax:** **query=***<string>*
        **Descriptiion:** Domains/IPs to query''',
        name='query', require = True)
    def generate(self):
        #if self.service=="csv":
        #    if not self.records:
        #        self.records = [record for record in csv.DictReader(self.csv_file)]
        if self.service=="Choose":
            yield {"Error":"Please, choose the search mode first"}
            return
        if self.service=="bulk_whois":
            if not self.records:
                self.records = [record for record in self.query.split("/")]
        #try:
        else:
            self.records = self.query
        key=self.get_api_key()
        if (self.service!="save_api")&(key=="error"):
            yield {"Error":"Setup error! Please, specify your API key in the setup"}
            return
        res,output = self.api(key ,self.service, self.records)
        if res=="json":
            #If no API errors 
            if ("Error" not in output)&("Success" not in output):
                #Query results
                if "error" in output:
                    yield {"Error": output["error"]}
                    return
                if ((self.service=="whois")|(self.service=="domain_report")|(self.service=="ip")):
                    #Catch error returned by API

                    #This returns transposed json for whois.
                    if "result" not in output: output["result"]=output["data"]["whois"]
                    for element in output["result"]:
                        form={}
                        #These fields will not be in the output
                        if ((element!="")&(element!="raw")&(element!="debug")&(element!="domain")):
                            #User may be stupid and enter IP instead of domain. Our API catches it, so this script will do the same.
                            try:
                                form[output["result"]["domain"].decode("idna")]=output["result"][element]
                                form["Domain"]=element.decode("idna")
                            except KeyError:
                                form[output["result"]["ip"]]=output["result"][element]
                                form["IP"]=element
                            yield form

                elif ("history" in self.service):
                    result=dict()
                    for element in output["output"]:
                        if element["date"] not in result:
                            result["date"]={"date":"","nameserver":"","email":"","registrant":"","registrar":""}
                        for key in element:
                            result["date"][element["type"]]=element["item"]
                    for element in result:
                        yield result[element]

                else:
                    if "data" in output:
                        output=output["data"]["related_domains"]
                    if "results" in output:
                        #Reverse queries
                        output=output["results"]
                    if "domains" in output:
                        output=output["domains"]
                    if "snaps" in output:
                        output=output["snaps"]
                    for element in output:
                            #join the keys in nested dicts
                            subfields={}
                            normalfields={}
                            if element=="error":
                                yield {"Error": output["error"]}
                                return
                            for key in element:
                                if isinstance(element[key],dict):
                                    subdict = element[key]
                                    for subkey in subdict:
                                        if key!=subkey:
                                            subfields[key+"_"+subkey] = subdict[subkey]
                                        else:
                                            subfields[key] = subdict[key]
                                else:
                                    normalfields[key] = element[key]
                            normalfields.update(subfields)
                            yield normalfields
            else:
                #Errors/Success messages.
                yield output
        #csv parsing
        elif res=="csv":
            for i in range(1,len(output)):

                    result={}
                    for j in range(len(output[i])):
                        try:
                            result[output[0][j]]=output[i][j]
                        except:
                            pass
                    yield result 
        elif res=="xml":
            yield output
        else:
            yield {"Error":"Unknown output type"}



    def __init__(self):
        super(SimulateCommand, self).__init__()
        self.records = None

dispatch(SimulateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
