import csv, sys, os, json, configparser, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from ds_utils import log
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from ds_reload import copy_files_to_tmp_location
from extract_csv_parms import extrace_csv
from setup import create_machine_types_filter_file

serverclass_csv = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app','lookups', 'serverclass.csv'])
ds_conf_path= splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'local', 'ds.conf'])

# Helper function to write rows to the CSV
def write_rows(file, rows):
    with open(file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def get_apps_present_in_json(path):
    try:
        # Get a list of all directories at the specified path
        directories = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
        
        # Convert the list to JSON format
        directories_json = {"apps": directories}
        
        return directories_json
    
    except FileNotFoundError:
        print(f"Error: The path '{path}' does not exist.")
        return json.dumps({"error": f"The path '{path}' does not exist."}, indent=4)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        log("ERROR",traceback.format_exc())
        return json.dumps({"error": str(e)}, indent=4)
 
@Configuration()
class UpdateDSConfig(GeneratingCommand):
    serverclass = Option(require=True)
    apps = Option(require=True)
    whitelist = Option(require=True)
    blacklist = Option(require=True)
    machineTypesFilter = Option(require=True)
    action = Option(require=True)
    whitelistFromPathname = Option(require=True)
    whitelistSelectField = Option(require=True)
    whitelistWhereField = Option(require=True)
    whitelistWhereEquals = Option(require=True)
    blacklistFromPathname = Option(require=True)
    blacklistSelectField = Option(require=True)
    blacklistWhereField = Option(require=True)
    blacklistWhereEquals = Option(require=True)
    
    def generate(self):

        try:
            
            action=self.action
            apps=self.apps
            serverclass=self.serverclass
            whitelist=self.whitelist
            blacklist=self.blacklist
            machineTypesFilter=self.machineTypesFilter
            
            # Mapping for whitelist and blacklist fields
            fields = {
                "whitelist": [
                    ("from_pathname", self.whitelistFromPathname),
                    ("select_field", self.whitelistSelectField),
                    ("where_field", self.whitelistWhereField),
                    ("where_equals", self.whitelistWhereEquals)
                ],
                "blacklist": [
                    ("from_pathname", self.blacklistFromPathname),
                    ("select_field", self.blacklistSelectField),
                    ("where_field", self.blacklistWhereField),
                    ("where_equals", self.blacklistWhereEquals)
                ]
            }
            os.makedirs(os.path.dirname(serverclass_csv), exist_ok=True) 
            if not os.path.exists(serverclass_csv):
                with open(serverclass_csv, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Serverclass", "App", "Key", "Value"]) 
            # Read the existing CSV
            with open(serverclass_csv, mode='r') as file:
                reader = csv.reader(file)
                rows = list(reader)

            # Remove existing rows with the same serverclass
            rows = [row for row in rows if not row[0] == serverclass]

            # Process actions
            if action == "Remove":
                log("INFO","Serverclass update in progress...")
                # Just remove all rows starting with the serverclass
                write_rows(serverclass_csv, rows)
                result = {"status": "success" , "message": "Serverclass upadated successfully"}
                yield result
                
            elif action in ["Update", "Add"]:
                log("INFO","Serverclass update in progress...")
                # New rows to add
                new_rows = []

                # Add/Update apps rows
                if apps=="Null":
                    new_rows.append([serverclass, "-", "restartSplunkd", "1"])    
                elif apps and apps.strip():
                    app_list = apps.split(",")
                    for app in app_list:
                        app = app.strip()
                        new_rows.append([serverclass, app, "restartSplunkd", "1"])

                # Add/Update whitelist rows
                if whitelist and whitelist.strip() and whitelist!="Null":
                    whitelist_list = whitelist.split(",")
                    for item in whitelist_list:
                        item = item.strip()
                        new_rows.append([serverclass, "-", "whitelist", item])

                # Add/Update blacklist rows
                if blacklist and blacklist.strip() and blacklist!="Null":
                    blacklist_list = blacklist.split(",")
                    for item in blacklist_list:
                        item = item.strip()
                        new_rows.append([serverclass, "-", "blacklist", item])

                # Add/Update machineTypesFilter rows
                if machineTypesFilter and machineTypesFilter.strip() and machineTypesFilter!="Null":
                    machine_types = machineTypesFilter.split(",")
                    for item in machine_types:
                        item = item.strip()
                        new_rows.append([serverclass, "-", "machineTypesFilter", item])

                # Add/Update Whitelist and Blacklist paths
                for list_type, field_values in fields.items():
                    for key_suffix, value in field_values:
                        if value and value.strip() and value != "Null":
                            new_rows.append([serverclass, "-", f"{list_type}_{key_suffix}", value])

                                    
                # Append new rows to the existing rows
                rows.extend(new_rows)

                # Write the updated rows to the CSV
                write_rows(serverclass_csv, rows)
                
                log("INFO","Serverclass updated Successfully")
                log("INFO", "Reload deployment server is in progress...")
                extrace_csv()
                create_machine_types_filter_file()
                copy_files_to_tmp_location()
                
                log("INFO","Successfully reloaded deployment server")
                
                result = {"status": "success" , "message": "Serverclass upadated successfully"}
                yield result
                
            elif action in ["getAllApps"]:
                if os.path.exists(ds_conf_path):
                    config = configparser.ConfigParser()
                    config.read(ds_conf_path)
                    try:
                        dest_location = config.get('general', 'dest_repositorylocation')
                        message = get_apps_present_in_json(dest_location)   
                        yield {"status": "success", "message" : message["apps"]}
                    except (configparser.NoSectionError, configparser.NoOptionError) as e:
                        log("ERROR",f"Error reading JSON file: {e}")
                        yield {"status": "error", "message": "Error reading conf file"}
                else:
                    yield {"status": "info", "message" : "JSON file is not present"}

        except Exception as e:
            # Handle errors and return error result to JavaScript
            log("ERROR", f"Error in update configuration")
            result = {"status": "error", "message": f"An error occurred: {str(e)}"}
            log("ERROR",traceback.format_exc())
            yield result


dispatch(UpdateDSConfig, sys.argv, sys.stdin, sys.stdout, __name__)
