
from splunk.persistconn.application import PersistentServerConnectionApplication
import splunk.rest as rest
import requests
import json
import os 
import configparser
import socket
import urllib.parse

log_dir = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk')
server_conf_dir = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'system', 'local')
server_conf_file = os.path.join(server_conf_dir, 'server.conf')
log_file = os.path.join(log_dir, 'apex_addon.log')
with open(log_file, "w") as f:
    pass
class EventReceiver(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    def log_debug(self, message):
        with open(log_file, "a") as f:
            f.write(message)
    
    def handle(self, args):
        try:
            if isinstance(args, bytes):
                args = json.loads(args.decode('utf-8'))
            elif isinstance(args, str):
                args = json.loads(args)
            payload = args.get('payload', {})

            if not payload:
                return {"payload": {"message": "Missing payload", "status": 400}}

            data = json.loads(payload)
            event = data.get('event')

            if 'key_fields' in event:
                for key in event['key_fields']:
                    event[key] = event['key_fields'][key]
                del event['key_fields']

            # Only process current_value if it exists in the event
            if 'current_value' in event:
                if event.get('field_name') == "Response Packets":
                    event['current_value'] = event['current_value'].replace("Pkts", "")

                # convert Apex-style number formatting to numeric values
                if 'k' in event['current_value']:
                    current_value_str = event['current_value'].replace("k", "")
                    current_value_str = current_value_str.rstrip()
                    current_value_float = float(current_value_str) * 1000
                    event['current_value'] = str(current_value_float)
                elif 'M' in event['current_value']:
                    current_value_str = event['current_value'].replace("M", "")
                    current_value_str = current_value_str.rstrip()
                    current_value_float = float(current_value_str) * 1000000
                    event['current_value'] = str(current_value_float)
                elif 'G' in event['current_value']:
                    current_value_str = event['current_value'].replace("G", "")
                    current_value_str = current_value_str.rstrip()
                    current_value_float = float(current_value_str) * 1000000000
                    event['current_value'] = str(current_value_float)
                elif 'T' in event['current_value']:
                    current_value_str = event['current_value'].replace("T", "")
                    current_value_str = current_value_str.rstrip()
                    current_value_float = float(current_value_str) * 1000000000000
                    event['current_value'] = str(current_value_float)
                else:
                    event['current_value'] = event['current_value'].rstrip()

  
            conf = self._get_config()
            if not conf:
                return {"payload": {"message": "HEC token not configured", "status": 400}}
            
            event_wrapper = {
                "event": event,
                "sourcetype": "apex",
                "source": conf.get("source"),
                "index": conf.get("index").lower()
            }
            hostname = socket.getfqdn()
            
            session_key = args.get('session', {}).get('authtoken')
            _, content = rest.simpleRequest(
                '/services/data/inputs/http/http?output_mode=json',
                sessionKey=session_key,
                method='GET'
            )
            # Store session key for secrets retrieval
            self.session_key = session_key
            response = json.loads(content)
            hec_port = response['entry'][0]['content']['port']

            hostname = conf.get('hostname')

            # if user does not configure hostname via configuration page, use servername from server.conf
            if hostname==None or hostname=='':
                hostname = self._get_server_name()
            # if servername is not configured in server.conf, try to use localhost
            if hostname==None or hostname=='': 
                hostname = 'localhost'

            hec_uri = 'https://' + hostname + ':' + hec_port + '/services/collector/event'
            ssl_path = conf.get("ssl_cert_path") or ""
            
            if ssl_path == None or ssl_path == '':
                hec_token = self._get_hec_token_from_secrets(conf.get('hec_secret_name'))
                if not hec_token:
                    return {"payload": {"message": "HEC token not found in secrets storage", "status": 400}}
                serverResponse = requests.post(hec_uri,
                          headers = {'Authorization': f'Splunk {hec_token}',
                                     'Content-Type': 'application/json'},
                          json=event_wrapper, 
                          verify=True)
            else: 
                hec_token = self._get_hec_token_from_secrets(conf.get('hec_secret_name'))
                if not hec_token:
                    return {"payload": {"message": "HEC token not found in secrets storage", "status": 400}}
                serverResponse = requests.post(hec_uri,
                          headers = {'Authorization': f'Splunk {hec_token}',
                                     'Content-Type': 'application/json'},
                          json=event_wrapper, 
                          verify=ssl_path)

            if serverResponse.status_code == 200:
                return {"payload": {"message": "Event written successfully", "status": 200}}
            else:
                self.log_debug(f'Failed to forward event to HEC. Error response: {serverResponse}')
                return {"payload": {"message": f"Failed to write event: {serverResponse.content}", "status": serverResponse.status_code}}
                
        except Exception as e:
            return {"payload": {"message": str(e), "status": 500}}
        
    def _get_hec_token_from_secrets(self, secret_name, realm="apex_hec_token"):
        """
        Retrieve HEC token from Splunk's secrets storage
        """
        try:
            if not secret_name:
                return None

            response, content = rest.simpleRequest(
                f'/services/storage/passwords/{realm}:{secret_name}',
                sessionKey=getattr(self, 'session_key', None),
                getargs={'output_mode': 'json'},
                method='GET'
            )
            
            if response.status == 200:
                secret_info = json.loads(content)
                if secret_info.get('entry') and len(secret_info['entry']) > 0:
                    return secret_info['entry'][0]['content']['clear_password']
            
            self.log_debug(f"Failed to retrieve secret {secret_name}: {response.status}")
            return None
            
        except Exception as e:
            self.log_debug(f"Error retrieving secret {secret_name}: {str(e)}")
            return None
    
    def _get_hec_token(self):
        """
        Retrieve HEC token - supports both new secrets format and legacy plain text format
        """
        try:
            conf = self._get_config()
            if not conf:
                return None
                
            # Try new secrets format first
            if 'hec_secret_name' in conf:
                token = self._get_hec_token_from_secrets(conf.get('hec_secret_name'))
                if token:
                    return token
            
            # Fallback to legacy plain text format (for backward compatibility)
            if 'hec_token' in conf:
                self.log_debug('Using legacy plain text token - consider migrating to secrets storage')
                return conf.get('hec_token')
                
            return None

        except Exception as e:
            self.log_debug(str(e))
            return None
    
    def _get_config(self):
        try:
            conf_file = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'TA-viavi-apex-addon', 'local', 'apex_settings.conf')
            if not os.path.exists(conf_file):
                return None
                
            parser = configparser.ConfigParser()
            parser.read(conf_file)
            if 'apex-settings' in parser:
                setup_str = parser['apex-settings']['setup']
                # Parse the string representation of the dictionary
                setup_dict = eval(setup_str)
                return setup_dict
            return None
        
        except Exception as e:
            self.log_debug(str(e))
            return None 
        
    def _get_server_name(self): 
        try:
            parser = configparser.ConfigParser()
            parser.read(server_conf_file)
            if 'general' in parser:
                return parser["general"]["serverName"]
            return ''
        except Exception as e:
            self.log_debug(str(e))
            return '' 
