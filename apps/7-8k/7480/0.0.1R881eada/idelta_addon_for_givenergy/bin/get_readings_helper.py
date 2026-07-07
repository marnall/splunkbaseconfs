import json
import logging
import requests

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi


ADDON_NAME = "idelta_addon_for_givenergy"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-idelta_addon_for_givenergy_account",
    )
    account_conf_file = cfm.get_conf("idelta_addon_for_givenergy_account")
    return account_conf_file.get(account_name).get("api_key")


def get_data_from_api(logger: logging.Logger, api_key: str, serial_no:str):
    logger.info("Getting data from an external API")
    url = "https://api.givenergy.cloud/v1/inverter/"+serial_no+"/system-data/latest"
    logger.debug("URL being called:" + url)
    logger.debug("Constructing header with API key")
    header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'}
    header['Authorization']= "Bearer " + api_key
    logger.debug("header constructed as python dict: " + str(header))
    payload={}
    response = requests.request("GET", url, headers=header, data=payload)
    logger.info("API call status code: " + str(response.status_code))
    logger.debug("Response: " + response.text)
    return response.text


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "get_readings://<input_name>": {
    #     "account": "<account_name>",
    #     "serial_no": "<inverter_serial_no>",
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
            inverter_serial_number = input_item.get("serial_no")
            data = get_data_from_api(logger, api_key, inverter_serial_number)
            sourcetype = "givenergy:inverter:systemdata"
            event_writer.write_event(
                    smi.Event(
                        data=data,
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )
            
            """
            for line in data:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(line, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )
            """
            
            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(data),
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "Error getting data for input", msg_before="Exception raised while ingesting data for " +input_name)
