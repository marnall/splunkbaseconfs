import json
import logging
import sys
import time
import traceback
from datetime import datetime

from tisc_rest_handler import validate_and_get_additional_attribute_field_names, validate_filter_and_create_json
import import_declare_test
import requests
from requests.auth import HTTPBasicAuth
from solnlib import conf_manager, log
from splunklib import modularinput as smi, client
from splunktaucclib.rest_handler.error import RestError
from constants import api_field_to_kv_store_field_mapping
from constants import INPUTS_METADATA_KV_STORE, INPUT_NAME, CONFIGURATION_NAME, LAST_EXECUTION_TIME, ADDON_NAME, APP_NAME
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_last_execution_filter(service, input_name, config_name):
    try:
        kvstore = service.kvstore[INPUTS_METADATA_KV_STORE]
        query = {INPUT_NAME: input_name, CONFIGURATION_NAME: config_name}
        result = kvstore.data.query(query=query)

        if result:
            last_time = result[0][LAST_EXECUTION_TIME]
            logger.debug(f"Using last_execution_time filter: {last_time}")
            return {
                "field_name": "sys_updated_on",
                "operator": ">=",
                "field_value": last_time
            }, True
        else:
            logger.debug(f"No previous execution found for {input_name}, {config_name}")
            return None, False
    except Exception as e:
        logger.error(f"Error retrieving metadata: {e}")
        return None, False

def update_last_execution_time(service, current_execution_time, input_name, config_name):
    try:
        kvstore = service.kvstore[INPUTS_METADATA_KV_STORE]

        query = {INPUT_NAME: input_name, CONFIGURATION_NAME: config_name}
        existing = kvstore.data.query(query=query)

        record = {
            INPUT_NAME: input_name,
            CONFIGURATION_NAME: config_name,
            LAST_EXECUTION_TIME: current_execution_time
        }

        if existing:
            kvstore.data.update(existing[0]['_key'], record)
            logger.debug(f"Updated last_execution_time for {input_name}, {config_name}")
        else:
            kvstore.data.insert(record)
            logger.debug(f"Inserted new last_execution_time entry for {input_name}, {config_name}")
    except Exception as e:
        logger.error(f"Failed to update execution time: {e}")


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def validate_input(definition: smi.ValidationDefinition):
    return

def insert_into_kvstore(service, records):
    """Insert record into the specified KV store."""

    # Splunk credentials
    size_of_records = sys.getsizeof(records)
    logger.debug(f"record for KV store is testing code flow {size_of_records}")

    # Get current time in TZ format for Created and Updated Time
    current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    logger.debug(f"current time is latest {current_time}")

    # Connect to Splunk
    try:
        kvstore_name = 'tisc_kv_store'
        kvstore = service.kvstore[kvstore_name]

        # Check if KV store exists
        if kvstore_name not in service.kvstore:
            logger.error(f"KV Store '{kvstore_name}' does not exist.")
            return

        for record in records:
            if not isinstance(record, dict):
                logger.error("Each record must be a dictionary.")
                continue

            sys_id = record.get('sys_id')  # Assuming sys_id is a key in records existing in kv store

            record['kvlookup_updated_time'] = current_time  # Updated Time for both new and existing records
            record['_key'] = sys_id

            # Querying the KV store to check for existing record
            try:
                existing_record = kvstore.data.query(query={"sys_id": sys_id})
            except Exception as e:
                logger.error(f"Failed to query KV store: {e}")
                continue

            if existing_record:
                logger.debug(f"Observable with sys_id '{sys_id}' already exists in the kv store {kvstore_name}. Updating record.")
                # updating the existing record
                existing_record[0].update(record)  # Update the existing record with new data
                try:
                    kvstore.data.update(existing_record[0]['_key'], existing_record[0])  # Update the existing record in the KV store
                    logger.debug(f"Successfully updated record in KV store '{kvstore_name}' with sys_id '{sys_id}'")
                except Exception as e:
                    logger.error(f"Failed to update record in KV store: {e}")
            else:
                logger.debug(f"Inserting new record into KV store with sys_id {kvstore_name} '{sys_id}'.")
                try:
                    record['kvlookup_created_time'] = current_time  # Created Time for new records
                    kvstore.data.insert(record)  # Insert the new record
                    logger.debug(f"Successfully inserted record into KV store '{kvstore_name}' with sys_id '{sys_id}'.")
                except Exception as e:
                    logger.error(f"Failed to insert record into KV store: {e}")

    except Exception as conn_error:
        logger.error(f"Failed to connect to Splunk: {conn_error}")



