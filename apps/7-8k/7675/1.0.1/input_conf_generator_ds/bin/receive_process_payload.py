import logging
import logging.handlers
from datetime import datetime as dt
import os
import json
import re
from collections import defaultdict
from pathlib import Path


from splunk.persistconn.application import PersistentServerConnectionApplication # type: ignore

def setup_logger(level):
    logger = logging.getLogger('input_conf_generator_ds')
    logger.setLevel(level)
    handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME']+'/var/log/splunk/input_conf_generator_ds.log', maxBytes=1000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger(logging.DEBUG)

class MyRestHandler(PersistentServerConnectionApplication):
    ###### customise path values if required  #####
    #app name and serverclass name in handle funtion 
    directory_path = Path(os.environ.get('SPLUNK_HOME', '')) / 'etc' / 'deployment-apps'
    serverclass_directory = Path(os.environ.get('SPLUNK_HOME', '')) / 'etc' / 'apps' / 'input_conf_generator_serverclass' / 'local'
    ###############################################

    def __init__(self, command_line, command_arg):
        super(MyRestHandler, self).__init__()

    def get_values(self, in_string):
        logger.debug(f"Received payload: {in_string}")
        try:
            # Decode the first level JSON
            outer_json = json.loads(in_string)
            logger.debug(f"Parsed outer JSON: {outer_json}")
            
            # Decode the payload wrapper (second level JSON)
            payload_wrapper = json.loads(outer_json.get('payload', '{}'))
            logger.debug(f"Parsed payload wrapper: {payload_wrapper}")
            
            # Handle additional escaping in the payload content (third level JSON)
            payload_raw = payload_wrapper.get('payload', '{}')
            logger.debug(f"Raw payload content before final parse 1: {payload_raw}")
            
            # Clean up the payload string
            payload_cleaned = payload_raw.strip('"\'')
            payload_cleaned = payload_cleaned.replace("\\'", '"')
            payload_cleaned = payload_cleaned.replace('\\n', '\n')
            payload_cleaned = payload_cleaned.replace('\\\"', '"')
            payload_cleaned = payload_cleaned.replace('\\\\', '\\')
            payload_cleaned = payload_cleaned.encode().decode('unicode_escape')
            
            logger.debug(f"Cleaned payload: {payload_cleaned}")
            
            # Parse the cleaned JSON
            payload_json = json.loads(payload_cleaned)

            
            # Extract required values with default fallbacks
            message = payload_json.get('message', '')
            precedence = payload_json.get('precedence', '')
            index_name = payload_json.get('my_index', '')
            my_sourcetype = payload_json.get('my_sourcetype', '')
            my_source = payload_json.get('my_source', [])
            my_host = payload_json.get('my_host', [])
            
            # Extract additional metadata
            additional_metadata = payload_json.get('additional_metadata', {})
            app_name = additional_metadata.get('app_name', '')
            environment = additional_metadata.get('environment', '')
            version = additional_metadata.get('version', '')
            
            logger.debug(f"Extracted values: message={message}, precedence={precedence}, index_name={index_name}, "
                        f"sourcetype={my_sourcetype}, sources={my_source}, hosts={my_host}, "
                        f"app_name={app_name}, environment={environment}, version={version}")
            
            return index_name, message, precedence, my_sourcetype, app_name, environment, version, my_source, my_host

        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {str(e)}")
            raise ValueError(f"Failed to decode JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in get_values: {str(e)}")
            raise ValueError(f"Unexpected error: {str(e)}")

    def generate_configs(self, sources, sourcetype, index):
        logger.debug(f"Generate config {sources,sourcetype,index}")
        configs = [
            f"[monitor://{source}]\n"
            f"index = {index}\n"
            f"sourcetype = {sourcetype}\n"
            f"disabled = false\n\n"
            for source in sources 
        ]
        logger.info(f"Generated {len(configs)} configurations")
        return configs


    def compare_and_update_input_configs(self, local_conf_path, configs, message):
        existing_configs = defaultdict(list)
        if local_conf_path.exists():
            logger.info(f"Reading existing configs from {local_conf_path}")
            
            with local_conf_path.open('r') as f:
                current_stanza = None
                for line in f:
                    line = line.strip()
                    if line.startswith('[monitor://'):
                        current_stanza = line
                    elif current_stanza and line:
                        existing_configs[current_stanza].append(line)
        
        new_configs = {}
        logger.info(f"Comparing existing configs with new configs")
        for config in configs:
            lines = config.strip().split('\n')
            if lines and lines[0].startswith('[monitor://'):
                stanza = lines[0]
                if stanza not in existing_configs:
                    new_configs[stanza] = lines[1:]

        if new_configs:
            logger.info(f"Attempting to write new configs : {local_conf_path}")
            with local_conf_path.open('a') as f:
                
                f.write(f'\n# *** Start of inputs from : {message} : Created at {dt.now().strftime("%Y-%m-%d %H:%M:%S %Z")}\n')
                
                for stanza, lines in new_configs.items():
                    f.write(f"{stanza}\n")
                    for line in lines:
                        f.write(f"{line}\n")
                    f.write('\n')
                
                f.write(f'\n# *** End of inputs from : {message}\n')

        return len(new_configs)

    def write_configs_to_file(self, configs, app_name, version, message, filename=None):
        if filename is None:
            
            directory = self.directory_path / app_name / 'default'
                
        try:
            
            app_conf_path = directory / 'app.conf'
            local_conf_path = directory / 'inputs.conf'
            
            directory.mkdir(parents=True, exist_ok=True)
            
            is_new_directory = not app_conf_path.exists()
            logger.debug(f"Directory : {directory} | is_new_directory : {is_new_directory}")
            
            
            if is_new_directory:
                logger.info(f"Created new app: {directory}")
                
                
                app_conf_path = os.path.join(directory, 'app.conf')
                current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                
                
                app_conf_content = f"""
#==============================================================================
# {app_name.center(76, '*')}
#==============================================================================
# Created by: input_conf_generator
# Author: Vignesh Narendran
# Update Date: {current_time}
# Version: {version}
# 
# Description:
# This file was automatically generated as part of the {app_name} Splunk app.
# It contains initial configuration settings. Don't modify any contents, 
# as it may affect the functionality of the app
#
# Warning: This app may be overwritten by future automated updates.
# 
#==============================================================================

"""
                with open(app_conf_path, 'w') as app_conf:
                    app_conf.write(app_conf_content.strip())

                logger.info(f"Created app.conf file: {app_conf_path}")
            else: 
                #to debug update time and version 
                with open(app_conf_path, 'r') as f:
                    lines = f.readlines()
                    with open(app_conf_path, 'w') as f:
                        for line in lines:
                            if line.startswith('version'):
                                f.write(f'version = {version}\n')
                                logger.info(f"Updated version : {version} in app.conf file: {app_conf_path}")
                            elif line.startswith('# Update Date:'):
                                current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S %Z")
                                f.write(f'# Update Date: {current_time}\n')
                                logger.info(f"Updated date : {current_time} in app.conf file: {app_conf_path}")
                            else:
                                f.write(line)
                logger.info(f"App : {app_name} existing in the target {directory}, attempting to compare and add new inputs") 

            logger.debug(f"Path: {local_conf_path} | Configs : {configs}")
            new_configs_len=self.compare_and_update_input_configs(local_conf_path, configs, message)
            action = "Created new" if is_new_directory else "Appended new configurations to"
            logger.info(f"{action} inputs.conf file: {local_conf_path}")
            logger.info(f"Added {new_configs_len} new configurations.")

            
            logger.info(f"Configuration update completed for {app_name}")
            return new_configs_len
        
        except Exception as e:
            logger.error(f"Failed to write configurations to file: {str(e)}")
            return False


    def compare_and_add_serverclass_whitelist_conf(self, app_name, serverclass_name, hosts):
        
        logger.debug(f"Processing serverclass with hosts: {hosts}")
        current_time = dt.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        
        os.makedirs(self.serverclass_directory, exist_ok=True)
        serverclass_path = os.path.join(self.serverclass_directory, 'serverclass.conf')
        logger.debug(f"Serverclass path: {serverclass_path}")
        
        logger.debug(f"Serverclass name: {serverclass_name}")   

        existing_content = ""
        existing_hosts = set()
        max_whitelist_num = -1
        server_class_exists = False
        app_stanza_start = None
        app_stanza_end = None

        # Read existing content and check for the server class
        if os.path.exists(serverclass_path):
            with open(serverclass_path, 'r') as f:
                existing_content = f.read()
                app_stanza_pattern = re.compile(rf'\[serverClass:{re.escape(serverclass_name)}\](.*?)(?=\n\[|\Z)', re.DOTALL)

                match = app_stanza_pattern.search(existing_content)
                logger.debug(f"App stanza pattern match: {match}")
                if match:
                    logger.info(f"Found existing server class configuration for {serverclass_name}")
                    server_class_exists = True
                    app_stanza_start = match.start()
                    app_stanza_end = match.end()
                    whitelist_pattern = re.compile(rf'whitelist\.(\d+)\s*=\s*(\S+)')
                    for match in whitelist_pattern.finditer(match.group(1)):
                        num, host = match.groups()
                        existing_hosts.add(host)
                        max_whitelist_num = max(max_whitelist_num, int(num))

        # Filter out existing hosts and create list of new hosts
        new_hosts = [host for host in hosts if host not in existing_hosts]
        logger.debug(f"Existing hosts: {existing_hosts}")
        logger.debug(f"New hosts to add: {new_hosts}")

        if not server_class_exists:
            logger.info(f"Creating new server class configuration for {serverclass_name}")
            content = f"""\n# Added on {current_time}
[serverClass:{serverclass_name}:app:{app_name}]
restartSplunkWeb = 0
restartSplunkd = 1
stateOnClient = enabled

[serverClass:{serverclass_name}]
"""
            for i, hostname in enumerate(new_hosts):
                content += f"whitelist.{i} = {hostname}\n"

            with open(serverclass_path, 'a') as f:
                f.write(content)
            logger.info(f"Added new server class configuration for {serverclass_name}")
            # self.reload_deploy_server(serverclass_name)
            return "New class added"

        elif new_hosts:
            logger.info(f"Adding new hosts to existing server class configuration for {serverclass_name}")
            content = f"""# Updated on {current_time}\n"""
            for i, hostname in enumerate(new_hosts, start=max_whitelist_num + 1):
                content += f"whitelist.{i} = {hostname}\n"
            updated_content = existing_content[:app_stanza_end] + content + existing_content[app_stanza_end:]

            with open(serverclass_path, 'w') as f:
                f.write(updated_content)

            logger.info(f"Added {len(new_hosts)} new hosts to existing server class {serverclass_name}")

            # self.reload_deploy_server(serverclass_name)
            return "existing class updated"

        else:
            logger.info(f"No new hosts to add for server class {serverclass_name}. Configuration unchanged.")
            return "no new updates"
    

    def handle(self, in_string):

        return_payload_string = ""
        try:
            logger.info(f"Received payload: {in_string}")
            index_name, message, precedence, my_sourcetypes, app_name, environment, version, my_sources, my_hosts = self.get_values(in_string)

            prefix_map = {"low": "z_", "normal": "y_", "high": "_"}

            ###### Update app_name and serverclass name format here ###########
            app_name = prefix_map[precedence] + environment + "_" + index_name + "_" + app_name             

            serverclass_name = f"{app_name}_{index_name}_{my_sourcetypes}"

            ###################################################################


            # perform all the calls from here, and get its status 
            if app_name:
                return_payload_string += "Payload extract = success | "
                configs = self.generate_configs(my_sources, my_sourcetypes, index_name)
                if configs:
                    return_payload_string += "Generate config = success | "
                    config_write_status = self.write_configs_to_file(configs, app_name, version, message)
                    if config_write_status:
                        return_payload_string += f"Write config = {config_write_status} written | "
                        

                        serverclass_status = self.compare_and_add_serverclass_whitelist_conf(app_name, serverclass_name, my_hosts)
                        if serverclass_status:
                            return_payload_string += f"Write serverclass = {serverclass_status} | "
                        else:
                            return_payload_string += "Write serverclass = failed | "
                    else:
                        return_payload_string += "Write config = failed | "
                else:
                    return_payload_string += "Generate config = failed | "
            else:
                return_payload_string = "Payload extract = failed | "

   
            return_payload_string += "..."

            return {
                'payload': {
                    "status": "success",
                    "message": "Payload received and logged.",
                    "Script_status": return_payload_string
                },
                'status': 200
            }

        except json.JSONDecodeError:
            logger.error("Invalid JSON format")
            return {
                'payload': {"status": "error", "message": "Invalid JSON format."},
                'status': 400
            }

        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                'payload': {"status": "error", "message": str(e)},
                'status': 500
            }


    def done(self):
        logger.info("Request completed, payload processed")

        """
        Called after the request completes (optional).
        """
        pass

