#add your custom response handler class to this module
import json
import datetime

#the default handler , does nothing , just passes the raw output directly to STDOUT
class DefaultResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, message):      
        print_xml_stream(message)
          
#template
class MyResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, message):        
        print_xml_stream(message)

                                                                  
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