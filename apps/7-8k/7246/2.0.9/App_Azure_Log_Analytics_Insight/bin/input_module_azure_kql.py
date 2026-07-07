# encoding = utf-8

import requests
import json
import os
import sys
import threading
import logging
from msal import ConfidentialClientApplication
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler
import datetime
import time

if os.name == 'posix':
    SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '/opt/splunk/')
elif os.name == 'nt':
    SPLUNK_HOME = os.environ.get('SPLUNK_HOME', 'C:\\Program Files\\Splunk\\')
else:
    SPLUNK_HOME = os.environ.get('SPLUNK_HOME', '/Applications/Splunk/')

CHECKPOINT_DIR = os.path.join(SPLUNK_HOME, 'etc', 'apps', 'App_Azure_Log_Analytics_Insight', 'checkpoint')
CHECKPOINT_FILE_PREFIX = "checkpoint_"
AUTHOR_NAME_ = '01001011 01110010 01100001 01101110 01110100 01101000 01101001 00100000 01001011 01100001 01101110 01100001 01110000 01100001 01101100 01100001'
author_name = ''.join(chr(int(binary, 2)) for binary in AUTHOR_NAME_.split())
if author_name != "Kranthi Kanapala":
    sys.exit("Verify, an error doth arise due to an invalid author name. Alas! The script is unable to run in this state.")

def validate_input(helper, definition):

    azure_account = definition.parameters.get('azure_account', None)
    workspace_app_id = definition.parameters.get('workspace_app_id', None)
    table_name = definition.parameters.get('table_name', None)
    query = definition.parameters.get('query', None)
    input_name = definition.parameters.get('name', None)
    sourcetype = definition.parameters.get('sourcetypes', None)
    pass

def get_latest_checkpoint(result, input_name):
    latest_checkpoint = None
    earliest_checkpoint = None
    try:
        if isinstance(result, str):
            result = json.loads(result)

        if isinstance(result, dict):
            tables = result.get("tables")
            if tables and len(tables) > 0:
                columns = tables[0].get("columns")
                if columns:
                    time_generated_column = next((column for column in columns if column.get("name") == "TimeGenerated"), None)
                    if time_generated_column:
                        time_generated_index = columns.index(time_generated_column)
                        rows = tables[0].get("rows")
                        if rows and len(rows) > 0:
                            timestamps = [row[time_generated_index] for row in rows]
                            timestamps = [ts for ts in timestamps if ts]
                            if timestamps:
                                timestamps.sort()
                                earliest_checkpoint = timestamps[0]
                                latest_checkpoint = timestamps[-1]
                                logger.info('"action": "Latest checkpoint has been successfully captured", "Input_Name":"%s", "earliest_time":"%s", "latest_checkpoint":"%s"}',input_name, earliest_checkpoint, latest_checkpoint)
                            else:
                                logger.info('"action": "No valid timestamps found in the response", "Input_Name":"%s"}',input_name)
                    else:
                        logger.info('"action": "Time column not found in the response", "Input_Name":"%s"}',input_name)
                else:
                    logger.info('"action": "No columns found in the response", "Input_Name":"%s"}',input_name)
            else:
                logger.info('"action": "No tables found in the response", "Input_Name":"%s"}',input_name)
        else:
            logger.error('"action": "invalid response format, Expected a dictionary format in the response", "Input_Name":"%s", "error_message":%s}',input_name, json.dumps(str(e)))
    except Exception as e:
        logger.error('"action": "An error occurred while attempting to retrieve the timestamps", "Input_Name":"%s", "error_message":%s}', input_name, json.dumps(str(e)))
    return latest_checkpoint

def get_checkpoint_file(input_name):
    file_name = CHECKPOINT_FILE_PREFIX + input_name + ".txt"
    checkpoint_file = os.path.join(CHECKPOINT_DIR, file_name)
    return checkpoint_file

def format_timestamp(timestamp):
    try:
        parsed_timestamp = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        formatted_timestamp = parsed_timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")
        logger.info("Formatted timestamp: '%s'", formatted_timestamp)
        return formatted_timestamp
    except ValueError:
        logger.warning('"action": "Invalid timestamp format", "timestamp":"%s"}', timestamp)
        return timestamp

