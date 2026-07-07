import json
import logging
import sys
from datetime import datetime as time, timedelta
from typing import List

import requests
import solnlib.modular_input.checkpointer as cp
from solnlib import conf_manager, log
from splunklib import modularinput as smi

import spiderSilk_resonance_data_transformers as transformers
from spiderSilk_resonance_config import *
from spiderSilk_resonance_lookup_tables import UpdateTable


def logger_for_input(input_name: str) -> logging.Logger:
    logging.info(f"Log Level configured in Application: {ADDON_NAME.lower()}_{input_name}")
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_keys(logger: logging.Logger, session_key: str) -> List[dict]:
    try:
        cfm = conf_manager.ConfManager(
                session_key,
                ADDON_NAME,
                realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-spidersilk_resonance_api_key",
        )
        account_conf_files = cfm.get_conf("spidersilk_resonance_api_key")
    except Exception as e:
        logger.info(f"No Account configurations found. Error: {e}")
        return []

    try:
        api_keys = []
        all_accounts = account_conf_files.get_all()
        for account_name, conf in all_accounts.items():
            api_keys.append({"name": account_name, "secret": conf['api_key']})

        return api_keys
    except Exception as e:
        logger.error(f"Error reading account config, Exception: {e}")
        return []


def add_checkpoint(logger: logging.Logger, checkpointer: cp.KVStoreCheckpointer, key: str, value: dict):
    """ADD a checkpoint with a specified key and value."""
    try:
        checkpointer.update(key, value)
        logger.debug(f"Checkpoint added for key: {key}")
    except Exception as e:
        logger.error(f"Error adding checkpoint for key: {key}, Exception: {e}")
        raise e


def check_checkpoint_exists(logger: logging.Logger, checkpointer: cp.KVStoreCheckpointer, key: str) -> bool:
    """Check if a checkpoint with the specified key exists."""
    try:
        checkpoint_value = checkpointer.get(key)
        exists = checkpoint_value is not None
        logger.debug(f"Checkpoint {'exists' if exists else 'does not exist'} for key: {key}")
        return exists
    except Exception as e:
        logger.error(f"Error checking checkpoint for key: {key}, Exception: {e}")
        raise e


def extract_transform_only_new_data(logger: logging.Logger, check_point_store: cp.KVStoreCheckpointer,
                                    api_meta: dict, api_data: dict, session_key: str):
    """
    Extracts new data entries from the provided API data that do not exist in the
    checkpoint store.

    This function iterates through a list of data dictionaries, identifying each entry's unique ID
    using metadata. It checks whether each unique ID already has an associated checkpoint. If it
    does, the entry is skipped, and a debug log is generated. If not, the data entry is added to
    the new data list for further processing.

    Args:
    logger (logging.Logger):
        A logger instance for logging debug information related to the process.
    check_point_store (cp.KVStoreCheckpointer):
        An instance of KVStoreCheckpointer used to verify the existence of checkpoints.
    api_meta (dict):
        A dictionary containing API metadata including the unique ID key and type information necessary for logging.

        api_meta is a Python dictionary object like:
        {
            "account": "Resonance Account Name configured in Splunk",
            "type": "API Type. eg: threats, darkweb, assets",
            "base_url": "<API BaseURL>",
            "uniqueID": "<Unique document identifier for the API>",
            "activeKey": "<Key identifier to check if it's Active>",
            "NotActiveKeyValue": "<Value identifier to check if it's Active>",
            "secret": "<api Secret Key>",
            "extra_headers": HTTP_CLIENT_EXTRA_HEADERS
        }

    api_data (list[dict]):
        A list of dictionaries representing the data received from an API to be filtered for new entries.

    Returns:
        A list of dictionaries representing data entries that are considered new
        (i.e., entries without existing checkpoints).
        {
            "count": 0,
            "<api_type>_list": []
        }
    """
    new_data = []

    ut = UpdateTable(logger, session_key, api_meta)

    for data in api_data:
        uuid = data[api_meta['uniqueID']]

        if api_meta['type'] != "assets":
            # check if a Threat or DW Leakage is still Active/Closed
            if data[api_meta['activeKey']] != api_meta['NotActiveKeyValue']:
                # check if it's already ingested
                if check_checkpoint_exists(logger, check_point_store, uuid):
                    logger.debug(f"Checkpoint already exists for {api_meta['type']} {uuid}, Account: "
                                 f"{api_meta['account']}, processing skipped.")
                else:
                    new_data.append(data)
        # Special handling for Assets data
        else:
            # check if it's already ingested
            if check_checkpoint_exists(logger, check_point_store, uuid):
                # if Asset already exists and  ingested
                if ut.record_exists(api_meta['type'], uuid):
                    if ut.is_record_old(api_meta['type'], uuid, data):
                        new_data.append(data)
                        pass

                logger.debug(f"Checkpoint already exists for {api_meta['type']} {uuid}, Account: "
                             f"{api_meta['account']}, processing skipped.")
            else:
                new_data.append(data)

        # Update the lookup table in Splunk KV Store irrespective of old/new data
        # as we need to update it either way.
        # TODO : move it to a separate thread/process with it's own data looping logic
        #        or better move it as separate splunk input with different periodic scheduling.
        if hasattr(ut, f"{api_meta['type']}_data_updater"):
            getattr(ut, f"{api_meta['type']}_data_updater")(data)

    # Run the transformers for new data
    if new_data:
        transformer_input = {"api_meta": api_meta, "api_data": new_data}
        if hasattr(transformers, f"{api_meta['type']}_data_transformer"):
            return getattr(transformers, f"{api_meta['type']}_data_transformer")(logger, transformer_input)

    return new_data


