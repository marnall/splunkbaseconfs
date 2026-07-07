"""
Helper module for retrieving AI API keys from Splunk's credential storage
This module can be imported by other scripts in the CyberWatch app
"""

import splunk.entity as entity

def get_api_key(session_key, provider=None):
    """
    Retrieve the active API key for AI operations
    
    Args:
        session_key: Splunk session key for authentication
        provider: Optional. Specific provider ('gemini' or 'openai'). 
                 If None, uses the active provider from config
    
    Returns:
        dict: {'provider': str, 'api_key': str} or None if not found
    """
    try:
        # If no provider specified, get the active one
        if not provider:
            provider = get_active_provider(session_key)
            if not provider:
                return None
        
        # Get the realm for this provider
        realm = 'cyberwatch_ai_%s' % provider
        
        # Get all passwords
        passwords = entity.getEntities(
            ['admin', 'passwords'],
            namespace='cyberwatch',
            owner='nobody',
            sessionKey=session_key
        )
        
        # Find the first key for this provider
        for name, password_entity in passwords.items():
            if password_entity.get('realm', '') == realm:
                # Note: The actual password is in clear_password field
                return {
                    'provider': provider,
                    'api_key': password_entity.get('clear_password', ''),
                    'key_name': name
                }
        
        return None
        
    except Exception as e:
        import sys
        import traceback
        print("Error getting API key: %s" % str(e), file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None


def get_active_provider(session_key):
    """
    Get the currently active AI provider
    
    Args:
        session_key: Splunk session key for authentication
    
    Returns:
        str: Provider name ('gemini' or 'openai') or None if not set
    """
    try:
        config = entity.getEntity(
            ['configs', 'conf-cyberwatch'],
            'ai_settings',
            namespace='cyberwatch',
            owner='nobody',
            sessionKey=session_key
        )
        return config.get('active_provider', '') or None
    except:
        return None


def get_all_api_keys(session_key, provider):
    """
    Get all API keys for a specific provider
    
    Args:
        session_key: Splunk session key for authentication
        provider: Provider name ('gemini' or 'openai')
    
    Returns:
        list: List of dicts with key information (without the actual API keys)
    """
    try:
        realm = 'cyberwatch_ai_%s' % provider
        
        passwords = entity.getEntities(
            ['admin', 'passwords'],
            namespace='cyberwatch',
            owner='nobody',
            sessionKey=session_key
        )
        
        keys = []
        for name, password_entity in passwords.items():
            if password_entity.get('realm', '') == realm:
                keys.append({
                    'name': name,
                    'provider': provider,
                    'created': password_entity.get('eai:acl', {}).get('modifiedTime', 'Unknown')
                })
        
        return keys
        
    except Exception as e:
        import sys
        print("Error getting API keys: %s" % str(e), file=sys.stderr)
        return []


# Example usage:
if __name__ == '__main__':
    """
    This is an example of how to use this module in other scripts
    """
    import splunk.auth as auth
    
    # Get session key (in a real script, you'd get this from the execution context)
    # session_key = auth.getSessionKey('admin', 'password')
    
    # Example 1: Get the active API key
    # api_config = get_api_key(session_key)
    # if api_config:
    #     print("Provider:", api_config['provider'])
    #     print("Key Name:", api_config['key_name'])
    #     # Use api_config['api_key'] to make API calls
    
    # Example 2: Get a specific provider's key
    # gemini_config = get_api_key(session_key, provider='gemini')
    
    # Example 3: Get active provider
    # active = get_active_provider(session_key)
    # print("Active provider:", active)
    
    pass
