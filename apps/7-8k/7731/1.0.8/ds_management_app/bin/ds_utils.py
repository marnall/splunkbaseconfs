import os,csv,re,traceback,time
import sa_import
from filelock import FileLock
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

checkpoint_csv = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'app_checkpoint.csv'])
dc_info_csv = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'lookups', 'dc_info.csv'])
dc_serverclass_mapping = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'lookups', 'dc_serverclass_mapping.csv'])
dc_app_status_csv = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'lookups', 'dc_app_status.csv'])

# Lock files
dc_info_lock_file = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'dc_info_lock_file.txt'])
dc_app_status_lock_file = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'dc_app_status_lock_file.txt'])
dc_phonehome_time_lock_file = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'dc_phonehome_time_lock_file.txt'])
dc_serverclass_mapping_lock_file = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'dc_serverclass_mapping_lock_file.txt'])


# CSV for the machineTypesFilter
machineTypesFilter_input_file = splunk_lib_util.make_splunkhome_path(["var", "run", "ds_management_app", "lookups", "serverclass.csv"])
machineTypesFilter_output_file = splunk_lib_util.make_splunkhome_path(["var", "run", "ds_management_app", "lookups", "machine_types_filter.csv"])
    
log_file_path = make_splunkhome_path(
    ['var', 'log', 'splunk', 'ds_management_app.log'])

client_log_file_path = make_splunkhome_path(
    ['var', 'log', 'splunk', 'ds_management_app_client.log'])

def log(level, message):
    with open(log_file_path, "a") as log_file:
        log_file.write(f"\n{level}: {message}")

def dc_historical_log(level, message):
    with open(client_log_file_path, "a") as log_file:
        log_file.write(f"\n{level}: {message}")
        

def create_machine_types_filter_file():
    """
    Reads a CSV file and writes rows with Key="machineTypesFilter" to a separate file.
    """
    try:
        with open(machineTypesFilter_input_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Prepare to write the filtered rows to a new file
            with open(machineTypesFilter_output_file, 'w', newline='') as outputfile:
                fieldnames = reader.fieldnames
                writer = csv.DictWriter(outputfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in reader:
                    key = row['Key'].strip()  # Handle any trailing spaces in the 'Key' column
                    if key == "machineTypesFilter":
                        writer.writerow(row)
        
        log("INFO",f"Successfully build lookup for machineTypesFilter.")
    except Exception as e:
        log("ERROR",f"An error occurred while building machineTypesFilter lookup:{e}")
        log("ERROR",traceback.format_exc())

def check_machineTypesFilter(machineTypesFilter_file_path, server_class, os_name):
    try:
        # log("INFO", "Inside check_machineTypesFilter function")
        
        with open(machineTypesFilter_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Check if Serverclass matches
                if row['Serverclass'].strip() == server_class:
                    allowed_os = [os.strip() for os in row['Value'].split(',')]
                    # log("INFO", f"Allowed OS values for {server_class}: {allowed_os}")
                    
                    for value in allowed_os:
                        # Replace '*' with '.*' to handle regex
                        regex_value = value.replace('*', '.*')
                        
                        if re.fullmatch(regex_value, os_name, re.IGNORECASE):
                            # log("INFO", f"OS '{os_name}' matches regex '{regex_value}'. Returning 'No action'.")
                            return "No action"
                    
                    # If no match is found in allowed_os
                    log("INFO", f"OS '{os_name}' does not match any allowed OS for server class '{server_class}'. Returning 'remove'.")
                    return "remove"
            
            # If Serverclass is not found in the CSV
            # log("INFO", f"Server class '{server_class}' not found in the CSV. Returning 'No action'.") 
            return "No action"
    except Exception as e:
        log("ERROR",f"Error: {e}")
        log("ERROR",traceback.format_exc())
        return f"Error: {e}"
    

def get_apps_for_input(input_values, csv_file_path, os_name,uf_guid):
    
    apps = set()            # To store unique app names
    whitelist_server_classes=set() # To store unique serverClass names
    blacklist_server_classes=set() # To store unique serverClass names
    
    # Step 1: Find serverClasses where "Value" matches input_value using regex
    with open(csv_file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            server_class = row['Serverclass']
            value = row['Value']
            mode = row['Key'].strip()
            app = row['App']
        
            
            if mode not in ["whitelist","blacklist"]:
                continue
            
            value = row["Value"].replace('*', '.*')
            
            for input_value in input_values:
                
                # Use regex to check if input_value matches the value
                if re.fullmatch(value, input_value, re.IGNORECASE):
                    if mode=="whitelist":
                        whitelist_server_classes.add(server_class)
                        break
                    elif mode=="blacklist":
                        blacklist_server_classes.add(server_class)
                        break
                    
    whitelist_server_classes -= blacklist_server_classes
    items_to_remove=set()
    
    
    for sc in whitelist_server_classes:
        machineTypeOutput=check_machineTypesFilter(machineTypesFilter_output_file,sc,os_name)
        if machineTypeOutput=="remove":
            items_to_remove.add(sc)

    whitelist_server_classes -= items_to_remove
      
    # Step 2: Find all apps associated with the identified serverClasses
    with open(csv_file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        apps.update(row['App'] for row in reader if row['Serverclass'] in whitelist_server_classes and row['App'] != '-')   
    
    current_time = int(time.time())
    message = f"{current_time},{uf_guid},{','.join(input_values)},\"{','.join(whitelist_server_classes)}\",\"{','.join(apps)}\""
    update_csv_file("dc_serverclass_mapping", message)
    return apps


def get_apps_checkpoint(list_of_apps):
    checkpoints = {}

    # Read the CSV file
    with open(checkpoint_csv, mode='r') as f:
        reader = csv.DictReader(f)
        
        # Populate the checkpoints dictionary
        for row in reader:
            checkpoints[row['app_name']] = row['checkpoint']
    
    # Get checkpoints for the provided list of apps
    return {app: checkpoints.get(app) for app in list_of_apps}


def update_csv_file(file_path, message):
    headers = []
    lock_file = ""
    if file_path == "dc_info_csv":
        file_path = dc_info_csv
        lock_file = dc_info_lock_file
        headers = ["_time", "guid", "ip", "private_ip", "hostname", "servername", "os", "clientname"]   
    elif file_path == "dc_serverclass_mapping":
        file_path = dc_serverclass_mapping
        lock_file = dc_serverclass_mapping_lock_file
        headers = ["_time", "guid", "clientname", "ip", "hostname", "servername", "serverclass_list", "apps_list"]
    elif file_path == "dc_app_status_csv":
        file_path = dc_app_status_csv
        lock_file = dc_app_status_lock_file
        headers = ["_time", "ip", "guid", "script_start_time", "phonehome_complete_time", "app_download_complete_time", "script_end_time", "installed_apps", "failed_apps"]

    lock = FileLock(lock_file)
    while True:
        try:
            with lock.acquire(timeout=60):  # Timeout after 10 seconds
                # Ensure the file exists and is accessible
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    with open(file_path, "w") as log_file:
                        log_file.write(",".join(headers) + "\n")
                        log_file.write(f"{message}\n")
                else:
                    # Append the message
                    with open(file_path, "a") as log_file:
                        log_file.write(f"{message}\n")
                break
        except TimeoutError:
            log("ERROR",f"Could not acquire lock for {file_path} within the timeout period.")
            log("ERROR",traceback.format_exc())