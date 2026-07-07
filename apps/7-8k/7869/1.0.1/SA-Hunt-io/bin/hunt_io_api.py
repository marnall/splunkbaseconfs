#!/usr/bin/env python
import json
import requests
import gzip
import sys
import os

# Add the bin directory to the path to ensure imports work
bin_path = os.path.dirname(os.path.abspath(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)

try:
    import splunk.entity as entity
    from splunk.persistconn.application import PersistentServerConnectionApplication
    from core.log import get_logger
    # Initialize logger
    logger = get_logger(__file__)
    logger.info("Successfully imported required modules")
except ImportError as e:
    # If we can't import the logger yet, use basic logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s pid=%(process)d | %(message)s'
    )
    logger = logging.getLogger('hunt_io_api')
    logger.error(f"Import error: {str(e)}")
    raise


class HuntIOApi(PersistentServerConnectionApplication):
    """
    REST handler class for Hunt.io API integration
    """
    
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        logger.info("HuntIOApi initialized")

    def handle(self, in_string):
        """
        Main handler method for REST endpoints
        """
        try:
            # Parse the request
            request = json.loads(in_string)
            
            # Log the raw request for debugging
            logger.debug(f"Raw request: {request}")
            
            # Define available endpoints and their handlers
            endpoint_handlers = {
                'c2feed': self._get_c2_feed,
                'iochunter': self._get_ioc_hunter_feed,
                'activec2': self._get_active_c2
            }
            
            # Extract and normalize endpoint from various possible sources
            endpoint = self._extract_endpoint(request)
            logger.info(f"Processing request for normalized endpoint: {endpoint}")
            
            # Get session key for API key retrieval
            session_key = request.get('session', {}).get('authtoken')
            if not session_key:
                logger.error("No session key found in request")
                return {
                    'payload': {'message': 'Authentication required'}, 
                    'status': 401
                }
            
            # Get API key from secure storage
            api_key = self._get_api_key(session_key)
            if not api_key:
                logger.error("API key not found in storage")
                return {
                    'payload': {'message': 'API key not found in storage'}, 
                    'status': 500
                }
            
            # Handle the request based on the endpoint
            handler = endpoint_handlers.get(endpoint)
            if handler:
                logger.info(f"Calling handler for endpoint: {endpoint}")
                return handler(api_key)
            else:
                logger.warning(f"Endpoint not found: {endpoint}")
                return {'payload': {'message': 'Endpoint not found'}, 'status': 404}
                
        except Exception as e:
            logger.error(f"Error in handle method: {str(e)}")
            return {'payload': {'message': str(e)}, 'status': 500}
    
    def _extract_endpoint(self, request):
        """
        Extract and normalize the endpoint from the request
        Handles various ways Splunk might send the endpoint info
        """
        # Try different possible locations for the endpoint info
        rest_path = request.get('rest_path', '')
        
        logger.debug(f"Rest path: {rest_path}")
        # Lastly check rest_path
        if rest_path:
            endpoint = rest_path.strip('/').split('/')[-1]
            if endpoint in ['c2feed', 'iochunter', 'activec2']:
                return endpoint
        
        # Return empty string if no endpoint found
        return ''
    
    def _get_api_key(self, session_key):
        """Retrieve the Hunt.io API key from Splunk's secure storage"""
        try:
            logger.debug("Retrieving API key from secure storage")
            entities = entity.getEntities(
                ['admin', 'passwords'], 
                namespace='SA-Hunt-io', 
                owner='nobody', 
                sessionKey=session_key
            )
            
            for i, c in entities.items():
                if c['realm'] == 'hunt_io_api_key':
                    logger.debug("API key found in secure storage")
                    return c['clear_password']
            
            logger.warning("API key not found in secure storage")
            return None
        except Exception as e:
            err_msg = f"Error retrieving API key: {str(e)}"
            logger.error(err_msg)
            raise Exception(err_msg)
    
    def _get_c2_feed(self, api_key):
        """Call the Hunt.io C2 Feed API and return the results"""
        try:
            logger.info("Fetching C2 feed from Hunt.io API")
            headers = {'token': api_key}
            response = requests.get(
                'https://api.hunt.io/v1/feeds/c2', 
                headers=headers, 
                stream=True
            )
            
            if response.status_code != 200:
                err_msg = f'Error from Hunt.io API: {response.text}'
                logger.error(f"C2 feed API returned status code {response.status_code}")
                return {
                    'payload': {'message': err_msg}, 
                    'status': response.status_code
                }
            
            # Decompress gzip response
            logger.info("Processing C2 feed data")
            decompressed_data = []
            with gzip.GzipFile(fileobj=response.raw) as f:
                for line in f:
                    if line.strip():
                        try:
                            json_line = json.loads(line)
                            decompressed_data.append(json_line)
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON line found in C2 feed")
                            pass
            
            count = len(decompressed_data)
            logger.info(f"Successfully processed C2 feed with {count} entries")
            return {'payload': decompressed_data, 'status': 200}
        
        except Exception as e:
            err_msg = f"Error fetching C2 feed: {str(e)}"
            logger.error(err_msg)
            return {'payload': {'message': err_msg}, 'status': 500}
    
    def _get_ioc_hunter_feed(self, api_key):
        """Call the Hunt.io IOC Hunter Feed API and return the results"""
        try:
            logger.info("Fetching IOC Hunter feed from Hunt.io API")
            headers = {'token': api_key}
            response = requests.get(
                'https://api.hunt.io/v1/feeds/ioc-hunter', 
                headers=headers, 
                params={'days': 720},
                stream=True
            )
            
            if response.status_code != 200:
                err_msg = f'Error from Hunt.io API: {response.text}'
                status_code = response.status_code
                logger.error(f"IOC Hunter feed API returned status code {status_code}")
                return {
                    'payload': {'message': err_msg}, 
                    'status': response.status_code
                }
            
            # Decompress gzip response
            logger.info("Processing IOC Hunter feed data")
            decompressed_data = []
            with gzip.GzipFile(fileobj=response.raw) as f:
                for line in f:
                    if line.strip():
                        try:
                            json_line = json.loads(line)
                            decompressed_data.append(json_line)
                        except json.JSONDecodeError:
                            logger.warning("Invalid JSON line in IOC Hunter feed")
                            pass
            
            count = len(decompressed_data)
            logger.info(f"Successfully processed IOC Hunter feed with {count} entries")
            return {'payload': decompressed_data, 'status': 200}
        
        except Exception as e:
            err_msg = f"Error fetching IOC Hunter feed: {str(e)}"
            logger.error(err_msg)
            return {
                'payload': {'message': err_msg}, 
                'status': 500
            }

    def _get_active_c2(self, api_key):
        """Call the Hunt.io Active C2 API and return the results"""
        try:
            logger.info("Fetching active C2 servers from Hunt.io API")
            headers = {'token': api_key, 'accept': 'application/json'}
            response = requests.get(
                'https://api.hunt.io/v1/c2s', 
                headers=headers
            )
            
            if response.status_code != 200:
                err_msg = f'Error from Hunt.io API: {response.text}'
                logger.error(f"Active C2 API returned status code {response.status_code}")
                return {
                    'payload': {'message': err_msg}, 
                    'status': response.status_code
                }
            
            # Process JSON response
            logger.info("Processing active C2 data")
            try:
                data = response.json()
                logger.info(f"Successfully processed active C2 data")
                return {'payload': data, 'status': 200}
            except json.JSONDecodeError as e:
                err_msg = f"Error decoding JSON response: {str(e)}"
                logger.error(err_msg)
                return {'payload': {'message': err_msg}, 'status': 500}
        
        except Exception as e:
            err_msg = f"Error fetching active C2 data: {str(e)}"
            logger.error(err_msg)
            return {'payload': {'message': err_msg}, 'status': 500}

# Define the entry point for the Persistent Server Connection
# Using a direct instance rather than a class reference


hunt_io_api = HuntIOApi(None, None) 