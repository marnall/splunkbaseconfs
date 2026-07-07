# encoding = utf-8

import requests
import json
import os
import sys
import threading
import logging
import traceback
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
            schema = result.get("Schema", [])
            rows = result.get("Results", [])

            if schema and rows:
                time_col_index = None
                for idx, col in enumerate(schema):
                    if col["Name"] == "TimeGenerated":
                        time_col_index = col["Name"]
                        break

                if time_col_index:
                    timestamps = [row[time_col_index] for row in rows if time_col_index in row and row[time_col_index]]
                    if timestamps:
                        timestamps.sort()
                        earliest_checkpoint = timestamps[0]
                        latest_checkpoint = timestamps[-1]
                        logger.info({
                            "action": "Latest checkpoint captured",
                            "Input_Name": input_name,
                            "earliest_time": earliest_checkpoint,
                            "latest_checkpoint": latest_checkpoint
                        })
                    else:
                        logger.info({
                            "action": "No valid timestamps found in the response",
                            "Input_Name": input_name
                        })
                else:
                    logger.info({
                        "action": "TimeGenerated column not found in schema",
                        "Input_Name": input_name
                    })
            else:
                logger.debug({
                    "action": "No schema or rows found in the response",
                    "Input_Name": input_name
                })
        else:
            logger.error({
                "action": "Invalid response format",
                "Input_Name": input_name
            })

    except Exception as e:
        logger.error({
            "action": "Error extracting checkpoint",
            "Input_Name": input_name,
            "error_message": str(e)
        })

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
        logger.warning({
            "action": "Invalid timestamp format",
            "timestamp": timestamp
        })
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
                logger.info({
                    "action": "Checkpoint value has been retrieved from existing records, resuming our quest from the checkpoint",
                    "Input_Name": input_name,
                    "checkpoint_file": checkpoint_file,
                    "retrieved_checkpoint": time_generated
                })
                return time_generated
            else:
                logger.info({
                    "action": "Checkpoint file is not found. This input must be very new or checkpoint file was deleted manually",
                    "Input_Name": input_name,
                    "checkpoint_file": checkpoint_file
                })
    except FileNotFoundError:
        logger.info({
            "action": "Checkpoint file is not found. This input must be very new or checkpoint file was deleted manually",
            "Input_Name": input_name,
            "checkpoint_file": checkpoint_file
        })
    except Exception as e:
        logger.error({
            "action": "Error retrieving checkpoint from existing checkpoint file",
            "checkpoint_file": checkpoint_file,
            "Input_Name": input_name,
            "error_message": str(e)
        })
        pass
        
    current_time = datetime.datetime.utcnow()
    three_minutes_ago = current_time - datetime.timedelta(minutes=3)
    formatted_timestamp = three_minutes_ago.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    logger.info({
        "action": "Alas! The checkpoint value has not been found. Fear not. Resuming our quest from the default timestamp",
        "Input_Name": input_name,
        "default_timestamp": formatted_timestamp,
        "checkpoint_file": checkpoint_file
    })
    
    return formatted_timestamp

def set_checkpoint(latest_checkpoint, input_name, azure_service):
    if latest_checkpoint is None:
        logger.info({
            "action": "The latest checkpoint value is None. We shall therefore forgo the writing to the checkpoint file",
            "Input_Name": input_name
        })
        return

    checkpoint_file = get_checkpoint_file(input_name)
    checkpoint_dir = os.path.dirname(checkpoint_file)
    os.makedirs(checkpoint_dir, exist_ok=True)

    try:
        with open(checkpoint_file, "w") as f:
            f.write(json.dumps(latest_checkpoint))
        logger.info({
            "action": "The checkpoint value has been inscribed unto the sacred file",
            "Input_Name": input_name,
            "checkpoint_file": checkpoint_file,
            "latest_checkpoint": latest_checkpoint,
            "service": azure_service
        })
        
    except Exception as e:
        logger.error({
            "action": "Error saving checkpoint to defined checkpoint file",
            "checkpoint_file": checkpoint_file,
            "Input_Name": input_name,
            "error_message": str(e),
            "service": azure_service
        })

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": datetime.datetime.utcnow().isoformat() + "Z",
            "levelname": record.levelname,
            "process_id": record.process,
            "thread_id": record.thread,
            "relativeCreated": int(record.relativeCreated),
        }

        try:
            if isinstance(record.msg, dict):
                log_record.update(record.msg)
            else:
                log_record["message"] = record.getMessage()
        except Exception as e:
            log_record["message"] = f"Failed to format log message: {str(e)}"

        return json.dumps(log_record)

