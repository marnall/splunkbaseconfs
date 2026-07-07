import os,sys,logging,hashlib,time,errno,subprocess
import xml.dom.minidom, xml.sax.saxutils
import time
import threading
import socket
import signal
from subprocess import Popen,PIPE

from logging.handlers import TimedRotatingFileHandler

from splunklib.client import Service

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
MYAPP = 'snmp_ta'

# Set up a specific logger
logger = logging.getLogger('snmpmodinput')
logger.propagate = False

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

RESPONSE_HANDLER_INSTANCE = None

base_app_dir = os.path.join(SPLUNK_HOME,"etc","apps",MYAPP)
base_mibs_dir = os.path.join(base_app_dir,"bin","mibs")
#Retained for legacy support
#dynamically load in any eggs
egg_dir = os.path.join(base_app_dir,"bin")

for filename in os.listdir(egg_dir):
    if filename.endswith(".egg"):
        sys.path.append(os.path.join(egg_dir ,filename))  

#Retained for legacy support
#directory of user  MIB python modules
mib_egg_dir = base_mibs_dir
sys.path.append(mib_egg_dir)
for filename in os.listdir(mib_egg_dir):
    if filename.endswith(".egg"):
       sys.path.append(os.path.join(mib_egg_dir ,filename)) 

#new locations of user MIBs since v1.7

#plaintext mibs
mib_user_plaintext_dir = os.path.join(base_mibs_dir,"user_plaintext_mibs")
mib_common_plaintext_dir = os.path.join(base_mibs_dir,"common_plaintext_mibs")

#precompiled/compiled MIBs
mib_python_dir = os.path.join(base_mibs_dir,"user_python_mibs")
sys.path.append(mib_python_dir)




from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.carrier.asynsock.dispatch import AsynsockDispatcher
from pysnmp.carrier.asynsock.dgram import udp, udp6
from pysnmp.entity import engine
from pysnmp.entity import config as pysnmp_config
from pyasn1.codec.ber import decoder
from pysnmp.proto import api,rfc1155,rfc1902
from pysnmp.smi import builder
from pysnmp.entity.rfc3413 import mibvar,ntfrcv
from pysnmp.smi import view
from pysnmp.smi import compiler
from pysnmp.proto.api import v2c
from pysnmp.debug import setLogger, Debug, Printer


# Patch pysnmp for COUNTER/TIMETICKS encodings that might decode into a negative value
def counterCloneHack(self, *args):
    if args and args[0] < 0:
        args = (0xffffffff+args[0]-1,) + args[1:]

    return self.__class__(*args)
rfc1155.Counter.clone = counterCloneHack
rfc1155.TimeTicks.clone = counterCloneHack
rfc1902.Counter32.clone = counterCloneHack


