import os, shutil,re, csv, hashlib, tarfile, configparser,time, traceback
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util
from ds_utils import log, create_machine_types_filter_file
from extract_csv_parms import extrace_csv
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util


#General Path
checkpoint_dir = splunk_lib_util.make_splunkhome_path(["var", "run", "ds_management_app", "checkpoint"])
ds_conf_path = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'local', 'ds.conf'])
reload_time_txt = splunk_lib_util.make_splunkhome_path(["var", "run", "ds_management_app", "checkpoint","reload_time.txt"])
   
# Define source and destination directories for copy_apps
# src_repository_location = splunk_lib_util.make_splunkhome_path(["etc", "deployment-apps"])   ### TO DO : Make this path dynamic from btool
# dst_repository_location = splunk_lib_util.make_splunkhome_path(["etc", "deployment-apps"])  ### TO DO : Make this path dynamic from conf file
checkpoint_copy_ds_app = os.path.join(checkpoint_dir, "checkpoint_copy_ds_app.txt")

# Define paths for converting .conf to .csv
serverclass_conf_file = splunk_lib_util.make_splunkhome_path(["etc", "system", "local", "serverclass.conf"])
serverclass_csv_file = splunk_lib_util.make_splunkhome_path(["etc", "apps", "ds_management_app", "lookups","serverclass.csv"])
checkpoint_serverclass_conversion = os.path.join(checkpoint_dir,"checkpoint_serverclass_conversion.txt")

# Define source and destination directories for set_app_checkpoint
apps_tgz_path = splunk_lib_util.make_splunkhome_path(['etc', 'system','static', 'ds_management_app','apps'])
checkpoint_csv = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'app_checkpoint.csv'])
checkpoint_each_app = os.path.join(checkpoint_dir, "checkpoint_each_app.txt")

# Define source and destination directories for push_script
ds_setup_app_dir = splunk_lib_util.make_splunkhome_path(['etc', 'apps', 'ds_management_app', 'data', 'setup_app'])

# Function to copy deployment-apps to ds_app
def copy_apps(override=False):
    paths = read_ds_config()
    src_repository_location = paths['source_repositoryLocation']
    dst_repository_location = paths['dest_repositoryLocation']
    
    if(src_repository_location==dst_repository_location):
        log("INFO", "Source and destination locations are the same. Aborting.")
        return
    
    if os.path.isfile(checkpoint_copy_ds_app):
        log("INFO","Deployment apps is already copied")
        return
    
    # Handle override logic
    if override=="true":
        log("INFO", "Override is True. Clearing destination directory.")
        # Remove the destination directory and recreate it
        if os.path.exists(dst_repository_location):
            shutil.rmtree(dst_repository_location)
        os.makedirs(dst_repository_location, exist_ok=True)
    else:
        # Ensure the destination directory exists
        os.makedirs(dst_repository_location, exist_ok=True)

    os.makedirs(checkpoint_dir, exist_ok=True)

    # Copy all contents from src_dir to dst_dir
    try:
        for item in os.listdir(src_repository_location):
            s = os.path.join(src_repository_location, item)
            d = os.path.join(dst_repository_location, item)
            if os.path.isdir(s):
                # If it's a directory, copy the directory only if override is False and it doesn't already exist
                if not os.path.exists(d) or override=="true":
                    shutil.copytree(s, d)
                else:
                    # If the directory exists, copy files individually
                    for sub_item in os.listdir(s):
                        sub_s = os.path.join(s, sub_item)
                        sub_d = os.path.join(d, sub_item)
                        if os.path.isdir(sub_s):
                            if not os.path.exists(sub_d) or override=="true":
                                shutil.copytree(sub_s, sub_d)
                        else:
                            shutil.copy2(sub_s, sub_d)
            else:
                # Copy files
                shutil.copy2(s, d)
        log("INFO","Deployment apps copied successfully.")
        with open(checkpoint_copy_ds_app, 'w') as fp:
            log("INFO","Checkpoint added for Deployment apps")
            
    except Exception as e:
        log("ERROR",f"Error copying Deployment apps: {e}")
        log("ERROR",traceback.format_exc())
        
        
