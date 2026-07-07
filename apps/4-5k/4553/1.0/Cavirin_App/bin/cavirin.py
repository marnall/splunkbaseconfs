import sys, time, os
import httplib, urllib, hashlib, base64, hmac, urlparse, md5
import xml.dom.minidom, xml.sax.saxutils
import logging
import tarfile, gzip
import requests
import base64
import json 
import traceback
import datetime

logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)
currentDT = datetime.datetime.utcnow()
deltaTime = currentDT - datetime.timedelta(minutes=5)
currentTime = str(currentDT.strftime('%Y-%m-%dT%H:%M:%S') + currentDT.strftime('.%f')[:4] + 'Z')
deltaTimeModified = str(deltaTime.strftime('%Y-%m-%dT%H:%M:%S') + deltaTime.strftime('.%f')[:4] + 'Z')




SCHEME = """<scheme>
    <title>Cavirin</title>
    <description>Cavirin Hybrid Cloud Security & Compliance Platform</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>

    <endpoint>
        <args>
            <arg name="endpoint">
                <title>API Endpoint</title>
                <description>Cavirin API Endpoint
                </description>
            </arg>

            <arg name="username">
                <title>Username</title>
                <description>Service Account username for Cavirin</description>
            </arg>

            <arg name="password" type="password">
                <title>Password</title>
                <description>Service Account password for Cavirin</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def init_stream():
    sys.stdout.write("<stream>")

def fini_stream():
    sys.stdout.write("</stream>")

def send_data(buf, name):
    sys.stdout.write("<event stanza='cavirin://"+name+"'><data>")
    sys.stdout.write(xml.sax.saxutils.escape(buf))
    sys.stdout.write("</data>\n")
    sys.stdout.write("</event>\n")

def send_data_time(buf, time, name):
    sys.stdout.write("<event stanza='cavirin://"+name+"'>")
    sys.stdout.write("<time>"+time+"</time><data>")
    sys.stdout.write(xml.sax.saxutils.escape(buf))
    sys.stdout.write("</data>\n")
    sys.stdout.write("</event>\n")

def send_done_key(source):
    sys.stdout.write("<event unbroken=\"1\"><source>")
    sys.stdout.write(xml.sax.saxutils.escape(source))
    sys.stdout.write("</source><done/></event>\n")

# prints XML error data to be consumed by Splunk
def print_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

def get_validation_data():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    logging.error("validation string = " + str(val_str))

    doc = xml.dom.minidom.parseString(val_str)
    logging.error("HELLO-CAVIRIN " + str(doc.toprettyxml()).replace("\n"," "))

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

    return val_data

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

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

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        validate_conf(config, "name")
        validate_conf(config, "endpoint")
        validate_conf(config, "username")
        validate_conf(config, "password")
        validate_conf(config, "checkpoint_dir")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config


def validate_input(endpoint, username, password):

    url = "https://"+endpoint+"/pulsar-server/login"
    username_password = ""+username+":"+password
    encodedup = username_password.encode()
    b64Val = base64.b64encode(encodedup).decode("utf-8")
    payload = "undefined="
    headers = {
    'Content-Type': "application/x-www-form-urlencoded",
    'Authorization': "Basic %s" % b64Val,
    'cache-control': "no-cache"
    }
    response = requests.request("POST", url, data=payload, headers=headers,verify=False) 
    response_json = response.json()
    if response.status_code != 200:
        print_error("Invalid username/password")
        return None

    return response_json['access_token']


def validate_arguments():
    
    logging.error("Before get_validation_data")
    val_data = get_validation_data()
    logging.error("After get_validation_data")

    endpoint = val_data["endpoint"]
    username = val_data["username"]
    password = val_data["password"]

    try:
        if endpoint.strip() == "" or username.strip() == "" or password.strip() == "":
            print_error("Endpoint/Username/Password cannot be empty.")
            raise Exception, "Endpoint/Username/Password is empty."
        else:
            logging.error("Before calling validate_input")
            response = validate_input(endpoint, username, password)
            
    except Exception as e:
        print_error("Invalid configuration specified: %s" % str(e))
        logging.error("Required fields are empty %s" % str(e))
        sys.exit(1)


def do_scheme():
    print SCHEME
    
def test():
    init_stream()
    send_data("src1", "test 1")
    send_data("src2", "test 2")
    send_done_key("src2")
    send_data("src3", "test 3")

def usage():
    print "usage: %s [--scheme|--validate-arguments]"
    sys.exit(2)

def run():

    init_stream()

    logging.error("Inside RUN")
    credentials = get_config()
    logging.error("Username = " + credentials["username"])
    logging.error("Password = " + credentials["password"])
    logging.error("Endpoint = " + credentials["endpoint"])
    
    dashboardURL = "https://"+ credentials["endpoint"] + "/pulsar-server/api/v0/cisodashboard/cisoInfra"
    topIssuesURL = "https://" + credentials["endpoint"] + "/pulsar-server/api/v0/cisodashboard/topIssues"
    auditTrailURL = "https://" + credentials["endpoint"] + "/pulsar-server/api/v0/admin/auditTrail"
    riAwsURL = "https://" + credentials["endpoint"] + "/pulsar-server/api/v0/resource/resourceInventory?env=AWS"
    riGcpURL = "https://" + credentials["endpoint"] + "/pulsar-server/api/v0/resource/resourceInventory?env=GCP"
    riAzureURL = "https://" + credentials["endpoint"] + "/pulsar-server/api/v0/resource/resourceInventory?env=Azure"

    dashboardPayload = {"groupNames":["All"],"assetgroup":[],"os":[],"env":[],"policypack_name":[],"limit":50,"groupID":"null"}
    auditTrailPayload = {"start_time":deltaTimeModified, "end_time":currentTime, "event_name":[], "search":[], "username":[]}

    access_token = validate_input(credentials["endpoint"], credentials["username"], credentials["password"])
    logging.error("Before checking")
    if access_token:
        logging.error("Valid access_token!")
        BearerToken = 'Bearer ' + access_token
        dashboardHeaders = {
        'Authorization': BearerToken,
        'Content-Type': "application/json",
        'cache-control': "no-cache"
        }
        dashboardResponse = requests.request("POST", dashboardURL, data=json.dumps(dashboardPayload), headers=dashboardHeaders ,verify=False)
        topIssuesResponse = requests.request("POST", topIssuesURL, data=json.dumps(dashboardPayload), headers=dashboardHeaders, verify=False)
        awsInventoryResponse = requests.request("GET", riAwsURL, data={}, headers=dashboardHeaders, verify=False)
        gcpInventoryResponse = requests.request("GET", riGcpURL, data={}, headers=dashboardHeaders, verify=False)
        azureInventoryResponse = requests.request("GET", riAzureURL, data={}, headers=dashboardHeaders, verify=False)

        logging.error("awsInventoryResponse = " + str(awsInventoryResponse))
 

        auditTrailResponse = requests.request("POST", auditTrailURL, data=json.dumps(auditTrailPayload), headers=dashboardHeaders, verify=False)

        content = json.loads(dashboardResponse.text.encode('utf-8'))
        topIssuesContent = json.loads(topIssuesResponse.text.encode('utf-8'))
        auditTrailContent = json.loads(auditTrailResponse.text.encode('utf-8'))
        awsInventoryContent = json.loads(awsInventoryResponse.text.encode('utf-8'))
        gcpInventoryContent = json.loads(gcpInventoryResponse.text.encode('utf-8'))
        azureInventoryContent = json.loads(azureInventoryResponse.text.encode('utf-8'))
                 
        cyberposture_blob = content['Result']['cyberposture']
        topIssues_blob = topIssuesContent['Result']
        auditTrail_blob = auditTrailContent['Result']
        aws_inventory_blob = awsInventoryContent['Result']
        gcp_inventory_blob = gcpInventoryContent['Result']
        azure_inventory_blob = azureInventoryContent['Result']
        
        security_types_predefined = ["Cyberposture", "Security", "Compliance"]

        for security_type in cyberposture_blob:
            data = []
            security_types_predefined.remove(security_type["security_type"])
            data.append("SECURITY_TYPE="+str(security_type["security_type"]))
            data.append("SECURITY_SCORE="+str(security_type["score"]))
            event = "INFRA_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

        for security_type in security_types_predefined:
            data = []
            data.append("SECURITY_TYPE="+str(security_type))
            data.append("SECURITY_SCORE=N/A")
            event = "INFRA_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

        env_score_blob = content['Result']['env']
        for env in env_score_blob:
            data = []
            data.append("ENVIRONMENT = " + str(env["name"]))
            data.append("SCORE = " + str(env["score"]))
            data.append("LOW = " + str(env["low"]))
            data.append("MEDIUM = " + str(env["med"]))
            data.append("HIGH = " + str(env["high"]))
            data.append("PASS = " + str(env["pass"]))
            
            event = "ENVIRONMENT_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

        asset_groups_blob = content['Result']['groups']
        for asset in asset_groups_blob:
            data = []
            data.append("ASSET_GROUP = " + str(asset["name"]))
            data.append("SCORE = " + str(asset["score"]))
            data.append("LOW = " + str(asset["low"]))
            data.append("MEDIUM = " + str(asset["med"]))
            data.append("HIGH = " + str(asset["high"]))
            data.append("PASS = " + str(asset["pass"]))

            event = "ASSET_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

        service_os_blob = content['Result']['os']
        for os in service_os_blob:
            data = []
            data.append("SERVICE_OS = " +str(os["display_os"]))
            data.append("SCORE = " + str(os["score"]))
            data.append("LOW = " + str(os["low"]))
            data.append("MEDIUM = " + str(os["med"]))
            data.append("HIGH = " + str(os["high"]))
            data.append("PASS = " + str(os["pass"]))

            event = "SERVICE_OS_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

        policy_packs_blob = content['Result']['policyPack']
        for policy_pack in policy_packs_blob:
            data = []
            data.append("POLICY_PACK = " +str(policy_pack["title"]))
            data.append("SCORE = " + str(policy_pack["score"]))
            data.append("LOW = " + str(policy_pack["low"]))
            data.append("MEDIUM = " + str(policy_pack["med"]))
            data.append("HIGH = " + str(policy_pack["high"]))
            data.append("PASS = " + str(policy_pack["pass"]))

            event = "POLICY_PACK_SCORE: %s" % ", ".join(data)
            send_data(event, credentials["name"])

    
        for issue in topIssues_blob:
            try:
                data = []
                data.append("IMPROVEMENT_POTENTIAL = " + str(issue["improvement_potential"]))
                data.append("TITLE = " + str(issue["title"]))
                data.append("ENVIRONMENT = " + str(issue["hosts"][0]["env"]))
                data.append("SERVICE_IMPACTED = " + str(issue["hosts"][0]["os"]))
                data.append("POLICYPACK_TITLE = " + str(issue["policypack_title"]))
                data.append("RESOURCES_AFFECTED = " + str(issue["impacted_resource_count"]))

                event = "TOP_ISSUES: %s" % ", ".join(data)
                
                send_data(event, credentials["name"])

            except Exception as e:
                logging.error("Error is " + str(e))

        logging.error("Current Time = " + str(currentTime))
        logging.error("Past Time = " + str(deltaTimeModified))

        for audit in auditTrail_blob:
            try:
                data = []
                parsed = json.loads(str(audit["event_details"]))
                data.append("EVENT_DETAILS = " + str(json.dumps(parsed, indent=4, sort_keys=True)))
                data.append("EVENT_NAME = " + str(audit["event_name"]))
                data.append("USERNAME = " + str(audit["username"]))

                event = "SYSTEM_EVENTS: %s" % ", ".join(data)
                send_data_time(event, audit["eventtime"], credentials["name"])

            except Exception as e:
                logging.error("Error is " + str(e))
                logging.error(traceback.extract_stack())

        for resource in aws_inventory_blob:

            try:
                data = []
                data.append("DISPLAY_OS = " + str(resource["display_os"]))
                data.append("COUNT = " + str(resource["count"]))

                event = "AWS_RESOURCE_INVENTORY: %s" % ", ".join(data)
                send_data(event, credentials["name"])

            except Exception as e:
                logging.error("Error is " + str(e))

        for resource in gcp_inventory_blob:

            try:
                data = []
                data.append("DISPLAY_OS = " + str(resource["display_os"]))
                data.append("COUNT = " + str(resource["count"]))

                event = "GCP_RESOURCE_INVENTORY: %s" % ", ".join(data)
                send_data(event, credentials["name"])

            except Exception as e:
                logging.error("Error is " + str(e))

        for resource in azure_inventory_blob:

            try:
                data = []
                data.append("DISPLAY_OS = " + str(resource["display_os"]))
                data.append("COUNT = " + str(resource["count"]))

                event = "AZURE_RESOURCE_INVENTORY: %s" % ", ".join(data)
                send_data(event, credentials["name"])

            except Exception as e:
                logging.error("Error is " + str(e))


    fini_stream()

        



if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            test()
        else:
            usage()
    else:
        # just request data from S3
        run()

    sys.exit(0)