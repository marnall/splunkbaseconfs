# ds_reload.py
import splunk.Intersplunk
import csv, os,platform, traceback
import shutil, time, sys
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from ds_utils import log,get_apps_for_input,get_apps_checkpoint
from setup import compress_app_update_checkpoint,serverclass_csv_file, create_machine_types_filter_file
from ds_utils import dc_info_csv
from extract_csv_parms import extrace_csv
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

apps_download_list_dir = splunk_lib_util.make_splunkhome_path(['etc', 'system', 'static', 'ds_management_app','apps_download_list'])
temp_apps_download_list_dir = splunk_lib_util.make_splunkhome_path(['var','run','ds_management_app','temp_apps_download_list'])
temp_dc_info_csv = splunk_lib_util.make_splunkhome_path(['var','run','ds_management_app', 'lookups','dc_info_csv.csv'])

RELOAD_SUMMARY=[]

def is_within_last_24_hours(epoch_time):
    try:
        current_time = int(time.time())
        twenty_four_hours_ago = current_time - 24 * 60 * 60
        return epoch_time >= twenty_four_hours_ago
    except Exception as e:
        splunk.Intersplunk.outputResults([{"status":"error","_raw": "ERROR in Lookup file dc_info.csv: _time is not in int formate"}])
        return False

def get_dynamic_max_workers():
    """Determine max_workers based on the OS and CPU cores."""
    try:
        cpu_cores = cpu_count()
        if platform.system() == "Windows":
            return max(2, cpu_cores)  # At least 2 workers, up to the number of cores
        else:
            return max(2, cpu_cores * 2)  # At least 2 workers, up to double the number of cores
    except Exception as e:
        return 4  # Default core
    
def process_row(row):
    try:
        if is_within_last_24_hours(int(row["_time"])):
            required_unique_keys = [row["guid"], row["ip"], row["hostname"], row["servername"]]
            required_apps = get_apps_for_input(required_unique_keys, serverclass_csv_file, row['os'],row["guid"])
            apps_with_checkpoint = get_apps_checkpoint(list(required_apps))

            make_name = f"{row['guid']}__{row['private_ip']}__{row['hostname']}__{row['os']}.txt"
            client_file_name = os.path.join(temp_apps_download_list_dir, make_name)
            
            with open(client_file_name, "w") as log_file:
                for key, value in apps_with_checkpoint.items():
                    log_file.write(f"{key},{value}\n")
        else:
            RELOAD_SUMMARY.append(f"Ignoring UF {row['hostname']} due to outdated time: {row['_time']}")
            log("WARN",f"Ignoring UF {row['hostname']} due to outdated time: {row['_time']}")
    except Exception as e:
        log("ERROR", f"Error processing row: {row} - {str(e)}")
        log("ERROR",traceback.format_exc())
        splunk.Intersplunk.outputResults([{"status":"error","_raw": f"Error processing row: {row} - {str(e)}"}])
        


def copy_files_to_tmp_location():
    
    try:
        # Copy the CSV file to the temporary location
        os.makedirs(os.path.dirname(dc_info_csv), exist_ok=True) 
        if not os.path.exists(dc_info_csv):
            with open(dc_info_csv, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["_time","guid","ip","private_ip","hostname","servername","os","clientname"]) 
        shutil.copy(dc_info_csv, temp_dc_info_csv)
        # log("INFO", f"Copied {dc_info_csv} to {temp_dc_info_csv}")
        log("INFO","Copied all UFs data to temporary location")

        os.makedirs(temp_apps_download_list_dir, exist_ok=True)
        # log("INFO", f"Temporary directory for .txt files: {temp_apps_download_list_dir}")
        log("INFO","Temporary directory to store .txt files is created")

        max_workers = get_dynamic_max_workers()
        log("INFO", f"Using {max_workers} threads for processing")
        
        # Read and process CSV rows concurrently
        with open(temp_dc_info_csv, mode='r') as csvfile:
            reader = csv.DictReader(csvfile)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                executor.map(process_row, reader)

        # Clear the original directory and move files
        if os.path.exists(apps_download_list_dir):
            shutil.rmtree(apps_download_list_dir)
        os.makedirs(apps_download_list_dir, exist_ok=True)

        for file_name in os.listdir(temp_apps_download_list_dir):
            if os.path.exists(os.path.join(apps_download_list_dir, file_name)):
                continue
            else:
                shutil.move(os.path.join(temp_apps_download_list_dir, file_name), apps_download_list_dir)
        
    except Exception as e:
        log("ERROR", "Error in deployment server reload")
        log("ERROR", str(e))
        log("ERROR",traceback.format_exc())
        splunk.Intersplunk.generateErrorResults([{"status":"error", "_raw": f'Error: {str(e)}', "summary":RELOAD_SUMMARY }])

    finally:
        # Clean up temporary files and directories
        if os.path.exists(temp_dc_info_csv):
            os.remove(temp_dc_info_csv)
        if os.path.exists(temp_apps_download_list_dir):
            shutil.rmtree(temp_apps_download_list_dir)

@Configuration()
class ReloadDS(GeneratingCommand):
    softReload=Option(require=False,default="False")

    def generate(self):
        try:
            log("INFO", "Reload deployment server is in progress...")
            if self.softReload.lower()!="true":
                compress_app_update_checkpoint()
            extrace_csv()
            create_machine_types_filter_file()
            copy_files_to_tmp_location()
            log("INFO", "Successfully reloaded deployment server !!!")
            yield {"status":"success", "_raw": "Successfully reloaded deployment server","summary":RELOAD_SUMMARY }
        
        except Exception as e:
            log("ERROR", "Error in deployment server reload")
            log("ERROR", str(e))
            log("ERROR",traceback.format_exc())
            yield {"status":"error", "_raw": f'Error: {str(e)}', "summary":RELOAD_SUMMARY }


dispatch(ReloadDS, sys.argv, sys.stdin, sys.stdout, __name__)