def read_ds_config():
    try:
        # Check if the file exists
        if not os.path.exists(ds_conf_path):
            return {"error": f"Configuration file not found at {ds_conf_path}"}

        # Read the configuration file
        config = configparser.ConfigParser()
        config.read(ds_conf_path)

        # Check if 'general' section exists
        if 'general' not in config:
            return {"error": "Missing [general] section in the configuration file"}

        # Extract values
        source_repo = config['general'].get('source_repositoryLocation', None)
        dest_repo = config['general'].get('dest_repositoryLocation', None)

        if source_repo is None or dest_repo is None:
            return {"error": "Required keys missing in [general] section"}

        # Return the values
        return {
            "source_repositoryLocation": source_repo,
            "dest_repositoryLocation": dest_repo
        }

    except Exception as e:
        log("ERROR",traceback.format_exc())
        return {"error": f"An error occurred while reading the configuration: {str(e)}"}
    

# Function to convert .conf file to .csv
def convert_conf_to_csv(override):
    if os.path.isfile(checkpoint_serverclass_conversion):
        log("INFO","Serverclass is already copied")
        return
    file_mode='a'
    if override=="true":
        log("INFO", "Override is True. Removing existing serverclass CSV.")
        file_mode='w'
        if os.path.isfile(serverclass_csv_file):
            os.remove(serverclass_csv_file)

    os.makedirs(os.path.dirname(serverclass_csv_file), exist_ok=True) 
    os.makedirs(checkpoint_dir, exist_ok=True)
    # Code to convert .conf file to .csv
    # Initialize data list to hold parsed content
    data = []

    # Regex to match the section headers and key-value pairs
    section_pattern = re.compile(r"\[(.*?)\]")
    kv_pattern = re.compile(r"([^=]+)\s*=\s*(.+)")
    host_pattern = r"^(blacklist|whitelist)(\.from_pathname|\.select_field|\.where_field|\.where_equals)?"

    # Attempt to read and parse the .conf file
    try:
        with open(serverclass_conf_file, 'r') as file:
            serverclass = None
            app = '-'
            for line in file:
                line = line.strip()
                
                # If line is a section header
                section_match = section_pattern.match(line)
                if section_match:
                    section = section_match.group(1)
                    # Parse serverclass and app from section
                    parts = section.split(':')
                    if len(parts)==4:
                        serverclass=parts[1]
                        app=parts[3]
                    elif len(parts)==2:
                        serverclass=parts[1]
                        app="-"
                    else:
                        serverclass="-"
                        app="-"                    
                    continue
                # If line is a key-value pair
                kv_match = kv_pattern.match(line)
                if kv_match:
                    key, value = kv_match.groups()
                    host_match = re.match(host_pattern, key)
                    if host_match:
                        if host_match.group(2):  
                            key=f"{host_match.group(1)}_{host_match.group(2)[1:]}"
                        else:  # Otherwise, it's just blacklist or whitelist
                            key=host_match.group(1)
                    data.append([serverclass, app, key, value])

        # Append or write data to the CSV file
        write_header = override=="true" or not os.path.isfile(serverclass_csv_file)
        
        # Write the parsed data to CSV
        with open(serverclass_csv_file, file_mode, newline='') as file:
            writer = csv.writer(file)
            if write_header:
                writer.writerow(['Serverclass', 'App', 'Key', 'Value'])  # CSV header
            writer.writerows(data)
            
        # After create csv from conf file need below steps.
        extrace_csv()
        create_machine_types_filter_file()
        
        log("INFO", "Conversion of serverclass.conf to serverclass.csv completed successfully.")
        with open(checkpoint_serverclass_conversion, 'w') as fp:
            log("INFO","Checkpoint added for Serverclass conversion")
            
    except Exception as e:
        log("ERROR", f"Error converting .conf file to CSV: {e}")
        log("ERROR",traceback.format_exc())
        

