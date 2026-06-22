import splunk.admin as admin
import splunk.rest as rest
import xml.etree.ElementTree as ET
import json
import uuid
import os
import configparser

log_dir = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk')
log_file = os.path.join(log_dir, 'apex_addon.log')
conf_file = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'TA-viavi-apex-addon', 'local', 'apex_settings.conf')
server_conf_dir = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'system', 'local')
server_conf_file = os.path.join(server_conf_dir, 'server.conf')
with open(log_file, "w") as f:
    pass

class ApexSetupTemplatesHandler(admin.MConfigHandler):
    def log_debug(self, message):
        with open(log_file, "a") as f:
            f.write(message)
    def setup(self):
        if self.requestedAction == admin.ACTION_CREATE:
            self.supportedArgs.addOptArg('hec_token_name')
            self.supportedArgs.addOptArg('index')
            self.supportedArgs.addOptArg('source')
            self.supportedArgs.addOptArg('ssl_cert_path')
            self.supportedArgs.addOptArg('hostname')
        elif self.requestedAction == admin.ACTION_REMOVE:
            self.log_debug('received action_remove')
            self.callerArgs.id='reset'
            self.supportedArgs.addOptArg('name')

    def handleList(self, confInfo): 
        confDict = {}

        if os.path.exists(conf_file):
            parser = configparser.ConfigParser()
            parser.read(conf_file)
            confDict = {section: dict(parser.items(section)) for section in parser.sections()}
            
        if confDict and 'apex-settings' in confDict:
            settings = confDict['apex-settings']
            for key, val in settings.items():
                if key == 'setup':
                    setup_dict = json.loads(val.replace('\'', '"'))
                    
                    # Check if this is old format with plain text hec_token, migrate to secrets
                    if 'hec_token' in setup_dict and 'hec_secret_name' not in setup_dict:
                        try:
                            # Migrate old plain text token to secrets storage
                            hec_token = setup_dict['hec_token']
                            secret_name = f"apex_hec_token_{setup_dict['hec_token_name']}"
                            self._store_secret(secret_name, hec_token, "Apex HEC Token")
                            
                            # Update config to use secrets format
                            setup_dict['hec_secret_name'] = secret_name
                            del setup_dict['hec_token']  # Remove plain text token
                            
                            # Save updated config
                            config = configparser.ConfigParser()
                            config.read(conf_file)
                            config['apex-settings']['setup'] = str(setup_dict)
                            with open(conf_file, 'w') as f:
                                config.write(f)
                            
                            self.log_debug(f'Migrated token to secrets storage: {secret_name}')
                        except Exception as e:
                            self.log_debug(f'Failed to migrate token to secrets: {str(e)}')
                    
                    # if we have a hec token in apex_settings but the token does not exist in splunk, the user may have manually deleted it 
                    # so we will delete it from apex_settings.conf 
                    if not self.does_hec_token_exist(setup_dict['hec_token_name']):
                        try:
                            self.log_debug('HEC token doesnt exist')
                            config = configparser.ConfigParser()
                            config.read(conf_file)
                            if not config.has_section('apex-settings'):
                                config.add_section('apex-settings')
                            config['apex-settings'] = {} 
                            with open(conf_file, 'w') as f:
                                config.write(f)
                            return
                        except Exception as e:
                            confInfo['error'].append('status', 'error')
                            self.log_debug(str(e))
                confInfo['apex-settings'].append(key, val)

            uri = self.get_mgmt_uri()
            if uri!=None: 
                confInfo['apex-settings'].append('mgmt_port', uri)

    def handleCreate(self, confInfo):
        try:
            # Get the parameters from the request
            hec_token_name = self.callerArgs.data.get('hec_token_name', [None])[0]
            index = self.callerArgs.data.get('index', [None])[0]
            source = self.callerArgs.data.get('source', [None])[0]
            ssl_cert_path = self.callerArgs.data.get('ssl_cert_path', [None])[0]
            hostname = self.callerArgs.data.get('hostname', [None])[0]
            
            if hostname==None or hostname=='':
                hostname=self._get_server_name()
            # Validate required parameters
            if not all([hec_token_name, index, source]):
                raise Exception("Missing required parameters: hec_token_name, index, source")

            token = str(uuid.uuid4())

            if not self.does_index_exist(index):
                raise Exception(f'Index {index} does not exist! Please create it first in the indexes page')
            
            if self.does_hec_token_exist(hec_token_name): 
                raise Exception(f'Token \'{hec_token_name}\' already exists! Delete it from Data Inputs before proceeding')

            postargs = {
                'name': hec_token_name,
                'index': index,
                'token': token,
                'useACK': '0',
                'disabled': '0',
                'output_mode': 'json'
            }
            
            # Create HEC token
            response, content = rest.simpleRequest(
                '/services/data/inputs/http',
                sessionKey=self.getSessionKey(),
                postargs=postargs,
                method='POST'
            )
            if response.status != 201:
                raise Exception(f"Failed to create HEC token: {content}")
            
            # Parse the response to get the token
            token_info = json.loads(content)
            hec_token = token_info['entry'][0]['content']['token']
            
            # Store HEC token securely using Splunk secrets storage
            secret_name = f"apex_hec_token_{hec_token_name}"
            self._store_secret(secret_name, hec_token, "apex_hec_token")
            
            # Save configuration to conf file (without the token)
            apex_config = {
                'hec_token_name': hec_token_name,
                'hec_secret_name': secret_name,
                'index': index,
                'source': source, 
                'ssl_cert_path': '' if ssl_cert_path==None else ssl_cert_path,
                'hostname': '' if hostname==None else hostname
            }

            config = configparser.ConfigParser()
            config['apex-settings'] = {}
            config['apex-settings']['setup'] = str(apex_config)

            os.makedirs(os.path.dirname(conf_file), exist_ok=True)
            with open(conf_file, 'w+') as f: 
                config.write(f)

            # Return the token in the response
            confInfo['setup'].append('hec_token', token)
            confInfo['setup'].append('status', 'success')
            confInfo['setup'].append('hostname', hostname)
            uriPort = self.get_mgmt_uri()
            if uriPort != None:
                confInfo['setup'].append('mgmt_port', uriPort)

        except Exception as e:
            confInfo['error'].append('status', 'error')
            confInfo['error'].append('message', str(e))

    def handleDelete(self, confInfo):
        self.log_debug('delete function')
        stanza_name = self.callerArgs.id  # Normally set by REST path

        if stanza_name is None:
            try:
                # The target name should be available in the request data
                # target_name = self.callerArgs.data.get('name', [None])[0]
                # if not target_name:
                #     target_name = 'reset'
                
                # Get current configuration to find the HEC token info
                if not os.path.exists(conf_file):
                    confInfo['reset'].append('status', 'success')
                    confInfo['reset'].append('message', 'Configuration already reset')
                    return
                    
                parser = configparser.ConfigParser()
                parser.read(conf_file)
                
                if 'apex-settings' in parser and 'setup' in parser['apex-settings']:
                    setup_str = parser['apex-settings']['setup']
                    setup_dict = json.loads(setup_str.replace("'", '"'))
                    
                    hec_token_name = setup_dict.get('hec_token_name')
                    hec_secret_name = setup_dict.get('hec_secret_name')
                    
                    # Delete HEC token from Splunk if it exists
                    if hec_token_name and self.does_hec_token_exist(hec_token_name):
                        token_endpoint = f'/services/data/inputs/http/http://{hec_token_name}'
                        response, content = rest.simpleRequest(
                            token_endpoint,
                            sessionKey=self.getSessionKey(),
                            method='DELETE'
                        )
                        if response.status not in [200, 404]:  # 404 means already deleted
                            self.log_debug(f'Warning: Could not delete HEC token: {response.status} - {content}')
                    
                    # Delete secret from secrets storage if it exists
                    if hec_secret_name:
                        self._delete_secret(hec_secret_name, "apex_hec_token")
                
                # Delete the configuration file
                if os.path.exists(conf_file):
                    os.remove(conf_file)
                    self.log_debug('Deleted apex_settings.conf')
                
                confInfo['reset'].append('status', 'success')
                confInfo['reset'].append('message', 'Configuration reset successfully')
                
            except Exception as e:
                confInfo['error'].append('status', 'error')
                confInfo['error'].append('message', f'Failed to reset configuration: {str(e)}')
                self.log_debug(f'Reset error: {str(e)}')

    def does_index_exist(self, index):
        try:
            response, content = rest.simpleRequest(
                '/services/data/indexes',
                sessionKey=self.getSessionKey(),
                getargs={'output_mode': 'xml'},
                method='GET'
            )

            if response.status == 200:
                root = ET.fromstring(content) 
                if root:
                    ns = {'atom': root.tag.split('}')[0].strip('{')}
                    entries = root.findall(".//atom:entry", ns)
                    indexes = [entry.find("atom:title", ns).text for entry in entries] # get list of all indexes 
                return (index.lower() in indexes)
            
            return False
        except Exception as e:
            self.log_debug(str(e))
            return False  
        
    def get_existing_hec_tokens(self):
        response, content = rest.simpleRequest(
            '/services/data/inputs/http?output_mode=json',
            sessionKey=self.getSessionKey(),
            method='GET'
        )

        if response.status == 200:
            content_json = json.loads(content)
            tokens = [entry['name'] for entry in content_json['entry']]
            return tokens 
        
        return []
    
    def does_hec_token_exist(self, hec_token_name):
        token = 'http://' + hec_token_name # append http:// to the token name because this is how it is returned by splunk API 
        tokens = self.get_existing_hec_tokens()

        if token in tokens:
            return True 
        
        return False
    
    def get_mgmt_uri(self):
        try:
            response, content = rest.simpleRequest(
                '/services/server/settings?output_mode=json',
                sessionKey=self.getSessionKey()
            )
            if response.status == 200:
                server_info = json.loads(content)
                return server_info['entry'][0]['content']['mgmtHostPort']
        except Exception:
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
    
    def _store_secret(self, name, password, realm):
        """
        Store a secret using Splunk's storage/passwords endpoint
        """
        postargs = {
            'name': name,
            'password': password,
            'realm': realm,
            'output_mode': 'json'
        }
        
        response, content = rest.simpleRequest(
            '/services/storage/passwords',
            sessionKey=self.getSessionKey(),
            postargs=postargs,
            method='POST'
        )
        
        if response.status not in [200, 201, 409]:  # 409 = already exists
            raise Exception(f"Failed to store secret: {response.status} - {content}")
        
        return True
    
    def _get_secret(self, name, realm="Apex Add-on"):
        """
        Retrieve a secret using Splunk's storage/passwords endpoint
        """
        try:
            response, content = rest.simpleRequest(
                f'/services/storage/passwords/{realm}:{name}:',
                sessionKey=self.getSessionKey(),
                getargs={'output_mode': 'json'},
                method='GET'
            )
            
            if response.status == 200:
                secret_info = json.loads(content)
                if secret_info.get('entry') and len(secret_info['entry']) > 0:
                    return secret_info['entry'][0]['content']['clear_password']
            
            return None
        except Exception as e:
            self.log_debug(f"Error retrieving secret: {str(e)}")
            return None
    
    def _delete_secret(self, name, realm="apex_hec_token"):
        """
        Delete a secret using Splunk's storage/passwords endpoint
        """
        try:
            response, content = rest.simpleRequest(
                f'/services/storage/passwords/{realm}:{name}:',
                sessionKey=self.getSessionKey(),
                method='DELETE'
            )
            
            if response.status not in [200, 404]:  # 404 means already deleted
                self.log_debug(f"Warning: Could not delete secret {name}: {response.status} - {content}")
                return False
            
            self.log_debug(f"Successfully deleted secret: {name}")
            return True
        except Exception as e:
            self.log_debug(f"Error deleting secret {name}: {str(e)}")
            return False 


# Initialize the handler
admin.init(ApexSetupTemplatesHandler, admin.CONTEXT_NONE)