log_directory = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk')
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, 'app_microsoft_defender.log')

logger = logging.getLogger("kk_logger")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(log_file, maxBytes=1048576, backupCount=1)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(JsonFormatter())

logger.addHandler(file_handler)
logger.propagate = False

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

        if "access_token" in result:
            access_token = result["access_token"]
            return access_token
        else:
            logger.error({
                "action": "Failed to acquire token from Microsoft",
                "service": azure_service,
                "Input_Name": input_name,
                "error_details": result
            })
            return None

    except Exception as e:
        logger.error({
            "action": "Exception occurred during token acquisition",
            "service": azure_service,
            "Input_Name": input_name,
            "error_message": str(e)
        })
        return None

def process_row(row, columns):
    data = {}
    for col in columns:
        column_name = col['name']
        try:
            value = row.get(column_name, None)

            if isinstance(value, str) and value.strip():
                try:
                    parsed_value = json.loads(value)
                    data[column_name] = parsed_value if isinstance(parsed_value, dict) else value
                except json.JSONDecodeError:
                    data[column_name] = value
            else:
                data[column_name] = value
        except Exception as e:
            logger.error({
                "action": "Exception in process_row",
                "column_name": column_name,
                "value": str(value),
                "error_message": str(e)
            })
            data[column_name] = value
    return data

def process_rows(rows, columns):
    logs = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_row, row, columns): row for row in rows}

        for future, row in futures.items():
            try:
                logs.append(future.result())
            except Exception as e:
                logger.error({
                    "action": "Error processing row in process_rows",
                    "row": row,
                    "error_type": type(e).__name__,
                    "error_message": str(e) if str(e).strip() else repr(e),
                    "traceback": traceback.format_exc()
                })
    return logs

def write_event_threadsafe(event, ew, input_name, azure_service):
    try:
        ew.write_event(event)
        return True
    except Exception as e:
        logger.error({
            "action": "Failed to write event to Splunk",
            "Input_Name": input_name,
            "error_message": str(e),
            "service": azure_service
        })
        return False

