#!/usr/bin/env python
"""
Hunt.io Active C2 Update Custom Command
This command retrieves active C2 data from Hunt.io and stores it in the active_c2_collection KV store.
"""
import sys
import os
import json
import splunk.entity as entity

# Add the bin directory to the path to ensure imports work
bin_path = os.path.dirname(os.path.abspath(__file__))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)

# Add lib directory to path for additional dependencies
lib_path = os.path.join(bin_path, 'lib')
if os.path.exists(lib_path) and lib_path not in sys.path:
    sys.path.insert(0, lib_path)

# Import splunklib modules from the local lib directory
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
import splunklib.client as client

try:
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
    logger = logging.getLogger('huntioactvec2update')
    logger.error(f"Import error: {str(e)}")
    raise


@Configuration()
class HuntIOActiveC2UpdateCommand(GeneratingCommand):
    """
    Custom search command that retrieves active C2 data from Hunt.io and updates the KV store.
    
    This command:
    1. Calls the activec2 REST API endpoint
    2. Deletes all existing entries in the active_c2_collection KV store
    3. Adds all new entries from the API response
    
    Usage:
    | huntioactvec2update
    """
    
    def get_api_key(self, session_key):
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
    
    def get_active_c2_data(self, api_key):
        """Call the Hunt.io Active C2 API and return the results"""
        try:
            logger.info("Fetching active C2 data from Hunt.io API")
            
            # Make internal call to splunk REST endpoint
            service_args = {
                'token': self._metadata.searchinfo.session_key,
                'app': 'SA-Hunt-io',
                'owner': 'nobody'
            }
            service = client.connect(**service_args)
            
            # Call the internal REST endpoint
            response = service.get('/servicesNS/nobody/SA-Hunt-io/activec2', 
                                  output_mode='json')
            
            # Parse the response
            content = json.loads(response['body'].read())
            
            if isinstance(content, dict) and 'message' in content:
                logger.error(f"Error from Hunt.io API: {content['message']}")
                return None
            
            # Handle the expected data structure
            if isinstance(content, dict) and 'active_c2s' in content:
                active_c2s = content['active_c2s']
                count = content.get('active_c2s_count', len(active_c2s))
                logger.info(f"Successfully retrieved {count} active C2 entries")
                return active_c2s
            
            logger.warning("Unexpected response format from Hunt.io API")
            return content
        
        except Exception as e:
            err_msg = f"Error fetching active C2 data: {str(e)}"
            logger.error(err_msg)
            return None
    
    def update_kvstore(self, data):
        """Update the KV store with the new data"""
        try:
            logger.info("Updating KV store with new active C2 data")
            
            # Get KV store collection
            collection_name = "active_c2_collection"
            service_args = {
                'token': self._metadata.searchinfo.session_key,
                'app': 'SA-Hunt-io',
                'owner': 'nobody'
            }
            service = client.connect(**service_args)
            collection = service.kvstore[collection_name]
            
            # Delete all existing entries
            logger.info("Deleting existing KV store entries")
            collection.data.delete()
            
            # Add new entries
            logger.info(f"Adding {len(data)} new entries to KV store")
            batch_size = 1000  # Process in batches to avoid timeouts
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                for entry in batch:
                    collection.data.insert(json.dumps(entry))
                
                logger.info(f"Added batch {i//batch_size + 1} ({i} to {min(i+batch_size, len(data))})")
            
            logger.info("KV store update completed successfully")
            return True
        
        except Exception as e:
            err_msg = f"Error updating KV store: {str(e)}"
            logger.error(err_msg)
            return False
    
    def generate(self):
        """
        Main command execution method.
        
        Yields:
            dict: Status information about the update process
        """
        try:
            # Get API key
            session_key = self._metadata.searchinfo.session_key
            api_key = self.get_api_key(session_key)
            
            if not api_key:
                yield {'status': 'error', 'message': 'API key not found in storage'}
                return
            
            # Get active C2 data
            active_c2_data = self.get_active_c2_data(api_key)
            
            if active_c2_data is None:
                yield {'status': 'error', 'message': 'Failed to retrieve active C2 data'}
                return
                
            if not active_c2_data or not isinstance(active_c2_data, list):
                yield {'status': 'error', 
                      'message': 'Active C2 data is empty or in unexpected format'}
                return
            
            # Update KV store
            success = self.update_kvstore(active_c2_data)
            
            if success:
                yield {'status': 'success', 
                      'message': f'Updated KV store with {len(active_c2_data)} entries'}
            else:
                yield {'status': 'error', 'message': 'Failed to update KV store'}
                
        except Exception as e:
            logger.error(f"Error in command execution: {str(e)}")
            yield {'status': 'error', 'message': str(e)}


dispatch(HuntIOActiveC2UpdateCommand, sys.argv, sys.stdin, sys.stdout, __name__) 