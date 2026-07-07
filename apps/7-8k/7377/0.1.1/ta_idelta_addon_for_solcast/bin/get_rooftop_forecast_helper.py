import json
import logging
import requests

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "ta_idelta_addon_for_solcast"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_idelta_addon_for_solcast_account",
    )
    account_conf_file = cfm.get_conf("ta_idelta_addon_for_solcast_account")
    return account_conf_file.get(account_name).get("api_key")


def get_data_from_api(logger: logging.Logger, api_key: str, resource_id:str):
    logger.info("Getting data from an external API")
    logger.debug("Using resource_id: "+resource_id)
    url="https://api.solcast.com.au/rooftop_sites/"+resource_id+"/forecasts?format=json"
    logger.debug("URL is: "+url)
    payload = {}
    headers = {
        'Authorization': 'Bearer '+ api_key
        }
    response = requests.request("GET", url, headers=headers, data=payload)
    logger.info("HTTP Response code from API call: "+str(response.status_code))
    if response.status_code!=200:
        error_json=json.loads(response.text)
        logger.error("status_code="+str(response.status_code)+" error_code=\""+error_json["response_status"]["error_code"]+"\" message=\""+error_json["response_status"]["message"]+"\"")
    logger.debug("Text Response Returned from API:")
    logger.debug(response.text)
    return response.text


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "get_rooftop_forecast://<input_name>": {
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
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            api_key = get_account_api_key(session_key, input_item.get("account"))
            resource_id = input_item.get("resource_id")
            data = json.loads(get_data_from_api(logger, api_key, resource_id))
            sourcetype = "solcast:forecast"
            logger.info("Size of data returned: "+str(len(data))+" bytes")
            for line in data["forecasts"]:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(line, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )
            
            log.events_ingested(
                logger,
                #normalized_input_name,
                input_name,
                sourcetype,
                len(data),
                input_item.get("index"),
                account=input_item.get("account")
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, msg_before="Exception raised while ingesting data for get_rooftop_forecast: ")
