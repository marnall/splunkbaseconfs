from json import dumps
from logging import Logger
from sys import argv, exit as sys_exit
from traceback import format_exc
from copy import deepcopy
from re import escape, sub
from typing import Optional
from datetime import timedelta, datetime, timezone
from os import environ, path
from sys import path as sys_path
from pathlib import Path


splunk_home = environ["SPLUNK_HOME"]
ADDON_NAME = "cybersixgill_actionable_alerts"
sys_path.append(path.join(splunk_home, "etc", "apps", ADDON_NAME, "lib"))
sys_path.append(str(Path(__file__).parent.absolute()))

from solnlib import conf_manager, log
from solnlib.splunk_rest_client import SplunkRestClient
from solnlib.modular_input.checkpointer import KVStoreCheckpointer
from splunklib import modularinput as smi
from splunklib.results import JSONResultsReader

from sixgill.sixgill_actionable_alert_client import SixgillActionableAlertClient

from utils import migrate_checkpointer_from_file_to_kvstore


CHANNEL_ID = "7d274d05e666cfa5a95aac2182a142b7"

LAST_X_DAYS = 30
PAGE_SIZE = 10

BLACKLIST_PATTERNS = ["@sixgill-start-highlight@", "@sixgill-end-highlight@"]

def is_exists(client: SplunkRestClient, unique_id: str, query=None, logger: Optional[Logger]=None):
    """Execute query on Splunk to check of existence of record with unique_id.

    Args:
        client (Service): Splunk SDK Service object
        unique_id (str): Unique ID
        query (str, optional): Override query to be executed. Defaults to None.
        logger (Logger, optional): Logging instance. Defaults to None.

    Returns:
        bool: Confirms existence of record in Splunk
    """
    if query is None:
        query = f'search sourcetype="src_cybersixgill_actionable_alert" | where unique_id="{unique_id}" | stats count as total'
    try:
        result_reader = JSONResultsReader(client.jobs.oneshot(query, output_mode='json'))
        result_dict = [r for r in result_reader][0] if result_reader else {}
        return int(result_dict.get("total", 0)) > 0
    except Exception as ex:
        logger.exception(ex) if logger else None
        return False