def fetch_data_from_tisc_instance(input_name, session_key, account_name, username, password, url, incoming_filters, interval, days_till_expiry, additional_attr_fields):
    logger.debug(f"Getting data from TISC API: {account_name}, username: {username}, url: {url}, incoming filters: {incoming_filters}, incoming additional attributes: {additional_attr_fields}")
    instance_url = url
    # URL of the endpoint
    url = url+'api/sn_sec_tisc/v1/threat_intel_data/observables'

    headers = {
        'Content-Type': 'application/json'
    }

    # Default fields
    values = [
        "threat_score",
        "confidence",
        "threat_level",
        "reputation",
        "source_reported_score",
        "threat_severity"
    ]

    for i in range(len(additional_attr_fields)):
        values.append(additional_attr_fields[i])

    # Payload
    data = {
        "page_size": "100",
        "page_token": "",
        "included_fields": {
            "observable": {
                "common_fields": {
                    "include_all_fields": False,
                    "values": values
                }
            }
        }
    }

    execution_success = True
    try:
        # Parse incoming filters from JSON string to dictionary
        filters_json = json.loads(incoming_filters)

        data['observable_filters'] = filters_json

        # Connect to Splunk
        service = client.connect(app=APP_NAME, token=session_key)

        # Add sys_updated_on filter if metadata exists
        sys_updated_filter, found = get_last_execution_filter(service, input_name, account_name)
        if found and sys_updated_filter:
            filters_json.setdefault("boolean_operator", "AND")
            filters_json.setdefault("filters", []).append(sys_updated_filter)

        data['observable_filters'] = filters_json


    except ValueError as e:
        execution_success = False
        raise ValueError("Invalid JSON: Unable to append observable_filters") from e


    logger.debug(f"Json Payload for fetching observable data:{data}")

    next_page_token = ""
    is_last_page = False
    all_observables = []

    numberOfObservables = 0
    current_execution_time = datetime.utcnow().isoformat() + "Z"
    while not is_last_page:
        data["page_token"] = next_page_token

        try:
            # Make the POST request with Basic Authentication
            response = requests.post(url, headers=headers, json=data, auth=HTTPBasicAuth(username, password))
            if response.status_code != 200:
                execution_success = False
                raise RestError(
                    response.status_code,
                    f"Failed to connect with Instance. Response code: {response.status_code}"
                )

            # Log the response status
            temp_response = response.json()
            observables_data = temp_response.get('observables', [])
        
            if not observables_data:
                logger.warning("No observables data found.")
                break

            # Collect all observables data
            all_observables.extend(observables_data)

            # Initialize an empty list to collect all records
            kvstore_records = []

            for observable in observables_data:
                numberOfObservables += 1
                sys_id = observable.get('sys_id', '')
                type_ = observable.get('type', '')
                value = observable.get('value', '')
                threat_score = observable.get('threat_score','')
                confidence = observable.get('confidence', '')
                threat_level = observable.get('threat_level','')
                reputation = observable.get('reputation', '')
                source_reported_score = observable.get('source_reported_score', '')
                threat_severity = observable.get('threat_severity', '')
                
                logger.debug(f"Observable Record - sys_id: {sys_id}, type: {type_}, value: {value}, "
                            f"confidence: {confidence}, reputation: {reputation}")

                kvstore_record = {
                    "sys_id": sys_id,
                    "type": type_,
                    "value": value,
                    "threat_score": threat_score,
                    "confidence": confidence,
                    "threat_level": threat_level,
                    "reputation": reputation,
                    "source_reported_score":source_reported_score,
                    "threat_severity": threat_severity,
                    "kvlookup_days_till_expiry": days_till_expiry,
                    "instance_url": instance_url,
                    "updated_by":account_name
                }
                # Add additional attributes if present
                for attr in additional_attr_fields:
                    kv_store_field = api_field_to_kv_store_field_mapping[attr]

                    if attr == "comments":
                        comment_objs = observable.get(attr, [])
                        comment_values = " |\n".join(
                            c.get("value", "").strip()
                            for c in comment_objs
                            if "value" in c
                        )
                        kvstore_record[kv_store_field] = comment_values
                    else:
                        kvstore_record[kv_store_field] = observable.get(attr, '')


                kvstore_records.append(kvstore_record)

            logger.debug(f"record to be updated in kv store is : {kvstore_records}")

            if kvstore_records:
                insert_into_kvstore(service, kvstore_records)

            if response.status_code != 200:
                raise RestError(400, f"Failed to connect with Instance with Response code: {response.status_code}")

            # Update the page token for the next call
            next_page_token = temp_response.get('next_page_token', "")
            is_last_page = temp_response.get('is_last_page', True)

            logger.debug(f"next_page_token: {next_page_token}, is_last_page_test: {is_last_page}")

        except Exception as e:
            execution_success = False
            logger.error(f"Error fetching data from TISC instance: {e}")
            logger.debug(f"Raw Response: {response.text}")
            break

    if execution_success:
        update_last_execution_time(service, current_execution_time, input_name, account_name)
        logger.debug("Last execution time updated successfully")
    else:
        logger.warning("Execution failed. Last execution time NOT updated.")

    logger.debug(f"Successfully fetched all pages of data from the instance. Total number of observables fetched: {numberOfObservables}")
    return all_observables


