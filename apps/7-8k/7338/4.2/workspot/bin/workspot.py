import sys, time, os, csv, base64, hmac, hashlib, shutil
import xml.dom.minidom
import logging

import json
import http.client as httplib
from urllib.parse import urlparse

import splunklib.client as client
from splunklib.modularinput import *

#set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

END_POINT_HOST = "control.workspot.com"
END_POINT_PORT = 443
MASK           = "<masked key>"

SCHEME = """<scheme>
    <title>Workspot</title>
    <description>Get events from Workspot Control.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>simple</streaming_mode>
    
    <endpoint>
        <args>
            <arg name="name">
                <title>Name</title>
                <description>Name of the data input.</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="endpoint_hostname">
                <title>Endpoint host</title>
                <description>Deployment endpoint hostname.</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            <arg name="key_id">
                <title>Key ID</title>
                <description>Your Workspot key ID.</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
    
            <arg name="secret_key">
                <title>Secret key</title>
                <description>Your Workspot secret key.</description>
                <required_on_edit>true</required_on_edit>
                <required_on_create>true</required_on_create>
            </arg>
            
            <arg name="http_proxy">
                <title>Proxy Address</title>
                <description>Web Proxy Address.</description>
                <required_on_edit>false</required_on_edit>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
    </scheme>
    """

def do_scheme():
    print (SCHEME)

# prints XML error data to be consumed by Splunk
def print_error(s):
    #print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)
    logging.error(s)

def log_response(resp):
    status, reason = resp.status, resp.reason
    s = "status=%s reason=\"%s\"" % (str(status), str(reason))
    if status == 200:
        logging.debug(s)
    else:
        logging.error(s)

# parse the workspot error string and extract the message
def get_workspot_error(s):
    return s

def validate_conf(config, key):
    if key not in config:
        raise Exception("Invalid configuration received from Splunk: key '%s' is missing." % key)

# number of expected columns in the checkpoint file
Checkpointer_COLS = 2

class Checkpointer:
    
    def __init__(self, checkpoint_dir):
        self.chkpoint_file_name = os.path.join(checkpoint_dir, "workspot.txt")
        self.chkpoint_value=0
        self.event_count=0
        # load checkpoint into memory
        self._load()
        self.last_chkpnt_time = 0.0
    
    def _load(self):
        f = self._open_checkpoint_file("r")
        if f is None:
            return
        
        reader = csv.reader(f)
        line = 1
        for row in reader:
            if len(row) >= Checkpointer_COLS:
                # the first column of the row is the checkpoint value, 
                #second column is the events count between checkpoints
                try:
                    self.chkpoint_value = row[0];
                    self.event_count = row[1];
                except:
                    logging.error("The CSV file='%s' line=%d appears to be corrupt." % \
                                  (self.chkpoint_file_name, line))
                    raise
            else:
                logging.warn("The CSV file='%s' line=%d contains less than %d columns." % \
                             (self.chkpoint_file_name, line, Checkpointer_COLS))
            line += 1
        
        f.close()
    
    def _open_checkpoint_file(self, mode):
        if not os.path.exists(self.chkpoint_file_name):
            return None
        # try to open this file
        f = None
        try:
            f = open(self.chkpoint_file_name, mode)
        except Exception(e):
            logging.error("Error opening '%s': %s" % (self.chkpoint_file_name, str(e)))
            return None
        return f
    
    # write a checkpoint value
    def save_chkpoint(self, chkpoint_value, event_count):
        tmp_file = self.chkpoint_file_name + ".tmp"
        f = None
        try:
            f = open(tmp_file, "w+")
        except Exception(e):
            logging.error("Unable to open file='%s' for writing: %s" % \
                          self.chkpoint_file_name, str(e))
        
        writer = csv.writer(f)
        
        writer.writerow([str(chkpoint_value), str(event_count)])
        
        f.close()
        shutil.move(tmp_file, self.chkpoint_file_name)
        self.chkpoint_value = chkpoint_value
        self.event_count = event_count
        self.last_chkpnt_time = time.time()