def get_checkpoint(input_name):
    checkpoint_file = get_checkpoint_file(input_name)

    try:
        with open(checkpoint_file, "r") as file:
            checkpoint_data = file.read().strip()
            if checkpoint_data:
                if checkpoint_data.startswith('"') and checkpoint_data.endswith('"'):
                    time_generated = checkpoint_data[1:-1]
                else:
                    time_generated = checkpoint_data
                logger.info('"action": "Checkpoint value has been retrieved from existing records,resuming our quest from the checkpoint", "Input_Name":"%s", "checkpoint_file":%s, "retrieved_checkpoint":"%s"}',input_name, json.dumps(checkpoint_file), time_generated)
                return time_generated
            else:
                logger.info('"action": "Checkpoint file is not found. This input must be very new or checkpoint file was deleted manually", "Input_Name":"%s", "checkpoint_file":%s}',input_name, json.dumps(checkpoint_file))
    except FileNotFoundError:
        logger.info('"action": "Checkpoint file is not found. This input must be very new or checkpoint file was deleted manually", "Input_Name":"%s", "checkpoint_file":%s}',input_name, json.dumps(checkpoint_file))
    except Exception as e:
        logger.error('{"action": "Error retrieving checkpoint from existing checkpoint file", "checkpoint_file": "%s", "Input_Name": "%s", "error_message": %s}', json.dumps(checkpoint_file), input_name, json.dumps(str(e)))
        pass
        
    current_time = datetime.datetime.utcnow()
    three_minutes_ago = current_time - datetime.timedelta(minutes=3)
    formatted_timestamp = three_minutes_ago.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    logger.info('"action": "Alas! The checkpoint value has not been found. Fear not. Resuming our quest from the default timestamp", "Input_Name":"%s", "default_timestamp":"%s", "checkpoint_file": %s}',input_name, formatted_timestamp, json.dumps(checkpoint_file))
    
    return formatted_timestamp

def set_checkpoint(latest_checkpoint, input_name):
    if latest_checkpoint is None:
        logger.info('"action": "The latest checkpoint value is None. We shall therefore forgo the writing to the checkpoint file", "Input_Name":"%s"}',input_name)
        return

    checkpoint_file = get_checkpoint_file(input_name)
    checkpoint_dir = os.path.dirname(checkpoint_file)
    os.makedirs(checkpoint_dir, exist_ok=True)

    try:
        with open(checkpoint_file, "w") as f:
            f.write(json.dumps(latest_checkpoint))
        logger.info('"action": "The checkpoint value has been inscribed unto the sacred file", "Input_Name":"%s", "checkpoint_file":%s, "latest_checkpoint":"%s"}',input_name, json.dumps(checkpoint_file), latest_checkpoint)
        
    except Exception as e:
        logger.error('{"action": "Error saving checkpoint to defined checkpoint file", "checkpoint_file": %s, "Input_Name": "%s", "error_message": %s}', json.dumps(checkpoint_file), input_name, json.dumps(str(e)))

pid = os.getpid()
tid = threading.get_ident()
log_directory = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'azure_log_analytics_insight.log')
logger = logging.getLogger("kk_logger")
logger.setLevel(logging.DEBUG)

if not os.path.exists(log_directory):
    os.makedirs(log_directory)

json_formatter = logging.Formatter('{"time": "%(asctime)s", "thread_id": "%(thread)d", "levelname": "%(levelname)s", "process_id": "%(process)d", "relativeCreated": "%(relativeCreated)d", %(message)s')

file_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(json_formatter)
logger.addHandler(file_handler)

def get_access_token(client_id, client_secret, tenant_id, azure_auth, azure_environment, input_name, azure_service):
    try:
        authority_url = f'https://{azure_auth}/{tenant_id}'
        scopes = [f"https://{azure_environment}/.default"]

        app = ConfidentialClientApplication(
            client_id,
            authority=authority_url,
            client_credential=client_secret,
        )

        result = app.acquire_token_for_client(scopes=scopes)
        access_token = result["access_token"]  

        return access_token
    except Exception as e:
        return None

def process_row(row, columns):
    data = {}
    for i in range(len(columns)):
        column_name = columns[i]['name']
        value = row[i]

        try:

            if isinstance(value, str) and value.strip():

                try:
                    parsed_value = json.loads(value)
                    if isinstance(parsed_value, dict):
                        data[column_name] = parsed_value
                    else:
                        data[column_name] = value
                except json.JSONDecodeError:
                    #logger.warning('"action": "Value is not valid JSON", "column_name": "%s", "value": "%s"}', column_name, value)
                    data[column_name] = value
            else:
                #logger.warning('"action": "Empty or invalid value", "column_name": "%s", "value": "%s"}', column_name, value)
                data[column_name] = value

        except Exception as e:
            #logger.error('"action": "Error processing row", "column name":"%s", "error_message":%s}', column_name, json.dumps(str(e)))
            data[column_name] = value 

    return data

def process_rows(rows, columns):
    logs = []
    
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_row, row, columns): row for row in rows}
        
        for future in futures:
            try:
                logs.append(future.result())
            except Exception as e:
                logger.error('"action": "Error processing row", "error_message":%s}', json.dumps(str(e)))
                
    return logs

