import sys
import json
import os
import gzip
import csv
import requests
import logging
from datetime import datetime
# Splunk imports
import splunk.rest as rest
# Local imports
import credentials as cred
from auth_handlers import TokenAuth


try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
# Get current app name
myapp = __file__.split(os.sep)[-3]
sys.path.append(make_splunkhome_path(["etc", "apps", myapp, "bin", "lib"]))

from cim_actions import ModularAction

logger = ModularAction.setup_logger('upload_ioc_report_modalert')

class UploadIOCAction(ModularAction):
    def __init__(self, settings, logger, action_name=None):
        super(UploadIOCAction, self).__init__(settings, logger, action_name)

    def write_event(self, data):
        self.addevent(json.dumps(data), sourcetype="trustar:report:ar")
        self.writeevents(index="main")
        del self.events[:]
        return

    def decrypt_existing_credentials(self, session_key, https_proxy_username, mod_input_name):
        key_values = {}
        key_type = ["key", "secret"]
        if https_proxy_username and https_proxy_username!="None":
            key_type.append("https_proxy_password")
        for _, value in enumerate(key_type):
            cred_manager = cred.CredentialManager(session_key)
            stanza_name = mod_input_name + "_" + value
            key_values[value] = cred_manager.get_clear_password(myapp, stanza_name, myapp)
        return key_values

    def get_enclves(self, session_key):
        try:
            path = "/servicesNS/nobody/Trustar/configs/conf-trustar_enclaves/enclave"
            _, content = rest.simpleRequest(path, method='GET', sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
        except Exception as exe:
            self.message("TruSTAR Error: Error while getting enclaves : %s " % str(exe), status="failure", level=logging.ERROR)
            self.write_event({'error_message': 'Error while getting enclaves', 'error': str(exe)})
            sys.exit(0)
        enclave_id = json.loads(content)['entry'][0].get('content')
        if enclave_id:
            enclave_id = enclave_id.get('enclaves')
        return enclave_id

    def create_proxy_uri(self, custom_auth_handler_args, https_proxy, https_proxy_port, https_proxy_username, https_proxy_password):
        proxy_address = None
        if https_proxy and https_proxy != "None":
            if https_proxy_username and https_proxy_username != "None":
                protocol = https_proxy.split("://")[0]
                server = https_proxy.split("://")[1]
                proxy_address = protocol + "://" + https_proxy_username + ":" + https_proxy_password + "@" + server + ":" + https_proxy_port
            else:
                proxy_address = https_proxy + ":" + https_proxy_port
        if proxy_address:
            custom_auth_handler_args.update({"proxies": proxy_address})
        return proxy_address

    def fetch_notable_event(self):
        raw = ""
        try:
            if os.path.exists(self.results_file):
                with gzip.open(self.results_file, 'rb') as fh:
                    for num, result in enumerate(csv.DictReader(fh)):
                        result.setdefault('rid', str(num))
                        self.update(result)
                        self.invoke()
                        raw = result.get('_raw') if '_raw' in result else result.get('orig_raw')
                        raw = raw.replace('"', "'")
        except Exception as exe:
            self.message("Unable to fetch notable event. " + str(exe), status="failure", level=logging.ERROR)
            self.write_event({'error_message': "Unable to fetch notable event", 'error': str(exe)})
            sys.exit(0)
        return raw

    def dowork(self):
        session_key = self.session_key
        raw = self.fetch_notable_event()
        try:
            path = "/services/data/inputs/trustar"
            _, content = rest.simpleRequest(path, method='GET', sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
        except Exception as exe:
            self.message("TruSTAR Error: Error while getting content : %s " % str(exe), status="failure", level=logging.ERROR)
            return self.write_event({'error_message': 'Error while getting content', 'error': str(exe)})
        data = json.loads(content)['entry']

        if not data:
            self.message('TruStar Error: Modular Input not found ', status="failure", level=logging.ERROR)
            return self.write_event({'error_message': 'Modular Input not found'})
        
        trustar_url = str(data[0]['content'].get('trustar_url')).strip().strip('/')
        https_proxy_username = str(data[0]['content'].get('https_proxy_username'))
        https_proxy = str(data[0]['content'].get('https_proxy'))
        https_proxy_port = str(data[0]['content'].get('https_proxy_port'))
        cert_path = str(data[0]['content'].get('cert_path'))
        mod_input_name = str(data[0].get('name'))
        time_began = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S")
        title = data[0]['acl'].get('app') + "Report_" + str(time_began)

        try:
            passwords = self.decrypt_existing_credentials(session_key, https_proxy_username, mod_input_name)
        except Exception as exe:
            self.message("TruSTAR Error: Error while decrypt credentials : %s " % str(exe), status="failure", level=logging.ERROR)
            return self.write_event({'error_message': 'Error while decrypt credentials', 'error': str(exe)})

        https_proxy_password = passwords.get('https_proxy_password')
        api_key = passwords.get('key')
        api_secret = passwords.get('secret')
        enclave_id = self.get_enclves(session_key)
        
        verify =True
        if cert_path and cert_path.strip() != "" and cert_path != "None":
            # Override verify with the provided certificate path
            verify = cert_path.strip()

        custom_auth_handler_args = {"url": trustar_url}

        # Create proxy url
        proxy_address = self.create_proxy_uri(custom_auth_handler_args, https_proxy, https_proxy_port, https_proxy_username, https_proxy_password)
        # Initialize object of "TokenAuth" class
        custom_auth_handler_instance = TokenAuth(**custom_auth_handler_args)
        # Get access token
        access_token = custom_auth_handler_instance.get_access_token(api_key, api_secret, verify)
        # Provide error and exit if access_token is not available
        if not access_token:
            self.message("Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect.", status="failure", level=logging.ERROR)
            return self.write_event({'error':'Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect.'})
        headers = {
            'Content-Type': 'application/json',
            "Authorization": "Bearer " + str(access_token['access_token']),
            "Client-Type":"API",
            "Client-Version": "1.3",
            "Client-Metatag": "SPLUNK"

        }
        proxies = {'http': proxy_address, 'https': proxy_address}

        post_data = {}
        if enclave_id:
            enclave_list = str(enclave_id).strip().split(",")
            if "*" in enclave_list:
                enclave_list.remove('*')
            post_data["distributionType"] = "ENCLAVE"
            post_data["enclaveIds"] = enclave_list
        else:
            post_data["distributionType"] = "COMMUNITY"

        url = trustar_url + "/api/1.3/reports"
        post_data ["title"] = title
        post_data["reportBody"] = raw
        try:
            response = requests.post(url, data=json.dumps(post_data), headers=headers, proxies=proxies)
        except Exception as exe:
            self.message("Unable to upload IOC. " + str(exe), status="failure", level = logging.ERROR)
            return self.write_event({"error_message":"Unable to upload IOC.", "error":str(exe)})
        if response.status_code == 200:
            # Prepare output to be displayed
            response = {"reportId": str(response.text)}
            self.message('Successfully created splunk event', status='success')
            return self.write_event(response)
        else:
            self.message("TruSTAR Error: Unable to upload IOC", status="failure", level=logging.ERROR)
            return self.write_event({"error_message":"Unable to upload IOC", "error":response.status_code})

if __name__ == "__main__":
    logger.info("Alert action upload_ioc_report started.")
    if len(sys.argv) > 1 and sys.argv[1] != "--execute":
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
    modaction = UploadIOCAction(sys.stdin.read(), logger, 'upload_ioc_report')
    modaction.addinfo()
    modaction.dowork()
    sys.exit(0)