SCHEME = """<scheme>
    <title>SNMP</title>
    <description>SNMP input to poll attribute values and catch traps</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>SNMP Input Name</title>
                <description>Name of this SNMP input</description>
            </arg>  
            <arg name="activation_key">
                <title>Activation Key</title>
                <description>Visit http://www.baboonbones.com/#activation to obtain a non-expiring key</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="snmp_mode">
                <title>SNMP Mode</title>
                <description>Whether or not this stanza is for polling attributes or listening for traps</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>                
            <arg name="destination">
                <title>Destination</title>
                <description>IP or hostname of the device you would like to query,or a comma delimited list</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="ipv6">
                <title>IP Version 6</title>
                <description>Whether or not this is an IP version 6 address. Defaults to false</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="port">
                <title>Port</title>
                <description>The SNMP port. Defaults to 161</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="snmp_version">
                <title>SNMP Version</title>
                <description>The SNMP Version , 1 or 2C, version 3 not currently supported. Defaults to 2C</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="object_names">
                <title>Object Names</title>
                <description>1 or more Objects Names , comma delimited , in either textual(iso.org.dod.internet.mgmt.mib-2.system.sysDescr.0) or numerical(1.3.6.1.2.1.1.3.0) format. By default a GET operation will be executed. If you require bulk operations , then select a SNMP Walking option</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="communitystring">
                <title>Community String</title>
                <description>Community String used for authentication.Defaults to "public"</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_securityName">
                <title>SNMPv3 USM Username</title>
                <description>SNMPv3 USM Username</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_securityEngineId">
                <title>SNMPv3 Engine ID</title>
                <description>SNMPv3 Engine ID</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_authKey">
                <title>SNMPv3 Authorization Key</title>
                <description>SNMPv3 secret authorization key used within USM for SNMP PDU authorization. Setting it to a non-empty value implies MD5-based PDU authentication (defaults to usmHMACMD5AuthProtocol) to take effect. Default hashing method may be changed by means of further authProtocol parameter</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_privKey">
                <title>SNMPv3 Encryption Key</title>
                <description>SNMPv3 secret encryption key used within USM for SNMP PDU encryption. Setting it to a non-empty value implies MD5-based PDU authentication (defaults to usmHMACMD5AuthProtocol) and DES-based encryption (defaults to usmDESPrivProtocol) to take effect. Default hashing and/or encryption methods may be changed by means of further authProtocol and/or privProtocol parameters. </description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_authProtocol">
                <title>SNMPv3 Authorization Protocol</title>
                <description>may be used to specify non-default hash function algorithm. Possible values include usmHMACMD5AuthProtocol (default) / usmHMACSHAAuthProtocol / usmNoAuthProtocol</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="v3_privProtocol">
                <title>SNMPv3 Encryption Key Protocol</title>
                <description>may be used to specify non-default ciphering algorithm. Possible values include usmDESPrivProtocol (default) / usmAesCfb128Protocol / usm3DESEDEPrivProtocol / usmAesCfb192Protocol / usmAesCfb256Protocol / usmNoPrivProtocol</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="snmpinterval">
                <title>Interval</title>
                <description>How often to run the SNMP query (in seconds). Defaults to 60 seconds</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="timeout">
                <title>Timeout</title>
                <description>SNMP attribute polling timeout (in seconds). Defaults to 1 second. NOTE: timer resolution is about 0.5 seconds</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="retries">
                <title>Automatic Retries</title>
                <description>Number of times to automatically retry polling before giving up. Defaults to 5</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="do_bulk_get">
                <title>Perform a SNMPWALK using GETBULK</title>
                <description>Defaults to false</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="do_get_subtree">
                <title>Perform a SNMPWALK using GETNEXT</title>
                <description>Defaults to false</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="split_bulk_output">
                <title>Split Bulk Results</title>
                <description>Whether or not to split up bulk output into individual events. Defaults to false.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="lexicographic_mode">
                <title>Lexicographic Mode (for all SNMP Walking operations)</title>
                <description>Walk SNMP agent's MIB till the end (if true), otherwise (if false) stop iteration when all response MIB variables leave the scope of initial MIB variables in the OID list. Default is false.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="non_repeaters">
                <title>Non Repeaters (for GETBULK operations)</title>
                <description>The number of objects that are only expected to return a single GETNEXT instance, not multiple instances. Defaults to 0.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="max_repetitions">
                <title>Max Repetitions (for GETBULK operations)</title>
                <description>The number of objects that should be returned for all the repeating OIDs.Defaults to 25.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="listen_traps">
                <title>Listen for TRAP messages</title>
                <description>Whether or not to listen for TRAP messages</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="trap_port">
                <title>TRAP listener port</title>
                <description>TRAP listener port. Defaults to 162.Ensure that you have the necessary OS user permissions for port values 0-1024</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="trap_host">
                <title>TRAP listener host</title>
                <description>TRAP listener host. Defaults to localhost.Ensure that you set this to the Hostname or IP that the trap client is sending to.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
    	    <arg name="trap_rdns">
        		<title>TRAP Origin Reverse DNS Lookup</title>
        		<description>TRAP Generating Host reverse DNS lookup. Forces host field to the DNS lookup if available insted of IP address. Defaults to false. Be aware may cause large DNS lookup volume</description>
        		<required_on_edit>false</required_on_edit>
        		<required_on_create>false</required_on_create>
    	    </arg>
            <arg name="mib_names">
                <title>MIB Names</title>
                <description>Comma delimited list of MIB names to be applied ie: IF-MIB,DNS-SERVER-MIB,BRIDGE-MIB</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="response_handler">
                <title>Response Handler</title>
                <description>Python classname of custom response handler</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="response_handler_args">
                <title>Response Handler Arguments</title>
                <description>Response Handler arguments string ,  key=value,key2=value2</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="log_level">
                <title>Log Level</title>
                <description>Logging level (info, error, debug etc..)</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="use_system_python">
                <title>Use System Python</title>
                <description>Whether or not to use a System python runtime vs Splunk's built in python runtime. Defaults to false.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="system_python_path">
                <title>System Python Path</title>
                <description>Defaults to /usr/bin/python</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="run_process_checker">
                <title>Run Process Checker</title>
                <description>Whether or not to autonomously manage the script's running state.Defaults to true.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def get_credentials():
   
   result = []
   try:
  
      for sp in SDK_SERVICE.storage_passwords:
        values = {}
        values['username'] = sp.username or "none"
        values['clear_password'] = sp.clear_password or "none"
        result.append(values)

   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return result

   return result

def do_validate():
    
    try:
        config = get_validation_config() 
        
        port=config.get("port")
        trap_port=config.get("trap_port")
        snmpinterval=config.get("snmpinterval")
        timeout=config.get("timeout")
        retries=config.get("retries")
        max_repetitions=config.get("max_repetitions") 
        non_repeaters=config.get("non_repeaters") 
        
        validationFailed = False
    
        
        if not port is None and int(port) < 1:
            print_validation_error("Port value must be a positive integer")
            validationFailed = True
        if not trap_port is None and int(trap_port) < 1:
            print_validation_error("Trap port value must be a positive integer")
            validationFailed = True
        if not non_repeaters is None and int(non_repeaters) < 0:
            print_validation_error("Non Repeaters value must be zero or a positive integer")
            validationFailed = True
        if not max_repetitions is None and int(max_repetitions) < 0:
            print_validation_error("Max Repetitions value must be zero or a positive integer")
            validationFailed = True
        if not snmpinterval is None and int(snmpinterval) < 1:
            print_validation_error("SNMP Polling interval must be a positive integer")
            validationFailed = True
        if not timeout is None and float(timeout) < 0:
            print_validation_error("SNMP Polling timeout must not be a negative number")
            validationFailed = True
        if validationFailed:
            sys.exit(2)
               
    except: # catch *all* exceptions
        e = sys.exc_info()[1]
        sys.exit(1)
        raise   

# Given an ip, return the host. Return the ip if no lookup found or if lookup disabled by configuration
def rlookup(ip):

     if trap_rdns:
        try:
            hostname, aliaslist, ipaddrlist = socket.gethostbyaddr(ip)
            return hostname
        except:
            return ip 
     else:
        return ip
    
def v3trapCallback(snmpEngine,stateReference,contextEngineId, contextName,varBinds,cbCtx):
    try:
        logger.info("V3 Trap Received")
        trap_metadata = ""
        server = ""
        ( transportDomain,transportAddress ) = snmpEngine.msgAndPduDsp.getTransportInfo(stateReference)
        try:
            server = "%s" % rlookup(transportAddress[0]) 
            trap_metadata += 'notification_from_address = "%s" ' % (transportAddress[0])
            trap_metadata += 'notification_from_domain = "%s" ' % (transportDomain[0])                              
        except: # catch *all* exceptions
            e = sys.exc_info()[1]
            logger.error("Exception resolving source address/domain of the trap: %s" % str(e))
        
        try:
            trap_metadata += 'context_engine_id = "%s" ' % (contextEngineId.prettyPrint())
            trap_metadata += 'context_name = "%s" ' % (contextName.prettyPrint())                              
        except: # catch *all* exceptions
            e = sys.exc_info()[1]
            logger.error("Exception resolving context of the trap: %s" % str(e))
                   
        handle_output(mibview_controller,varBinds,server,from_trap=True,trap_metadata=trap_metadata) 
         
    except: # catch *all* exceptions
        e = sys.exc_info()[1]
        logger.error("Exception receiving trap %s" % str(e))
            
def trapCallback(transportDispatcher, transportDomain, transportAddress, wholeMsg):
    
    try:
        if not wholeMsg:
            logger.error('Receiving trap , error processing the inital message in the trapCallback handler')
            
        while wholeMsg:
            msgVer = int(api.decodeMessageVersion(wholeMsg))
            logger.info("Trap Received")
            if msgVer in api.protoModules:
                pMod = api.protoModules[msgVer]
            else:
                logger.error('Receiving trap , unsupported SNMP version %s' % msgVer)
                return
            reqMsg, wholeMsg = decoder.decode(wholeMsg, asn1Spec=pMod.Message(),)
            
            reqPDU = pMod.apiMessage.getPDU(reqMsg)
            
            trap_metadata =""
            server = ""
            try:
                server = "%s" % rlookup((transportAddress[0])) 
                trap_metadata += 'notification_from_address = "%s" ' % (transportAddress[0])
                trap_metadata += 'notification_from_port = "%s" ' % (transportAddress[1])
            except: # catch *all* exceptions
                e = sys.exc_info()[1]
                logger.error("Exception resolving source address/domain of the trap: %s" % str(e))
            
            if reqPDU.isSameTypeWith(pMod.TrapPDU()):
                if msgVer == api.protoVersion1:
                    if server == "":
                        server = pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint()

                    trap_metadata += 'notification_enterprise = "%s" ' % (pMod.apiTrapPDU.getEnterprise(reqPDU).prettyPrint())
                    trap_metadata += 'notification_agent_address = "%s" ' % (pMod.apiTrapPDU.getAgentAddr(reqPDU).prettyPrint())
                    trap_metadata += 'notification_generic_trap = "%s" ' % (pMod.apiTrapPDU.getGenericTrap(reqPDU).prettyPrint())
                    trap_metadata += 'notification_specific_trap = "%s" ' % (pMod.apiTrapPDU.getSpecificTrap(reqPDU).prettyPrint())
                    trap_metadata += 'notification_uptime = "%s" ' % (pMod.apiTrapPDU.getTimeStamp(reqPDU).prettyPrint())
                    
                    varBinds = pMod.apiTrapPDU.getVarBinds(reqPDU)
                else:
                    varBinds = pMod.apiPDU.getVarBinds(reqPDU)
                    
                      
                
            handle_output(mibview_controller,varBinds,server,from_trap=True,trap_metadata=trap_metadata) 
            
    except: # catch *all* exceptions
        e = sys.exc_info()[1]
        logger.error("Exception receiving trap %s" % str(e))
                  
    return wholeMsg        

    
def do_run(config):
    

    logger.info("SNMP Modular Input executing")

    global SESSION_TOKEN
    global SPLUNK_PORT
    global SDK_SERVICE

    SESSION_TOKEN = config.get("session_key")
    server_uri = config.get("server_uri")
    SPLUNK_PORT = server_uri[18:]

    #get SDK Service handle
    args = {'host':'localhost','port':SPLUNK_PORT,'token':SESSION_TOKEN,'owner':'nobody','app':MYAPP}
    SDK_SERVICE = Service(**args)  
    
    activation_key = config.get("activation_key").strip()
    app_name = "SNMP Modular Input"


    
    if len(activation_key) > 32:
        activation_hash = activation_key[:32]
        activation_ts = activation_key[32:][::-1]
        current_ts = time.time()
        m = hashlib.md5()
        m.update((app_name + activation_ts).encode('utf-8'))
        if not m.hexdigest().upper() == activation_hash.upper():
            logger.error("Trial Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)
        if ((current_ts - int(activation_ts)) > 604800):
            logger.error("Trial Activation key for App '%s' has now expired. Please visit http://www.baboonbones.com/#activation to purchase a non expiring key." % app_name)
            sys.exit(2)
    else:
        m = hashlib.md5()
        m.update((app_name).encode('utf-8'))
        if not m.hexdigest().upper() == activation_key.upper():
            logger.error("Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % app_name)
            sys.exit(2)
      

    credentials_list = get_credentials()

    for c in credentials_list:
        replace_key='{encrypted:%s}' % c['username']

        for k, v in config.items():
            config[k] = v.replace(replace_key,c['clear_password'])
              
    #params
    snmp_mode=config.get("snmp_mode","")
    
    destination_list=config.get("destination")
    
    if not destination_list is None:
        destinations = list(map(str,destination_list.split(",")))   
        #trim any whitespace using a list comprehension
        destinations = [x.strip(' ') for x in destinations]
        
    port=int(config.get("port",161))
    snmpinterval=int(config.get("snmpinterval",60))   
    timeout_val=float(config.get("timeout",1.0))
    num_retries=int(config.get("retries",5))
    ipv6=int(config.get("ipv6",0))
    

    response_handler_args={} 
    response_handler_args_str=config.get("response_handler_args")
    if not response_handler_args_str is None:
        response_handler_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=') for item in response_handler_args_str.split(',')))
        
    response_handler=config.get("response_handler","DefaultResponseHandler")
    module = __import__("responsehandlers")
    class_ = getattr(module,response_handler)

    global RESPONSE_HANDLER_INSTANCE
    RESPONSE_HANDLER_INSTANCE = class_(**response_handler_args)
    
    #snmp 1 and 2C params
    snmp_version=config.get("snmp_version","2C")
    
    communitystring=config.get("communitystring","public")   
    
    v3_securityName=config.get("v3_securityName","") 
    v3_securityEngineId=config.get("v3_securityEngineId",None)
    v3_authKey=config.get("v3_authKey",None) 
    v3_privKey=config.get("v3_privKey",None) 
    v3_authProtocol_str=config.get("v3_authProtocol","usmHMACMD5AuthProtocol") 
    v3_privProtocol_str=config.get("v3_privProtocol","usmDESPrivProtocol") 

    v3_authProtocol = get_v3_authProtocol_obj(v3_authProtocol_str)
    v3_privProtocol = get_v3_privProtocol_obj(v3_privProtocol_str) 
    
    
    #object names to poll
    object_names=config.get("object_names")
    if not object_names is None:
        oid_args = list(map(str,object_names.split(",")))   
        #trim any whitespace using a list comprehension
        oid_args = [x.strip(' ') for x in oid_args]
    
    
    
    #GET BULK params
    do_subtree=int(config.get("do_get_subtree",0))
    do_bulk=int(config.get("do_bulk_get",0))
    split_bulk_output=int(config.get("split_bulk_output",0))
    lexicographic_mode=int(config.get("lexicographic_mode",0))
    non_repeaters=int(config.get("non_repeaters",0))
    max_repetitions=int(config.get("max_repetitions",25))
    
    #TRAP listener params
    listen_traps=int(config.get("listen_traps",0))
    #some backwards compatibility gymnastics
    if snmp_mode == 'traps':
        listen_traps = 1
        
    trap_port=int(config.get("trap_port",162))
    trap_host=config.get("trap_host","localhost")
   
    global trap_rdns
    trap_rdns=int(config.get("trap_rdns",0))
 
    #MIBs to load
    mib_names=config.get("mib_names")
    mib_names_args=None
    if not mib_names is None:
        mib_names_args = list(map(str,mib_names.split(",")))   
        #trim any whitespace using a list comprehension
        mib_names_args = [x.strip(' ') for x in mib_names_args]
        
    
    logger.info("Building MIBs")

    try:
        mibBuilder = builder.MibBuilder()
     
        global mibview_controller       
        mibview_controller = view.MibViewController(mibBuilder)
     
        mibBuilder.addMibSources(builder.DirMibSource(mib_egg_dir))
        mibBuilder.addMibSources(builder.DirMibSource(mib_python_dir))
     
              
        for filename in os.listdir(mib_egg_dir):
            if filename.endswith(".egg"):  
                mibBuilder.addMibSources(builder.ZipMibSource(filename))       
                   
        compiler.addMibCompiler(mibBuilder, sources=['file://'+mib_user_plaintext_dir,'file://'+mib_common_plaintext_dir], destination=mib_python_dir)

        if mib_names_args:
            mibBuilder.loadModules(*mib_names_args)

    except: # catch *all* exceptions
            e = sys.exc_info()[1]
            logger.error("Looks like an error building/loading your MIBs, ensure that you have all the required MIBs as well any MIB dependencies satisfied from the MIB file IMPORT section : %s" % str(e))
            
         

    if listen_traps:

         logger.info("Running in Trap Listener mode")

         if snmp_version == "1" or snmp_version == "2C":
             trapThread = TrapThread(trap_port,trap_host,ipv6)
             trapThread.start()
         if snmp_version == "3":
             trapThread = V3TrapThread(trap_port,trap_host,ipv6,v3_securityName,v3_securityEngineId,v3_authKey,v3_authProtocol,v3_privKey,v3_privProtocol)
             trapThread.start()  
      
    if not (object_names is None) and not(destination_list is None) and not listen_traps: 
        
        logger.info("Running in Attribute Polling mode")

        mp_model_val=1  

        if snmp_version == "1":
            mp_model_val=0
                     
        for destination in destinations:
                      
            apt = AttributePollerThread(destination,port,ipv6,snmp_version,do_bulk,do_subtree,lexicographic_mode,snmpinterval,non_repeaters,max_repetitions,oid_args,split_bulk_output,mp_model_val,timeout_val,num_retries,communitystring,v3_securityName,v3_authKey,v3_privKey,v3_authProtocol,v3_privProtocol) 
            apt.start()        

class AttributePollerThread(threading.Thread):
    
     def __init__(self,destination,port,ipv6,snmp_version,do_bulk,do_subtree,lexicographic_mode,snmpinterval,non_repeaters,max_repetitions,oid_args,split_bulk_output,mp_model_val,timeout_val,num_retries,communitystring,v3_securityName,v3_authKey,v3_privKey,v3_authProtocol,v3_privProtocol):
         
         threading.Thread.__init__(self)      
         
         self.ipv6=ipv6
         self.mp_model_val=mp_model_val
         self.timeout_val=timeout_val
         self.num_retries=num_retries
         self.communitystring=communitystring
         self.v3_securityName=v3_securityName
         self.v3_authKey=v3_authKey
         self.v3_privKey=v3_privKey
         self.v3_authProtocol=v3_authProtocol
         self.v3_privProtocol=v3_privProtocol
         self.destination=destination
         self.port=port
         self.snmp_version=snmp_version
         self.do_bulk=do_bulk
         self.do_subtree=do_subtree
         self.lexicographic_mode=bool(lexicographic_mode)
         self.snmpinterval=snmpinterval
         self.non_repeaters=non_repeaters
         self.max_repetitions=max_repetitions
         self.oid_args=oid_args
         self.split_bulk_output=split_bulk_output
            
        
         self.initialize()
         

     def initialize(self):

         self.cmdGen = cmdgen.CommandGenerator()

         if self.snmp_version == "3":
             self.security_object = cmdgen.UsmUserData( self.v3_securityName, authKey=self.v3_authKey, privKey=self.v3_privKey, authProtocol=self.v3_authProtocol, privProtocol=self.v3_privProtocol )
         else:
             self.security_object = cmdgen.CommunityData(self.communitystring,mpModel=self.mp_model_val)
        
         if self.ipv6:
             self.transport = cmdgen.Udp6TransportTarget((self.destination, self.port), timeout=self.timeout_val, retries=self.num_retries)
         else:
             self.transport = cmdgen.UdpTransportTarget((self.destination, self.port), timeout=self.timeout_val, retries=self.num_retries)


         logger.info("Attribute Poller initialized")

    
     def reinitialize(self):

        self.initialize()


     def run(self):
         
         try:
                                       
             while True:  
                 if self.do_bulk and not self.snmp_version == "1":
                     try:   
                         logger.info("Performing SNMP Walk using GETBULK Command")   
                         errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.bulkCmd(
                             self.security_object,
                             self.transport,
                             self.non_repeaters, self.max_repetitions,
                             *self.oid_args, lookupNames=True, lookupValues=True, lexicographicMode=self.lexicographic_mode)
                     except: # catch *all* exceptions
                         e = sys.exc_info()[1]
                         logger.error("Exception with bulkCmd to %s:%s: %s" % (self.destination, self.port, str(e)))
                         time.sleep(float(self.snmpinterval))
                         self.reinitialize()
                         continue
                 elif self.do_subtree and not self.snmp_version == "1":
                     try:
                         logger.info("Performing SNMP Walk using GETNEXT Command")
                         errorIndication, errorStatus, errorIndex, varBindTable = self.cmdGen.nextCmd(
                             self.security_object,
                             self.transport,
                             *self.oid_args, lookupNames=True, lookupValues=True, lexicographicMode=self.lexicographic_mode)
                     except: # catch *all* exceptions
                         e = sys.exc_info()[1]
                         logger.error("Exception with nextCmd to %s:%s: %s" % (self.destination, self.port, str(e)))
                         time.sleep(float(self.snmpinterval))
                         self.reinitialize()
                         continue
                 else:
                     try:
                         logger.info("Sending GET Command")
                         errorIndication, errorStatus, errorIndex, varBinds = self.cmdGen.getCmd(
                             self.security_object,
                             self.transport,
                             *self.oid_args, lookupNames=True, lookupValues=True)
                     except: # catch *all* exceptions
                         e = sys.exc_info()[1]
                         logger.error("Exception with getCmd to %s:%s: %s" % (self.destination, self.port, str(e)))
                         time.sleep(float(self.snmpinterval))
                         self.reinitialize()
                         continue
    
                 if errorIndication:
                     logger.error(errorIndication)
                     self.reinitialize()
                 elif errorStatus:
                     logger.error(errorStatus)
                     self.reinitialize()
                 else:
                     if self.do_bulk:
                         handle_output(mibview_controller,varBindTable,self.destination,table=True,split_bulk_output=self.split_bulk_output) 
                     elif self.do_subtree:
                         handle_output(mibview_controller,varBindTable,self.destination,table=True,split_bulk_output=self.split_bulk_output)
                     else:  
                         handle_output(mibview_controller,varBinds,self.destination,table=False,split_bulk_output=self.split_bulk_output)  
                            
                 time.sleep(float(self.snmpinterval))        
            
         except: # catch *all* exceptions
             e = sys.exc_info()[1]
             logger.error("Looks like an error: %s" % str(e))
             logger.error('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
             sys.exit(1)
         
         
                 
class TrapThread(threading.Thread):
    
     def __init__(self,port,host,ipv6):
         threading.Thread.__init__(self)
         self.port=port
         self.host=host
         self.ipv6=ipv6


     def run(self):
         
        transportDispatcher = AsynsockDispatcher()
        transportDispatcher.registerRecvCbFun(trapCallback)
        if self.ipv6:
            transport = udp6.Udp6SocketTransport()
            domainName = udp6.domainName
        else:
            transport = udp.UdpSocketTransport()  
            domainName = udp.domainName
                
        try:     
            transportDispatcher.registerTransport(domainName, transport.openServerMode((self.host, self.port)))
      
            transportDispatcher.jobStarted(1)

            logger.info("Trap Listener initialized , listening on host %s port %s" % (self.host, self.port))

            # Dispatcher will never finish as job#1 never reaches zero
            transportDispatcher.runDispatcher()  

               
        except: # catch *all* exceptions
            e = sys.exc_info()[1]
            transportDispatcher.closeDispatcher()
            logger.error("Failed to register transport and run dispatcher: %s" % str(e))
            sys.exit(1)


         
class V3TrapThread(threading.Thread):
    
     def __init__(self,port,host,ipv6,user,engine_id,auth_key,auth_proto,priv_key,priv_proto):
         threading.Thread.__init__(self)
         self.port=port
         self.host=host
         self.ipv6=ipv6
         self.user=user
         self.engine_id=engine_id
         self.auth_key=auth_key
         self.auth_proto=auth_proto
         self.priv_key=priv_key
         self.priv_proto=priv_proto

     def run(self):
         
        try:

            snmpEngine = engine.SnmpEngine()

            logger.info("Adding a UDP Transport for SNMPv3 Trap Listening, host %s , port %s" % (self.host,self.port))
            
            if self.ipv6:
                domainName = udp6.domainName
                pysnmp_config.addTransport(snmpEngine,domainName,udp6.Udp6Transport().openServerMode((self.host, self.port)))
            else:
                domainName = udp.domainName
                pysnmp_config.addTransport(snmpEngine,domainName,udp.UdpTransport().openServerMode((self.host, self.port))) 

            logger.info("Added UDP Transport for SNMPv3 Trap Listening")
                              
            if self.user and self.auth_proto and self.auth_key and self.priv_proto and self.priv_key:

                logger.info("Adding a SNMPv3 USM User entry for %s from inputs.conf definition" % self.user)

                try:

                    #this is the legacy functionality , left in for backwards compatibility , that will only add a single SNMPv3 USM User
                    if self.engine_id is None:
                        pysnmp_config.addV3User(snmpEngine, self.user,self.auth_proto, self.auth_key,self.priv_proto,self.priv_key)
                    else:
                        pysnmp_config.addV3User(snmpEngine, self.user,self.auth_proto, self.auth_key,self.priv_proto,self.priv_key,securityEngineId=v2c.OctetString(hexValue=self.engine_id))

                except: # catch *all* exceptions
                    e = sys.exc_info()[1]
                    logger.error("Error adding SNNPv3 USM User: %s" % str(e))



            #this is the newer functionality that will build a table of multiple SNMPv3 USM Users from the snmpv3_usm_users.conf file
            build_snmpv3_usm_users_table(snmpEngine)
      
            # Register SNMP Application at the SNMP engine
            ntfrcv.NotificationReceiver(snmpEngine, v3trapCallback)

            snmpEngine.transportDispatcher.jobStarted(1) # this job would never finish            
            
            logger.info("V3 Trap Listener initialized , listening on host %s port %s" % (self.host, self.port))

            # Run I/O dispatcher which would receive queries and send confirmations
            snmpEngine.transportDispatcher.runDispatcher()
 
        except: # catch *all* exceptions
            e = sys.exc_info()[1]
            snmpEngine.transportDispatcher.closeDispatcher()
            logger.error("Looks like an error starting the V3 Trap listener: %s" % str(e))
            sys.exit(1)
            
            
# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print("<error><message>%s</message></error>" % xml.sax.saxutils.escape(s))

def handle_output(mibView,response_object,destination,table=False,from_trap=False,trap_metadata=None,split_bulk_output=False): 
    
    try:
        if destination == "":
            destination = os.environ.get("SPLUNK_SERVER")
         
        RESPONSE_HANDLER_INSTANCE(response_object,destination,logger,table=table,from_trap=from_trap,trap_metadata=trap_metadata,split_bulk_output=split_bulk_output,mibView=mibView)
        sys.stdout.flush()               
    except:
        e = sys.exc_info()[1]
        logger.error("Looks like an error handling the response output: %s" % str(e))
    
def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    sys.exit(2)

def do_scheme():
    print(SCHEME)

def get_input_config(config_str):
    config = {}

    try:
        # read everything from stdin
        # config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        
        session_key_node = root.getElementsByTagName("session_key")[0]
        if session_key_node and session_key_node.firstChild and session_key_node.firstChild.nodeType == session_key_node.firstChild.TEXT_NODE:
            data = session_key_node.firstChild.data
            config["session_key"] = data 
            
        server_uri_node = root.getElementsByTagName("server_uri")[0]
        if server_uri_node and server_uri_node.firstChild and server_uri_node.firstChild.nodeType == server_uri_node.firstChild.TEXT_NODE:
            data = server_uri_node.firstChild.data
            config["server_uri"] = data   
            
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        if param_name and param.firstChild and \
                           param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                            data = param.firstChild.data
                            config[param_name] = data
                            

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
           checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception("Invalid configuration received from Splunk.")

        
    except Exception as e:
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))

    return config

#build a table of SNMPv3 USM Users from the snmpv3_usm_users.conf file
def build_snmpv3_usm_users_table(snmpEngine):

    try:

        logger.info("Building SNMPv3 USM Users table from snmpv3_usm_users.conf")

        #get the usm users conf file
        USM_CONF_FILE = "snmpv3_usm_users"

        try:
            USM_CONF = SDK_SERVICE.confs[USM_CONF_FILE]
        except: # catch *all* exceptions
            e = sys.exc_info()[1]
            logger.warning("No SNMPv3 USM users conf file found : %s" % str(e))
            return
        
        #set global defaults
        common_settings = {}
        common_settings["v3_securityName"] = ""
        common_settings["v3_authProtocol"] = "usmHMACMD5AuthProtocol"
        common_settings["v3_privProtocol"] = "usmDESPrivProtocol"
        common_settings["v3_securityEngineId"] = None
        common_settings["v3_authKey"] = None
        common_settings["v3_privKey"] = None


        COMMON_SETTINGS_STANZA_NAME = "common_settings"
        #update common settings with anything set in the conf file
        if USM_CONF.__contains__(COMMON_SETTINGS_STANZA_NAME): 

            COMMON_SETTINGS_STANZA_OBJECT = USM_CONF[COMMON_SETTINGS_STANZA_NAME]
            #prune out None values so our defaults kick in
            COMMON_SETTINGS_STANZA = {k: v for k, v in COMMON_SETTINGS_STANZA_OBJECT.content().items() if v is not None}

            common_settings.update(COMMON_SETTINGS_STANZA)


        #iterate over each "usm_" stanza and add to usm users table
        for USM_STANZA_OBJECT in USM_CONF:

            stanza_name = USM_STANZA_OBJECT.name

            #don't process common_settings again
            if stanza_name.startswith("usm_"):

                #prune out None values so our defaults kick in
                usm_stanza = {k: v for k, v in USM_STANZA_OBJECT.content().items() if v is not None}

                v3_securityName = usm_stanza.get("v3_securityName",common_settings["v3_securityName"])
                v3_securityEngineId = usm_stanza.get("v3_securityEngineId",common_settings["v3_securityEngineId"])
                v3_authKey = usm_stanza.get("v3_authKey",common_settings["v3_authKey"])
                v3_privKey = usm_stanza.get("v3_privKey",common_settings["v3_privKey"])
                v3_authProtocol_str = usm_stanza.get("v3_authProtocol",common_settings["v3_authProtocol"])
                v3_privProtocol_str = usm_stanza.get("v3_privProtocol",common_settings["v3_privProtocol"])

                v3_authProtocol = get_v3_authProtocol_obj(v3_authProtocol_str)
                v3_privProtocol = get_v3_privProtocol_obj(v3_privProtocol_str)


                if v3_securityName and v3_authProtocol and v3_authKey and v3_privProtocol and v3_privKey:

                    logger.info("Adding SNMPv3 USM User entry from %s stanza" % stanza_name)

                    try:

                        if v3_securityEngineId is None:
                            pysnmp_config.addV3User(snmpEngine, v3_securityName,v3_authProtocol, v3_authKey,v3_privProtocol,v3_privKey)
                        else:
                            pysnmp_config.addV3User(snmpEngine, v3_securityName,v3_authProtocol, v3_authKey,v3_privProtocol,v3_privKey,securityEngineId=v2c.OctetString(hexValue=v3_securityEngineId))

                    except: # catch *all* exceptions
                        e = sys.exc_info()[1]
                        logger.error("Error adding SNNPv3 USM User: %s" % str(e))
        
        logger.info("Completed Building SNMPv3 USM Users table")

    except: # catch *all* exceptions
        e = sys.exc_info()[1]
        logger.error("Error building the SNMPv3 USM Users table : %s" % str(e))
       



def get_v3_authProtocol_obj(v3_authProtocol_str):

    if v3_authProtocol_str == "usmHMACMD5AuthProtocol":
        v3_authProtocol = cmdgen.usmHMACMD5AuthProtocol
    elif v3_authProtocol_str == "usmHMACSHAAuthProtocol":
        v3_authProtocol = cmdgen.usmHMACSHAAuthProtocol
    elif v3_authProtocol_str == "usmHMAC128SHA224AuthProtocol":
        v3_authProtocol = cmdgen.usmHMAC128SHA224AuthProtocol
    elif v3_authProtocol_str == "usmHMAC192SHA256AuthProtocol":
        v3_authProtocol = cmdgen.usmHMAC192SHA256AuthProtocol 
    elif v3_authProtocol_str == "usmHMAC256SHA384AuthProtocol":
        v3_authProtocol = cmdgen.usmHMAC256SHA384AuthProtocol 
    elif v3_authProtocol_str == "usmHMAC384SHA512AuthProtocol":
        v3_authProtocol = cmdgen.usmHMAC384SHA512AuthProtocol 
    elif v3_authProtocol_str == "usmNoAuthProtocol":
        v3_authProtocol = cmdgen.usmNoAuthProtocol   
    else:
        v3_authProtocol = cmdgen.usmNoAuthProtocol

    return v3_authProtocol


def get_v3_privProtocol_obj(v3_privProtocol_str):

    if v3_privProtocol_str == "usmDESPrivProtocol":
        v3_privProtocol = cmdgen.usmDESPrivProtocol
    elif v3_privProtocol_str == "usm3DESEDEPrivProtocol":
        v3_privProtocol = cmdgen.usm3DESEDEPrivProtocol
    elif v3_privProtocol_str == "usmAesCfb128Protocol":
        v3_privProtocol = cmdgen.usmAesCfb128Protocol
    elif v3_privProtocol_str == "usmAesCfb192Protocol":
        v3_privProtocol = cmdgen.usmAesCfb192Protocol
    elif v3_privProtocol_str == "usmAesCfb256Protocol":
        v3_privProtocol = cmdgen.usmAesCfb256Protocol
    elif v3_privProtocol_str == "usmNoPrivProtocol":
        v3_privProtocol = cmdgen.usmNoPrivProtocol
    else:
        v3_privProtocol = cmdgen.usmNoPrivProtocol 

    return v3_privProtocol


#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    item_node = root.getElementsByTagName("item")[0]
    if item_node:

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

class ProcessCheckerThread(threading.Thread):

   def __init__(self, pid):
      threading.Thread.__init__(self)
      self.pid = pid
      
   def run(self):

      while(True):  
          time.sleep(5) 
          try:
            if os.name == 'nt':
                tasklist_response = subprocess.check_output('tasklist /FO csv /FI "PID eq '+str(self.pid)+'"')
                for line in tasklist_response.splitlines():
                    if str(line).find("No tasks are running"):
                        raise OSError(errno.ESRCH)               
            else:   
                #doesn't kill , just checks if process is running on POSIX systems only
                os.kill(self.pid, 0)
          except OSError as error:
            if error.errno == errno.ESRCH: 
                logger.info("Parent PID %s is not runnning , exiting." % self.pid)
                if child_pid is None:
                    pass
                else:
                    logger.info("Killing child process %s" % child_pid)
                    if os.name == 'nt':
                        os.kill(child_pid, signal.CTRL_C_EVENT)
                    else:    
                        os.kill(child_pid, signal.SIGTERM)

                this_pid = os.getpid()
                logger.info("Killing this process %s" % this_pid) 
                if os.name == 'nt':
                    os.kill(this_pid, signal.CTRL_C_EVENT)
                else:  
                    os.kill(this_pid, signal.SIGTERM)


if __name__ == '__main__':
   
    actual_execution = False
    
    if(sys.argv[-1] == "--redirected"):
       actual_execution = True

    if not actual_execution and len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":           
            do_scheme()
            sys.exit(0)
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
            sys.exit(0)
        else:
            usage()
    else:

        config_str = sys.stdin.read()               
        config = get_input_config(config_str) 

        #generate a unique log name for each stanza. 
        stanza_name = config.get("name")
        hash_of_stanza_name = hashlib.md5(stanza_name.encode('utf-8'))
        LOG_NAME = hash_of_stanza_name.hexdigest() + "_snmpmodinput_app_modularinput.log"
        LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk",LOG_NAME)
        global log_formatter,log_handler

        log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s stanza:{0}'.format(stanza_name))
        log_handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
        log_handler.setFormatter(log_formatter)
        logger.addHandler(log_handler)

        run_process_checker=bool(int(config.get("run_process_checker",1)))

        global child_pid
        child_pid = None

        if run_process_checker:
            parent_pid = os.getppid()
            processCheckerThread = ProcessCheckerThread(parent_pid)
            logger.info("Starting process checker thread for parent PID %s " % parent_pid)
            processCheckerThread.start()

        
        if not actual_execution:
             
            use_system_python=bool(int(config.get("use_system_python",0)))
            system_python_path=config.get("system_python_path","/usr/bin/python")

            if use_system_python:
                script_args = [ system_python_path,sys.argv[0] ]
                #script_args.extend(sys.argv[1:])
                script_args.append("--redirected")

                
                #cleanup up the Splunk python environment settings
                if 'LD_LIBRARY_PATH' in os.environ:
                    del os.environ['LD_LIBRARY_PATH']
                
                # Now we can run our command   
                process = Popen(script_args,stdout=sys.stdout, stdin=PIPE, stderr=sys.stderr)

                
                child_pid = process.pid
                logger.info("Using System python at %s , child process opening with PID %s" % (system_python_path,child_pid))

                stdout_value, stderr_value = process.communicate(input=config_str.encode())             
                process.wait()
                sys.exit(process.returncode)
            else:
                logger.info("Using Splunk's python")
                actual_execution = True

        if actual_execution:               

            #change log level from configuration stanza if present
            log_level_str = config.get("log_level","INFO")

            log_level = logging.getLevelName(log_level_str)
            logger.setLevel(log_level)
            
            #enable pysnmp library debug logging
            if log_level_str == "DEBUG":
                debug_printer = Printer(
                    logger=logger,
                    handler=log_handler,
                    formatter=log_formatter
                )
                setLogger(Debug('io','dsp','msgproc','secmod','proxy',printer=debug_printer))

            do_run(config)
                
            sys.exit(0)
