import json
import os
from datetime import datetime, timedelta, timezone

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi

from maze_api_client import MazeAPIClient

ADDON_NAME = "maze_security"
CHECKPOINT_FILE = "maze_investigations_search_checkpoint"


def logger_for_input(input_name):
    return log.Logs().get_logger(f"{ADDON_NAME}_{input_name}")


def get_account_credentials(session_key, account_name):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{ADDON_NAME}_account",
    )
    account_conf = cfm.get_conf(f"{ADDON_NAME}_account")
    account = account_conf.get(account_name)
    return account.get("api_key"), account.get("api_url")


def checkpoint_dir(input_type):
    path = os.path.join(
        os.environ.get("SPLUNK_HOME", "/opt/splunk"),
        "var", "lib", "splunk", "modinputs", input_type,
    )
    os.makedirs(path, exist_ok=True)
    return path


def load_checkpoint(input_type, key):
    path = os.path.join(checkpoint_dir(input_type), key)
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    return None


def save_checkpoint(input_type, key, value):
    path = os.path.join(checkpoint_dir(input_type), key)
    with open(path, "w") as f:
        f.write(value)


def validate_input(definition):
    return


def stream_events(inputs, event_writer):
    for input_name, input_item in inputs.inputs.items():
        normalized_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_name)

        try:
            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_name)

            account_name = input_item.get("account")
            api_key, api_url = get_account_credentials(session_key, account_name)
            client = MazeAPIClient(api_url, api_key, logger=logger)

            ckpt_key = f"{CHECKPOINT_FILE}_{normalized_name}"
            updated_from = load_checkpoint("maze_investigations_search", ckpt_key)

            if not updated_from:
                backfill_days = int(input_item.get("backfill_days", "0") or "0")
                if backfill_days > 0:
                    updated_from = (
                        datetime.now(timezone.utc) - timedelta(days=backfill_days)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                    logger.info(
                        "No checkpoint found, backfilling %d days (from %s)",
                        backfill_days, updated_from,
                    )

            latest_updated_at = updated_from
            count = 0

            for investigation in client.search_investigations_all(
                updated_from=updated_from
            ):
                inv_id = investigation.get("id", "")
                inv_ts = investigation.get("updated_at", "")
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(investigation),
                        index=input_item.get("index", "default"),
                        sourcetype="maze:investigations",
                        source=f"maze:investigations:search:{inv_id}",
                        host="maze_api",
                        time=inv_ts,
                    )
                )
                count += 1

                if inv_ts and (not latest_updated_at or inv_ts > latest_updated_at):
                    latest_updated_at = inv_ts

            if latest_updated_at:
                save_checkpoint("maze_investigations_search", ckpt_key, latest_updated_at)

            log.events_ingested(
                logger, input_name, "maze:investigations", count,
                input_item.get("index"), account=account_name,
            )
            log.modular_input_end(logger, normalized_name)

        except Exception as e:
            logger.error("Error in maze_investigations_search: %s", str(e), exc_info=True)
