#!/usr/bin/env python3

"""
ThreatMon IOC Feed Modular Input
Copyright 2023 ThreatMon
"""

import sys
import os
import json
import time
import logging
import requests
import csv
import datetime
import hashlib

# Add the splunklib to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import splunklib.modularinput as mi
import splunklib.client as client
from splunklib.modularinput import *


class ThreatMonModinput(mi.Script):
    """ThreatMon IOC Feed Modular Input"""
    
    APP_NAME = "TA-ThreatMon"
    
    def get_scheme(self):
        """Return scheme for introspection"""
        scheme = Scheme("ThreatMon IOC Feed")
        scheme.description = "Collect IOCs from ThreatMon API"
        scheme.use_external_validation = False
        scheme.streaming_mode = Scheme.streaming_mode_xml
        scheme.use_single_instance = False  # Allow multiple instances
        
        # CRITICAL: Don't define 'interval' or 'polling_interval' here
        # Splunk automatically handles 'interval' parameter from inputs.conf
        
        # Define custom arguments (optional parameters)
        verify_ssl_arg = Argument("verify_ssl")
        verify_ssl_arg.data_type = Argument.data_type_boolean
        verify_ssl_arg.description = "Verify SSL certificates"
        verify_ssl_arg.required_on_create = False
        scheme.add_argument(verify_ssl_arg)
        
        log_level_arg = Argument("log_level")
        log_level_arg.data_type = Argument.data_type_number
        log_level_arg.description = "Log level (DEBUG=10, INFO=20, WARNING=30, ERROR=40)"
        log_level_arg.required_on_create = False
        scheme.add_argument(log_level_arg)
        
        return scheme
    
    def validate_input(self, validation_definition):
        """Validate input configuration"""
        pass
    
    def stream_events(self, inputs, ew):
        """Main execution method"""
        for input_name, input_item in inputs.inputs.items():
            try:
                # Get session key
                session_key = self._input_definition.metadata["session_key"]
                
                # Setup logging
                self.setup_logging(input_item.get("log_level", "30"))
                
                # Get configuration from Splunk setup
                config = self.get_config_from_splunk(session_key)
                
                if not config.get('username') or not config.get('password'):
                    ew.log(EventWriter.ERROR, "Missing username or password in configuration")
                    continue
                
                # Fetch IOCs
                iocs = self.fetch_iocs(config, ew)
                
                if iocs:
                    # CRITICAL: Store to KV store FIRST to get existing IOC list
                    # This returns the list of NEW IOCs that were just added
                    new_iocs = self.store_to_kv(iocs, session_key, ew)
                    
                    # Write ONLY new events to Splunk index
                    if new_iocs:
                        self.write_events(new_iocs, ew, input_item)
                        ew.log(EventWriter.INFO, f"Processed {len(new_iocs)} new IOCs (skipped {len(iocs) - len(new_iocs)} duplicates)")
                    else:
                        ew.log(EventWriter.INFO, f"No new IOCs (all {len(iocs)} already exist)")
                    
            except Exception as e:
                ew.log(EventWriter.ERROR, f"Error: {str(e)}")
                if hasattr(self, 'logger'):
                    self.logger.error(f"Error: {str(e)}", exc_info=True)
    
    def setup_logging(self, log_level="30"):
        """Setup logging"""
        splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
        log_dir = os.path.join(splunk_home, 'etc', 'apps', self.APP_NAME, 'logs')
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        self.logger = logging.getLogger("threatmon_ioc_feed")
        self.logger.setLevel(int(log_level))
        
        handler = logging.FileHandler(os.path.join(log_dir, "threatmon_ioc_feed.log"))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def get_config_from_splunk(self, session_key):
        """Get configuration from Splunk setup"""
        # CRITICAL: Default config - must be configured via setup page
        config = {
            "username": "",
            "password": "",
            "collection_id": "91a7b528-80eb-42ed-a74d-c6fbd5a26116",  # Default collection
            "verify_ssl": True,
            "log_level": 20,
            "interval": 3600,
            "index": "threat_intel"
        }
        
        try:
            service = client.connect(token=session_key, app=self.APP_NAME)
            
            if 'ta-threatmon' in service.confs:
                threatmon_conf = service.confs['ta-threatmon']
                if 'main' in threatmon_conf:
                    main_stanza = threatmon_conf['main']
                    
                    # Read all config values from ta-threatmon.conf
                    for key in ['username', 'password', 'collection_id', 'index', 'log_level']:
                        if key in main_stanza and main_stanza[key]:
                            if key in ['log_level']:
                                try:
                                    config[key] = int(main_stanza[key])
                                except (ValueError, TypeError):
                                    pass
                            else:
                                config[key] = str(main_stanza[key]).strip()
                    
                    # Support both 'interval' and 'update_interval' for backwards compatibility
                    if 'interval' in main_stanza and main_stanza['interval']:
                        try:
                            config['interval'] = int(main_stanza['interval'])
                        except (ValueError, TypeError):
                            pass
                    elif 'update_interval' in main_stanza and main_stanza['update_interval']:
                        try:
                            config['interval'] = int(main_stanza['update_interval'])
                        except (ValueError, TypeError):
                            pass
                    
                    if 'verify_ssl' in main_stanza:
                        ssl_value = main_stanza['verify_ssl']
                        config['verify_ssl'] = ssl_value in ['1', 'true', 'True', True]
                        
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Error loading config: {str(e)}")
            
        return config
    
    def fetch_iocs(self, config, ew):
        """Fetch IOCs from ThreatMon API"""
        if not all([config['username'], config['password']]):
            ew.log(EventWriter.ERROR, "Missing username or password")
            return []
        
        # Build URL
        if config.get('collection_id') and config['collection_id'].strip():
            url = f"https://ioc.threatmonit.io/taxii/collections/{config['collection_id']}/objects/?limit=250&more=true"
        else:
            url = "https://ioc.threatmonit.io/taxii/collections/"
        
        headers = {"Accept": "application/taxii+json;version=2.1"}
        iocs = []
        
        try:
            session = requests.Session()
            response = session.get(
                url,
                headers=headers,
                auth=(config['username'], config['password']),
                timeout=30,
                verify=config.get('verify_ssl', True)
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if config.get('collection_id'):
                    # Single collection response
                    if 'objects' in data:
                        iocs.extend(self.process_objects(data['objects']))
                else:
                    # Multiple collections - get all
                    if 'collections' in data:
                        for collection in data['collections']:
                            collection_id = collection.get('id')
                            if collection_id:
                                collection_url = f"https://ioc.threatmonit.io/taxii/collections/{collection_id}/objects/?limit=250"
                                collection_response = session.get(
                                    collection_url,
                                    headers=headers,
                                    auth=(config['username'], config['password']),
                                    timeout=30,
                                    verify=config.get('verify_ssl', True)
                                )
                                if collection_response.status_code == 200:
                                    collection_data = collection_response.json()
                                    if 'objects' in collection_data:
                                        iocs.extend(self.process_objects(collection_data['objects']))
                
                ew.log(EventWriter.INFO, f"Fetched {len(iocs)} IOCs from ThreatMon API")
                
            else:
                ew.log(EventWriter.ERROR, f"API request failed with status {response.status_code}")
                
        except Exception as e:
            ew.log(EventWriter.ERROR, f"Error fetching IOCs: {str(e)}")
            
        return iocs
    
    def process_objects(self, objects):
        """Process STIX objects into IOC format"""
        iocs = []
        
        for obj in objects:
            if obj.get('type') == 'indicator':
                try:
                    ioc_data = {
                        'id': obj.get('id', ''),
                        'type': 'indicator',
                        'pattern': obj.get('pattern', ''),
                        'value': self.extract_ioc_value_from_pattern(obj.get('pattern', '')),
                        'labels': ','.join(obj.get('labels', [])),
                        'created': obj.get('created', ''),
                        'modified': obj.get('modified', ''),
                        'valid_from': obj.get('valid_from', ''),
                        'valid_until': obj.get('valid_until', ''),
                        'confidence': obj.get('confidence', ''),
                        'lang': obj.get('lang', ''),
                        'spec_version': obj.get('spec_version', ''),
                        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z'
                    }
                    
                    # Add external references if available
                    if 'external_references' in obj:
                        refs = []
                        for ref in obj['external_references']:
                            refs.append(f"{ref.get('source_name', '')}: {ref.get('url', '')}")
                        ioc_data['external_references'] = '; '.join(refs)
                    
                    iocs.append(ioc_data)
                    
                except Exception as e:
                    continue
                    
        return iocs
    
    def extract_ioc_value_from_pattern(self, pattern):
        """Extract IOC value from STIX pattern"""
        import re
        
        if not pattern:
            return ""
        
        # Extract value between quotes
        match = re.search(r"= '([^']+)'", pattern)
        if match:
            return match.group(1)
        
        match = re.search(r'= "([^"]+)"', pattern)
        if match:
            return match.group(1)
        
        return pattern
    
    # Checkpoint functions removed - using real-time index search instead
    
    def write_events(self, iocs, ew, input_item):
        """Write IOC events to Splunk (only NEW IOCs, duplicates already filtered by KV Store)"""
        written_count = 0
        index_name = input_item.get('index', 'threat_intel')
        
        for ioc in iocs:
            try:
                ioc_id = ioc.get('id', '').strip()
                if not ioc_id:
                    continue
                
                # Create event for new IOC
                event = Event()
                event.stanza = getattr(input_item, 'name', 'threatmon_ioc_feed')
                
                # Add metadata
                ioc['event_id'] = ioc_id
                ioc['ingestion_time'] = datetime.datetime.utcnow().isoformat() + 'Z'
                
                event.data = json.dumps(ioc)
                event.sourcetype = input_item.get('sourcetype', 'threatmon:ioc')
                event.index = index_name
                
                ew.write_event(event)
                written_count += 1
                     
            except Exception as e:
                ew.log(EventWriter.ERROR, f"Error writing event: {str(e)}")
        
        if written_count > 0:
            ew.log(EventWriter.INFO, f"Written {written_count} events to index '{index_name}'")
    
    def store_to_kv(self, iocs, session_key, ew):
        """Store IOCs to KV store with upsert logic and return list of NEW IOCs only"""
        new_iocs = []
        
        try:
            service = client.connect(token=session_key, app=self.APP_NAME)
            collection = service.kvstore['threatmon_ioc_collection']
            
            new_count = 0
            updated_count = 0
            
            # Get existing _key values to track new vs updated IOCs
            existing_keys = set()
            try:
                for existing_ioc in collection.data.query():
                    if '_key' in existing_ioc:
                        existing_keys.add(existing_ioc['_key'])
            except Exception as e:
                ew.log(EventWriter.WARNING, f"Could not read existing KV keys: {str(e)}")
            
            # Process IOCs with batch_save (upsert based on _key)
            for ioc in iocs:
                try:
                    ioc_id = ioc.get('id', '').strip()
                    if not ioc_id:
                        continue
                    
                    # CRITICAL: Create deterministic _key from IOC ID hash
                    kv_key = hashlib.sha224(ioc_id.encode('utf-8')).hexdigest()
                    
                    current_time = datetime.datetime.utcnow().isoformat() + 'Z'
                    ioc_data = ioc.copy()
                    ioc_data['_key'] = kv_key
                    
                    if kv_key in existing_keys:
                        # Update existing IOC
                        ioc_data['last_updated'] = current_time
                        ioc_data.pop('first_seen', None)
                        updated_count += 1
                    else:
                        # Insert new IOC
                        ioc_data['first_seen'] = current_time
                        ioc_data['last_updated'] = current_time
                        new_count += 1
                        new_iocs.append(ioc)
                    
                    collection.data.batch_save(ioc_data)
                        
                except Exception as e:
                    ew.log(EventWriter.ERROR, f"Error processing IOC: {str(e)}")
                    continue
            
            if new_count > 0 or updated_count > 0:
                ew.log(EventWriter.INFO, f"KV Store: {new_count} new, {updated_count} updated")
            
        except Exception as e:
            ew.log(EventWriter.ERROR, f"KV Store error: {str(e)}")
        
        return new_iocs


if __name__ == "__main__":
    ThreatMonModinput().run(sys.argv)
    sys.exit(0)