def get_account_details_test(session_key, account_name):

    logger.debug("inside get account Details methodGetting data from an external TISC Application TEST")
    """
    Returns username, password, and instance_url for a specific account_name.
    :param session_key: session key for particular modular input.
    :param account_name: account name configured in the addon.
    :return: Dictionary containing username, password, and instance_url if found, else None.
    """
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            APP_NAME,
            realm=f"__REST_CREDENTIAL__#{APP_NAME}#configs/conf-splunk_tisc_addon_account",
        )
        account_conf_file = cfm.get_conf("splunk_tisc_addon_account")

        account_details = account_conf_file.get(account_name)

        if account_details is None:
            logging.warning(f"Account '{account_name}' not found in configuration.")
            return None

        return {
            "username": account_details.get("username"),
            "password": account_details.get("password"),
            "instance_url": account_details.get("instanceUrl"),
        }

    except KeyError as e:
        logging.error(f"KeyError while retrieving account details for '{account_name}': {e}")
    except Exception as e:
        logging.error(f"An error occurred while retrieving account details: {e}")
        traceback.print_exc()

    return None


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    logger.debug("Getting data from an external TISC Application")
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "splunk_tisc_addon://<input_name>": {
    #     "account": "<account_name>",
    #     "disabled": "0",
    #     "host": "$decideOnStartup",
    #     "index": "<index_name>",
    #     "interval": "<interval_value>",
    #     "python.version": "python3",
    #   },
    # }
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger.debug("Getting data from TISC Application")
        try:
            session_key = inputs.metadata["session_key"]
            logger.debug(f"Getting data from an external TISC Application, input item: {input_item}")
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )

            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            days_till_expiry = input_item.get("days_till_expiry")
            logger.debug(f"days_till_expiry_test {days_till_expiry}")
            interval = input_item.get("interval")
            logger.debug(f"interval_test {interval}")

            advancedCheckBox = input_item.get("advanced")
            logger.debug(f"advancedCheckBox value={advancedCheckBox}")

            incoming_filters = ""
            if(advancedCheckBox=="0"):
                incoming_filters = input_item.get("filters")
                _, jsonOutput = validate_filter_and_create_json(incoming_filters)
                incoming_filters = jsonOutput
            elif(advancedCheckBox=="1"):
                incoming_filters = input_item.get("json_filters")

            additional_attrs = input_item.get("additional_attributes")
            _, additional_attr_fields = validate_and_get_additional_attribute_field_names(additional_attrs)

            accountName = input_item["account"]
            account_information = get_account_details_test(session_key, accountName)
            username_config = account_information["username"]
            password_config = account_information["password"]
            instance_url = account_information["instance_url"]
            
            observable_data = fetch_data_from_tisc_instance(normalized_input_name, session_key, accountName, username_config, password_config, instance_url, incoming_filters, interval, days_till_expiry, additional_attr_fields)

            sourcetype = "servicenow_tisc_intelligence"
            for line in observable_data:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(line, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(observable_data),
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for tisc input: ")
