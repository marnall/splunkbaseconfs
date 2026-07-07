#add your custom response handler class to this module
import json
import datetime
from datetime import datetime,timedelta
import requests
import logging
import sys

#the default handler , does nothing , just passes the raw output directly to STDOUT
class DefaultResponseHandler:
    
    def __init__(self,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)
        
    def __call__(self, response_object,raw_response_output,req_args,endpoint):
              
        try:       
            print_xml_stream(raw_response_output)
        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing JSON : %s" % e)

#handler for processing Elevate JSON Result Arrays and performing paging
class ElevateJSONResultsArrayHandler:  
    
    def __init__(self,logger,**args):
        self.logger = logger
        self.logger.info("%s initialised" % self.__class__.__name__)

    def __call__(self, response_object,raw_response_output,req_args,endpoint):
        
        try:
            output = json.loads(raw_response_output)
            
            url = response_object.url
            total_elements = output["total_elements"]
            page_size = output["page_size"]
            pages = output["pages"]

            self.logger.info("Processing JSON response from %s...Total Elements %s, Page Size %s, Pages %s" % (url,total_elements,page_size,pages) )             

            has_next = output["has_next"]
            
            for result in output["results"]:
                print_xml_stream(json.dumps(result))

            while has_next:
                #paging logic
                next_page_token = output["next_page_token"]

                if not "params" in req_args:
                    req_args["params"] = {}

                req_args["params"]["page_token"] = next_page_token

                next_response = requests.get(url,**req_args)

                try:
                    next_response.raise_for_status()  

                    raw_response_output = next_response.text
                    
                    output = json.loads(raw_response_output)
                
                    has_next = output["has_next"]
                    
                    for result in output["results"]:
                        print_xml_stream(json.dumps(result))

                except requests.exceptions.HTTPError as e:
                    error_output = next_response.text
                    error_http_code = next_response.status_code                
                    self.logger.error("HTTP Request error during paging loop: %s Code: %s Message: %s" % (str(e),error_http_code, error_output))
                    return

            self.logger.info("Completed Processing JSON response")             

                

        except:  
            e = sys.exc_info()[0]  
            self.logger.error("Error processing Elevate JSON Result Array : %s" % e)
        
                                                                   
#HELPER FUNCTIONS
    
# prints XML stream
def print_xml_stream(s):
    print("<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s))



def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text