import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ta_cyber_triage_declare

import logging
import logging.handlers
import json
import ssl
import traceback

from solnlib import conf_manager
from httplib2 import Http, ProxyInfo, socks


from splunk.persistconn.application import PersistentServerConnectionApplication


def setup_logger(level):
     logger = logging.getLogger('ta_cyber_triage_test_connection')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/ta_cyber_triage_test_connection.log', maxBytes=25000000, backupCount=5)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
     logger.addHandler(file_handler)
     return logger


logger = setup_logger(logging.INFO)

app_name = "TA-cyber-triage"


class TestConnection(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()
        
    def build_http_connection(self, config, timeout=120, disable_ssl_validation=False):
        """
        :config: dict like, proxy and account information are in the following
                format {
                    "username": xx,
                    "password": yy,
                    "proxy_url": zz,
                    "proxy_port": aa,
                    "proxy_username": bb,
                    "proxy_password": cc,
                    "proxy_type": http,http_no_tunnel,sock4,sock5,
                    "proxy_rdns": 0 or 1,
                }
        :return: Http2.Http object
        """
        if not config:
            config = {}

        proxy_type_to_code = {
            "http": socks.PROXY_TYPE_HTTP,
            #"http_no_tunnel": socks.PROXY_TYPE_HTTP_NO_TUNNEL,
            "socks4": socks.PROXY_TYPE_SOCKS4,
            "socks5": socks.PROXY_TYPE_SOCKS5,
        }
        if config.get("proxy_type") in proxy_type_to_code:
            proxy_type = proxy_type_to_code[config["proxy_type"]]
        else:
            proxy_type = socks.PROXY_TYPE_HTTP

        rdns = config.get("proxy_rdns")

        proxy_info = None
        if config.get("proxy_url") and config.get("proxy_port"):
            if config.get("proxy_username") and config.get("proxy_password"):
                proxy_info = ProxyInfo(
                    proxy_type=proxy_type,
                    proxy_host=config["proxy_url"],
                    proxy_port=int(config["proxy_port"]),
                    proxy_user=config["proxy_username"],
                    proxy_pass=config["proxy_password"],
                    proxy_rdns=rdns,
                )
            else:
                proxy_info = ProxyInfo(
                    proxy_type=proxy_type,
                    proxy_host=config["proxy_url"],
                    proxy_port=int(config["proxy_port"]),
                    proxy_rdns=rdns,
                )
        if proxy_info:
            http = Http(
                proxy_info=proxy_info,
                timeout=timeout,
                disable_ssl_certificate_validation=disable_ssl_validation,
            )
        else:
            http = Http(
                timeout=timeout,
                disable_ssl_certificate_validation=disable_ssl_validation,
            )

        if config.get("username") and config.get("password"):
            http.add_credentials(config["username"], config["password"])
        return http

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be  encoded before being returned.
        """
        
        in_string_json = json.loads(in_string)
        session_key= in_string_json["session"]["authtoken"]
        
        payload = {
        }
        
        success = True
        json_err_msg = ''
        ex = None
        
        try:
            cfm = conf_manager.ConfManager(session_key, app_name, realm = "__REST_CREDENTIAL__#TA-cyber-triage#configs/conf-ta_cyber_triage_settings")
            conf = cfm.get_conf("ta_cyber_triage_settings")
            additional_parameters = conf.get('additional_parameters')
        
            # Configuration settings
            server = additional_parameters['server']
            rest_port = additional_parameters['rest_port']
            api_key = additional_parameters['api_key']
            win_user = additional_parameters['username']
            win_pass = additional_parameters['password']
            event_index = additional_parameters['index']
            verify_server_cert = additional_parameters['verify_server_cert']
            base_url = 'https://{0}:{1}/api'.format(server, rest_port)
            api_headers = {'restApiKey': api_key}

            proxy = conf.get('proxy')
            proxy_enabled = False

            payload["base_url"] = base_url

            # Convert necessary options to bool values
            # Checkboxes/drop downs return 1/Yes if selected and 0 if unselected/No
            # helper.get_proxy() returns {} if not configured
            try:
                verify_server_cert = bool(int(verify_server_cert))
                if "proxy_enabled" in proxy:
                    proxy_enabled = bool(int(proxy["proxy_enabled"]))

            except ValueError as val_e:
                error_message = traceback.format_exc()
                logger.error(error_message)

            # If user wants to verify the server cert we expect a cybertriage.pem file to be located in
            # %SPLUNK_HOME%\etc\auth. If the file does not exist we log an error. It will be caught as an SSLError
            # when doing the http request. If SPLUNK_HOME is not found we let splunk catch the error, this should never happen.
            if verify_server_cert:
                pem_path = '{}\\etc\\auth\\cybertriage.pem'.format(os.environ['SPLUNK_HOME'])
                verify_server_cert = pem_path
                if not os.path.isfile(pem_path):
                    logger.error('Certificate not found: {}'.format(pem_path))

            http_config = None
            if proxy_enabled:
                http_config = proxy
            
            try:
                http = self.build_http_connection(http_config, disable_ssl_validation=not verify_server_cert)
                (resp, content) = http.request(base_url + '/correlation/checkcredentials', "GET", headers=api_headers)
                
                responseStatusCode = resp.status
                payload["serverStatusCode"] = responseStatusCode

            except ssl.SSLCertVerificationError as e:
                json_err_msg = 'Unable to verify the Cyber Triage server certificate'
                success = False
                ex = e
            except ConnectionRefusedError as e:
                json_err_msg = 'Error while connecting to the Cyber Triage server ({})'.format(server)
                success = False
                ex = e           
            except socks.ProxyConnectionError as e:
                json_err_msg = 'Error connecting to proxy'
                success = False
                ex = e   

        except Exception as e:
            error_message = traceback.format_exc()
            logger.error(error_message)
            success = False

        if success:
            return {'payload': payload, 'status': 200}
        else:
            return {'payload': { 'errorMsg': json_err_msg }, 'status': 200 }

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
