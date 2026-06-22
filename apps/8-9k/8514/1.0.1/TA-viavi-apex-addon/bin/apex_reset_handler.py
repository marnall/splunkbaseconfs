import splunk.admin as admin
import splunk.rest as rest
import json
import os
import configparser

log_dir = os.path.join(os.environ.get('SPLUNK_HOME', ''), 'var', 'log', 'splunk')
log_file = os.path.join(log_dir, 'apex_addon.log')
conf_file = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'TA-viavi-apex-addon', 'local', 'apex_settings.conf')

class ApexResetHandler(admin.MConfigHandler):
    def log_debug(self, message):
        try:
            with open(log_file, "a") as f:
                f.write(f"{message}\n")
        except Exception:
            pass  # Fail silently for logging errors

    def setup(self):
        # Only support POST (create) action for reset
        if self.requestedAction == admin.ACTION_CREATE:
            pass  # No specific arguments needed for reset

    def handleList(self, confInfo):
        # Not supported for reset endpoint
        confInfo['error'].append('status', 'error')
        confInfo['error'].append('message', 'GET not supported on reset endpoint')

    def handleCreate(self, confInfo):
        """Handle POST /reset request"""
        try:
            self.log_debug('Reset endpoint called')
            
            # Check if configuration file exists
            if not os.path.exists(conf_file):
                confInfo['reset'].append('status', 'success')
                confInfo['reset'].append('message', 'Configuration already reset')
                self.log_debug('Configuration file does not exist, already reset')
                return
                
            # Read current configuration
            parser = configparser.ConfigParser()
            parser.read(conf_file)
            
            if 'apex-settings' in parser and 'setup' in parser['apex-settings']:
                setup_str = parser['apex-settings']['setup']
                setup_dict = json.loads(setup_str.replace("'", '"'))
                
                hec_token_name = setup_dict.get('hec_token_name')
                hec_secret_name = setup_dict.get('hec_secret_name')
                
                self.log_debug(f'Found configuration - token_name: {hec_token_name}, secret_name: {hec_secret_name}')
                
                # Delete HEC token from Splunk if it exists
                if hec_token_name and self._does_hec_token_exist(hec_token_name):
                    token_endpoint = f'/services/data/inputs/http/{hec_token_name}'
                    response, content = rest.simpleRequest(
                        token_endpoint,
                        sessionKey=self.getSessionKey(),
                        method='DELETE'
                    )
                    if response.status not in [200, 404]:  # 404 means already deleted
                        self.log_debug(f'Warning: Could not delete HEC token: {response.status} - {content}')
                    else:
                        self.log_debug(f'Successfully deleted HEC token: {hec_token_name}')
                
                # Delete secret from secrets storage if it exists
                if hec_secret_name:
                    self._delete_secret(hec_secret_name, "apex_hec_token")
            
            # Delete the configuration file
            if os.path.exists(conf_file):
                os.remove(conf_file)
                self.log_debug('Deleted apex_settings.conf')
            
            confInfo['reset'].append('status', 'success')
            confInfo['reset'].append('message', 'Configuration reset successfully')
            self.log_debug('Reset completed successfully')
            
        except Exception as e:
            error_msg = f'Failed to reset configuration: {str(e)}'
            confInfo['error'].append('status', 'error')
            confInfo['error'].append('message', error_msg)
            self.log_debug(f'Reset error: {error_msg}')

    def handleEdit(self, confInfo):
        # Not supported for reset endpoint
        confInfo['error'].append('status', 'error')
        confInfo['error'].append('message', 'PUT not supported on reset endpoint')

    def handleRemove(self, confInfo):
        # Not supported for reset endpoint
        confInfo['error'].append('status', 'error')
        confInfo['error'].append('message', 'DELETE not supported on reset endpoint')

    def _does_hec_token_exist(self, hec_token_name):
        """Check if HEC token exists"""
        try:
            token = 'http://' + hec_token_name
            response, content = rest.simpleRequest(
                '/services/data/inputs/http?output_mode=json',
                sessionKey=self.getSessionKey(),
                method='GET'
            )

            if response.status == 200:
                content_json = json.loads(content)
                tokens = [entry['name'] for entry in content_json['entry']]
                return token in tokens
            
            return False
        except Exception as e:
            self.log_debug(f'Error checking HEC token existence: {str(e)}')
            return False

    def _delete_secret(self, name, realm="apex_hec_token"):
        """Delete a secret using Splunk's storage/passwords endpoint"""
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
admin.init(ApexResetHandler, admin.CONTEXT_NONE)