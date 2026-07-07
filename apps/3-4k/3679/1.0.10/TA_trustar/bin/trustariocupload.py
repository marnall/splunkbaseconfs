# Python imports
import sys
import json
import os
import os.path as op
from xml.dom.minidom import parseString
import re
import requests
from datetime import datetime, date, time
import urllib

# Splunk imports
import splunk.rest as rest
import splunk.Intersplunk
import logger_manager as log

# Local imports
import credentials as cred
from auth_handlers import TokenAuth

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
# Get current app name
myapp = __file__.split(os.sep)[-3]
APP_DIR = op.join(SPLUNK_HOME, "etc", "apps", myapp, "bin")
# Set up logger
logger = log.setup_logging('trustar_upload_ioc_custom_command')

# Get results of the search
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
# Obtain session key
sessionKey = settings.get("sessionKey")
# Obtain Splunk username
auth_string = settings.get("authString")
parsed_xml_content = parseString(auth_string)
splunk_username_tag = parsed_xml_content.getElementsByTagName("username")[0]
splunk_username = str(splunk_username_tag.firstChild.data)

try:
    if results:
        reportBody = str(dict(results[0])['_raw'])
    else:
        reportBody = str(str(settings.get('search').split("raw_event=")[-1]).split("| table")[0])
except Exception as exe:
    logger.error("TruSTAR Error: Error while getting post data , %s " % str(exe))

timeBegan = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
title = str(settings.get('namespace'))+"Report_"+str(timeBegan)

post_data = {"title": title,"reportBody":reportBody}
verify = True
try:
    # Make REST call    
    # We are keeping "/services/data/inputs/trustar" path as we have define the stanza name "trustar" in README/inputs.spec file 
    path = "/services/data/inputs/trustar"
    rsp, content = rest.simpleRequest(path, method='GET', sessionKey=sessionKey, raiseAllErrors=True)
except Exception as exe:
    logger.error("TruSTAR Error: Error while getting content : %s " % str(exe))
    splunk.Intersplunk.parseError("TruSTAR Error: Error while getting input form details.Please check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log"
                                      " for more information.")

try:
    # Parse the config XML
    doc = parseString(content)

    # Get root element
    root = doc.documentElement
    id_value = root.getElementsByTagName("id")[1]

    if id_value and id_value.firstChild and \
            id_value.firstChild.nodeType == id_value.firstChild.TEXT_NODE:
        value_title = id_value.firstChild.data

    mod_input_name = value_title.split("/")[-1]
    server_uri = value_title.split("/")[0]+"//"+value_title.split("/")[2]
    # Parse data
    content_data = rest.format.parseFeedDocument(content)
    content_dict = content_data[0].toPrimitive()

    https_proxy_username = str(content_dict.get('https_proxy_username'))
    https_proxy = str(content_dict.get('https_proxy'))
    https_proxy_port = str(content_dict.get('https_proxy_port'))
    cert_path = str(content_dict.get('cert_path'))
    try:
        path = "/servicesNS/nobody/Trustar/configs/conf-trustar_enclaves/enclave"
        rsp, content = rest.simpleRequest(path, method='GET', sessionKey=sessionKey, getargs={"output_mode": "json"}, raiseAllErrors=True)
    except Exception as exe:
        logger.error("TruSTAR Error: Error while getting Enclaves : %s " % str(exe))
        splunk.Intersplunk.parseError( "TruSTAR Error: Error while getting Enclaves.Please check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log for more information.")
        sys.exit(-1)
    enclave_id = json.loads(content)['entry'][0].get('content')
    if enclave_id:
        enclave_id = enclave_id.get('enclaves')


except Exception as exe:
    logger.error("TruSTAR Error: Error while manipulating content : %s " % str(exe))
    splunk.Intersplunk.parseError("TruSTAR Error: Error while getting content.Please check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log"
                                      " for more information.")


def decrypt_existing_credentials():
    """ Retrieves auth_password from passwords.conf.

    :param key_type: type of key (key or secret)
    :return: clear password
    """
    key_values = {}
    key_type = ["key","secret"]
    if https_proxy_username and https_proxy_username!="None":
        key_type.append("https_proxy_password")
    try:
        for idx, value in enumerate(key_type):
            cred_manager = cred.CredentialManager(sessionKey, server_uri)
            stanza_name = urllib.unquote(mod_input_name)+"_"+value
            key_values[value] = cred_manager.get_clear_password(myapp, stanza_name, myapp)
    except Exception as exe:
        logger.error("TruSTAR Error: Error while decrypt credentials : %s " % str(exe))
        splunk.Intersplunk.parseError("TruSTAR Error: Error while decrypting credentials.Please check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log"
                                      " for more information.")
    return key_values


# Strip out spaces from certificate path if path is not empty string
if cert_path and cert_path.strip() != "" and cert_path != "None":
    # Override verify with the provided certificate path
    verify = cert_path.strip()
data_list = decrypt_existing_credentials()

https_proxy_password = data_list.get('https_proxy_password')
api_key = data_list.get('key')
secret_key = data_list.get('secret')

custom_auth_handler_args = {"url": str(content_dict.get('trustar_url')).strip().strip('/')}

# Create proxy url
if https_proxy and https_proxy!="None":
    if https_proxy_username and https_proxy_username!="None":
        protocol = https_proxy.split("://")[0]
        server = https_proxy.split("://")[1]
        proxy_address = protocol+"://"+https_proxy_username+":"+https_proxy_password+"@"+server+":"+https_proxy_port
    else:
        proxy_address = https_proxy+":"+https_proxy_port
else:
    proxy_address = None

if proxy_address:
    custom_auth_handler_args.update({"proxies": proxy_address})

# Initialize object of "TokenAuth" class
custom_auth_handler_instance = TokenAuth(**custom_auth_handler_args)

# Get access token
access_token = custom_auth_handler_instance.get_access_token(api_key, secret_key, verify)
# Provide error and exit if access_token is not available
if not access_token:
    logger.error("Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect.")
    splunk.Intersplunk.parseError("Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect and check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log"
                                      " for more information.")
    sys.exit(2)

headers = {
    'Content-Type': 'application/json',
    "Authorization": "Bearer " + str(access_token['access_token']),
    "Client-Type":"API",
    "Client-Version": "1.3",
    "Client-Metatag": "SPLUNK"

}
proxies = {'http':proxy_address, 'https':proxy_address}

if enclave_id:
    enclaveId = str(enclave_id).strip().split(",")
    if "*" in enclaveId:
        enclaveId.remove('*')
    distributionType = "ENCLAVE"
    post_data["distributionType"] = distributionType
    post_data["enclaveIds"] = enclaveId
else:
    distributionType = "COMMUNITY"
    post_data["distributionType"] = distributionType

url = str(content_dict.get('trustar_url')).strip().strip('/')+"/api/1.3/reports"

try: 
    response = requests.post(url, data=json.dumps(post_data), headers=headers, proxies=proxies)

    # Prepare output to be displayed
    response = {"reportId": str(response.text)}
    outputResult = [{"Response": json.dumps(response)}]
    splunk.Intersplunk.outputResults(outputResult)
    
except Exception:
    logger.exception("TruStar Error: Error while uploading IOC")
    splunk.Intersplunk.parseError("Error encountered while executing command."
                                      " Please check $SPLUNK_HOME/var/log/trustar/trustar_upload_ioc_custom_command.log"
                                      " for more information.")
    sys.exit(-1)
