"""
REST Handler for managing AI API keys in CyberWatch app
This handler provides secure storage of API keys using Splunk's credential storage
"""

import sys
import os
import json
import splunk
import splunk.admin as admin
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

class APIKeyHandler(admin.ConfigHandler):
    """
    REST Handler for AI API Key management
    Handles GET, POST, and DELETE operations for API keys
    """
    
    def setup(self):
        """
        Set up supported arguments for the handler
        """
        if self.requestedAction == admin.ACTION_CREATE or self.requestedAction == admin.ACTION_EDIT:
            self.supportedArgs.addReqArg('provider')
            self.supportedArgs.addReqArg('name')
            self.supportedArgs.addReqArg('api_key')
        
        if self.requestedAction == admin.ACTION_LIST:
            self.supportedArgs.addOptArg('provider')
    
    def handleList(self, confInfo):
        """
        Handle GET requests - List all API keys (without revealing the actual keys)
        """
        try:
            provider = self.callerArgs.data.get('provider', [None])[0]
            
            # Get all passwords from Splunk's credential storage
            try:
                passwords = entity.getEntities(
                    ['admin', 'passwords'],
                    namespace='cyberwatch',
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )
            except Exception as e:
                passwords = {}
            
            # Filter and format API keys
            for name, password_entity in passwords.items():
                # Check if this is an AI API key (they have a specific naming pattern)
                realm = password_entity.get('realm', '')
                if realm.startswith('cyberwatch_ai_'):
                    key_provider = realm.replace('cyberwatch_ai_', '')
                    
                    # Filter by provider if specified
                    if provider and key_provider != provider:
                        continue
                    
                    # Add to confInfo - each key is a separate entry
                    confInfo[name].append('provider', key_provider)
                    confInfo[name].append('name', name)
                    confInfo[name].append('created', password_entity.get('eai:acl', {}).get('modifiedTime', 'Unknown'))
            
        except Exception as e:
            raise

    
    def handleCreate(self, confInfo):
        """
        Handle POST requests - Save a new API key
        """
        try:
            provider = self.callerArgs.data['provider'][0]
            key_name = self.callerArgs.data['name'][0]
            api_key = self.callerArgs.data['api_key'][0]
            
            # Validate inputs
            if not provider or not key_name or not api_key:
                raise admin.ArgValidationException("Provider, name, and api_key are required")
            
            if provider not in ['gemini', 'openai']:
                raise admin.ArgValidationException("Provider must be 'gemini' or 'openai'")
            
            # Create a unique realm for this provider
            realm = 'cyberwatch_ai_%s' % provider
            
            # Store password using Splunk's credential storage
            try:
                entity.getEntity(
                    ['admin', 'passwords'],
                    key_name,
                    namespace='cyberwatch',
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )
                # If we get here, credential exists - update it
                entity.updateEntity(
                    ['admin', 'passwords'],
                    key_name,
                    {'password': api_key, 'realm': realm},
                    namespace='cyberwatch',
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )
            except splunk.ResourceNotFound:
                # Credential doesn't exist - create it
                entity.createEntity(
                    ['admin', 'passwords'],
                    key_name,
                    {'password': api_key, 'realm': realm},
                    namespace='cyberwatch',
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )
            
            confInfo['result'].append('status', 'success')
            confInfo['result'].append('message', 'API key saved successfully')
            
        except Exception as e:
            self.logger.error("Error in handleCreate: %s" % str(e))
            raise
    
    def handleRemove(self, confInfo):
        """
        Handle DELETE requests - Remove an API key
        """
        try:
            # The key name is passed in the URL path
            key_name = self.callerArgs.id
            
            # Delete the credential
            entity.deleteEntity(
                ['admin', 'passwords'],
                key_name,
                namespace='cyberwatch',
                owner='nobody',
                sessionKey=self.getSessionKey()
            )
            
            confInfo['result'].append('status', 'success')
            confInfo['result'].append('message', 'API key deleted successfully')
            
        except Exception as e:
            self.logger.error("Error in handleRemove: %s" % str(e))
            raise


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
            self.logger.error("Error in handleList: %s" % str(e))
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
            self.logger.error("Error in handleCreate: %s" % str(e))
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


# Initialize the handlers
admin.init(APIKeyHandler, admin.CONTEXT_APP_AND_USER)