# Function to calculate checksum of all files in a directory
def calculate_directory_checksum(directory):
    hash_md5 = hashlib.md5()
    for root, dirs, files in os.walk(directory):
        for filename in sorted(files):  # Sort files for consistency
            filepath = os.path.join(root, filename)
            with open(filepath, "rb") as f:
                # Update checksum for each file's contents
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Function to calculate checksum of given file
def calculate_file_checksum(file_path):
    """Calculate MD5 checksum of a single file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
      
def get_reload_time():
    try:
        # Read the epoch time from the file
        with open(reload_time_txt, "r") as file:
            epoch_time = int(file.read().strip())  # Convert the string to an integer
        return epoch_time
    except FileNotFoundError:
        log("INFO",f"Error: File {reload_time_txt} not found.")
        return 0
    except ValueError:
        log("INFO",f"Error: Invalid content in {reload_time_txt}. Cannot convert to integer.")
        log("ERROR",traceback.format_exc())
        return 0

def set_reload_time():
    current_epoch_time = int(time.time())
    
    # Write the epoch time to the file
    with open(reload_time_txt, "w") as file:
        file.write(str(current_epoch_time))
    
def is_folder_or_files_modified_after_last_reload(folder_path,reload_time):

    for root, dirs, files in os.walk(folder_path):
        # Check the folder itself
        if reload_time - os.path.getmtime(root) < 0:
            return True
        
        # Check all files in the folder
        for file_name in files:
            file_path = os.path.join(root, file_name)
            if reload_time - os.path.getmtime(file_path) < 0 :
                return True
    
    return False

# Function to compress all directory in ds_apps and move tgz to ~/var/run. 
# Also Update checkpoint.csv
def compress_app_update_checkpoint():
    reload_time = get_reload_time()
    set_reload_time()
    paths = read_ds_config()
    dst_repository_location = paths['dest_repositoryLocation']
    # Initialize list to store checkpoint data for CSV
    os.makedirs(apps_tgz_path, exist_ok=True)  # Ensure output directory exists
    os.makedirs(os.path.dirname(checkpoint_csv), exist_ok=True) 
    os.makedirs(checkpoint_dir, exist_ok=True)
    checkpoint_data = []
    # Process each directory in ds_app
    for app_dir in os.listdir(dst_repository_location):
        full_app_dir = os.path.join(dst_repository_location, app_dir)
        if os.path.isdir(full_app_dir):  # Ensure it's a directory
            tarball_path = os.path.join(apps_tgz_path, f"{app_dir}.tgz")
            if not is_folder_or_files_modified_after_last_reload(full_app_dir,reload_time):
                checksum = calculate_file_checksum(tarball_path)
                checkpoint_data.append([app_dir, checksum])
                continue

            # Compress the directory into a .tgz file
            with tarfile.open(tarball_path, "w:gz") as tar:
                tar.add(full_app_dir, arcname=app_dir)
            log("INFO",f"Processed and compressed {app_dir} successfully.")
            
            # Calculate checksum
            checksum = calculate_file_checksum(tarball_path)
            
            # Store checksum data for CSV file
            checkpoint_data.append([app_dir, checksum])

    # Write all checksums to the CSV file
    with open(checkpoint_csv, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['app_name', 'checkpoint'])  # Write header
        writer.writerows(checkpoint_data)  # Write checkpoint data
    log("INFO", "compressed app and updated checkpoint.")
    
def set_app_checkpoint():
    if os.path.isfile(checkpoint_each_app):
        log("INFO","Checkpoint for each app is already created")
        return
    
    compress_app_update_checkpoint()
    
    with open(checkpoint_each_app, 'w') as fp:
        log("INFO","Checkpoint for each app added successfully.")
        pass
    log("INFO","Checksum and compression process completed successfully.")
        
# Function to create serverclass and push setup apps in the serversclass
def push_script():
    paths = read_ds_config()
    src_repository_location = paths['source_repositoryLocation']
    
    
    # Ensure the deployment directory exists
    os.makedirs(ds_setup_app_dir, exist_ok=True)
    os.makedirs(src_repository_location, exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    try:        
        for file_name in os.listdir(ds_setup_app_dir):
            if file_name.endswith(".tgz"):
                file_path = os.path.join(ds_setup_app_dir, file_name)
                app_name = file_name.rsplit('.', 1)[0]  # Extract app name by removing the .tgz extension
                app_deployment_path = os.path.join(src_repository_location, app_name)
                
                # Remove existing app directory if it exists
                if os.path.exists(app_deployment_path):
                    shutil.rmtree(app_deployment_path)
                    log("INFO",f"Removed existing app directory: {app_deployment_path}")
                
                # Extract the .tgz file to the deployment directory
                with tarfile.open(file_path, "r:gz") as tar:
                    tar.extractall(path=src_repository_location)
                    log("INFO",f"Extracted {file_name} to {src_repository_location}")
                           
      
        log("INFO","Successfully added setup app for DS")
                  
        
    except Exception as e:
        log("ERROR", f"Error while adding setup apps :{e}")
        log("ERROR",traceback.format_exc())

