import itertools
import sys
import os
import re
import multiprocessing 
import hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib import client
from splunklib.modularinput import *

import splunklib.six as six
import time
import json
import requests
import datetime
from functools import lru_cache

import calendar

# Global cache for FieldMapper instances to avoid recreating them
_mapper_cache = {}

def map_single_event(data_entry, name_to_display):
    event_json = map_nested_json(data_entry, name_to_display)
    return event_json

def get_mapping_hash(name_map):
    """
     MD5 hash for field mappings.
    
    Args:
        name_map (dict): Field mapping dictionary
        
    Returns:
        str: MD5 hash of the sorted mapping
    """
    # Create deterministic string representation
    sorted_items = sorted(name_map.items())
    mapping_string = json.dumps(sorted_items, sort_keys=True, separators=(',', ':'))
    
    # Generate MD5 hash
    return hashlib.md5(mapping_string.encode('utf-8')).hexdigest()

def map_section(data_section, name_to_display, ew=None):
    """
    Optimized batch processing using cached mapper with MD5 hash keys.
    """
    if not data_section:
        if ew:
            ew.log("INFO", "DG_ARC: No events to process. missing or empty data section.")
        return []
    
    # Create MD5 hash-based cache key
    name_map_key = get_mapping_hash(name_to_display)
    
    # Always use cached mapper (removed threshold check)
    if name_map_key not in _mapper_cache:
        _mapper_cache[name_map_key] = FieldMapper(name_to_display)
        # Limit cache size
        if len(_mapper_cache) > 100:
            oldest_key = next(iter(_mapper_cache))
            del _mapper_cache[oldest_key]
    
    mapper = _mapper_cache[name_map_key]
    
    # Batch process with the cached mapper
    mapped_data = []
    for data_entry in data_section:
        event_json = mapper.map_data(data_entry)
        mapped_data.append(event_json)
    
    return mapped_data

def split_into_n_parts(lst, n):
    if n <= 0:
        raise ValueError("n must be > 0")
    length = len(lst)
    base_size, remainder = divmod(length, n)

    result = []
    start = 0

    for i in range(n):
        size = base_size + (1 if i < remainder else 0)
        part = lst[start:start + size]
        result.append(part)
        start += size

    return result