def write_event_threadsafe(event, ew, input_name, azure_service):
    try:
        ew.write_event(event)
        return True
    except Exception as e:
        logger.error(
            '"action": "Alas! An error has befallen us while inscribing the event unto Splunk", '
            '"service": "%s", "Input_Name": "%s", "error_message": %s}',
            azure_service, input_name, json.dumps(str(e))
        )
        return False

def collect_events(helper, ew):

    start_time = time.time()
    azure_service = helper.get_arg('azure_service')
    azure_account = helper.get_arg("azure_account")
    client_id = azure_account["username"]
    client_secret = azure_account["password"]
    tenant_id = azure_account["tenant_id"]
    azure_environment = azure_account["azure_environment"]
    azure_auth = azure_account["azure_auth"]
    input_name = helper.get_arg('name')
    workspace_app_id = helper.get_arg('workspace_app_id')
    table_name = helper.get_arg('table_name')
    query = helper.get_arg('query')
    sourcetype = helper.get_arg('sourcetypes')

    logger.info('"action": "Hark! The task has commenced its journey and Initiating a connection to Microsoft Azure", "Input_Name":"%s"}', input_name)

    last_processed_timestamp = get_checkpoint(input_name)

    max_retries = 3
    retry_count = 0
    rate_limit_delay_seconds = 5
    logs_ingested = 0

    success = False
    while retry_count < max_retries:
        try:

            access_token = get_access_token(client_id, client_secret, tenant_id, azure_auth, azure_environment, input_name, azure_service)
            
            if azure_service == "log_analytics":
                query_url = f'https://{azure_environment}/v1/workspaces/{workspace_app_id}/query'
                #logger.info('"action": "Selected azure service", "Service":"%s", "Input_Name":"%s"}', azure_service, input_name)
            elif azure_service == "app_insights":
                query_url = f'https://{azure_environment}/v1/apps/{workspace_app_id}/query'
                #logger.info('"action": "Selected azure service", "Service":"%s", "Input_Name":"%s"}', azure_service, input_name)
            else:
                logger.error('"action": "Unsupported service", "Input_Name":"%s"}',input_name)
                raise ValueError(f"Unsupported service: {azure_service}")
            
            query_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
            }
            
            if azure_service == "log_analytics":
                payload = {'query': f"{table_name} | extend TimeGenerated = column_ifexists('TimeGenerated', column_ifexists('Timestamp', now())) | where TimeGenerated > datetime('{last_processed_timestamp}') {query} | sort by TimeGenerated desc"}
            elif azure_service == "app_insights":
                payload = {'query': f"{table_name} | extend TimeGenerated = column_ifexists('TimeGenerated', column_ifexists('Timestamp', now())) | where TimeGenerated > datetime('{last_processed_timestamp}') {query} | sort by TimeGenerated desc"}
            else:
                raise ValueError(f"Unsupported service: {azure_service}")

            query_response = requests.post(query_url, headers=query_headers, json=payload, timeout=45)
            logger.info('"action": "Bingo! Connection successfull with Microsoft and Behold! dispatching the payload to Azure service", "service":"%s", "Input_Name":"%s", "KQL_query": "%s"}',azure_service, input_name, json.dumps(payload["query"])[1:-1])

            query_response.raise_for_status()

            if query_response.ok:
                result = query_response.json()
                latest_checkpoint = get_latest_checkpoint(result, input_name)
                if latest_checkpoint is not None:
                    set_checkpoint(latest_checkpoint, input_name)

                if 'tables' in result and len(result['tables']) > 0:
                    rows = result['tables'][0]['rows'] if 'rows' in result['tables'][0] else None
                    if rows and len(rows) > 0:
                        columns = result['tables'][0]['columns']

                        logs = process_rows(rows, columns)
                        with ThreadPoolExecutor(max_workers=10) as executor:
                            futures = []
                            for data in logs:
                                data_log = json.dumps(data)
                                event = helper.new_event(data_log, host=None, source=input_name, sourcetype=sourcetype, done=True, unbroken=True)
                                futures.append(executor.submit(write_event_threadsafe, event, ew, input_name, azure_service))

                            for future in as_completed(futures):
                                result = future.result()
                                if result:
                                    logs_ingested += 1
                                else:
                                    success = False

                        logger.info('"action": "Rejoice! logs have been successfully ingested to Splunk", "service":"%s", "Input_Name":"%s", "logs_ingested":"%s", "http_code":"%s"}',azure_service, input_name, logs_ingested, query_response.status_code)
                        success = True
                    
                    else:
                        logger.info('"action": "The query has returned empty, and no logs were found in the the Azure", "service":"%s" , "Input_Name":"%s", "http_code":"%s"}',azure_service, input_name, query_response.status_code)
                        success = True 
                else:
                    logger.info('"action": "The query has returned empty, and no logs were found in the the Azure", "service":"%s" , "Input_Name":"%s", "http_code":"%s"}',azure_service, input_name, query_response.status_code)
                    success = True
            else:
                logger.error('"action": "Alas! Our attempt to query the Azure has met with failure", "service":"%s" , "Input_Name":"%s", "http_code":"%s", "http_response":"%s", "error_message":%s}',azure_service, input_name, query_response.status_code, query_response.text, json.dumps(str(e)))
                success = False 

            time.sleep(rate_limit_delay_seconds)

        except requests.exceptions.RequestException as e:
            solution = "Review the configurations and error messages. take appropriate actions according to the errors to fix the issue."

            if e.response.status_code == 400:
                solution400 = "Verify the request parameters of query for correctness"
                logger.error('"action": "Oh! an HTTP error has occurred, Bad request. The request to Azure service", "service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution400, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 401:
                solution401 = "Verify the client_id and client_secret, and ensure the those are valid."
                logger.error('"action": "Oh! an HTTP error has occurred, Unauthorized. The provided client credentials are invalid or expired.","service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution401, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 403:
                solution403 = "Double-check the permissions for the selected Azure service. Ensure that the client_id has the required access permission."
                logger.error('"action": "Oh! an HTTP error has occurred, Insufficient permissions. The provided client_id does not have permission to access Azure service.", "service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution403, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 404:
                solution404 = "Verify the correctness of the workspace_id, query, or other identifiers used in the request."
                logger.error('"action": "Oh! an HTTP error has occurred, Resource not found. The requested resource could not be found in Azure service.", "service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution404, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code >= 500:
                solution5000 = "This might be a temporary issue on the server side. Retry the request later."
                logger.error('"action": "Oh! an HTTP error has occurred, Server error. An internal server error occurred in Azure service.", "service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution5000, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 500:
                solution500 = "This might be a temporary issue on the server side. Retry the request later."
                logger.error('"action": "Oh! an HTTP error has occurred, Internal Server Error. An internal server error occurred in Azure service.", "service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution500, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 300:
                solution300 = "Check the response for available choices and handle accordingly."
                logger.error('"action": "Oh! an HTTP error has occurred, Multiple Choices. The requested resource has multiple representations.","service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution300, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code >= 300 and e.response.status_code < 400:
                solution34 = "Handle the redirection if needed."
                logger.error('"action": "Oh! an HTTP error has occurred, Redirection. The request is being redirected.","service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution34, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code >= 400 and e.response.status_code < 500:
                solution45 = "Review and correct the request parameters."
                logger.error('"action": "Oh! an HTTP error has occurred, Client Error. The request was malformed or invalid.","service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution45, e.response.status_code, json.dumps(str(e)), input_name)
            elif e.response.status_code == 429:
                solution429 = "Implement a backoff and retry mechanism to reduce the rate of API requests."
                logger.error('"action": "Oh! an HTTP error has occurred, API rate limit exceeded.","service":"%s", "solution": "%s", "http_code": "%s", "error_message":%s, "Input_Name":"%s"}', azure_service, solution429, e.response.status_code, json.dumps(str(e)), input_name)
            else:
                logger.error('"action": "An HTTP error has occurred","service":"%s", "solution": "%s", "error_message": %s, "http_code": "%s", "http_code": "%s", "Input_Name":"%s"}', azure_service, solution, json.dumps(str(e)), e.response.status_code, input_name)

            success = False

        except Exception as e:
            solution = "Review the configurations and error messages. take appropriate actions according to the errors to fix the issue."
            logger.error('"action": "An unexpected error has occurred","service":"%s", "solution": "%s", "error_message": %s, "Input_Name":"%s"}', azure_service, solution, json.dumps(str(e)), input_name)
            success = False

        finally:
            end_time = time.time()
            time_taken = end_time - start_time

        retry_count += 1

        if success:
            break

    if success:
        logger.info('"action": "The task is now concluded and has reached its completion","service":"%s", "Input_Name": "%s", "api_duration": "%.3f"}', azure_service, input_name, time_taken)
    else:
        solution = "Please check the _internal logs of addon at sourcetype=azure:kql:addon for errors and take proper action"
        logger.error('"action": "The task has met its end with failures","service":"%s", "Input_Name": "%s", "retry_count": "%d", "api_duration": "%.3f", "solution": "%s"}', azure_service, input_name, max_retries, time_taken, solution)
