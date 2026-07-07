"""
ToDo: We may need this capability downstream, for now default is used.
Scheme pattern referenced from http://docs.splunk.com/Documentation/Splunk/latest/AdvancedDev/ModInputsExample
"""
import json
import datetime
import sys,logging,os,time,re

logging.root
logging.root.setLevel(logging.ERROR)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)


class DefaultResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint):        
        print_xml_stream(raw_response_output)

        
class MyResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint):        
        print_xml_stream("Not implemented yet!")

def print_xml_stream(s):
    print "<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s)


def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text