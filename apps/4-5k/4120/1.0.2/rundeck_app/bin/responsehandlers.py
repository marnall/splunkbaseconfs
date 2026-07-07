'''
Splunk Modular Input for polling data from Rundeck REST endpoints

This module allows you to define custom response handlers that can be applied to the Rundeck REST API response JSON prior to
indexing in Splunk

June 2018

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Rundeck, Inc. ( www.rundeck.com )
'''

import json,re,sys
from datetime import datetime
from urlparse import urlparse
import requests
import logging
from splunklib.client import connect
from splunklib.client import Service

#default custom handler , does nothing , just passes the raw JSON output directly to STDOUT               
class RundeckJSONHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try: 
            print_xml_stream_with_host(raw_response_output,get_host(endpoint))
        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON : %s" % e)

#handler for processing simple JSON arrays
class RundeckJSONArrayHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:        
            output = json.loads(raw_response_output)

            for entry in output:
                print_xml_stream_with_host(json.dumps(entry),get_host(endpoint))

        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON Array : %s" % e)

'''
Endpoint specific custom handlers
'''

class RundeckAuthTokenRefreshHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service
        self.duration = args["duration"]
        self.expiry_window_secs = args["expiry_window_secs"]

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:       
            output = json.loads(raw_response_output)
            expiration = output["expiration"]
            user = output["user"]
            token = output["token"]
            roles = output["roles"]

            now = datetime.now() 
            expires = datetime.strptime(expiration,'%Y-%m-%dT%H:%M:%SZ')

            difference = (expires - now).total_seconds()

            if difference <= int(self.expiry_window_secs):
                host = get_host(endpoint)
                self.logger.info("Refreshing token for host %s" % host)
                #refresh token as we are within the  refresh window
                create_endpoint_fragment = "tokens/"+user
                create_endpoint = re.sub("token/.+",create_endpoint_fragment,endpoint)
                create_body_json = {}
                create_body_json["user"] = user
                create_body_json["roles"] = roles
                create_body_json["duration"] = self.duration
                req_args["data"]= json.dumps(create_body_json)

                r = requests.post(create_endpoint,**req_args)
                create_response = json.loads(r.text)

                new_token = create_response["token"]

                #a hack to allow updating of a credential in passwords.conf which you can't do using the standard storage/passwords

                storage_passwords = self.service.storage_passwords

                try:
                    self.logger.debug("Deleting rundeck credential for host %s" % host)                                
                    storage_passwords.delete(host)      
                except:  
                    e = sys.exc_info()[0]  
                    self.logger.error("Error deleting rundeck credential for host %s : %s" % (host,e)) 
                try:
                    self.logger.debug("Creating rundeck credential for host %s" % host)
                    storage_passwords.create(new_token,host) 
                except:  
                    e = sys.exc_info()[0]  
                    self.logger.error("Error creating rundeck credential for host %s : %s" % (host,e))
        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error performing auth token refresh for endpoint %s" % host)

class RundeckJSONResourcesHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:       
            output = json.loads(raw_response_output)
            project = 'none'
            try:
                project = re.findall("https://.+/(.+)/resources",endpoint)[0]
            except:
                #error
                e = sys.exc_info()[0]

            for entry in output:
                resource = output[entry]
                #inject the project name           
                output_event = {}
                output_event["project"] = project
                for key,val in resource.items():
                    if key in ["tags","hostname","nodename","description"]:
                        output_event[key] = val
                    else:
                        output_event["attr_"+key] = val

                print_xml_stream_with_host(json.dumps(output_event),get_host(endpoint))
        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON Resources : %s" % e)

class RundeckJSONExecutionsHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:      
            output = json.loads(raw_response_output)

            maxtime = 0
            original_begin = 0

            if "begin" in req_args["params"]:
                original_begin = req_args["params"]["begin"]
                maxtime = req_args["params"]["begin"]

            paging_total = output["paging"]["total"]
            paging_offset = output["paging"]["offset"]
            paging_count = output["paging"]["count"]

            while paging_offset < paging_total:

                for entry in output["executions"]:
                    try:
                        endtime = entry["date-ended"]["unixtime"]
                        if endtime > maxtime:
                            maxtime = endtime
                    except:
                        #error
                        e = sys.exc_info()[0]

                    if "job" in entry:
                        entry["adhoc"] = "false"
                    else:
                        entry["adhoc"] = "true"

                    print_xml_stream_with_host(json.dumps(entry),get_host(endpoint))

                #increment offset
                new_offset = paging_offset+paging_count

                if new_offset < paging_total:
                    req_args["params"]["offset"] = new_offset
                    r = requests.get(endpoint,**req_args)
                    output = json.loads(r.text)
                    paging_count = output["paging"]["count"]
                    paging_total = output["paging"]["total"]
                    #in case the endpoint keeps resetting the offset to 0 in the responses, use our own tracking instead
                    paging_offset = output["paging"]["offset"]
                    if paging_offset == 0:
                        paging_offset = new_offset

                else:
                    break

            #for subsequent runs we start of at the last event history end time
            if not endpoint in state:
                state[endpoint] = {}
            if maxtime > original_begin:
                maxtime = maxtime + 1000 
            state[endpoint]["begin"] = maxtime 

        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON Executions : %s" % e)

class RundeckJSONProjectEventsHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:        
            output = json.loads(raw_response_output)

            maxtime = 0
            original_begin = 0

            if "begin" in req_args["params"]:
                original_begin = req_args["params"]["begin"]
                maxtime = req_args["params"]["begin"]

            paging_total = output["paging"]["total"]
            paging_offset = output["paging"]["offset"]
            paging_count = output["paging"]["count"]

            while paging_offset < paging_total:

                for entry in output["events"]:
                    try:
                        endtime = entry["endtime"]
                        if endtime > maxtime:
                            maxtime = endtime
                    except:
                        #error
                        e = sys.exc_info()[0]

                    print_xml_stream_with_host(json.dumps(entry),get_host(endpoint))

                #increment offset
                new_offset = paging_offset+paging_count

                if new_offset < paging_total:
                    req_args["params"]["offset"] = new_offset
                    r = requests.get(endpoint,**req_args)
                    output = json.loads(r.text)
                    paging_count = output["paging"]["count"]
                    paging_total = output["paging"]["total"]
                    #in case the endpoint keeps resetting the offset to 0 in the responses, use our own tracking instead
                    paging_offset = output["paging"]["offset"]
                    if paging_offset == 0:
                        paging_offset = new_offset

                else:
                    break

            #for subsequent runs we start of at the last event history end time
            if not endpoint in state:
                state[endpoint] = {}
            if maxtime > original_begin:
                maxtime = maxtime + 1000 
            state[endpoint]["begin"] = maxtime 

        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON Events : %s" % e)

class RundeckJSONLogStorageHandler:  

    def __init__(self,service,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        self.service = service

    def __call__(self, response_object,raw_response_output,state,req_args,endpoint):

        try:        
            output = json.loads(raw_response_output)

            paging_total = output["total"]
            paging_offset = output["offset"]
            paging_count = 0

            while paging_offset < paging_total:

                for entry in output["executions"]:
                    paging_count = paging_count + 1
                    print_xml_stream_with_host(json.dumps(entry),get_host(endpoint))

                #increment offset
                new_offset = paging_offset+paging_count

                if new_offset < paging_total:
                    req_args["params"]["offset"] = new_offset
                    r = requests.get(endpoint,**req_args)
                    output = json.loads(r.text)
                    paging_count = 0
                    paging_total = output["total"]
                    #in case the endpoint keeps resetting the offset to 0 in the responses, use our own tracking instead
                    paging_offset = output["offset"]
                    if paging_offset == 0:
                        paging_offset = new_offset

                else:
                    break
        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON Log Storage : %s" % e)

'''
HELPER FUNCTIONS
'''

#pull the host part out of a URI
def get_host(endpoint):
    parsed_uri = urlparse(endpoint)
    host = '{uri.netloc}'.format(uri=parsed_uri)
    return host

# prints XML stream
def print_xml_stream(s):
    print "<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s)

# prints XML stream with host meta data
def print_xml_stream_with_host(s,host):
    print "<stream><event unbroken=\"1\"><data>%s</data><host>%s</host><done/></event></stream>" % (encodeXMLText(s),host)

# handle some escaping
def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text