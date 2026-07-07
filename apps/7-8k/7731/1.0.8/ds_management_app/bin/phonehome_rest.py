import sys, os,traceback,time
sys.path.append(os.path.dirname(__file__))
import sa_import
import json, threading
from ds_utils import log, get_apps_for_input, get_apps_checkpoint,update_csv_file
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

apps_download_list_dir = splunk_lib_util.make_splunkhome_path(['etc', 'system','static', 'ds_management_app','apps_download_list'])
runtime_serverclass = splunk_lib_util.make_splunkhome_path(['var', 'run', 'ds_management_app', 'lookups', 'serverclass.csv'])

class DCStatusHandler(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    
    def handle(self, in_string):
        
        result_event = threading.Event()
        result_container = {}
        # Create a new thread for each request
        thread = threading.Thread(target=self.process_request, args=(in_string, result_container, result_event))
        thread.start()

        # Wait for the thread to finish processing
        result_event.wait()

        # Return the result captured from the thread
        return result_container.get("result", {"payload": {"error": "Processing failed", "status": 500}})

    def process_request(self, in_string, result_container, result_event):
        
        try:
            payload={}
            
            data=json.loads(in_string)
            dc = data.get("connection", {}).get("src_ip",{})
            uf_name = data.get("form")
            # uf_name=[["0","win_1"],["1","win_2"]]
            log("INFO", "Getting phonehome from deployment client: "+str(dc))
            uf_names={name[0]:name[1] for name in uf_name}
            uf_names["ip"]=dc
            current_time = int(time.time())
            update_csv_file("dc_info_csv",f"{current_time},{uf_names['guid']},{uf_names['ip']},{uf_names['private_ip']},{uf_names['hostname']},{uf_names['servername']},{uf_names['os']},{uf_names['clientname']}")
            log("INFO",f"Stored client info: {dc}")
            required_unique_keys=[uf_names["clientname"],uf_names["ip"],uf_names["hostname"],uf_names["servername"]]
            required_apps = get_apps_for_input(required_unique_keys, runtime_serverclass, uf_names['os'],uf_names['guid'])
            
            apps_with_checkpoint=get_apps_checkpoint(list(required_apps))
            log("INFO","List of apps is ready. Sending to DC...")

            os.makedirs(apps_download_list_dir, exist_ok=True)
            make_name= f"{uf_names['guid']}__{uf_names['private_ip']}__{uf_names['hostname']}__{uf_names['os']}.txt"
            client_file_name = os.path.join(apps_download_list_dir,make_name)
            

            with open(client_file_name, "w") as log_file:
                for key, value in apps_with_checkpoint.items():
                    log_file.write(f"{key},{value}\n")

            payload={}
            payload["info"] = "Success"
            payload["status"] = 200
        except Exception as e:
            log("ERROR", f"Failed to process phonehome request: {str(e)}")
            log("ERROR",traceback.format_exc())
            payload["error"] = "Error while processing your request. Please check logs on deployment server"
            payload["status"] = 500

        # Store the result and set the event to notify the main thread
        result_container["result"] = {"payload": payload}
        result_event.set()
        