def get_data_from_api(logger: logging.Logger, api_meta: dict, page: 1, limits: 100):
    """
    Fetch data from the resonance API with given parameters and log the process.

    Parameters:
    logger (logging.Logger):
        A logger instance for logging debug and error information.
    api_meta (dict):
        All API metadata required to fetch data.

        api_meta is a Python dictionary object like:
        {
            "account": "Resonance Account Name configured in Splunk",
            "type": "API Type. eg: threats, darkweb, assets",
            "base_url": "<API BaseURL>",
            "uniqueID": "<Unique document identifier for the API>",
            "activeKey": "<Key identifier to check if it's Active>",
            "NotActiveKeyValue": "<Value identifier to check if it's Active>",
            "secret": "<api Secret Key>",
            "extra_headers": HTTP_CLIENT_EXTRA_HEADERS
        }

    Returns:
    dict
        Returns the data dictionary if the request is successful, otherwise returns the exception encountered.
        {
            "count": 0,
            "<api_type>_list": []
        }

    Raises:
        requests.exceptions.RequestException: If there's an issue with the API request.
    """
    logger.debug(f"Fetching for account {api_meta['account']} with api URL: {api_meta['base_url']}, Page: {page}, "
                 f"Limits: {limits}")

    api_headers = {"Authorization": f"Bearer {api_meta['secret']}"}
    api_headers.update(api_meta['extra_headers'] if 'headers' in api_meta else {})

    api_url = f"{api_meta['base_url']}?page={page}&limit={limits}&active_only=0"

    try:
        response = requests.get(api_url, headers=api_headers, timeout=10)
        response.raise_for_status()
        resp_data = response.json()
        logger.debug(f"Successfully fetched for API URL: {api_meta['base_url']}, Page: {page}, Limits: {limits}, "
                     f"Account : {api_meta['account']}")
        return resp_data['data']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching for resonance api URL: {api_meta['base_url']}, Page: {page}, Limits: {limits}"
                     f", Account : {api_meta['account']} Error :{e}")
        return e


def splunk_event_writer(logger: logging.Logger, event_writer: smi.EventWriter,
                        check_point_store: cp.KVStoreCheckpointer, events_input: dict):
    """
    Process and write events to a Splunk index, while maintaining checkpoints to
    prevent re-ingestion of the same events. Iterates over events from the input,
    checks if a checkpoint for each event already exists, and writes the event to
    the index if it does not. Updates checkpoints and logs ingestion status.

    Parameters:
    logger (logging.Logger):
        A logger object for logging debug and error messages throughout the event writing process.
    event_writer (smi.EventWriter):
        A Splunk EventWriter instance used to write events to the Splunk index.
    check_point_store (cp.KVStoreCheckpointer):
        A KVStoreCheckpointer object used to manage checkpoints for events, preventing duplicate ingestion's.
    events_input (dict):
        A dictionary containing the events to be ingested. It should have a key 'events' that maps to a list of event
        data.

        event_input is a Python dictionary object like:
        {
            "index_name": "<index_name>",
            "input_name": "<input_name>",
            "account_name": "<account_name>",
            "source_type": "<source_type>",
            "api_meta": "<api_meta object>",
            "events": []"event_object",
        }

        api_meta is a Python dictionary object like:
        {
            "account": "Resonance Account Name configured in Splunk",
            "type": "API Type. eg: threats, darkweb, assets",
            "base_url": "<API BaseURL>",
            "uniqueID": "<Unique document identifier for the API>",
            "activeKey": "<Key identifier to check if it's Active>",
            "NotActiveKeyValue": "<Value identifier to check if it's Active>",
            "secret": "<api Secret Key>",
            "extra_headers": HTTP_CLIENT_EXTRA_HEADERS
        }

        event_object is a Python dictionary object of api type(assets||darkweb|threats) fetched fom respective API.

    Raises:
        Handles all general exceptions during the ingestion process, logs the exception, and raises no specific
        errors directly.
    """

    api_type = events_input['api_meta']['type']

    # The difference in API data unique identifier is made same
    # across diff data with help of data transformers.
    # All data reaching this point should have unique Identifier's as `uuid`
    api_uniq_id = "uuid"

    events_ingested_count = 0

    logger.debug(f"Starting ingestion of {len(events_input['events'])} {api_type} events for "
                 f"Account : {events_input['account_name']} ")
    try:
        for event in events_input['events']:
            event_uuid = event[api_uniq_id]
            event_writer.write_event(
                    smi.Event(
                            data=json.dumps(event, ensure_ascii=False, default=str),
                            index=events_input['index_name'],
                            source=f"spiderSilk_resonance_{events_input['account_name']}",
                            sourcetype=events_input['source_type'],
                    )
            )
            check_point_value = {"uuid": event_uuid, "status": "ingested", "type": api_type,
                                 "account": events_input['account_name'],
                                 "injestionTime": time.now().strftime('%Y-%m-%d %H:%M:%S')}
            add_checkpoint(logger, check_point_store, event_uuid, check_point_value)
            events_ingested_count += 1

        if events_ingested_count > 0:
            input_name = events_input['input_name']
            modular_input_name = input_name.split("/")[-1]
            log.modular_input_start(logger, modular_input_name)
            log.events_ingested(logger, input_name, events_input['source_type'], events_ingested_count,
                                modular_input_name, account=events_input['account_name'])
            log.modular_input_end(logger, modular_input_name)
    except Exception as e:
        log.log_exception(logger, e, "IngestionError", msg_before="Exception raised while ingesting data.")