def collect_events(helper, ew):

    start_time = time.time()
    azure_service = 'MDE'
    azure_account = helper.get_arg("azure_account")
    client_id = azure_account["username"]
    client_secret = azure_account["password"]
    tenant_id = azure_account["tenant_id"]
    azure_environment = azure_account["azure_environment"]
    azure_auth = azure_account["azure_auth"]
    input_name = helper.get_arg('name')
    table_name = helper.get_arg('table_name')
    query = helper.get_arg('query')
    sourcetype = helper.get_arg('sourcetypes')

    logger.info({
        "action": "Initiating connection to Microsoft Defender Advanced Hunting",
        "Input_Name": input_name,
        "service": azure_service
    })

    last_processed_timestamp = get_checkpoint(input_name)

    max_retries = 2
    retry_count = 0
    rate_limit_delay_seconds = 5
    logs_ingested = 0
    success = False

    while retry_count < max_retries:
        try:
            access_token = get_access_token(
                client_id, client_secret, tenant_id, azure_auth, azure_environment, input_name, azure_service
            )
            query_url = f'https://{azure_environment}/api/advancedhunting/run'
            query_headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                "Query": f"{table_name} | extend TimeGenerated = column_ifexists('TimeGenerated', column_ifexists('Timestamp', now())) | where TimeGenerated > datetime('{last_processed_timestamp}') {query} | sort by TimeGenerated desc"
            }

            logger.info({
                "action": "Bingo! Connection successful with Microsoft and Behold! dispatching the payload to Azure service",
                "service": azure_service,
                "Input_Name": input_name,
                "KQL_query": payload.get('Query')
            })

            query_response = requests.post(query_url, headers=query_headers, json=payload, timeout=45)

            '''try:
                logger.debug({"action": "Raw JSON response from Defender API","raw_response": query_response.json()})
            except Exception as e:
                logger.warning({
                    "action": "Unable to parse JSON from response",
                    "error_message": str(e)
                })'''

            query_response.raise_for_status()

            result = query_response.json()
            latest_checkpoint = get_latest_checkpoint(result, input_name)
            if latest_checkpoint:
                set_checkpoint(latest_checkpoint, input_name, azure_service)

            if 'Results' in result and result['Results']:
                rows = result['Results']
                schema = result['Schema'] if 'Schema' in result else []
                columns = [{'name': col['Name']} for col in schema]

                logs = process_rows(rows, columns)

                with ThreadPoolExecutor(max_workers=10) as executor:
                    futures = []
                    for data in logs:
                        data_log = json.dumps(data)
                        event = helper.new_event(
                            data_log, host=None, source=input_name,
                            sourcetype=sourcetype, done=True, unbroken=True
                        )
                        futures.append(executor.submit(write_event_threadsafe, event, ew, input_name, azure_service))

                    for future in as_completed(futures):
                        if future.result():
                            logs_ingested += 1
                        else:
                            success = False 

                if logs_ingested > 0:
                    logger.info({
                        "action": "Logs successfully ingested into Splunk",
                        "service": azure_service,
                        "Input_Name": input_name,
                        "logs_ingested": logs_ingested,
                        "http_code": query_response.status_code
                    })
                else:
                    logger.info({
                        "action": "Query executed successfully but returned no logs",
                        "service": azure_service,
                        "Input_Name": input_name,
                        "http_code": query_response.status_code
                    })

                success = True
            else:
                logger.info({
                    "action": "The query returned no results",
                    "service": azure_service,
                    "Input_Name": input_name,
                    "http_code": query_response.status_code
                })
                success = True

        except requests.exceptions.RequestException as e:
            response = getattr(e, 'response', None)
            response_code = getattr(e.response, 'status_code', None)
            try:
                response_text = e.response.text if e.response else str(e)
            except Exception:
                response_text = str(e)

            log_data = {
                "action": "HTTP request error" if response_code else "Network or configuration error (no response from server)",
                "status_code": response_code,
                "error_message": response_text,
                "Input_Name": input_name,
                "service": azure_service
            }
            logger.error(log_data)

            if response_code == 429:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = int(retry_after)
                except (TypeError, ValueError):
                    delay = rate_limit_delay_seconds * (2 ** retry_count)
                logger.warning({
                    "action": "Rate limit encountered. Backing off before retrying.",
                    "delay_seconds": delay,
                    "retry_after_header": retry_after,
                    "Input_Name": input_name,
                    "service": azure_service
                })
                time.sleep(delay)
            else:
                time.sleep(rate_limit_delay_seconds)

        except Exception as e:
            log_data = {
                "action": "Unexpected error during data collection",
                "error_message": str(e),
                "Input_Name": input_name,
                "service": azure_service
            }
            logger.error(log_data)
            time.sleep(rate_limit_delay_seconds)

        finally:
            retry_count += 1
            if success:
                break

    end_time = time.time()
    time_taken = end_time - start_time

    if success:
        logger.info({
            "action": "Data collection completed successfully",
            "Input_Name": input_name,
            "service": azure_service,
            "logs_ingested": logs_ingested,
            "api_duration": round(time_taken, 3)
        })
    else:
        logger.error({
            "action": "Data collection failed after maximum retries",
            "Input_Name": input_name,
            "retry_count": retry_count,
            "service": azure_service,
            "api_duration": round(time_taken, 3)
        })