def remove_patterns(item):
    if isinstance(item, dict):
        return {k: remove_patterns(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [remove_patterns(i) for i in item]
    elif isinstance(item, str):
        return sub(r"|".join(map(escape, BLACKLIST_PATTERNS)), "", item)
    return item


def get_from_and_to_date(
    from_date,
    duration_in_days: int,
    operation="+",
    date_format="%Y-%m-%d %H:%M:%S",
):
    """Calculate from and to date based on operation and duration.

    Args:
        from_date (datetime): From date .ie start date
        duration_in_days (int): Duration in days, should be +ve
        operation (str, optional): Expected values are + and -. Defaults to "+".
        date_format (str, optional): Format for date. Defaults to "%Y-%m-%d %H:%M:%S".

    Raises:
        ValueError: In case of invalid operation. expected are '+' and '-'

    Returns:
        tuple(str, str): from date and to date
    """
    duration = timedelta(days=duration_in_days)
    if operation == "+":
        to_date = from_date + duration
    elif operation == "-":
        to_date = from_date - duration
    else:
        raise ValueError(f"Invalid operation={operation}")
    return format(from_date, date_format), format(to_date, date_format)


def logger_for_input(input_name: str) -> Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_account_api_key(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-cybersixgill_actionable_alerts_account",
    )
    account_conf_file = cfm.get_conf("cybersixgill_actionable_alerts_account")
    return account_conf_file.get(account_name)


def get_data_from_api(logger: Logger, session_key: str,input_name: str, client_id: str, client_secret: str, organization_id: Optional[str]):
    start = 0
    actionable_alerts_client = SixgillActionableAlertClient(
        client_id, client_secret, CHANNEL_ID, logger=logger, verify=True
    )
    kv_chk_pt: KVStoreCheckpointer = migrate_checkpointer_from_file_to_kvstore(session_key, f"{input_name}_last_run")
    # checkpoint_path = Path(splunk_home).absolute() / f"var/lib/splunk/modinputs/{ADDON_NAME}"
    # with suppress(FileExistsError):
    #     checkpoint_path.mkdir(exist_ok=True, parents=True)
    # file_chk_pt = checkpointer.FileCheckpointer(checkpoint_dir=str(checkpoint_path))
    last_run = kv_chk_pt.get(f"{input_name}_last_run")
    if last_run:
        from_date_raw = datetime.fromtimestamp(last_run, timezone.utc)
        from_date = str(from_date_raw.strftime("%Y-%m-%d %H:%M:%S"))
        now = datetime.now(timezone.utc)
        last_run = now.timestamp()
        # file_chk_pt.update(f"{input_name}_last_run", last_run)
        logger.info(f"{from_date} and last_run={last_run}")
    else:
        now = datetime.now(timezone.utc)
        last_run = now.timestamp()
        # file_chk_pt.update(f"{input_name}_last_run", last_run)
        _, from_date = get_from_and_to_date(now, LAST_X_DAYS, operation="-")
        logger.info(f"{from_date} and last_run={last_run}")
    all_alerts = []
    splunk_client = SplunkRestClient(session_key=session_key, app=ADDON_NAME)
    while True:
        actionable_alerts = actionable_alerts_client.get_actionable_alerts_bulk(
            from_date=from_date, limit=PAGE_SIZE, offset=start, sort_order="asc",
            organization_id=organization_id
        )
        logger.info(f"start={start}, offset={PAGE_SIZE}")
        start = start + PAGE_SIZE
        if not actionable_alerts:
            logger.info("Empty response from API")
            break
        logger.info(f"# of actionable alerts received : {len(actionable_alerts)}")

        for actionable_alert in actionable_alerts:
            alert_id = actionable_alert.get("id")
            portal_url = f"https://portal.cybersixgill.com/#/?actionable_alert={alert_id}"
            if "status" not in actionable_alert:
                actionable_alert["status"] = {
                    "status": "treatment_required",
                    "name": "treatment_required",
                    "user": "",
                }
            # Sub alerts logic
            alert_info = actionable_alerts_client.get_actionable_alert(alert_id, organization_id=organization_id) or {}
            es_item = alert_info.get("es_item", {})
            if es_item == "Not Applicable":
                actionable_alert["threat_actor"] = ""
                actionable_alert["threat_source"] = ""
                threat_actor = None
            else:
                threat_actor = alert_info.get("es_item", {}).get(
                    "creator_plain_text"
                ) or alert_info.get("es_item", {}).get("creator")
                threat_actor = threat_actor or ""
                actionable_alert["threat_actor"] = threat_actor
                if threat_actor:
                    actor_source = alert_info.get("es_item", {}).get("site")
                    actionable_alert["threat_source"] = actor_source
                else:
                    actionable_alert["threat_source"] = ""

            sub_alerts = actionable_alert.pop("sub_alerts", [])
            for sub_alert in sub_alerts:
                unique_id = f'{alert_id}__{int(sub_alert.get("aggregate_alert_id"))}'

                if not is_exists(splunk_client, unique_id, logger=logger):
                    sub_item = deepcopy(actionable_alert)
                    sub_item.update(sub_alert)
                    sub_item["unique_id"] = unique_id
                    sub_item["parent_id"] = alert_id
                    sub_item["portal_url"] = portal_url
                    sub_item["alert_info"] = alert_info
                    sub_item = remove_patterns(sub_item)
                    all_alerts.append(sub_item)
                else:
                    logger.info(f"not saving sub_alert with unique id: {unique_id}")

            # Sub alerts logic ends
            if not is_exists(splunk_client, alert_id, logger=logger):
                # logger.info(f"{alert_info=}")
                additional_info = alert_info.get("additional_info", {})
                actionable_alert["parent_id"] = None
                actionable_alert["organization_name"] = additional_info.get("organization_name") or additional_info.get("organization_reference")
                if es_item == "Not Applicable":
                    content = additional_info.get("cve_description")
                else:
                    content = alert_info.get("es_item", {}).get("highlight", {}).get("content")
                    content = content[0] if content and isinstance(content, list) else content
                existing_content = str(actionable_alert["content"])
                logger.info(f"creating alert with id={alert_id}")
                actionable_alert["_time"] = actionable_alert["date"]
                actionable_alert["alert_creation_date"] = datetime.now(timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                actionable_alert["portal_url"] = portal_url
                actionable_alert["content"] = str(content) if content else existing_content
                actionable_alert["matched_assets"] = alert_info.get("matched_assets")
                actionable_alert["sub_alerts_count"] = len(sub_alerts)
                if threat_actor:
                    actor_source = alert_info.get("es_item", {}).get("site")
                    actionable_alert["threat_source"] = actor_source
                    actionable_alert[
                        "actor_url_with_context"
                    ] = f"https://portal.cybersixgill.com/#/actor/{threat_actor}/{actor_source}"
                    actionable_alert[
                        "actor_url_without_context"
                    ] = f"https://portal.cybersixgill.com/#/actor/{threat_actor}/"
                
                # Save alert info
                actionable_alert["alert_info"] = alert_info

                actionable_alert = remove_patterns(actionable_alert)
                all_alerts.append(actionable_alert)
            else:
                logger.info(f"skipping alert with id {alert_id}, it may already exist")
    kv_chk_pt.update(f"{input_name}_last_run", last_run)
    return all_alerts


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("actionable_alerts_input")
        scheme.description = "actionable_alerts_input input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument(
                "name", title="Name", description="Name", required_on_create=True
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        # inputs.inputs is a Python dictionary object like:
        # {
        #   "actionable_alerts_input://<input_name>": {
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
                    conf_name=f"{ADDON_NAME}_settings",
                )
                logger.setLevel(log_level)
                log.modular_input_start(logger, normalized_input_name)
                creds = get_account_api_key(session_key, input_item.get("account"))
                cybersixgill_client_id = creds.get("cybersixgill_client_id", "")
                cybersixgill_client_secret = creds.get("cybersixgill_secret_id", "")
                organization_id = creds.get("cybersixgill_organization_id")
                if not all([cybersixgill_client_id, cybersixgill_client_secret]):
                    continue
                # logger.info(f"info : {cybersixgill_client_id}, {cybersixgill_client_secret}, {organization_id}")
                all_alerts = get_data_from_api(logger, session_key, normalized_input_name , cybersixgill_client_id, cybersixgill_client_secret, organization_id)
                sourcetype = "src_cybersixgill_actionable_alert"
                for alert in all_alerts:
                    event_writer.write_event(
                        smi.Event(
                            data=dumps(alert, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                        )
                    )
                log.events_ingested(
                    logger, input_name, sourcetype, len(all_alerts), input_item.get("index")
                )
                log.modular_input_end(logger, input_name)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"actionable_alerts_input: {e}. Traceback: "
                    f"{format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(argv)
    sys_exit(exit_code)