def validate_input(definition: smi.ValidationDefinition):
    """When using external validation, after splunkd calls the modular input with
    --scheme to get a scheme, it calls it again with --validate-arguments for
    each instance of the modular input in its configuration files, feeding XML
    on stdin to the modular input to do validation. It is called the same way
    whenever a modular input's configuration is edited.

    :param definition: a ValidationDefinition object
    """
    return


def create_lock(session_key):
    """Method to create an application lock to avoid duplicate process.
    :param session_key: Splunk session token
    """
    lock_store = cp.KVStoreCheckpointer("execution_status_kvstore", session_key, ADDON_NAME)
    key = "resonance_crawler_lock"
    start_time = time.now().strftime('%Y-%m-%d %H:%M:%S')
    logger = logger_for_input("app_lock")
    logger.setLevel(logging.INFO)

    try:
        lock_status = lock_store.get(key)
        logger.debug(lock_status)
    except Exception as e:
        logger.error(f"Unable to check if Resonance crawler is already running or not. Error: {e}")
        sys.exit(1)

    if lock_status is not None:
        if lock_status['status'] == "running":
            prev_start_time = time.strptime(lock_status['startTime'], '%Y-%m-%d %H:%M:%S')
            if time.now() - prev_start_time > timedelta(hours=MAX_APP_LOCK_DURATION_HOURS):
                logger.warning(f"Resonance crawler is been locked for more than {MAX_APP_LOCK_DURATION_HOURS} hours, "
                               f"resetting lock.")
                lock_store.update(key, {"status": "running", "startTime": prev_start_time, "finishTime": "0"})
                logger.info("Resonance crawler application lock reset and created new lock for new process.")
            else:
                logger.info("Resonance crawler is already running, exiting.")
                sys.exit(0)
        else:
            lock_store.update(key, {"status": "running", "startTime": start_time, "finishTime": "0"})
            logger.info("Resonance crawler application lock created to avoid duplicate process")
    else:
        lock_store.update(key, {"status": "running", "startTime": start_time, "finishTime": "0"})
        logger.info("Resonance crawler application lock created to avoid duplicate process")


