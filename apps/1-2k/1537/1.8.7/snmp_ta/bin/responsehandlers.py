#add your custom response handler class to this module
import sys,json,csv,io,logging,time
from pysnmp.smi import view, rfc1902
from pysnmp.proto.rfc1905 import EndOfMibView

#the default handler , does nothing , just passes the raw output directly to STDOUT
class DefaultResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,destination,logger,table=False,from_trap=False,trap_metadata=None,split_bulk_output=False,mibView=None):        
        splunkevent =""
        current_timestamp = int(time.time())
        #handle traps
        if from_trap:
            
            try: 
                logger.info("Processing Trap")
                response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]
            except: 
                e = sys.exc_info()[1]
                logger.error("Exception resolving MIBs for trap: %s" % str(e))

            for name, val in response_object:
                try:
                    splunkevent += '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())     
                except: # catch *all* exceptions
                    e = sys.exc_info()[1]
                    logger.error("Exception processsing trap: %s" % str(e))

                
            splunkevent = trap_metadata + splunkevent       
            print_xml_single_instance_mode(destination, splunkevent,current_timestamp)
          
        #handle tables  
        elif table:
            logger.info("Processing Attribute Table")
            for varBindTableRow in response_object:
                try:                
                    varBindTableRow = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in varBindTableRow]
                except: 
                    e = sys.exc_info()[1]
                    logger.error("Exception resolving MIBs for table: %s" % str(e)) 
                for name, val in varBindTableRow:
                    try:
                        if val.isSameTypeWith(EndOfMibView()):
                            logger.info("End Of MIB View")
                        else:
                            output_element = '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())                               
                            if split_bulk_output:
                                print_xml_single_instance_mode(destination, output_element,current_timestamp)     
                            else:    
                                splunkevent += output_element 
                    except: # catch *all* exceptions
                        e = sys.exc_info()[1]
                        logger.error("Exception processsing attribute row: %s" % str(e))
            if not split_bulk_output:
                print_xml_single_instance_mode(destination, splunkevent,current_timestamp)            
        #handle scalars
        else: 
            logger.info("Processing Attribute Scalar")
            try:   
                response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]

            except: 
                e = sys.exc_info()[1]
                logger.error("Exception resolving MIBs for scalar: %s" % str(e)) 
            for name, val in response_object:
                try:
                    splunkevent += '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())
                except: # catch *all* exceptions
                    e = sys.exc_info()[1]
                    logger.error("Exception processsing attribute: %s" % str(e))

            print_xml_single_instance_mode(destination, splunkevent,current_timestamp)      
                   
#Like DefaultResponseHandler, but splits multiple OIDs pulled from a GET request (instead of GETBULK) into separate events.
class SplitNonBulkResponseHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,destination,logger,table=False,from_trap=False,trap_metadata=None,split_bulk_output=False,mibView=None):
        splunkevent =""
        current_timestamp = time.time()

        #handle traps
        if from_trap:
            try:                
                response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]
            except: 
                e = sys.exc_info()[1]
                logger.error("Exception resolving MIBs for trap: %s" % str(e))
            for name, val in response_object:
                try:
                    splunkevent += '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())     
                except: # catch *all* exceptions
                    e = sys.exc_info()[1]
                    logger.error("Exception processsing trap: %s" % str(e))

                
            splunkevent = trap_metadata + splunkevent       
            print_xml_single_instance_mode(destination, splunkevent,current_timestamp)

        #handle tables
        elif table:
            for varBindTableRow in response_object:
                try:                
                    varBindTableRow = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in varBindTableRow]
                except: 
                    e = sys.exc_info()[1]
                    logger.error("Exception resolving MIBs for table: %s" % str(e))
                for name, val in varBindTableRow:
                    if val.isSameTypeWith(EndOfMibView()):
                        logger.info("End Of MIB View")
                    else:
                        output_element = '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())
                        if split_bulk_output:
                            print_xml_single_instance_mode(destination, output_element,current_timestamp)
                        else:
                            splunkevent += output_element
            if not split_bulk_output:
                print_xml_single_instance_mode(destination, splunkevent,current_timestamp)
        #handle scalars
        else:
            for name, val in response_object:
                try:                
                    response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]
                except: 
                    e = sys.exc_info()[1]
                    logger.error("Exception resolving MIBs for scalar: %s" % str(e)) 
                output_element = '%s = "%s" ' % (name.prettyPrint(), val.prettyPrint())
                if split_bulk_output:
                    print_xml_single_instance_mode(destination, output_element,current_timestamp)
                else:
                    splunkevent += output_element
                    
            if not split_bulk_output:
                print_xml_single_instance_mode(destination, splunkevent,current_timestamp)

class JSONFormatterResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,destination,logger,table=False,from_trap=False,trap_metadata=None,split_bulk_output=False,mibView=None):        
        #handle tables 
        current_timestamp = time.time()        
        if table:
            values = []
            for varBindTableRow in response_object:
                row = {}
                try:                
                    varBindTableRow = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in varBindTableRow]
                except: 
                    e = sys.exc_info()[1]
                    logger.error("Exception resolving MIBs for table: %s" % str(e))
                for name, val in varBindTableRow:
                    if val.isSameTypeWith(EndOfMibView()):
                        logger.info("End Of MIB View")
                    else:                              
                        row[name.prettyPrint()] = val.prettyPrint()
                values.append(row)
            print_xml_single_instance_mode(destination, json.dumps(values),current_timestamp)            
        #handle scalars
        else: 
            values = {} 
            try:                
                response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]
            except: 
                e = sys.exc_info()[1]
                logger.error("Exception resolving MIBs for scalar: %s" % str(e)) 
            for name, val in response_object:
                values[name.prettyPrint()] = val.prettyPrint()
            print_xml_single_instance_mode(destination, json.dumps(values),current_timestamp)      

class RawJSONFormatterResponseHandler:
    
    def __init__(self,**args):
        self.split_by_index = False
        if 'split_by_index' in args.keys():
            self.split_by_index = args['split_by_index']
        pass
        
    def __call__(self, response_object,destination,logger,table=False,from_trap=False,trap_metadata=None,split_bulk_output=False,mibView=None):        
        #handle tables  
        logger.info("Executing the custom JSONFormatterResponseHandler")       
        if table:
            logger.info("Handle an OID table")
            values = {}
            indexes = {}

            logger.info("Iterating over table rows and performing MIB translation")
            for varBindTableRow in response_object:
                row = {}
                try:                
                    varBindTableRow = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in varBindTableRow]
                except: 
                    e = sys.exc_info()[1]
                    logger.error("Exception resolving MIBs for table: %s" % str(e))

                for name, val in varBindTableRow:
                    if val.isSameTypeWith(EndOfMibView()):
                        logger.info("End Of MIB View")
                    else:                              
                        row[name.prettyPrint()] = val.prettyPrint()
                        if split_bulk_output:
                            print_xml_single_instance_mode_no_timestamp(destination, json.dumps(row))
                        else:
                            if self.split_by_index:
                                n = name.prettyPrint().replace('"','')
                                index = n.split('.')[-1]
                                if index not in indexes.keys():
                                    indexes[index] = {}
                                n = n[:-(len(str(index))+1)]
                                indexes[index][n] = val.prettyPrint()
                            else:
                                values[name.prettyPrint()] = val.prettyPrint()
            if self.split_by_index:
                for i in indexes.keys():
                    indexes[i]['idx']=i.replace('"','')
                    print_xml_single_instance_mode_no_timestamp(destination, json.dumps(indexes[i]))
            else:
                print_xml_single_instance_mode_no_timestamp(destination, json.dumps(values))            
        #handle scalars
        else:
            logger.info("Handle an OID scalar")
            values = {} 
            try:
                logger.info("Performing MIB translation on scalar value")           
                response_object = [rfc1902.ObjectType(rfc1902.ObjectIdentity(x[0]), x[1]).resolveWithMib(mibView) for x in response_object]
            except: 
                e = sys.exc_info()[1]
                logger.error("Exception resolving MIBs for scalar: %s" % str(e)) 
            for name, val in response_object:
                values[name.prettyPrint()] = val.prettyPrint()
            print_xml_single_instance_mode_no_timestamp(destination, json.dumps(values))   

# prints XML stream with no prepended timestamp
def print_xml_single_instance_mode_no_timestamp(server, event):
    
    if len(event) > 0:
        print("<stream><event><data>%s</data><host>%s</host></event></stream>" % (encodeXMLText(event), server))
 

# prints XML stream
def print_xml_single_instance_mode(server, event,current_timestamp):
    
    if len(event) > 0:
        event = "timestamp=%s %s" % (current_timestamp,event)
        print("<stream><event><data>%s</data><host>%s</host></event></stream>" % (encodeXMLText(event), server))
    

def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text