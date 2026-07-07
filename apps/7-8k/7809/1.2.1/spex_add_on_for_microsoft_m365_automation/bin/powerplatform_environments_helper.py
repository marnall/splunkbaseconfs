import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import json
import logging
import requests
import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from spex_m365_automation import settings, auth, environments
from spex_m365_automation.checkpoint import Checkpoint
from spex_m365_automation.settings import get_proxy_settings


ADDON_NAME = "spex_add_on_for_microsoft_m365_automation"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
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

             # Load proxy settings if enabled
            use_proxy = input_item.get("use_proxy", "0") in ("1", "true", "True")
            proxies = get_proxy_settings(session_key, logger=logger) if use_proxy else None


            # Get config
            appreg = settings.get_appreg_config(session_key, input_item.get("app_registration"))
            CLIENT_ID = appreg.get("client_id")
            CLIENT_SECRET = appreg.get("client_secret")
            TENANT_ID = appreg.get("tenantId")
            CLOUD = appreg.get("cloud_type", "public")

            token = auth.get_client_credentials_token(CLIENT_ID, CLIENT_SECRET, TENANT_ID, cloud=CLOUD, proxies=proxies)

            cp = Checkpoint(
                session_key=session_key,
                input_name=normalized_input_name,
                app_name=ADDON_NAME,
                use_kv_store=True
            )

            cp_key = f"{normalized_input_name}_last_modified"
            last_run = cp.get(cp_key, default="1970-01-01T00:00:00Z")
            logger.info(f"Last checkpoint for {input_name}: {last_run}")
            last_checkpoint_ts = dateparser.parse(last_run)
            adjusted_ts = last_checkpoint_ts - timedelta(seconds=1)
            last_run_str = adjusted_ts.isoformat()

            # Fetch environments
            envs_list = environments.get_environments(token, last_modified=last_run_str, expand=True, cloud=CLOUD, proxies=proxies)
            latest_event_ts = adjusted_ts
            sourcetype = "environments"

            for env in envs_list:
                env_time_str = env.get("properties", {}).get("lastModifiedTime")
                logger.debug(f"Env: {env.get('name')} | Modified: {env_time_str} | Checkpoint: {last_checkpoint_ts.isoformat()}")

                if env_time_str:
                    env_ts = dateparser.parse(env_time_str)
                    if env_ts > last_checkpoint_ts:
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(env, ensure_ascii=False, default=str),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                            )
                        )
                        if env_ts > latest_event_ts:
                            latest_event_ts = env_ts
                    else:
                        logger.debug(f"Skipped env {env.get('name')} — too old.")


            # Only update if something newer was found
            if latest_event_ts > last_checkpoint_ts:
                cp.update(cp_key, latest_event_ts.isoformat())
                logger.info(f"Updated checkpoint to {latest_event_ts.isoformat()} for key: {cp_key}")
            else:
                logger.info("No newer environments found; checkpoint not updated.")

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(envs_list),
                input_item.get("index"),
                account=input_item.get("appreg"),
            )
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(logger, e, "environments_error", msg_before="Exception while ingesting environment data:")
