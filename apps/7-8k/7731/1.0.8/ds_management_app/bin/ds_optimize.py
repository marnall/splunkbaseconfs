import sys,traceback
from ds_utils import log,dc_info_lock_file,dc_app_status_lock_file,dc_phonehome_time_lock_file,dc_serverclass_mapping_lock_file
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
import splunklib.client as client
import splunklib.results as results
from filelock import FileLock


def run_locked_search(service, query, lock_file):
    """
    Executes a search query with file locking to ensure concurrency control.
    """
    lock = FileLock(lock_file)
    try:
        with lock.acquire(timeout=300):  # Wait up to 10 seconds for the lock
            search_results = service.jobs.oneshot(query)
            return search_results
            
    except TimeoutError:
        log("ERROR", f"Timeout occurred while waiting for lock: {lock_file}")
        log("ERROR", traceback.format_exc())
    except Exception as e:
        log("ERROR", f"An error occurred during search execution: {str(e)}")
        log("ERROR", traceback.format_exc())
    

    
@Configuration()
class DSOptimize(GeneratingCommand):

    def generate(self):
        try:
            # Retrieve the session key
            session_key = self.metadata.searchinfo.session_key
            splunk_host = self.metadata.searchinfo.splunkd_uri.split("://")[1].split(":")[0]
            splunk_port = int(self.metadata.searchinfo.splunkd_uri.split(":")[-1])

            # Connect to Splunk using the session key
            service = client.connect(
                token=session_key,
                host=splunk_host,
                port=splunk_port      
            )
            searches = {
                "dc_info": {
                    "query": "| inputlookup dc_info.csv \
                        | stats latest(*) as * latest(_time) as _time by guid ip \
                        | table _time,guid,ip,private_ip,hostname,servername,os,clientname \
                        | outputlookup dc_info.csv",
                    "lock_file": dc_info_lock_file
                },
                "dc_app_status": {
                    "query": "| inputlookup dc_app_status.csv\
                        | stats latest(*) as * latest(_time) as _time by guid, ip \
                        | table _time,ip,guid,script_start_time,phonehome_complete_time,app_download_complete_time,script_end_time,installed_apps,failed_apps \
                        | outputlookup dc_app_status.csv",
                    "lock_file": dc_app_status_lock_file
                },
                "dc_phonehome_time": {
                    "query": "| inputlookup dc_phonehome_time.csv\
                        | stats latest(*) as * latest(_time) as _time by guid ip hostname\
                        | table _time,guid,ip,hostname,os\
                        | outputlookup dc_phonehome_time.csv",
                    "lock_file": dc_phonehome_time_lock_file
                },
                "dc_app_status_time": {
                    "query": "| inputlookup dc_serverclass_mapping.csv\
                        | stats latest(*) as * latest(_time) as _time by guid ip\
                        | table _time,guid,clientname,ip,hostname,servername,serverclass_list,apps_list\
                        | outputlookup dc_serverclass_mapping.csv",
                    "lock_file": dc_serverclass_mapping_lock_file
                }
            }
                
            # Execute each search with its corresponding lock file
            for name, search_details in searches.items():
                try:
                    run_locked_search(service, search_details["query"], search_details["lock_file"])
                    log("INFO", f"Search '{name}' completed successfully.")
                except Exception as search_error:
                    log("ERROR", f"Error executing search '{name}': {search_error}")
                    log("ERROR", traceback.format_exc())

            yield {"status": "success", "message": "All searches completed successfully."}

        except Exception as e:
            log.error("Error running search: %s" % e)
            log("ERROR", traceback.format_exc())
            yield {"status": "error", "message": f"An error occurred: {str(e)}"}


dispatch(DSOptimize, sys.argv, sys.stdin, sys.stdout, __name__)