def get_app_version():
    """Get version from app.manifest file."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        app_root = os.path.dirname(current_dir)
        app_conf_path = os.path.join(app_root, "default", "app.conf")
        if os.path.exists(app_conf_path):
            with open(app_conf_path, 'r') as f:
                content = f.read()
                # Look for version in [launcher] section
                match = re.search(r'\[launcher\][^\[]*version\s*=\s*(\S+)', content, re.DOTALL)
                if match:
                    return match.group(1).strip()

        manifest_path = os.path.join(os.path.dirname(current_dir), "app.manifest")
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            version = manifest["info"]["id"]["version"]
            return version
    except Exception as e:
        pass
    return "Not found"

class FieldMapper:
    """
    Optimized field mapping class that precomputes mappings once and reuses them.
    This eliminates the overhead of rebuilding mapping dictionaries for every call.
    """
    def __init__(self, name_map):
        self.name_map = name_map
        self.parent_key_map = {}
        self.child_key_maps = {}
        self.leaf_map = {}
        self._build_mappings()
    
    def _build_mappings(self):
        """Precompute all mappings once during initialization."""
        for field_name, display_name in self.name_map.items():
            if '.' not in field_name:
                continue
                
            parts = field_name.split('.')
            leaf_name = parts[-1]
            
            # Store leaf mapping if not already present
            if leaf_name not in self.name_map:
                self.leaf_map[leaf_name] = display_name
            
            # Process parent levels
            for i in range(len(parts) - 1):
                parent = '.'.join(parts[:i+1])
                
                if parent not in self.parent_key_map:
                    parent_display = parts[i]
                    if i == 0 and display_name:
                        first_word = display_name.split()[0] if display_name.split() else parts[i]
                        parent_display = first_word
                    self.parent_key_map[parent] = parent_display
                
                if parent not in self.child_key_maps:
                    self.child_key_maps[parent] = {}
                
                if i == len(parts) - 2:
                    child_key = parts[i+1]
                    self.child_key_maps[parent][child_key] = display_name
    
    def map_data(self, data):
        """Map data using precomputed mappings."""
        return self._map_recursive(data)
    
    def _map_recursive(self, data):
        """Optimized recursive mapping with minimal lookups."""
        if isinstance(data, list):
            return [self._map_recursive(item) for item in data]
        
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # Single lookup with fallback chain
                mapped_key = (self.name_map.get(key) or 
                             self.parent_key_map.get(key) or 
                             self.leaf_map.get(key) or 
                             key)
                
                # Handle nested structures
                if key in self.child_key_maps:
                    child_map = self.child_key_maps[key]
                    if isinstance(value, dict):
                        mapped_value = {
                            (child_map.get(child_key) or 
                             self.leaf_map.get(child_key) or 
                             child_key): self._map_recursive(child_val)
                            for child_key, child_val in value.items()
                        }
                    elif isinstance(value, list) and value and isinstance(value[0], dict):
                        mapped_value = [
                            {(child_map.get(child_key) or 
                              self.leaf_map.get(child_key) or 
                              child_key): self._map_recursive(child_val)
                             for child_key, child_val in item.items()}
                            for item in value
                        ]
                    else:
                        mapped_value = self._map_recursive(value)
                else:
                    mapped_value = self._map_recursive(value)
                
                result[mapped_key] = mapped_value
            
            return result
        
        else:
            return data

def precompute_field_mapper(name_map):
    """
    Pre-compute and cache a FieldMapper using MD5 hash key.
    Always caches regardless of field count.
    """
    name_map_key = get_mapping_hash(name_map)
    if name_map_key not in _mapper_cache:
        _mapper_cache[name_map_key] = FieldMapper(name_map)
        # Limit cache size
        if len(_mapper_cache) > 100:
            oldest_key = next(iter(_mapper_cache))
            del _mapper_cache[oldest_key]

def clear_mapper_cache():
    """Clear the mapper cache to free memory if needed."""
    global _mapper_cache
    _mapper_cache.clear()

def map_nested_json(data, name_map):
    """
    Always use cached mapper with MD5 hash key.
    """
    # Create MD5 hash-based cache key
    name_map_key = get_mapping_hash(name_map)
    
    # Always use cached mapper 
    if name_map_key not in _mapper_cache:
        _mapper_cache[name_map_key] = FieldMapper(name_map)
        # Limit cache size to prevent memory issues
        if len(_mapper_cache) > 100:
            # Remove oldest entries (simple FIFO)
            oldest_key = next(iter(_mapper_cache))
            del _mapper_cache[oldest_key]
    
    return _mapper_cache[name_map_key].map_data(data)

def get_cpu_count():
    """Get the number of CPU cores available on the system"""
    try:
        return multiprocessing.cpu_count()
    except Exception:
        return 1  # Default to 1 if unable to determine

def get_splunk_recommended_max_threads():
    """
    Calculate Splunk's recommended max threads based on their formula:
    MAX_HTTP_REST_THREADS = MAX_RAM / (256K * sizeof(void *)) / 3
    """
    try:
        import psutil
        # Get total RAM in bytes
        total_ram = psutil.virtual_memory().total
        
        # sizeof(void *) is typically 8 on 64-bit systems, 4 on 32-bit
        import sys
        void_ptr_size = 8 if sys.maxsize > 2**32 else 4
        
        # Apply Splunk's formula: RAM / (256K * sizeof(void *)) / 3
        splunk_max_threads = total_ram // (256 * 1024 * void_ptr_size) // 3
        
        # Ensure minimum of 1 and reasonable maximum
        return max(1, min(splunk_max_threads, 100))
    except ImportError:
        # psutil not available, fall back to CPU count
        return get_cpu_count()
    except Exception:
        return get_cpu_count()

def get_recommended_max_threads():
    """Get the recommended maximum threads considering both CPU and Splunk limits"""
    cpu_count = get_cpu_count()
    splunk_limit = get_splunk_recommended_max_threads()
    
    # Use the more conservative limit
    recommended_max = min(cpu_count, splunk_limit)
    
    # Ensure at least 1 thread
    return max(1, recommended_max)


class DGArcEventsModInput(Script):

    MASK = "------"
    VERSION = get_app_version()  # Match with app.manifest
    RELEASE_MODE = True  # Set to False for development/testing

    def get_scheme(self):
        # Setup scheme.
        scheme = Scheme("DigitalGuardian ARC Events")
        scheme.description = "Streams events from DigitalGuardian ARC"
        scheme.use_external_validation = False

        # Input parameter token description and settings
        token_argument = Argument("client_id")
        token_argument.title = "API Client ID"
        token_argument.data_type = Argument.data_type_string
        token_argument.description = "e.g: 0c0632a6-84f4-4758-cae3-f7b4613367bb"
        token_argument.required_on_create = True
        # not validating UUID format for now, need to confirm with DG ARC API team if UUID is always formatted as such
        # token_argument.validation = "validate(match('client_id','^[0-9a-fA-F-]{36}$'),'Client ID must be a valid UUID')"
        scheme.add_argument(token_argument)

        secret_argument = Argument("client_secret")
        secret_argument.title = "API Client Secret"
        secret_argument.data_type = Argument.data_type_string
        secret_argument.description = "Enter your API Client Secret (e.g. Ab1Cd2Ef3Gh4Ij5Kl6)"
        secret_argument.required_on_create = True
        scheme.add_argument(secret_argument)

        gateway_url = Argument("gateway_url")
        gateway_url.title = "Gateway Base URL"
        gateway_url.data_type = Argument.data_type_string
        gateway_url.description = "e.g: (https://servername)"
        gateway_url.required_on_create = True
        gateway_url.validation = "validate(match('gateway_url','^https://'),'Gateway Base URL must start with https://')"
        scheme.add_argument(gateway_url)

        auth_server_url = Argument("auth_server_url")
        auth_server_url.title = "Auth Server URL"
        auth_server_url.data_type = Argument.data_type_string
        auth_server_url.description = "e.g: (https://servername)"
        auth_server_url.required_on_create = True
        auth_server_url.validation = "validate(match('auth_server_url','^https://'),'Auth Server URL must start with https://')"
        scheme.add_argument(auth_server_url)

        export_profile = Argument("export_profile")
        export_profile.title = "Export Profile"
        export_profile.description = "UUID of the DG ARC Export Profile to use (e.g: 38fa78bb-5b82-41dc-80ba-5fec588f1572)"
        export_profile.data_type = Argument.data_type_string
        export_profile.required_on_create = True
        scheme.add_argument(export_profile)

        rest_api_version = Argument("rest_api_version")
        rest_api_version.title = "REST API Version"
        rest_api_version.description = "ARC REST API Version (optional) 1.0 or 2.0"
        rest_api_version.data_type = Argument.data_type_string
        rest_api_version.required_on_create = True
        rest_api_version.default_value = "2.0"
        rest_api_version.validation= "validate(match('rest_api_version','^(1.0|2.0)$'),'REST API Version must be either 1.0 or 2.0')"
        scheme.add_argument(rest_api_version)

        export_format = Argument("export_format")
        export_format.title = "Export Format"
        export_format.description = "(Specifying 'JSON' or  'JSON Flattened Table' improves processing time.) "
        export_format.data_type = Argument.data_type_string
        export_format.required_on_create = True
        export_format.default_value = "Auto-Detect Format Type"
        export_format.validation = "validate(match('export_format','^(Auto-Detect Format Type|json|flattened)$'),'Data Format must be either \"Auto-Detect Format Type\" or \"JSON\" or \"JSON Flattened Table\"')"
        scheme.add_argument(export_format)

        restcall_interval = Argument("restcall_interval")
        restcall_interval.title = "Rest API call interval"
        restcall_interval.description = "interval to sleep inbetween back to back rest call (default: 10)"
        restcall_interval.data_type = Argument.data_type_string
        restcall_interval.default_value = "10"
        scheme.add_argument(restcall_interval)

        thread_count = Argument("thread_count")
        thread_count.title = "Thread count"
        max_threads = get_recommended_max_threads()
        cpu_cores = get_cpu_count()
        splunk_limit = get_splunk_recommended_max_threads()
        thread_count.description = f"Number of threads used to process events (default: 1, max recommended: {max_threads} - CPU cores: {cpu_cores}, Splunk REST limit: {splunk_limit})"
        thread_count.data_type = Argument.data_type_string
        thread_count.default_value = "1"
        thread_count.validation = f"validate(isint('thread_count') AND tonumber('thread_count') >= 1 AND tonumber('thread_count') <= {max_threads}, 'Thread count must be between 1 and {max_threads} (recommended max based on CPU cores and Splunk REST limits)')"
        scheme.add_argument(thread_count)

        return scheme

    def validate_input(self, instance):
        auth_server_url = instance.parameters["auth_server_url"]
        gateway_url = instance.parameters["gateway_url"]

        if not auth_server_url.startswith("https://") or not gateway_url.startswith("https://"):
            raise ValueError("All URLs must start with 'https://'")
        
        # Validate thread count with Splunk-aware limits
        try:
            thread_count = int(instance.parameters.get("thread_count", "1"))
            max_threads = get_recommended_max_threads()
            cpu_cores = get_cpu_count()
            splunk_limit = get_splunk_recommended_max_threads()
            
            if thread_count < 1 or thread_count > max_threads:
                raise ValueError(f"Thread count must be between 1 and {max_threads}. "
                               f"(CPU cores: {cpu_cores}, Splunk REST limit: {splunk_limit})")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError("Thread count must be a valid integer")
            raise
        
        return True

    def encrypt_password(self, username, password, session_key):
        try:
            mgmt_hst_prt = self.management_host_port()
            args = {'token': session_key}
            args.update(mgmt_hst_prt)
            service = client.connect(**args)
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(
                        username=storage_password.username)
                    break

            service.storage_passwords.create(password, username)

        except Exception as e:
            raise Exception(" An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))

    def mask_password(self, session_key, input_name, username):
        try:
            mgmt_hst_prt = self.management_host_port()
            args = {'token': session_key}
            args.update(mgmt_hst_prt)
            service = client.connect(**args)
            kind, input_name = input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                "client_secret": self.MASK
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception(" Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, username):
        try:
            mgmt_hst_prt = self.management_host_port()
            args = {'token': session_key}
            args.update(mgmt_hst_prt)
            service = client.connect(**args)
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    return storage_password.content.clear_password
            return None
        except Exception as e:
            raise Exception(" An error occured when retrieving token: %s" % str(e))

    def get_splunklib_version(self):
        """Get the version of splunklib being used"""
        try:
            import splunklib
            file_path = getattr(splunklib, '__file__', 'unknown location')

            if 'lib/splunklib' in file_path:
                simple_path = 'lib/splunklib'
            else:
                simple_path = os.path.basename(os.path.dirname(file_path))

            version = getattr(splunklib, '__version__', 'Unknown version')
            return f"{version} (from {simple_path})"
        except Exception as e:
            return f"Error determining version: {str(e)}"

    def get_auth_token(self, auth_url, client_id, secret, ew):
        """Get authentication token from auth server"""
        url = f"{auth_url}/as/token.oauth2"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'client_id': client_id,
            'client_secret': secret,
            'grant_type': 'client_credentials',
            'scope': 'client'
        }
        ew.log("INFO", 'DG ARC - url=%s' % (url))
        r = requests.post(url, headers=headers, data=data, timeout=30, verify=self.RELEASE_MODE)
        if r.status_code != 200:
            ew.log("ERROR", f"Failed to retrieve token: {r.text}")
            return None
        return r.json().get("access_token")

    def management_host_port(self):
        """Get the management host and port for the Splunk instance"""
        try:
            import splunk
            return {'host': splunk.getDefault('host'), 'port': splunk.getDefault('port')}
        except ImportError:
            return {'host': 'localhost', 'port': 8089}

    def write_to_log_file(self, message, ew, file_prefix="raw_events"):
        """Write message to a log file in Splunk's log directory"""
        try:
            # Determine Splunk log directory
            splunk_home = os.environ.get('SPLUNK_HOME', '/opt/splunk')
            log_dir = os.path.join(splunk_home, 'var', 'log', 'splunk', 'ta_dg_arc')

            # Create log directory if it doesn't exist
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Create a filename with current date
            current_date = datetime.datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(log_dir, f"{file_prefix}_{current_date}.log")

            # Append message to log file
            with open(log_file, 'a') as f:
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                f.write(f"[{timestamp}] {message}\n")

            return True
        except Exception as e:
            ew.log("ERROR", f"Failed to write to log file: {str(e)}")
            return False

    def analyze_json_structure(self, response_json, ew):
        """
        Analyze JSON structure to determine if it's complex (nested) or flat.

        Args:
            response_json: The parsed JSON response
            ew: EventWriter for logging

        Returns:
            bool: True if complex JSON, False if flat
        """
        ew.log("INFO", "=== JSON STRUCTURE ANALYSIS ===")

        # Extract fields and data sections
        fields_section = []
        data_section = []

        # Quick extraction of fields and data
        if isinstance(response_json, dict):
            fields_section = response_json.get("fields", [])
            data_section = response_json.get("data", [])

            # If data not found at root level, check one level deeper
            if not data_section:
                for value in response_json.values():
                    if isinstance(value, dict) and "data" in value:
                        data_section = value["data"]
                        break

            ew.log("INFO", f"Root structure: dictionary with {len(response_json)} keys")
            if fields_section:
                ew.log("INFO", f"Found fields section with {len(fields_section)} fields")
            if data_section:
                ew.log("INFO", f"Found data section with {len(data_section)} entries")
        else:
            ew.log("INFO", f"Root is not a dictionary but a {type(response_json).__name__}")
            return True  # Non-dictionary root is considered complex

        # No data found, default to complex
        if not data_section:
            ew.log("WARNING", "No data section found")
            return True

        # Analyze first data entry to determine structure
        try:
            first_entry = data_section[0]

            # If first entry is a dictionary, check for nested structures
            if isinstance(first_entry, dict):
                # Quick check: sample first few keys for nested structures
                for i, (key, value) in enumerate(first_entry.items()):
                    if i >= 3:  # Only check first 3 keys
                        break
                    if isinstance(value, (dict, list)):
                        ew.log("INFO", "STRUCTURE: COMPLEX (dictionary with nested structures)")
                        return True

                ew.log("INFO", "STRUCTURE: COMPLEX (dictionary with simple values)")
                return True

            # If first entry is a list, check if it's a list of primitives with matching fields
            elif isinstance(first_entry, list):
                # Check if all items are primitive types
                is_primitive_list = all(not isinstance(item, (dict, list))
                                        for item in first_entry[:10])  # Check first 10 items max

                # If primitive list with matching fields, it's flat
                if is_primitive_list and fields_section and len(fields_section) >= len(first_entry):
                    ew.log("INFO", "STRUCTURE: FLAT (list of primitive values with matching fields section)")
                    return False
                else:
                    ew.log("INFO", "STRUCTURE: COMPLEX (list without matching fields or with non-primitive items)")
                    return True

            # Any other type is considered complex
            else:
                ew.log("INFO", f"STRUCTURE: COMPLEX (unusual first entry type: {type(first_entry).__name__})")
                return True

        except (IndexError, TypeError) as e:
            ew.log("WARNING", f"Error analyzing data structure: {str(e)}")
            return True  # Default to complex on error

        # Default fallback
        ew.log("INFO", "STRUCTURE: COMPLEX (default)")
        return True

    def _process_complex_json(self, response_json, input_name, gateway_url, target_index, timestamp, ew, thread_count=1):
        """Process complex/nested JSON responses"""
        ew.log("INFO", "Processing complex JSON with nested structures")

        # Extract data and fields sections
        data_section = []
        fields_section = []

        if isinstance(response_json, dict):
            if "fields" in response_json:
                fields_section = response_json["fields"]

            if "data" in response_json:
                data_section = response_json["data"]
            else:
                # Search for data in nested dictionaries
                for key, value in response_json.items():
                    if isinstance(value, dict) and "data" in value:
                        data_section = value["data"]
                        break

        if not data_section:
            ew.log("WARNING", "No data found in complex JSON response")
            return 0

        # Create field name mapping
        name_to_display = {}
        for field in fields_section:
            if "name" in field and "display_name" in field:
                name_to_display[field["name"]] = field["display_name"]

        # Pre-compute the mapper for better performance 
        if name_to_display:
            precompute_field_mapper(name_to_display)

        count = 0

        # Use the configured thread count 
        split_data_section = split_into_n_parts(data_section, thread_count)

        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=thread_count) as executor:
            results = list(executor.map(map_section, split_data_section, itertools.repeat(name_to_display)))

        mapped_data = list(itertools.chain.from_iterable(results))

        for mapped_entry in mapped_data:
            count = self.write_event(count, mapped_entry, ew, gateway_url, input_name, target_index, timestamp)

        return count

    def write_event(self, count, event_json, ew, gateway_url, input_name, target_index, timestamp):
        # Create and write event
        raw_event = Event()
        raw_event.stanza = f"{input_name}_{timestamp}"
        raw_event.sourceType = "dg:arc"
        raw_event.host = gateway_url.split("//")[1].split(":")[0] if "//" in gateway_url else gateway_url
        if target_index:
            raw_event.index = target_index
        raw_event.data = json.dumps(event_json)
        ew.write_event(raw_event)
        count += 1
        return count

    def _process_flat_json(self, response_json, input_name, gateway_url, target_index, timestamp, ew):
        """Process flat JSON responses"""
        ew.log("INFO", "Processing flattened JSON")

        # Extract fields and data
        data_section = response_json.get("data", [])
        fields_section = response_json.get("fields", [])

        if not data_section:
            ew.log("WARNING", "No data found in flat JSON response")
            return 0

        count = 0
        for data_entry in data_section:
            try:
                # Initialize event JSON
                event_json = {}

                # Mapping fields to values for flat structure
                if isinstance(data_entry, list):
                    for i, field in enumerate(fields_section):
                        if i < len(data_entry):
                            field_name = field.get("display_name", f"field_{i}")
                            field_value = data_entry[i]
                            if field_value != '-':  # Skip empty/placeholder values
                                event_json[field_name] = field_value

                count = self.write_event(count, event_json, ew, gateway_url, input_name, target_index, timestamp)

            except Exception as e:
                ew.log("ERROR", f"Error processing flat JSON event: {str(e)}")
                continue

        return count

    def send_ack(self, ack_url, headers, ew):
        ew.log("INFO", f"DG ARC - starting request - url={ack_url}")
        r = requests.post(ack_url, headers=headers, timeout=60, verify=self.RELEASE_MODE)

        if r.status_code != 204:
            ew.log("ERROR", f"Unable to acknowledge receipt with ARC Server.  Received code: {r.status_code}")
            return False
        else:
            ew.log("INFO", f"ACK sent successfully")
        return True

    def stream_events(self, inputs, ew):
        """
        Process events from DG ARC API with automatic format detection.
        Uses the same pagination logic as the original flat events handler.
        """
        for input_name, input_item in six.iteritems(inputs.inputs):
            try:
                now = calendar.timegm(time.gmtime())*1000
                ew.log("INFO", f"Starting input: {input_name}")

                #splunklib version logging
                splunklib_version = self.get_splunklib_version()
                ew.log("INFO", f"Using Splunklib version: {splunklib_version}")
                ew.log("INFO", f"TA-dg_arc version: {self.VERSION}")

                # Sets input variables
                session_key = self._input_definition.metadata['session_key']
                e_input_name = re.sub(r"^.*?\/\/", "", input_name)
                client_id = input_item["client_id"]
                client_secret = input_item["client_secret"]
                gateway_url = input_item["gateway_url"]
                auth_url = input_item["auth_server_url"]
                interval = input_item["interval"]
                export_profile = input_item["export_profile"]
                target_index = input_item.get("index", None)
                rest_api_version = input_item.get("rest_api_version", "2.0")
                export_format = input_item.get("export_format", "json")
                
                # Wire the new parameters with Splunk-aware validation
                restcall_interval = int(input_item.get("restcall_interval", "10"))
                thread_count_input = int(input_item.get("thread_count", "1"))
                
                # Validate and limit thread count using Splunk-aware calculations
                cpu_cores = get_cpu_count()
                splunk_limit = get_splunk_recommended_max_threads()
                max_threads = get_recommended_max_threads()
                thread_count = min(thread_count_input, max_threads)
                
                if thread_count != thread_count_input:
                    ew.log("WARNING", f"Requested thread count ({thread_count_input}) exceeds recommended maximum ({max_threads}). Using {thread_count} threads instead.")
                
                ew.log("INFO", f"DG ARC - Server CPU cores: {cpu_cores}")
                ew.log("INFO", f"DG ARC - Splunk REST thread limit: {splunk_limit}")
                ew.log("INFO", f"DG ARC - Recommended max threads: {max_threads}")
                ew.log("INFO", f"DG ARC - Rest call interval: {restcall_interval} seconds")
                ew.log("INFO", f"DG ARC - Thread count: {thread_count}")

                interval_seconds = int(interval)
                interval_minutes = interval_seconds / 60
                ew.log("INFO", f'DG ARC - interval={interval_seconds}s ({interval_minutes:.1f} minutes)')
                ew.log("INFO", f"DG ARC - sending data to index: {target_index}")

                # Masking token process
                if client_secret != self.MASK:
                    self.encrypt_password(
                        e_input_name, client_secret, session_key)
                    self.mask_password(session_key, input_name, e_input_name)

                client_secret = self.get_password(session_key, e_input_name)
                token = self.get_auth_token(auth_url, client_id, client_secret, ew)
                if not token:
                    ew.log("ERROR", "Failed to get authentication token")
                    continue
                ew.log("INFO", f"TOKEN: {token[:10]}...")

                if rest_api_version not in ["1.0", "2.0"]:
                    error_msg = (
                        f"Invalid REST API version: {rest_api_version}. "
                        f"Only versions 1.0 and 2.0 are supported. "
                        "Please check your DigitalGuardian ARC Events data input and set the correct REST API version."
                    )
                    ew.log("ERROR", error_msg)
                    return
                # Access DG ARC Logs
                url = f"{gateway_url}/rest/{rest_api_version}/export_profiles/{export_profile}/export"
                ack_url = f"{gateway_url}/rest/{rest_api_version}/export_profiles/{export_profile}/acknowledge"

                ew.log("INFO", f"DG ARC - Request URL: {url}")
                headers = {
                    'Authorization': f"Bearer {token}",
                    'Accept': 'application/json'
                }

                count = 0
                max_retries = 3
                retry_count = 0
                sleep_seconds = restcall_interval  # Use the configured interval defaulting at 10

                while True:
                    try:
                        start_process = time.perf_counter()
                        ew.log("INFO", f"DG ARC - starting request - url={url}")
                        r = requests.post(url, headers=headers, timeout=60, verify=self.RELEASE_MODE)
                        end_process = time.perf_counter()

                        if r.status_code != 200:
                            ew.log("ERROR", f"Failed to retrieve events: {r.text}")
                            break
                        else:
                            ew.log("INFO", f"Timer - request posted in : {end_process - start_process:4f}  seconds")

                        try:
                            response_json = json.loads(r.text)
                            # Get the configured data format preference
                            ew.log("INFO", f"Configured data format: {export_format}")

                            # Auto-detect structure if needed
                            is_complex = True  # Default to complex
                            if export_format == "json":
                                is_complex = True  # JSON format is treated as complex
                            elif export_format == "flattened":
                                is_complex = False  # Flattened format is treated as flat
                            else:
                                # Fall back to auto-detection for other values or future formats
                                is_complex = self.analyze_json_structure(response_json, ew)
                                ew.log("INFO", f"Structure auto-detection result: {'COMPLEX' if is_complex else 'FLATTENED'} JSON")

                            # Route to appropriate handler based on detection
                            events_processed = 0

                            start_process = time.perf_counter()

                            if is_complex:
                                events_processed = self._process_complex_json(response_json, e_input_name, gateway_url, target_index, now, ew, thread_count)
                            else:
                                events_processed = self._process_flat_json(response_json, e_input_name, gateway_url, target_index, now, ew)

                            count += events_processed
                            end_process = time.perf_counter()

                            # Log cache size after processing events
                            ew.log("INFO", f"FieldMapper Cache size: {len(_mapper_cache)}/100 entries")

                            ew.log("INFO", f"Timer - process ran in : {end_process - start_process:4f} seconds for :{events_processed} records to index: {target_index or 'main'}")

                            # Use the same threshold logic as stream_flat_events (10,000)
                            if events_processed < 10000:
                                # Break because ARC has less than 10k events at this interval
                                ew.log("INFO", f"Less than 10000 events for the batch received. Breaking Loop. Total events accumulated so far: {count}")
                                self.send_ack(ack_url, headers, ew)
                                break
                            else:
                                # Rerun the loop because this max of 10k events may not be all that arc had
                                ew.log("INFO", f"Maximum of 10000 events received this batch. Rerunning Loop. Total events accumulated so far: {count}")

                            if not self.send_ack(ack_url, headers, ew):
                                break

                            # Adding sleep after processing each batch of events to avoid overwhelming the server
                            # 10k events takes about 10 seconds to process
                            ew.log("INFO", f"Sleeping for {sleep_seconds} seconds before next request")
                            time.sleep(sleep_seconds)
                            ew.log("INFO", f"Processing events for input={e_input_name}, target_index={target_index}")


                        except json.JSONDecodeError as jde:
                            ew.log("ERROR", f"Failed to parse JSON response: {str(jde)}")
                            break

                    except requests.RequestException as req_error:
                        retry_count += 1
                        if retry_count <= max_retries:
                            ew.log("WARNING", f"Network error retrieving events (attempt {retry_count}/{max_retries}): {str(req_error)}")
                            time.sleep(2 * retry_count)  # Exponential backoff
                            continue
                        else:
                            ew.log("ERROR", f"Maximum retries reached for network error: {str(req_error)}")
                            break
                    except Exception as e:
                        ew.log("ERROR", f"Unexpected error: {str(e)}")
                        import traceback
                        ew.log("ERROR", f"Traceback: {traceback.format_exc()}")
                        break

                ew.log("INFO", f"DG_ARC: DONE with {count} events for index: {target_index or 'main'}")

            except Exception as e:
                ew.log("ERROR", f"Exception: {str(e)}")
                import traceback
                ew.log("ERROR", f"Traceback: {traceback.format_exc()}")
            finally:
                # Close all written events to Splunk's indexing pipeline
                ew.close()

if __name__ == "__main__":
    sys.exit(DGArcEventsModInput().run(sys.argv))