def release_lock(session_key):
    """Method to release the application lock.
    :param session_key: Splunk session token
    """
    lock_store = cp.KVStoreCheckpointer("execution_status_kvstore", session_key, ADDON_NAME)
    key = "resonance_crawler_lock"
    logger = logger_for_input("app_lock")
    logger.setLevel(logging.INFO)

    try:
        lock_status = lock_store.get(key)
        lock_status['status'] = "completed"
        lock_status['finishTime'] = time.now().strftime('%Y-%m-%d %H:%M:%S')
        lock_store.update(key, lock_status)
        logger.info("Resonance crawler application lock released.")
    except Exception as e:
        logger.error(f"Unable to release the lock for Resonance crawler. Error: {e}")
        sys.exit(1)


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    """This function handles all the action: splunk calls this modular input
    without arguments, streams XML describing the inputs to stdin, and waits
    for XML on stdout describing events.

    If you set use_single_instance to True on the scheme in get_scheme, it
    will pass all the instances of this input to a single instance of this
    script.

            inputs.inputs is a Python dictionary object like:
            {
              "spiderSilk_resonance://<input_name>": {
                "account": "<account_name>",
                "disabled": "0",
                "host": "$decideOnStartup",
                "index": "<index_name>",
                "interval": "<interval_value>",
                "python.version": "python3",
              },
            }

    Parameters:
    inputs (smi.InputDefinition):
        The input definitions containing metadata and parameters for the events to be streamed.
        The structure includes input metadata and specific input items.
    event_writer (smi.EventWriter):
        An instance of an EventWriter used to output events to Splunk.

    Raises:
    Exception:
        An error occurring during the API crawling or event writing process will be logged along with
        the context of the API type, base URL, page number, and account name.
    """

    session_key = inputs.metadata['session_key']

    create_lock(session_key)

    for input_name, input_item in inputs.inputs.items():
        modular_input_name = input_name.split("/")[-1]
        index_name = input_item.get("index")

        logger = logger_for_input(modular_input_name)
        log_level = conf_manager.get_log_level(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name="spidersilk_resonance_settings",
        )
        logger.setLevel(log_level)
        logger.info(f"Log level configured to {log_level}")

        api_keys = get_account_api_keys(logger, session_key)
        if len(api_keys) == 0:
            logger.info("No API keys configured, skipping crawling")
            continue

        # Crawl each API and send to splunk event writer
        # TODO: Make it async/threaded (Future Enhancement)
        for api_key in api_keys:
            account_name = api_key['name']
            logger.info(f"Starting crawler for Account: {account_name}")
            for api_type, api in APIS_TO_CRAWL.items():
                source_type = f"resonance_{api_type}"
                cp_store = cp.KVStoreCheckpointer(f"{source_type}_kvstore", session_key, ADDON_NAME)

                page_num = 1
                page_limit = api['limit']
                consumed_results_count = 0
                data_key = f"{api_type}_list"
                api_meta = {
                    "account": account_name,
                    "type": api_type,
                    "base_url": api['api_base_url'],
                    "uniqueID": api['uniqueID'],
                    "activeKey": api['activeKey'],
                    "NotActiveKeyValue": api['NotActiveKeyValue'],
                    "secret": api_key['secret'],
                    "extra_headers": HTTP_CLIENT_EXTRA_HEADERS
                }
                try:
                    data = get_data_from_api(logger, api_meta, page_num, page_limit)
                    total_results_count = data['count']
                    current_results_count = len(data[data_key])
                    logger.info(f"Account Name: {account_name}, API: {api_type} Total: {total_results_count} Fetched:"
                                f" {current_results_count}, Page: {page_num}, Limits: {page_limit}")

                    new_transformed_data = extract_transform_only_new_data(
                            logger, cp_store, api_meta, data[data_key], session_key)
                    event_input = {
                        "index_name": index_name,
                        "input_name": input_name,
                        "account_name": account_name,
                        "source_type": source_type,
                        "api_meta": api_meta,
                        "events": new_transformed_data,
                    }

                    if new_transformed_data:
                        splunk_event_writer(logger, event_writer, cp_store, event_input)
                    else:
                        logger.info(f"No new data for {api_type} API, Account: {account_name}, Page: {page_num}, "
                                    f"Ingestion Skipped.")

                    # Handling Pagination
                    consumed_results_count += current_results_count

                    while consumed_results_count < total_results_count:
                        logger.info(f"There are more pages to crawl for {api_type} API, Account: {account_name}, "
                                    f"continuing to crawl further pages.")
                        page_num += 1
                        data = get_data_from_api(logger, api_meta, page_num, page_limit)
                        current_results_count = len(data[data_key])
                        logger.debug(f"Account Name: {account_name}, API: {api_type} Total {total_results_count} "
                                     f"fetched : {current_results_count}, Page: {page_num}, Limits: {page_limit}")

                        new_transformed_data = extract_transform_only_new_data(
                                logger, cp_store, api_meta, data[data_key], session_key)
                        event_input["events"] = new_transformed_data
                        if new_transformed_data:
                            splunk_event_writer(logger, event_writer, cp_store, event_input)
                        else:
                            logger.info(f"No new data for {api_type} API, Account: {account_name}, Page: {page_num}, "
                                        f"Ingestion Skipped.")

                        consumed_results_count += current_results_count

                except Exception as e:
                    logger.error(
                            f"Error occurred while Crawling data for {api_type} API: {api['api_base_url']} "
                            f"Page: {page_num}, Limits: {page_limit} for Account Name: {account_name} Exception: {e}")
                    log.log_exception(
                            logger, e, "APIReadError",
                            msg_before=f"Error occurred while Crawling data for {api_type} API: {api['api_base_url']} "
                                       f"Page: {page_num}, Limits: {page_limit} for Account Name: {account_name}")

    release_lock(session_key)