#read XML configuration passed from splunkd
def get_config():
    config = {}
    
    try:
        # read everything from stdin
        config_str = sys.stdin.read()
        
        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if conf_node:
            logging.debug("XML: found configuration")
            stanza = conf_node.getElementsByTagName("stanza")[0]
            if stanza:
                stanza_name = stanza.getAttribute("name")
                if stanza_name:
                    logging.debug("XML: found stanza " + stanza_name)
                    config["name"] = stanza_name
                    
                    params = stanza.getElementsByTagName("param")
                    for param in params:
                        param_name = param.getAttribute("name")
                        logging.debug("XML: found param '%s'" % param_name)
                        if param_name and param.firstChild and \
                            param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                                data = param.firstChild.data
                                config[param_name] = data
                                logging.debug("XML: '%s' -> '%s'" % (param_name, data))
        
        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if checkpnt_node and checkpnt_node.firstChild and \
            checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE:
                config["checkpoint_dir"] = checkpnt_node.firstChild.data
                logging.debug("Check point dir = %s", config["checkpoint_dir"])
        
        sessionkey_node = root.getElementsByTagName("session_key")[0]
        if sessionkey_node and sessionkey_node.firstChild and \
            sessionkey_node.firstChild.nodeType == sessionkey_node.firstChild.TEXT_NODE:
                config["session_key"] = sessionkey_node.firstChild.data
                
        if not config:
            raise Exception("Invalid configuration received from Splunk.")
        
        # just some validation: make sure these keys are present (required)
        validate_conf(config, "name")
        validate_conf(config, "key_id")
        validate_conf(config, "secret_key")
        validate_conf(config, "checkpoint_dir")
    except Exception(e):
        raise Exception("Error getting Splunk configuration via STDIN: %s" % str(e))
    
    return config

def get_validation_data():
    val_data = {}
    
    # read everything from stdin
    val_str = sys.stdin.read()
    
    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement
    
    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")
        
        name = item_node.getAttribute("name")
        val_data["stanza"] = name
        
        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if name and param.firstChild and \
                param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                    val_data[name] = param.firstChild.data
                    
        sessionkey_node = root.getElementsByTagName("session_key")[0]
        if sessionkey_node and sessionkey_node.firstChild and \
            sessionkey_node.firstChild.nodeType == sessionkey_node.firstChild.TEXT_NODE:
                val_data["session_key"] = sessionkey_node.firstChild.data        
    
    return val_data

# check the workspot credentials are valid
def validate_arguments():
    val_data = get_validation_data()
    key_id = val_data["key_id"]
    
    endpoint_hostname = val_data["endpoint_hostname"]
    logging.info("Endpoint hostname from config %s" % endpoint_hostname)
    global END_POINT_HOST
    END_POINT_HOST = endpoint_hostname
    
    http_proxy = None
    if "http_proxy" in val_data:
        http_proxy = val_data["http_proxy"]
        
    secret_key = val_data["secret_key"]
    if secret_key == MASK:
        session_key = val_data["session_key"]
        secret_key = get_password(session_key, key_id)

    validate_config(key_id, secret_key, http_proxy)
        
def validate_config(key_id, secret_key, http_proxy):
    try:
        # Submit POST request for data retrieval
        conn = get_http_connection(http_proxy)
        
        url = '/services/data/v2/event'
        body = '{"version":"4.2","provider":"Splunk","test":"true"}'
        
        #conn.sock.settimeout(timeout)
        headers = {}
        add_headers(headers, key_id, secret_key, 'POST', url, body)
        headers['Content-type'] = 'application/json; charset=UTF-8';
        
        conn.request('POST', url, body, headers)
        resp = conn.getresponse()
        if resp.status != 200:
            logging.error("Invalid workspot credentials %s:" % (key_id))
            raise (Exception,"HTTP request to Workspot Control returned with status code %d (%s): %s" % (resp.status,resp.reason, resp.read()))
        
        log_response(resp)
        
        conn.close()
    except Exception(e):
        print_error("Invalid configuration specified: %s" % str(e))
        sys.exit(1)

