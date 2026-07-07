import sys, os, traceback
import time
from datetime import datetime
sys.path.append(os.path.dirname(__file__))
import json, threading
from ds_utils import log,update_csv_file
from splunk.persistconn.application import PersistentServerConnectionApplication

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
            dc_info = data.get("form")
            # dc_info=[["0","win_1"],["1","win_2"]]
            log("INFO", f"Getting call from deployment client: {str(dc)} - to save app information")
            app_data={name[0]:name[1] for name in dc_info}

            # for key in app_data:
            #     if key in ["current_time","script_start_time", "phonehome_complete_time", "app_download_complete_time", "script_end_time"]:            
            #         if app_data[key]:  # Check if the value is not empty or None
            #             try:
            #                 dt_object = datetime.strptime(app_data[key], "%Y-%m-%d %H:%M:%S")
            #                 app_data[key] = int(time.mktime(dt_object.timetuple()))
            #             except ValueError as e:
            #                 app_data[key]=""
            #                 log("ERROR",f"Error parsing datetime for key '{key}': {e}")  
            for key in app_data:
                app_data[key] = app_data.get(key, "")  
                                
            update_csv_file("dc_app_status_csv", f"{app_data['current_time']},{dc},{app_data['guid']},{app_data['script_start_time']},{app_data['phonehome_complete_time']},{app_data['app_download_complete_time']},{app_data['script_end_time']},\"{app_data['installed_apps']}\",\"{app_data['failed_apps']}\"")
            

            payload["info"] = "Success"
            payload["status"] = 200
            log("INFO",f"Successfully saved app information for deployment client: {str(dc)}")

        except Exception as e:
            log("ERROR", f"Failed to process request - save DC info: {str(e)}")
            log("ERROR",traceback.format_exc())
            payload["error"] = "Error while processing your request. Please check logs on deployment server"
            payload["status"] = 500

        # Store the result and set the event to notify the main thread
        result_container["result"] = {"payload": payload}
        result_event.set()