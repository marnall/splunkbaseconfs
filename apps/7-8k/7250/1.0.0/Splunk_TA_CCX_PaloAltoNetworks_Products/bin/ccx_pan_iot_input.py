import json
import logging
import sys
import traceback
import import_declare_test
import paniot
import datetime
from solnlib import conf_manager, log
from splunklib import modularinput as smi

ADDON_NAME = "Splunk_TA_CCX_PaloAltoNetworks_Products"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-splunk_ta_ccx_paloaltonetworks_products_account",
    )
    account_conf_file = cfm.get_conf("splunk_ta_ccx_paloaltonetworks_products_account")
    return {
        "customerid": account_conf_file.get(account_name).get("customer_id"),
        "access_key_id": account_conf_file.get(account_name).get("api_key_id"),
        "access_key": account_conf_file.get(account_name).get("api_key")
    }


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("ccx_pan_iot_input")
        scheme.description = "ccx_pan_iot_input input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        return scheme
    
    def get_alert_data_from_api(self, logger: logging.Logger, account: dict, normalized_input_name: str, index:str, event_writer: smi.EventWriter):
        logger.info("Getting alert data from an external API")
        sourcetype="pan:iot_alert"
        data = self.service.kvstore["ccx_pan_addon_for_splunk_state"].data
        try:
            state = data.query_by_id(normalized_input_name)["state"]
        except:
            state = None
        count = 0
        args = {
            'type': 'policy_alert'
        }
        if state:
            args["stime"] = state
        latest = None
        with paniot.IotApi(**account) as api:
            for ok, x in api.alerts_all(query_string=args):
                if ok:
                    date_str = x["date"]
                    date = datetime.datetime.fromisoformat(date_str[:-1]).replace(tzinfo=datetime.timezone.utc)
                    if not latest:
                        latest = date
                    elif date > latest:
                        latest = date
                    event_writer.write_event(
                        smi.Event(
                            time=date.astimezone().timestamp(),
                            data=json.dumps(x, ensure_ascii=False, default=str),
                            index=index,
                            sourcetype=sourcetype,
                        )
                    )
                    count += 1
                else:
                    raise paniot.ApiError('%s: %s' % (
                        x.status_code, x.reason))
        log.events_ingested(
            logger, normalized_input_name, sourcetype, count
        )
        if latest:
            # Add 1ms so we don't receive the same event again
            latest_str = (latest + datetime.timedelta(milliseconds=1)).replace(tzinfo=datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            if state:   
                data.update(normalized_input_name, data={"state": latest_str, "input": normalized_input_name})
            else:
                data.insert({"_key": normalized_input_name, "state": latest_str, "input": normalized_input_name})
    
    def get_device_data_from_api(self, logger: logging.Logger, account: dict, normalized_input_name: str, index:str, event_writer: smi.EventWriter):
        logger.info("Getting device data from an external API")
        sourcetype="pan:iot_device"
        data = self.service.kvstore["ccx_pan_addon_for_splunk_state"].data
        try:
            state = data.query_by_id(normalized_input_name)["state"]
        except:
            state = None
        count = 0
        args = {}
        if state:
            args["stime"] = state
        latest = None
        with paniot.IotApi(**account) as api:
            for ok, x in api.devices_all(**args, detail=True, query_string={'filter_monitored': 'yes'}):
                if ok:
                    date_str = x["last_activity"]
                    date = datetime.datetime.fromisoformat(date_str[:-1]).replace(tzinfo=datetime.timezone.utc)
                    if not latest:
                        latest = date
                    elif date > latest:
                        latest = date
                    event_writer.write_event(
                        smi.Event(
                            time=date.astimezone().timestamp(),
                            data=json.dumps(x, ensure_ascii=False, default=str),
                            index=index,
                            sourcetype=sourcetype,
                        )
                    )
                    count += 1
                else:
                    raise paniot.ApiError('%s: %s' % (
                        x.status_code, x.reason))
        log.events_ingested(
            logger, normalized_input_name, sourcetype, count
        )
        if latest:
            # Add 1ms so we don't receive the same event again
            latest_str = (latest + datetime.timedelta(milliseconds=1)).replace(tzinfo=datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            if state:   
                data.update(normalized_input_name, data={"state": latest_str, "input": normalized_input_name})
            else:
                data.insert({"_key": normalized_input_name, "state": latest_str, "input": normalized_input_name})

    def get_vulnerability_data_from_api(self, logger: logging.Logger, account: dict, normalized_input_name: str, index:str, event_writer: smi.EventWriter):
        logger.info("Getting vulnerability data from an external API")
        sourcetype="pan:iot_vulnerability"
        data = self.service.kvstore["ccx_pan_addon_for_splunk_state"].data
        try:
            state = data.query_by_id(normalized_input_name)["state"]
        except:
            state = None
        count = 0
        args = {
            "groupby": "device"
        }
        if state:
            args["stime"] = state
        latest = None
        with paniot.IotApi(**account) as api:
            for ok, x in api.vulnerabilities_all(**args):
                if ok:
                    date_str = x["date"]
                    date = datetime.datetime.fromisoformat(date_str[:-1]).replace(tzinfo=datetime.timezone.utc)
                    if not latest:
                        latest = date
                    elif date > latest:
                        latest = date
                    event_writer.write_event(
                        smi.Event(
                            time=datetime.datetime.fromisoformat(x["detected_date"][0][:-1]).replace(tzinfo=datetime.timezone.utc).astimezone().timestamp(),
                            data=json.dumps(x, ensure_ascii=False, default=str),
                            index=index,
                            sourcetype=sourcetype,
                        )
                    )
                    count += 1
                else:
                    raise paniot.ApiError('%s: %s' % (
                        x.status_code, x.reason))
        log.events_ingested(
            logger, normalized_input_name, sourcetype, count
        )
        if latest:
            # Add 1ms so we don't receive the same event again
            latest_str = (latest + datetime.timedelta(milliseconds=1)).replace(tzinfo=datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            if state:   
                data.update(normalized_input_name, data={"state": latest_str, "input": normalized_input_name})
            else:
                data.insert({"_key": normalized_input_name, "state": latest_str, "input": normalized_input_name})

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        # inputs.inputs is a Python dictionary object like:
        # {
        #   "ccx_pan_iot_input://<input_name>": {
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
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=f"splunk_ta_ccx_paloaltonetworks_products_settings",
                )
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                account = get_account(session_key, input_item.get("account"))
                type = input_item.get("log_type")

                if type == "vulnerability":
                    self.get_vulnerability_data_from_api(logger, account, normalized_input_name, input_item.get("index"), event_writer)
                if type == "device":
                    self.get_device_data_from_api(logger, account, normalized_input_name, input_item.get("index"), event_writer)
                if type == "alert":
                    self.get_alert_data_from_api(logger, account, normalized_input_name, input_item.get("index"), event_writer)
                log.modular_input_end(logger, normalized_input_name)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"ccx_pan_iot_input: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
