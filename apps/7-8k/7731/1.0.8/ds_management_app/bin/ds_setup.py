import sys, subprocess, configparser, traceback, os, json
from ds_utils import log  
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from extract_csv_parms import make_path
from setup import  push_script

dc_app_tgz_path = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'data', 'setup_app'])
store_setup_info_path= splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'checkpoint', 'setup_info.json'])

def convert_path_to_string(path):
    # Make path based on OS and return in string formate
    if path.startswith("$SPLUNK_HOME"):
        splited_path=make_path(str(path))
        updated_path = splunk_lib_util.make_splunkhome_path(splited_path[1:])
    else:
        splited_path=make_path(str(path))
        updated_path = (os.sep).join(splited_path)

    
    return updated_path


@Configuration()
class SetupDS(GeneratingCommand):
    dsIP = Option(require=False)
    repositoryLocation=Option(require=False)
    phonehome=Option(require=False)

    def generate(self):

        try:
            if self.dsIP:  
                log("INFO", "DS setup is started ...")
                # Build the btool command
                splunk_bin = make_splunkhome_path(["bin", "splunk"])
                command = [splunk_bin, "btool", "serverclass", "list", "global"]
                
                result = subprocess.run(command, capture_output=True, text=True, check=True)

                filtered_output = [
                    (line.split("=")[1]).strip() for line in result.stdout.splitlines() if "repositoryLocation" in line
                ]
                if not filtered_output:
                    log("ERROR","No repositoryLocation found in btool output")
                    raise ValueError("No repositoryLocation found in btool output")
                
                source_repositoryLocation = convert_path_to_string(filtered_output[0])
                dest_repositoryLocation = convert_path_to_string(self.repositoryLocation)

                ds_conf_path = splunk_lib_util.make_splunkhome_path(['etc','apps','ds_management_app','local','ds.conf'])
                dc_conf_path = os.path.join(source_repositoryLocation, "ds_addon", "local", "dc.conf")
                dc_input_conf_path = os.path.join(source_repositoryLocation, "ds_addon", "local", "inputs.conf")

                ####### Create DS.conf file
                os.makedirs(os.path.dirname(ds_conf_path), exist_ok=True)
                config = configparser.ConfigParser()
                if os.path.exists(ds_conf_path):
                    config.read(ds_conf_path)

                if 'general' not in config:
                    config['general'] = {}
                config['general']['source_repositoryLocation'] = str(source_repositoryLocation)
                config['general']['dest_repositoryLocation'] = str(dest_repositoryLocation)
                with open(ds_conf_path, 'w') as configfile:
                    config.write(configfile)
                log("INFO","Successfull created ds.conf file")
        

                ######## Update DC.conf
                push_script()
                os.makedirs(os.path.dirname(dc_conf_path), exist_ok=True)
                config = configparser.ConfigParser()
                if os.path.exists(dc_conf_path):
                    config.read(dc_conf_path)
                    
                if 'general' not in config:
                    config['general'] = {}
                config['general']['ds_ui_url'] = self.dsIP

                with open(dc_conf_path, 'w') as configfile:
                    config.write(configfile)
                    
                log("INFO","Successfull created dc.conf file")    
                
                ######## Update inputs.conf 
                os.makedirs(os.path.dirname(dc_input_conf_path), exist_ok=True)
                config = configparser.ConfigParser()
                if os.path.exists(dc_input_conf_path):
                    config.read(dc_input_conf_path)
                
                linux_section_name = "script://./bin/dc_linux.sh"
                config[linux_section_name]={}
                config[linux_section_name]["interval"]= self.phonehome
                
                win_section_name = f"script://.\\bin\dc_windows.bat"
                config[win_section_name]={}
                config[win_section_name]["interval"]= self.phonehome

                with open(dc_input_conf_path, 'w') as configfile:
                    config.write(configfile, space_around_delimiters=False)   
                log("INFO","Successfull created inputs.conf file")   
                
                ###### Store info in tmp file
                store_setup_info= {}
                store_setup_info['dsIP'] = self.dsIP
                store_setup_info['source_repositoryLocation'] = source_repositoryLocation
                store_setup_info['dest_repositoryLocation'] = self.repositoryLocation
                store_setup_info['phonehome'] = self.phonehome
                with open(store_setup_info_path, 'w') as f:
                    json.dump(store_setup_info, f)
                    log("INFO", "Created checkpoint for all files")
                    
                log("INFO", "DS setup completed")
                yield {"status": "success", "message" : "Setup Completed"}
                    
            else:
                if os.path.exists(store_setup_info_path):
                    try:
                        with open(store_setup_info_path, 'r') as f:
                            yield {"status": "success", "message" : json.load(f)}
                    except json.JSONDecodeError as e:
                        log("ERROR",f"Error reading JSON file: {e}")
                        yield {"status": "error", "message": "Error reading JSON file"}
                else:
                    yield {"status": "info", "message" : "JSON file is not present"}

        except Exception as e:
            # Handle errors and return error result to JavaScript
            log("ERROR", f"Error during dssetup execution: {str(e)}")
            log("ERROR",traceback.format_exc())
            result = {"status": "error", "message": f"An error occurred: {str(e)}"}
            yield result


dispatch(SetupDS, sys.argv, sys.stdin, sys.stdout, __name__)