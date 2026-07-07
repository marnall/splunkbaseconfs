from Constants import * 
from manageengine_ec_utils import *
from datetime import datetime 
import json
import time
import datetime
import math
import os
from manageengine_ec_data_collector_audit_service import *

class ECDataCollector():
    def __init__(self, helper, ew) -> None:
        self.helper = helper
        self.event_writer = ew

    def collect_module_data(self):
        syncStatus = None
        remarks = None
        self.helper.log_info("From collect Module Data")
        
        if not self.check_if_sync_running():
            self.helper.log_warning("-------------- Sync Started -----------------")
            input_module = self.helper.get_input_type()
            now = math.trunc(time.time() * 1000)
            self.helper.log_warning("Sync Start Time for the input module"+input_module + str(now))
            input_name = self.helper.get_input_stanza_names()
            
            status_check_point = input_name + "_" + SYNC_STATUS_CHECK_POINT

            self.helper.save_check_point(status_check_point, 'Started')
            
           

            # Checking if user has configured any custom settings in default/custom.conf
            if input_module == VULNERABILITY_MODULE:
                self.check_custom_configs()
                 # Updating Configuration details in Endpoint Central Server

            set_input_details(self.helper)
            response = self.update_configuration_data()      
            if input_module == AUDIT_MODULE and response is not None:
                self.helper.log_info("Audit Module is enabled in the input stanza")
                self.helper.log_info(response)
                if "status" in response:
                    if "buildNumber"  not in response:
                        self.helper.log_error("Audit Module is not supported in this version of Endpoint Central Server. Please upgrade to the latest version. So going to disable the Audit Module Input")
                        self.enabledOrdisableAuditModuleInput(is_enabled=False, input_name=input_name)
                        self.helper.save_check_point("audit_module_disabled","true")
                        self.update_sync_status("autodisable", "Audit Module is not supported in this version of Endpoint Central Server.") 
                        return
                    else:
                        if self.helper.get_check_point("audit_module_disabled") == "true":
                            self.helper.log_info("Audit Module is supported in this version of Endpoint Central Server. So enabling the Audit Module Input")
                            self.enabledOrdisableAuditModuleInput(is_enabled=True,input_name=input_name)
                            self.helper.delete_check_point("audit_module_disabled")
                

            # Depending on the module, data collection will be redirected
            self.helper.log_info("Entering into the module: " + input_module)
            if input_module == VULNERABILITY_MODULE:
                if not self.update_input_data(VULNERABILITY_MODULE_ID, "false") == "skip":
                    syncStatus, remarks = self.vulnerability_data_collector(VULNERABILITY_MODULE_ID)
                    # Updating Sync Status
                    self.update_sync_status(syncStatus, remarks)
                    self.helper.delete_check_point(status_check_point)
                    now = math.trunc(time.time() * 1000)
                    self.helper.log_warning("Sync End Time for the input module "+input_module + str(now))

            elif input_module == AUDIT_MODULE:
                if not self.update_input_data(AUDIT_MODULE_ID, "false") == "skip":
                    input_details = self.helper.get_input_stanza()
                    interval = input_details[input_name][INTERVAL]
                    lastUpdatedTime = self.helper.get_check_point(END_TIME)
                    if lastUpdatedTime:
                        self.helper.log_info("Last Updated Time: " + str(lastUpdatedTime))
                        self.helper.log_info("Interval: " + str(interval))
                        startTime  = lastUpdatedTime
                        endTime = int(time.time() * 1000)
                    else:
                        endTime = int(time.time() * 1000)
                        startTime = endTime - int(interval) * 1000
                   
                    
                    startTimestamp = datetime.fromtimestamp(int(startTime) / 1000).strftime("%Y-%m-%d %H:%M:%S")
                    endTimestamp = datetime.fromtimestamp(int(endTime) / 1000).strftime("%Y-%m-%d %H:%M:%S")

                    self.helper.log_info(f"Fetching Audit Data from EC server between: {startTimestamp} → {endTimestamp}") 
                    status,remark = fetchAuditData(self.helper,self.event_writer,startTime,endTime,AUDIT_API)
                    self.helper.log_info("Audit Data Collection Status: " + str(status) + " Remark: " + str(remark))
                    
                    now = math.trunc(time.time() * 1000)
                    if status == SUCCESS:
                       self.helper.save_check_point(END_TIME,endTime) 
                       remark =now
                    else:
                        if not lastUpdatedTime:
                            self.helper.save_check_point(END_TIME,endTime) 
                    self.update_sync_status(status, remark)               
                    # Collecting Audit Data
                    self.helper.log_warning("Sync End Time for the input module "+input_module + str(now))
        else:
            self.helper.log_warning("Sync skipped")



        
    
    def check_if_sync_running(self):
        try:
            input_name = self.helper.get_input_stanza_names()
            status_check_point = input_name + "_" + SYNC_STATUS_CHECK_POINT
            self.helper.delete_check_point(status_check_point)
            if self.helper.get_check_point(status_check_point) == None:
                return False
            else:
                return True
        except Exception as error:
            self.helper.log_error('Error occurred in check_if_sync_running' + str(error))
            return False


    def check_custom_configs(self):
        self.helper.log_info("------------ Checking for custom configs --------------")
        try:
            input_name = self.helper.get_input_stanza_names()
            vuln_check_point = input_name + "_" + VULNERABILITY_MODULE
            vulnerabilityStatus = ["open", "closed"]
            current_working_directory = os.path.dirname(os.path.abspath(__file__))
            os_name = os.name
            system_name = platform.system()

            conf_file_path = str(current_working_directory) + "\\..\\default\custom.conf"
            # Checking the OS to see if its linux, if so, then we change the path traversal format
            if os_name == 'posix' or system_name == 'Linux':
                conf_file_path = str(current_working_directory) + "/../default/custom.conf"

            parseLines = False

            if not os.path.exists(conf_file_path):
                self.helper.log_info(str(conf_file_path) + " File Dosen't exist")
                return
            
            with open(conf_file_path, 'r') as file:
                # Read all lines from the file
                lines = file.readlines()

            # Loop through the lines and replace the specified text
            with open(conf_file_path, 'w') as file:
                for line in lines:
                    # Initate Full Sync Check
                    if "manageengine:ec:vulnerability" in str(line):
                        parseLines = True
                    if parseLines:
                        keyValuePairs = line.split("=")
                        if "initiate_full_sync" in str(keyValuePairs[0]) and "True" in str(keyValuePairs[1]):
                            for status in vulnerabilityStatus:
                                self.helper.delete_check_point(vuln_check_point + "_" + status)
                            line = line.replace('True', 'False')
                            self.helper.log_info("------------ Full Sync Initiated --------------")
                    file.write(line)
        except Exception as error:
            self.helper.log_error('Error occurred in check_custom_configs' + str(error))


    # Collecting data of both open and closed vulnerabilities
    def vulnerability_data_collector(self, module_id):
        try:
            vulnerabilityStatus = ["open", "closed"]
            payload = None
            syncStatus = ""
            remarks = ""
            vuln_api_details = self.get_api_details(module_id)

            if "api" not in vuln_api_details:
                if ERROR_MSG in vuln_api_details:
                    return FAILURE, vuln_api_details[ERROR_MSG]
                else:
                    return FAILURE, str(vuln_api_details)

            vuln_api = vuln_api_details["api"][1:]
            vuln_api_url = construct_url(self.helper, vuln_api)
            for status in vulnerabilityStatus:
                payload = {}
                payload["vulnerabilityStatus"] = status
                syncStatus, remarks = self.collect_vuln_data(module_id, payload, vuln_api_url)
            return str(syncStatus), str(remarks)
        except Exception as error:
            self.helper.log_error('Error occurred in vulnerability_data_collector' + str(error))
            return FAILURE, 'Error occurred in vulnerability_data_collector'



    #  We will use APIDETAILS API to fetch the vulnerabilities API from EC Server
    #  Using the vulnerabilities API we will fetch the vulnerability data
    #  We will parse the Json data and post it as events
    def collect_vuln_data(self, module_id, payload, vuln_api_url):
        self.helper.log_info("------------ Vulnerability Data Collection Started for status: " + str(payload["vulnerabilityStatus"]) + "-----------------------")
        hitAPI = True
        lockoutCounter = 0
        prevMetaData = ""
        apiHitCount = 0
        try:
            input_name = self.helper.get_input_stanza_names()
            status = payload["vulnerabilityStatus"]
            while hitAPI:
                apiHitCount += 1
                vuln_check_point = input_name + "_" + VULNERABILITY_MODULE + "_" + status
                updatedtime = self.helper.get_check_point(vuln_check_point)
                if updatedtime != None:
                    payload["updatedTime"] = updatedtime
                response = construct_endpoint(helper=self.helper, url=vuln_api_url, method=METHOD_GET, payload=payload)
                response = json.loads(response.content.decode())
                if ERROR_MSG in response:
                    self.helper.log_error("Error: " + response[ERROR_MSG])
                    hitAPI = False
                elif ERRORCODE in response:
                    self.helper.log_error("Error Code: " + str(response[ERRORCODE]) + "  Error Description: " + response[ERROR_MSG])
                    time.sleep(360)
                    lockoutCounter += 1
                    if lockoutCounter > 20:
                        hitAPI = False
                        self.helper.log_error("Error Code: Failure,  Error Description: API locked out more than 20 times, Increase API threshold")
                        return FAILURE, "API locked out more than 20 times, Increase API threshold"
                elif ERROR_CODE in response[META_DATA]:
                    if "204" in str(response[META_DATA][ERROR_CODE]):
                        hitAPI = False
                        now = math.trunc(time.time() * 1000)
                        return SUCCESS, str(now)
                    self.helper.log_error("Error Code: " + str(response[META_DATA][ERROR_CODE]) + "  Error Description: " + response[META_DATA]["error_description"])
                    hitAPI = False
                    return FAILURE, str(response[META_DATA][ERROR_CODE]) + ": " + response[META_DATA]["error_description"]
                else:
                    process_module_data(self.helper, self.event_writer, response["message_response"]["data"], module_id, response[META_DATA], status, prevMetaData)
                    payload["cursor"] = response[META_DATA]["cursor"]
                    prevMetaData = response[META_DATA]
                    hitAPI = True if response[META_DATA]["isNextPageAvailable"] == True or response[META_DATA]["isNextPageAvailable"] == "True" or response[META_DATA]["isNextPageAvailable"] == "true" else False
                    self.helper.log_info("IsnextPageAvailable :" + str(hitAPI))
            now = math.trunc(time.time() * 1000)
            self.helper.log_info("Api Hit Count: " + str(apiHitCount))
            return SUCCESS, str(now)
        except Exception as error:
            hitAPI = False
            self.helper.log_error('Error occurred in collect_vuln_data' + str(error))
            return FAILURE, "Error occurred in collect_vuln_data"


    # Depending upon the module id, we will fetch the module API from EC Server
    def get_api_details(self, module_id):
        self.helper.log_info("------------ In Get API Details --------------")
        try:
            delimiter = "/"
            apidetails_api = delimiter.join([EC_API_CATEGORY, INTEGRATIONS, SPLUNK, APIDETAILS])
            apidetails_url = construct_url(self.helper, apidetails_api)
            payload = {}
            payload["module_id"] = module_id
            response = construct_endpoint(helper=self.helper, url=apidetails_url, method=METHOD_GET, payload=payload)
            return json.loads(response.content.decode())
        except Exception as error:
            self.helper.log_error('Error occurred in get_api_details' + str(error))
    


    # Checking if the input configured in EC server, still exists in Splunk
    def check_if_input_exists(self, configured_input_name, module_id):
        try:
            current_working_directory = os.path.dirname(os.path.abspath(__file__))
            os_name = os.name
            system_name = platform.system()
            input_file_paths = [str(current_working_directory) + "\\..\\default\inputs.conf", str(current_working_directory) + "\\..\\local\inputs.conf"]

            # Checking the OS to set certificate in ec.ca-bundle
            if os_name == 'posix' or system_name == 'Linux':
                input_file_paths = [str(current_working_directory) + "/../default/inputs.conf", str(current_working_directory) + "/../local/inputs.conf"]
            
            inputs_path = None
            for input_file_path in input_file_paths:
                if os.path.exists(input_file_path):
                    inputs_path = input_file_path
                    break
            
            if inputs_path == None:
                return "false"
            
            input_entry = "[" + get_input_name(module_id) + "://" + configured_input_name + "]"
            with open(inputs_path, 'r') as file:
                for line in file:
                    if input_entry in str(line):
                        return "true"
            return "false"
        except Exception as error:
            self.helper.log_error('Error occurred in check_if_input_exists' + str(error))
            return "false"

    # Update input details in EC Server
    def update_input_data(self, module_id, update_flag):    
        self.helper.log_info("------------ In Update Input Data --------------")
        try:
            delimiter = "/"
            input_integration_api = delimiter.join([EC_API_CATEGORY, INTEGRATIONS, SPLUNK, INTEGRATION])
            input_integration_url = construct_url(self.helper, input_integration_api)
            input_details = self.helper.get_input_stanza()
            
            try:
                input_name = self.helper.get_input_stanza_names()
            except Exception as error:
                self.helper.log_error('Error occurred in update_input_data while fetching input name: ' + str(error))
                self.helper.log_error(traceback.format_exc())
                return "skip"
            
            payload = {}
            payload["input_name"] = input_name
            payload["module_id"] = module_id
            payload["interval"] = input_details[input_name][INTERVAL]
            payload["config_name"] = input_details[input_name][GLOBAL_ACCOUNT][NAME]
            payload["update_flag"] = update_flag
            response = construct_endpoint(helper=self.helper, url=input_integration_url, method=METHOD_POST, payload=payload)
            response = json.loads(response.content.decode())
            self.helper.log_info("Response from EC Server: " + str(response))
            # Same Input - Unchanged
            if "status" not in response:
                self.helper.log_info("Input insertion skipped")
                return "continue"
            else:
                # Input first time insertion
                if response["status"] == SUCCESS:
                    self.helper.log_info("Status: " + response["status"] + " : Message: " + response["message"] + " for the module: " + self.helper.get_input_type())
                    return "continue"
                #  Same Input Updated / Diff input - Same config, server 
                elif response["status"] == ERROR:
                    if "configured_input_name" in response:
                        configured_input_name = response["configured_input_name"]
                        if self.check_if_input_exists(configured_input_name, module_id) == "true":
                            self.helper.log_error(get_input_name(module_id) + " " + response["message"])
                            return "skip"
                        else:
                            return self.update_input_data(module_id, "true")
                    else:
                        self.helper.log_error(get_input_name(module_id) + " " + response["message"])
                        return "skip"
        except Exception as error:
            self.helper.log_error('Error occurred in update_input_data' + str(error))
            self.helper.log_error(error)
            return "skip"


    # Update configuration details in EC Server
    def update_configuration_data(self):
        self.helper.log_info("------------ In Update Config Data --------------")
        try:
            stanza_details = get_input_details()
            input_name = stanza_details["input_name"]
            config_name = stanza_details[input_name][GLOBAL_ACCOUNT][NAME]
            delimiter = "/"
            configuration_api = delimiter.join([EC_API_CATEGORY, INTEGRATIONS, SPLUNK, CONFIGURATION])
            configuration_url = construct_url(self.helper, configuration_api)
            payload = {}
            payload["config_name"] = config_name
            if stanza_details[input_name][GLOBAL_ACCOUNT][SERVER_TYPE] == OP_SERVER:
                payload["productCode"] = "DCEE"
            else:
                payload["productCode"] = "DCODEE"
            response = construct_endpoint(helper=self.helper, url=configuration_url, method=METHOD_POST, payload=payload)
            response = json.loads(response.content.decode())
            if "message" in response:
                self.helper.log_info("Status: " + response["status"] + " : Message: " + response["message"])
            return response
        except Exception as error:
            self.helper.log_error('Error occurred in update_configuration_data')
            self.helper.log_error(error)
    

    # After all the data has been fetched from EC Server, we will post this Sync API to update the status of the sync
    def update_sync_status(self, status, remarks):
        self.helper.log_info("------------ Updating Sync Status --------------")
        try:
            delimiter = "/"
            sync_status_api = delimiter.join([EC_API_CATEGORY, INTEGRATIONS, SPLUNK, STATUS])
            sync_status_url = construct_url(self.helper, sync_status_api)
            input_name = self.helper.get_input_stanza_names()
            payload = {}
            payload["status"] = status
            payload["remarks"] = remarks
            payload["input_name"] = input_name
            if status =="autodisable":
                payload["status"] = FAILURE
         
            response = construct_endpoint(helper=self.helper, url=sync_status_url, method=METHOD_POST, payload=payload)
            response = json.loads(response.content.decode())
            if ERRORCODE in str(response):
                self.helper.log_error("Sync Status: " + str(response[ERROR_MSG]))
        except Exception as error:
            self.helper.log_error('Error occurred in update_sync_status' +  str(error))




    def enabledOrdisableAuditModuleInput(self, is_enabled, input_name):
        """
        Enable or disable the audit module input in inputs.conf file
        
        Args:
            is_enabled (bool): True to enable, False to disable
            input_name (str): Name of the input to enable/disable
        """
        try:
            current_working_directory = os.path.dirname(os.path.abspath(__file__))
            os_name = os.name
            system_name = platform.system()
            inputconf_path = None
            
            # Set path based on OS
            if os_name == 'nt' or system_name == 'Windows':
                inputconf_path = os.path.join(current_working_directory, "..", "local", "inputs.conf")
            elif os_name == 'posix' or system_name == 'Linux':
                inputconf_path = os.path.join(current_working_directory, "..", "local", "inputs.conf")
            else:
                self.helper.log_error('Unrecognized operating system: ' + str(system_name))
                return
            
            inputconf_path = os.path.abspath(inputconf_path)
            
            # Check if file exists
            if not os.path.exists(inputconf_path):
                self.helper.log_error('inputs.conf file not found at: ' + inputconf_path)
                return
            
            # Read the file
            with open(inputconf_path, 'r') as f:
                lines = f.readlines()
            
            updated_lines = []
            target_stanza = f"[endpointcentral_actionlog://{input_name}]"
            in_target_stanza = False
            stanza_found = False
            
            for line in lines:
                stripped_line = line.strip()
                
                # Check if we're entering the target stanza
                if stripped_line == target_stanza:
                    in_target_stanza = True
                    stanza_found = True
                    updated_lines.append(line)
                # Check if we're entering a different stanza
                elif stripped_line.startswith("[") and stripped_line.endswith("]"):
                    in_target_stanza = False
                    updated_lines.append(line)
                # If we're in the target stanza and find the disabled line
                elif in_target_stanza and stripped_line.startswith("disabled"):
                    if is_enabled:
                        updated_lines.append("disabled = 0\n")
                        self.helper.log_info(f"Enabled audit module input: {input_name}")
                    else:
                        updated_lines.append("disabled = 1\n")
                        self.helper.log_info(f"Disabled audit module input: {input_name}")
                else:
                    updated_lines.append(line)
            
            if not stanza_found:
                self.helper.log_warning(f"Audit module input stanza not found: {target_stanza}")
                return
            
            # Write the updated content back to the file
            with open(inputconf_path, 'w') as f:
                f.writelines(updated_lines)
                
            self.helper.log_info(f"Successfully updated inputs.conf for audit module: {input_name}")
            
        except Exception as e:
            self.helper.log_error(f'Error occurred in enabledOrdisableAuditModuleInput: {str(e)}')