def encrypt_password(username, password, session_key):
    args = {'token':session_key}
    service = client.connect(**args)
    try:
        # If the credential already exists, delte it.
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                service.storage_passwords.delete(username=storage_password.username)
                break

        # Create the credential.
        service.storage_passwords.create(password, username)

    except Exception as e:
        raise Exception ("An error occurred updating sensitive data. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

def mask_password(input_kind, input_name, session_key, username, endpoint_hostname):
    try:
        args = {'token':session_key}
        service = client.connect(**args)
        logging.info("inputKind: %s, input_name: %s" % (input_kind, input_name))
             
        item = service.inputs.__getitem__((input_name, input_kind))

        if item:
            logging.info("Found non null item")
        kwargs = {
            'key_id': username,
            'secret_key': MASK,
            'endpoint_hostname': endpoint_hostname
        }
        item.update(**kwargs).refresh()
    except Exception as e:
        raise Exception("Error updating inputs.conf: %s" % str(e))
            
def get_password(session_key, username):
    args = {'token':session_key}
    service = client.connect(**args)

    # Retrieve the password from the storage/passwords endpoint    
    for storage_password in service.storage_passwords:
        if storage_password.username == username:
            return storage_password.content.clear_password
        
def run():
    
    #httplib.HTTPConnection.debuglevel = 1
    
    config = get_config()
    
    key_id = config["key_id"]
    secret_key = config["secret_key"]
    session_key = config["session_key"]
    http_proxy = None
    if "http_proxy" in config:
        http_proxy = config["http_proxy"]

    endpoint_hostname = None
    if "endpoint_hostname" in config:
        endpoint_hostname = config["endpoint_hostname"]
        global END_POINT_HOST
        END_POINT_HOST = endpoint_hostname
    
    clear_secret_key = ""
    
    chk = Checkpointer(config["checkpoint_dir"])
    
    try:
        # If the password is not masked, mask it.
        if secret_key != MASK:
            input_kind, input_name = config["name"].split("://")
            encrypt_password(key_id, secret_key, session_key)
            mask_password(input_kind, input_name, session_key, key_id, endpoint_hostname)

        clear_secret_key = get_password(session_key, key_id)

    except Exception as e:
        logging.error("Error decrypting secret key: %s" % str(e))
        raise Exception("Error decrypting secret key")
          
    fetch_data(chk, key_id, clear_secret_key, http_proxy)

def get_http_connection(http_proxy):
    #timeout = 5.0
    if not http_proxy is None:
        url = urlparse.urlparse('http://' + http_proxy)
        conn = httplib.HTTPSConnection(url.hostname, url.port)
        conn.set_tunnel(END_POINT_HOST, END_POINT_PORT)
    else:
        conn = httplib.HTTPSConnection(END_POINT_HOST, END_POINT_PORT)
        conn.connect()
        
    return conn

def add_headers(headers, key_id, secret_key, method, path, body):
    date_str = gen_date_string()
    headers['Authorization'] = get_auth_header_value(key_id, secret_key, date_str, method , path, body)
    headers['x-ws-timestamp'] = date_str

# returns "Authorization" header string
def get_auth_header_value(key_id, secret_key, date_str, method, path, body):
    body_hash = ''
    if body:
        body_hash = hashlib.md5(body.encode('utf-8')).hexdigest()
    to_sign = string_to_sign(method, date_str, path, body_hash)
    signaturebytes = base64.encodebytes(hmac.new(bytes(secret_key, 'utf-8') , bytes(to_sign, 'utf-8'), hashlib.sha256).digest()).strip()
    signature = str(signaturebytes, encoding='UTF-8')
    Val = ("%s:%s" % (key_id, signature))
    b64Bytes = base64.b64encode(bytes(Val, 'utf-8'))
    b64Val = str(b64Bytes, encoding='UTF-8')
    return "WS %s" % b64Val

def string_to_sign(method, date_str, path, body):
    return "%s\n%s\n%s\n\nx-ws-timestamp:%s" % (method, body, path, date_str)

def gen_date_string():
    return int(time.time() * 1000.0)

def fetch_data(chk, key_id, secret_key, http_proxy):
    
    while True:
        data_available = True
        chkpoint_value = chk.chkpoint_value
        event_count = int(chk.event_count)
        error_status_code = 0
        
        try:
            while data_available:
                
                # Submit POST request for data retrieval
                conn = get_http_connection(http_proxy)
                url = '/services/data/v2/event'
                body = '{"version":"4.2","provider":"Splunk","checkpoint":"' + str(chkpoint_value) + '"}'
                #conn.sock.settimeout(timeout)
                headers = {}
                add_headers(headers, key_id, secret_key, 'POST', url, body)
                headers['Content-type'] = 'application/json; charset=UTF-8';
                
                conn.request('POST', url, body, headers)
                
                resp = conn.getresponse()
                
                if resp.status != 202:
                    error_status_code = resp.status
                    raise Exception("HTTP POST request to Workspot Control returned with status code %d (%s): %s" % (resp.status, resp.reason, get_workspot_error(resp.read())))
                
                responseStr = resp.read()
                data = json.loads(responseStr)
                url = str(data["poll"])
                
                logging.debug("poll url=" + url)
                conn.close
                
                # Do a HEAD request for status check using the poll url from above response
                head_status_code = 0;
                headers.clear()
                add_headers(headers, key_id, secret_key, 'HEAD', url, '')
                while (head_status_code != 200):
                    # check every 30 seconds
                    time.sleep(30)
                    conn = get_http_connection(http_proxy)
                    conn.request('HEAD', url, None, headers)
                    resp = conn.getresponse()
                    
                    head_status_code = resp.status
                    if head_status_code != 200 and head_status_code != 202:
                        error_status_code = resp.status
                        raise Exception("HTTP HEAD request to Workspot Control returned with status code %d" % (head_status_code))
                    conn.close
                
                # Data is ready to be fetched...Do a GET request to fetch the data
                conn = get_http_connection(http_proxy)
                headers.clear()
                add_headers(headers, key_id, secret_key, 'GET', url, '')
                conn.request('GET', url, None, headers)
                resp = conn.getresponse()
                #logging.debug("GET response=" + resp.read())
                
                if resp.status != 200 and resp.status != 204:
                    error_status_code = resp.status
                    raise Exception("HTTP GET request to Workspot Control returned with status code %d (%s): %s" % (resp.status,resp.reason, get_workspot_error(resp.read())))
                
        
                if resp.status == 204:
                    data_available = False
                else:
                    response_data = resp.read()
                    
                    i = 1
                    output = json.loads(response_data)
                    for event in output["events"]:
                        if i > event_count:
                            print (json.dumps(event))
                            if (i % 5 == 0):
                                #save checkpoint info every 5 events
                                chk.save_chkpoint(chkpoint_value, i)
                        i = i+1
                    
                    sys.stdout.flush()
        
                    #save checkpoint info
                    new_chkpoint = resp.getheader('X-WS-CHECKPOINT')
                    rec_count = int(resp.getheader('X-WS-NUM-REC'))
                    chk.save_chkpoint(new_chkpoint, 0)
        
                    chkpoint_value = new_chkpoint
                    event_count = 0

                    # If the data returned is less than 1000 (standard chunk size), the client already caught up with the server.
                    # Wait till next sync interval (15 min.), to fetch furthur data.
                    if i < 1001:
                        data_available = False

                conn.close()
                
                # check every 10 seconds for more entries
                time.sleep(10)
                
        except Exception as e:
            sys.stdout.flush()
            logging.error("Error fetching events %s" % str(e))

        if (error_status_code == 403 or error_status_code == 401):
            logging.debug("Key is no longer valid or Company is suspended. Stopping the client")
            break
        else:
            #sleep for 15 min.
            logging.debug("Scheduling the next run after 15 min.")
            time.sleep(900)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            print ('No tests for the scheme present')
        else:
            print ('Invalid arguments')
    else:
        # request data from Workspot Control
        run()
    
    sys.exit(0)