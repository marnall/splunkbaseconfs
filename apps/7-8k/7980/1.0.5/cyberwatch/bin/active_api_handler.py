"""
REST Handler for managing active AI API configuration in CyberWatch app
"""

import sys
import splunk
import splunk.admin as admin
import splunk.entity as entity

class ActiveAPIHandler(admin.ConfigHandler):
    """
    REST Handler for managing the active API configuration
    """
    
    def setup(self):
        """
        Set up supported arguments for the handler
        """
        if self.requestedAction == admin.ACTION_CREATE or self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addReqArg('provider')
    
    def handleList(self, confInfo):
        """
        Handle GET requests - Get the active API configuration
        """
        try:
            # Read from a custom conf file
            active_api = self._get_active_api_config()
            
            confInfo['active_api'].append('provider', active_api.get('provider', ''))
            confInfo['active_api'].append('key_name', active_api.get('key_name', ''))
            
        except Exception as e:
            raise
    
    def handleCreate(self, confInfo):
        """
        Handle POST requests - Set the active API configuration
        """
        try:
            provider = self.callerArgs.data['provider'][0]
            
            # Validate provider
            if provider not in ['gemini', 'openai']:
                raise admin.ArgValidationException("Provider must be 'gemini' or 'openai'")
            
            # Save to conf file
            self._set_active_api_config(provider)
            
            confInfo['result'].append('status', 'success')
            confInfo['result'].append('message', 'Active API configuration saved')
            
        except Exception as e:
            raise
    
    def _get_active_api_config(self):
        """
        Get the active API configuration from conf file
        """
        try:
            config = entity.getEntity(
                ['configs', 'conf-cyberwatch'],
                'ai_settings',
                namespace='cyberwatch',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )
            return {
                'provider': config.get('active_provider', ''),
                'key_name': config.get('active_key_name', '')
            }
        except:
            return {'provider': '', 'key_name': ''}
    
    def _set_active_api_config(self, provider):
        """
        Set the active API configuration in conf file
        """
        try:
            # Try to update existing entry
            entity.updateEntity(
                ['configs', 'conf-cyberwatch'],
                'ai_settings',
                {'active_provider': provider},
                namespace='cyberwatch',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )
        except splunk.ResourceNotFound:
            # Create new entry if it doesn't exist
            entity.createEntity(
                ['configs', 'conf-cyberwatch'],
                'ai_settings',
                {'active_provider': provider},
                namespace='cyberwatch',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )


# Initialize the handler
admin.init(ActiveAPIHandler, admin.CONTEXT_APP_AND_USER)
