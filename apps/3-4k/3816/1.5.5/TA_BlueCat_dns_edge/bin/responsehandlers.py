from __future__ import print_function
#add your custom response handler class to this module
from builtins import range
from builtins import object
import json
import datetime
import sys,logging,os
import ijson
from ijson import parse

logger = logging.getLogger("root")
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

class BlueCatResponseHandler(object):

    def __init__(self,**args):
        pass

    def __call__(self,resp,response_type,dns_server,endpoint):
        if endpoint == "/v2/api/customer/dnsQueryLog/stream":
            parser = ijson.parse(resp.raw)
            object_builder = ijson.ObjectBuilder()
            for prefix, event, value in parser:
                object_builder.event(event, value)
                if event == 'end_map' and prefix == 'item':
                    obj = object_builder.value
                    try:
                        obj['extracted_source'] = obj.pop('source')
                    except:
                        obj = obj[0]
                        obj['extracted_source'] = obj.pop('source')
                    print_xml_stream(json.dumps(obj))
                    object_builder = ijson.ObjectBuilder()
        else:         
            response_json = json.loads(resp.text)
            array_length = len(response_json)
            for j in range(array_length):
                print_xml_stream(json.dumps(response_json[j]))

                                              
                                                                                         
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
