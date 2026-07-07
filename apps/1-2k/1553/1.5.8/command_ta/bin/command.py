import sys,logging,os,time,subprocess,re,hashlib
import xml.dom.minidom, xml.sax.saxutils
#for running on Universal Forwarders where the library is not present
try:
    import splunk.entity as entity
except:
    pass
from logging.handlers import TimedRotatingFileHandler
           
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","commandmodinput_app_modularinput.log")

# Set up a specific logger
logger = logging.getLogger('commandmodinput')

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)

CMD_OUTPUT_HANDLER_INSTANCE = None

SCHEME = """<scheme>
    <title>Command</title>
    <description>Command input wrapper for executing commands and indexing the output</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>

    <endpoint>
        <args>    
            <arg name="name">
                <title>Command Input Name</title>
                <description>Name of this command input definition</description>
            </arg>
            <arg name="activation_key">
                <title>Activation Key</title>
                <description>Visit http://www.baboonbones.com/#activation to obtain a non-expiring key</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="command_name">
                <title>Command Name</title>
                <description>Name of the system command if on the PATH (ps),  or if not , the full path to the command (/bin/ps).Environment variables in the format $VARIABLE$ can be included and they will be substituted ie: $SPLUNK_HOME$</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="command_args">
                <title>Command Arguments</title>
                <description>Arguments string for the command.Environment variables in the format $VARIABLE$ can be included and they will be substituted ie: $SPLUNK_HOME$</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg> 
            <arg name="streaming_output">
                <title>Streaming Output</title>
                <description>Whether or not the command output is streaming</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>      
            <arg name="execution_interval">
                <title>Command Execution Interval</title>
                <description>Interval time in seconds to execute the command</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="output_handler">
                <title>Command Output Handler</title>
                <description>Python classname of custom command output handler</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="output_handler_args">
                <title>Command Output Handler Arguments</title>
                <description>Command output handler arguments string ,  key=value,key2=value2</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="log_level">
                <title>Log Level</title>
                <description>Logging level (info, error, debug etc..)</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def get_credentials(session_key):
   myapp = 'command_ta'
   try:
      # list all credentials
      entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                    owner='nobody', sessionKey=session_key)
   except Exception as e:
      logger.error("Could not get credentials from splunk. Error: %s" % str(e))
      return {}

   return entities.items()

def do_validate():
    
    try:
        config = get_validation_config() 
        
        command_name=config.get("command_name")
        execution_interval=config.get("execution_interval")
        output_handler=config.get("output_handler")   
        
        validationFailed = False
    
        try:
            if not output_handler is None:
                module = __import__("outputhandlers")
                class_ = getattr(module,output_handler)
                instance = class_()
        except Exception as e:
            print_validation_error("Output Handler "+output_handler+" can't be instantiated")
            validationFailed = True
        try:
            if not execution_interval is None and int(execution_interval) < 1:
                print_validation_error("Execution interval must be a positive integer")
                validationFailed = True
        except Exception as e:
            print_validation_error("Execution interval must be an integer")
            validationFailed = True
        if not command_name is None and which(command_name) is None:
            print_validation_error("Command name "+command_name+" does not exist")
            validationFailed = True
        if validationFailed:
            sys.exit(2)
               
    except RuntimeError as e:
        logger.error("Looks like an error: %s" % str(e))
        sys.exit(1)
        raise   
     
def which(program):

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None
    
def do_run(config):
    

    SESSION_TOKEN = config.get("session_key")

    global STANZA
    STANZA = config.get("name")
    
    activation_key = config.get("activation_key").strip()
    app_name = "Command Modular Input"

    logger.info("%s : Executing Command Modular Input" % STANZA)
    
    if len(activation_key) > 32:
        activation_hash = activation_key[:32]
        activation_ts = activation_key[32:][::-1]
        current_ts = time.time()
        m = hashlib.md5()
        m.update((app_name + activation_ts).encode('utf-8'))
        if not m.hexdigest().upper() == activation_hash.upper():
            logger.error("%s : Trial Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % (STANZA,app_name))
            sys.exit(2)
        if ((current_ts - int(activation_ts)) > 604800):
            logger.error("%s : Trial Activation key for App '%s' has now expired. Please visit http://www.baboonbones.com/#activation to purchase a non expiring key." % (STANZA,app_name))
            sys.exit(2)
    else:
        m = hashlib.md5()
        m.update((app_name).encode('utf-8'))
        if not m.hexdigest().upper() == activation_key.upper():
            logger.error("%s : Activation key for App '%s' failed. Please ensure that you copy/pasted the key correctly." % (STANZA,app_name))
            sys.exit(2)
        
    
    credentials_list = get_credentials(SESSION_TOKEN)

    for i, c in credentials_list:
        replace_key='{encrypted:%s}' % c['username']

        for k, v in config.items():
            config[k] = v.replace(replace_key,c['clear_password'])


    command_name=config.get("command_name")
    command_args=config.get("command_args")
    
    command_string = command_name
    if command_args:
        command_string = command_string+" "+command_args
     
    try:    
        env_var_tokens = re.findall("\$(?:\w+)\$",command_string)
        for token in env_var_tokens:
            command_string = command_string.replace(token,os.environ.get(token[1:-1]))
    except: 
        e = sys.exc_info()[1]
        logger.error("%s : Looks like an error replacing environment variables: %s" % (STANZA,str(e)))  
         
    streaming_output=int(config.get("streaming_output",0))
    
    execution_interval=int(config.get("execution_interval",60))
    
    cmd_output_handler_args={} 
    cmd_output_handler_args_str=config.get("output_handler_args")
    if not cmd_output_handler_args_str is None:
        cmd_output_handler_args = dict((k.strip(), v.strip()) for k,v in 
              (item.split('=') for item in cmd_output_handler_args_str.split(',')))
        
    cmd_output_handler=config.get("output_handler","DefaultCommandOutputHandler")
    module = __import__("outputhandlers")
    class_ = getattr(module,cmd_output_handler)

    global CMD_OUTPUT_HANDLER_INSTANCE
    CMD_OUTPUT_HANDLER_INSTANCE = class_(**cmd_output_handler_args)
    
    while True:
            
        try:
            logger.info("%s : Executing command" % STANZA)
            proc = run_command(command_string)
            output_buffer = ""
            while True:
                line = proc.stdout.readline()
                line = line.decode('utf-8')
                if line != '':
                    if streaming_output :
                      handle_output(line.rstrip())
                    else :
                      output_buffer = output_buffer + line
                else:
                    break
            if not streaming_output:
                handle_output(output_buffer) 

            logger.info("%s : Sleeping until next execution" % STANZA)   
            time.sleep(float(execution_interval))
        except RuntimeError as e:
            logger.error("%s : Looks like an error: %s" % (STANZA,str(e)))
            sys.exit(2) 
        
def run_command(command):
    return subprocess.Popen(command,shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        
def handle_output(output): 
    
    try:  
        logger.info("%s : Processing command output" % STANZA)
        CMD_OUTPUT_HANDLER_INSTANCE(output)
        sys.stdout.flush()               
    except RuntimeError as e:
        logger.error("%s : Looks like an error handling the command output: %s" % (STANZA,str(e)))
        
# prints validation error data to be consumed by Splunk
def print_validation_error(s):
    print("<error><message>%s</message></error>" % xml.sax.saxutils.escape(s))
    
# prints XML stream
def print_xml_single_instance_mode(s):
    print("<stream><event><data>%s</data></event></stream>" % xml.sax.saxutils.escape(s))
    
# prints XML stream
def print_xml_multi_instance_mode(s,stanza):
    print("<stream><event stanza=""%s""><data>%s</data></event></stream>" % stanza,xml.sax.saxutils.escape(s))
    
# prints simple stream
def print_simple(s):
    print("%s\n" % s)
    
def usage():
    print("usage: %s [--scheme|--validate-arguments]")
    logger.error("Incorrect Program Usage")
    sys.exit(2)

def do_scheme():
    print(SCHEME)

def get_input_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

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
            logger.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logger.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name

                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logger.debug("XML: found param '%s'" % param_name)
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


#read XML configuration passed from splunkd, need to refactor to support single instance mode
def get_validation_config():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logger.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logger.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logger.debug("Found param %s" % name)
            if name and param.firstChild and \
               param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data

    return val_data

if __name__ == '__main__':
      
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":           
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            do_validate()
        else:
            usage()
    else:
        config = get_input_config()  

        #change log level from configuration stanza if present
        log_level = logging.getLevelName(config.get("log_level","INFO"))
        logger.setLevel(log_level)
        
        do_run(config)
        
    sys.exit(0)
