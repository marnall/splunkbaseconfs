import sys
import json
import re
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
# from s3_folder_watcher import log_new_s3_folders
import import_declare_test
from utils import S3Utility
import time
from logger import Logger
from event_logs import EventLogs
from common import Common
from inputs import Inputs
from solnlib import conf_manager
from solnlib.soln_exceptions import ConfManagerException
from dataclasses import dataclass
from typing import List

@dataclass
class EventInfo:
    index: str
    interval: str
    name: str
    bucket_name: str
    aws_account: str
    current_event_types: List[str]
    current_input_names: List[str] 
    start_date: str

@dataclass
class AWSAccountInfo:
    region: str
    access_key_id: str
    secret_access_key: str

@dataclass
class ConfUpdateContext:
    session_key: str
    aws_account: str
    event_log_name: str
    discovered_event_types: List[str]
    unique_mapping: dict
    event_name: str
    unique_in_s3_original: List[str]

@dataclass
class ProcessingContext:
    session_key: str
    event_info: EventInfo
    aws_info: AWSAccountInfo
    s3_bucket_folders: set

class S3AutoLogDiscovery(PersistentServerConnectionApplication):
    
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self._ta_name = import_declare_test.ta_name
        self._aws_account_conf_name = "ta_cisco_cloud_security_addon_aws_account"
        self._realm = f"__REST_CREDENTIAL__#{self._ta_name}#configs/conf-{self._aws_account_conf_name}"

    def update_input_names_in_conf(self, session_key, input_name_configs, unique_in_s3):
        """
        Generic method to update input_names field in multiple conf files.
        
        Args:
            session_key: Splunk session key
            input_name_configs: List of tuples (conf_file, stanza_name, event_log_inputs_name, realm)
            unique_in_s3: List of event types to add
        
        Returns:
            dict: Status results for each conf file
        """
        results = {}
        
        for conf_file, stanza_name, event_log_inputs_name, realm in input_name_configs:
            try:
                conf_realm = realm if realm else self._realm
                cfm = conf_manager.ConfManager(session_key, self._ta_name, realm=conf_realm)
                conf = cfm.get_conf(conf_file)
                stanza = conf.get(stanza_name, {})
                input_names = stanza.get("input_names", "")
                input_names_list = [name.strip() for name in input_names.split(",") if name.strip()]

                # Prepare new input names to add
                new_input_names = [f"{event_log_inputs_name}_{etype}" for etype in unique_in_s3]
                updated = False
                for new_name in new_input_names:
                    if new_name not in input_names_list:
                        input_names_list.append(new_name)
                        updated = True

                if updated:
                    conf.update(stanza_name, {"input_names": ",".join(input_names_list)})
                    results[conf_file] = "input_names updated"
                else:
                    results[conf_file] = "input_names already up-to-date"
                    
            except Exception as e:
                results[conf_file] = f"input_names update failed: {str(e)}"
        
        return results
    
    def handle(self, in_string):
        """Main handler for S3 auto-discovery requests."""
        try:
            # Parse and validate request - returns tuple
            event_name, session_key, method = self._parse_params(in_string)
            
            if method != 'post':
                return {'payload': {'message': f'Method {method} not supported'}, 'status': 405}
            
            # Get configuration information
            event_info = self._get_event_info(session_key, event_name)
            aws_info = self._get_aws_account_info(session_key, event_info.aws_account)
            s3_bucket_folders = self._get_s3_folders(
                session_key, 
                aws_info.region, 
                aws_info.access_key_id, 
                aws_info.secret_access_key, 
                event_info.bucket_name
            )            
            # Create processing context
            processing_context = ProcessingContext(
                session_key=session_key,
                event_info=event_info,
                aws_info=aws_info,
                s3_bucket_folders=s3_bucket_folders
            )

            # Refactored logic into method
            unique_mapping, discovered_event_types, unique_in_s3_original = self._get_discovered_event_types(processing_context)

            # Update configurations
            conf_context = ConfUpdateContext(
                session_key=session_key,
                aws_account=event_info.aws_account,
                event_log_name=event_info.name,
                discovered_event_types=discovered_event_types,
                unique_mapping=unique_mapping,
                event_name=event_name,
                unique_in_s3_original=unique_in_s3_original
            )

            update_confs = self._update_confs_for_created_inputs(conf_context)
            
            # Process auto-discovery
            created_event_types = self._create_new_inputs(processing_context, unique_mapping)
    
            return {'payload': {'message': f'S3 folders processed for {event_info.aws_account}'}, 'status': 200}
        except Exception as e:
            return {'payload': {"message": str(e)}, "status": 500}
        
    def _get_discovered_event_types(self, processing_context: ProcessingContext):
        """
        Identify discovered event types from S3 folders not already present in current inputs.
        Returns:
            unique_mapping (dict): Mapping of S3 folder to event type.
            discovered_event_types (list): List of newly discovered event types.
            unique_in_s3_original (list): List of unique S3 folders considered.
        """
        try:
            event_config = processing_context.event_info

            # Unique S3 folders before removing 'logs'
            unique_in_s3_original = [
                folder for folder in processing_context.s3_bucket_folders 
                if re.sub(r'logs$', '', folder) not in event_config.current_event_types
            ]

            # Create mapping dictionary
            unique_mapping = {
                folder: re.sub(r'logs$', '', folder) 
                for folder in unique_in_s3_original
            }
            discovered_event_types = []
            for prefix, event_type in unique_mapping.items():
                input_name = f"{event_config.name}_{event_type}"
                if input_name not in event_config.current_input_names:
                    discovered_event_types.append(event_type)

            return unique_mapping, discovered_event_types, unique_in_s3_original
        except Exception as e:
            return {'payload': {"message": str(e)}, "status": 500}
        
    def _parse_params(self, in_string):
        try:
            params = Common().parse_in_string(in_string)
            form = params.get('form', {})
            event_name = form.get('event_name')
            session = params.get('session', {})
            session_key = session.get('authtoken')
            method = params.get('method').lower()
            return event_name, session_key, method
        except Exception as e:
            raise ValueError(f"Failed to parse parameters: {e}")

    def _get_event_info(self, session_key: str, event_name: str) -> EventInfo:
        """Get event configuration information as a structured object."""
        try:
            event = EventLogs(session_key=session_key, name=event_name)
            event_mapping = event.event_mapping
            
            # Get current inputs information
            inputs_list = event.input_names.split(",")
            act_inputs = Inputs.get_inputs_with_filters(
                session_key=session_key,
                name=inputs_list
            )
            
            current_event_types = [i.event_type for i in act_inputs]
            current_input_names = [i.name for i in act_inputs]
            
            return EventInfo(
                index=event_mapping["all_events"].index,
                interval=event_mapping["all_events"].interval,
                name=event.name,
                bucket_name=event.bucket_name,
                aws_account=event.aws_account,
                current_event_types=current_event_types,
                current_input_names=current_input_names,
                start_date=event_mapping["all_events"].start_date
            )
        except Exception as e:
            raise ValueError(f"Failed to get event info: {e}")
        
    def _get_aws_account_info(self, session_key: str, aws_account: str) -> AWSAccountInfo:
        """Get AWS account configuration information."""
        try:
            conf_mgr = conf_manager.ConfManager(session_key, self._ta_name, realm=self._realm)
            aws_account_conf = conf_mgr.get_conf(self._aws_account_conf_name)
            account_info = aws_account_conf.get(aws_account, {})
            
            return AWSAccountInfo(
                region=account_info.get("region", ""),
                access_key_id=account_info.get("access_key_id", ""),
                secret_access_key=account_info.get("secret_access_key", "")
            )
        except Exception as e:
            raise ValueError(f"Failed to get AWS account info: {e}")

    def _get_s3_folders(self, session_key, region, access_key_id, secret_access_key, bucket_name):
        try:
            if bucket_name and region and access_key_id and secret_access_key:
                s3_util = S3Utility(session_key)
                prefixes = s3_util.get_event_type_prefixes(region, access_key_id, secret_access_key, bucket_name, prefix="")
                # More robust folder extraction
                s3_bucket_folders = set()
                for p in prefixes:
                    if p and p.strip():  # Skip empty/whitespace prefixes
                        # Remove trailing slash and get last component
                        folder = p.rstrip('/').split('/')[-1]
                        if folder:  # Only add non-empty folder names
                            s3_bucket_folders.add(folder)
            return s3_bucket_folders
        except Exception as e:
            raise ValueError(f"Failed to get S3 folders: {e}")

    def _create_new_inputs(self, context: ProcessingContext, unique_mapping: dict):
        """
        Create new inputs based on discovered S3 folders.
        
        Args:
            context: ProcessingContext containing all necessary configuration
            
        Returns:
            Tuple[Dict, List, List]: unique_mapping, created_event_types, unique_in_s3_original
        """
        try:
            event_config = context.event_info
            aws_config = context.aws_info
            
            created_inputs_results = {}
            for prefix, event_type in unique_mapping.items():
                input_name = f"{event_config.name}_{event_type}"
                if input_name in event_config.current_input_names:
                    created_inputs_results[event_type] = "already exists"
                    continue
                    
                normalized_prefix = prefix if prefix.endswith('/') else prefix + '/'
                try:
                    Inputs.create(
                        name=input_name,
                        session_key=context.session_key,
                        interval=event_config.interval,
                        index=event_config.index,
                        region=aws_config.region,
                        access_key_id=aws_config.access_key_id,
                        secret_access_key=aws_config.secret_access_key,
                        bucket_name=event_config.bucket_name,
                        prefix=normalized_prefix,
                        start_date=event_config.start_date,
                        event_type=event_type,
                        account_name=event_config.aws_account,
                        event_log_name=event_config.name
                    )
                    created_inputs_results[event_type] = "creation success"
                except Exception as e:
                    created_inputs_results[event_type] = f"creation failed: {e}"
                    raise ValueError(f"Failed to create input {input_name}: {e}")
                    
            created_event_types = [
                event_type for event_type, result in created_inputs_results.items() 
                if result == "creation success"
            ]            
            return created_event_types
            
        except Exception as e:
            raise ValueError(f"Failed to create new inputs: {e}")

    def _update_confs_for_created_inputs(self, context: ConfUpdateContext):
        """Update all related conf files after new inputs are created."""
        try:
            if not context.discovered_event_types:
                return {'payload': {"message": "No new inputs created, skipping conf updates"}, "status": 200}
            # Define input name update configurations
            input_name_configs = [
                (self._aws_account_conf_name, context.aws_account, context.event_log_name, self._realm),
                ("ta_cisco_cloud_security_addon_event_logs", context.event_log_name, context.event_log_name, self._realm)
            ]
            
            # Update input names configurations in batch
            input_results = self.update_input_names_in_conf(
                context.session_key, 
                input_name_configs, 
                context.discovered_event_types
            )
            
            # Prepare all conf file updates
            conf_updates = self._prepare_conf_updates(context.unique_mapping, context.unique_in_s3_original)
            
            # Update all conf files using the consolidated method
            conf_results = {}
            for conf_file, updates_config in conf_updates.items():
                result = self.update_conf_file(context.session_key, conf_file, updates_config)
                conf_results[conf_file] = result
                
            all_results = {
                "input_names": input_results,
                "conf_files": conf_results
            }
            
            return {
                'payload': {
                    "message": "Configuration updates completed successfully", 
                    "results": all_results
                }, 
                "status": 200
            }
            
        except Exception as e:
            raise ValueError(f"Failed to update confs for created inputs: {e}")

    def _prepare_conf_updates(self, unique_mapping, unique_in_s3_original):
        """
        Prepare configuration updates for all conf files in a structured format.
        
        Returns:
            dict: Configuration updates organized by conf file type
        """
        try:
            conf_updates = {
                "props": [],
                "transforms": [],
                "eventtypes": [],
                "tags": []
            }
            
            # Prepare transforms.conf updates
            for folder in unique_in_s3_original:
                
                conf_updates["transforms"].append({
                    'stanza_name': f"{folder}_fields",
                    'stanza_data': {
                        "DELIMS": ",",
                        "FIELDS": " "
                    },
                    'check_exists': True
                })
            
            # Prepare props.conf updates
            for prefix, event_type in unique_mapping.items():
                stanza_name = f"cisco:cloud_security:{event_type}"
                report_field = f"{prefix}_fields"
                conf_updates["props"].append({
                    'stanza_name': stanza_name,
                    'stanza_data': {
                        "TRANSFORMS-extract_and_remove_s3_uri": "extract_s3_uri_field, remove_s3_uri_field",
                        f"REPORT-{prefix}-fields": report_field,
                        "LINE_BREAKER": "([\\r\\n]+)",
                        "SHOULD_LINEMERGE": "false",
                        "CHARSET": "AUTO",
                        "disabled": "false",
                        "TRUNCATE": "1000000",
                        "MAX_EVENTS": "1000000",
                        "EVAL-product": '"Cisco Secure Access and Umbrella"',
                        "EVAL-vendor": '"Cisco"',
                        "EVAL-vendor_product": '"Cisco Secure Access/Umbrella"',
                        "EVAL-app": '"Cisco Secure Access Add-on for Splunk"',
                        "MAX_TIMESTAMP_LOOKAHEAD": "22",
                        "NO_BINARY_CHECK": "true",
                        "TIME_PREFIX": "^",
                        "TIME_FORMAT": '"%Y-%m-%d %H:%M:%S"',
                        "TZ": "UTC"
                    },
                    'check_exists': True
                })

            # Prepare eventtypes.conf and tags.conf updates
            for prefix, event_type in unique_mapping.items():
                stanza_name = f"{prefix}_eventtype"
                color = "et_yellow"
                priority = 5
                sourcetype = f"cisco:cloud_security:{event_type}"
                
                # Eventtypes config
                conf_updates["eventtypes"].append({
                    'stanza_name': stanza_name,
                    'stanza_data': {
                        "color": color,
                        "priority": str(priority),
                        "search": f'sourcetype="{sourcetype}" source="cisco_cloud_security_addon"'
                    },
                    'check_exists': True
                })
                
                # Tags config
                conf_updates["tags"].append({
                    'stanza_name': f"eventtype={stanza_name}",
                    'stanza_data': {},
                    'check_exists': True
                })
            return conf_updates
        except Exception as e:
            raise ValueError(f"Failed to prepare conf updates: {e}")

    def update_conf_file(self, session_key, conf_file, updates_config):
        """
        Generic method to update any conf file with multiple stanzas.
        
        Args:
            session_key: Splunk session key
            conf_file: Name of the conf file (e.g., 'tags', 'eventtypes', 'transforms', 'props')
            updates_config: List of dictionaries containing stanza configurations
                        Each dict should have: {'stanza_name': str, 'stanza_data': dict, 'check_exists': bool}
        
        Returns:
            dict: Summary of operations performed
        """
        try:
            cfm = conf_manager.ConfManager(session_key, self._ta_name, realm=self._realm)
            conf = cfm.get_conf(conf_file)
            
            results = []
            for config in updates_config:
                stanza_name = config['stanza_name']
                stanza_data = config['stanza_data']
                check_exists = config.get('check_exists', True)
                
                stanza_exists = False
                if check_exists:
                    try:
                        conf.get(stanza_name)
                        stanza_exists = True
                    except Exception:
                        stanza_exists = False
                        
                    if stanza_exists:
                        results.append(f"{stanza_name}: already exists")
                        continue
                
                conf.update(stanza_name, stanza_data)
                results.append(f"{stanza_name}: added")
            
            return {
                "status": "success",
                "file": conf_file,
                "results": results,
                "message": f"{conf_file}.conf updated successfully"
            }
        except Exception as e:
            return {
                "status": "error", 
                "file": conf_file,
                "message": f"{conf_file}.conf update failed: {str(e)}"
            }