import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import json
import logging
import import_declare_test
from spex_m365_automation.settings import get_appreg_config, get_svc_account_config, get_proxy_settings
from spex_m365_automation.checkpoint import Checkpoint
from spex_m365_automation.orchestrators.flows_collector import collect_flows
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from dateutil import parser as dateparser
from datetime import datetime, timedelta, timezone


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

            #Get App Registration and Service Account
            appreg = get_appreg_config(session_key, input_item.get("app_registration"))
            svcacct = get_svc_account_config(session_key, input_item.get("service_account"))

             # Load proxy settings if enabled
            use_proxy = input_item.get("use_proxy", "0") in ("1", "true", "True")
            proxies = get_proxy_settings(session_key, logger=logger) if use_proxy else None


            client_id = appreg.get("client_id")
            client_secret = appreg.get("client_secret")
            tenant_id = appreg.get("tenantId")
            cloud = appreg.get("cloud_type", "public")
            username = svcacct.get("username")
            password = svcacct.get("api_key")

            #Checkpoint
            cp = Checkpoint(
                session_key=session_key,
                input_name=normalized_input_name,
                app_name=ADDON_NAME,
                use_kv_store=True
            )

            cp_key = f"{normalized_input_name}_last_modified"

            last_run = cp.get(cp_key, default="1970-01-01T00:00:00Z")
            logger.info(f"Last checkpoint for {input_name}: {last_run}")

            # Parse and adjust timestamp
            last_checkpoint_ts = dateparser.parse(last_run)
            adjusted_ts = last_checkpoint_ts - timedelta(seconds=1)
            
            last_run_str = adjusted_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

            #Collect Flows
            flows = collect_flows(
                client_id=client_id,
                client_secret=client_secret,
                tenant_id=tenant_id,
                username=username,
                password=password,
                last_run=last_run_str,
                logger=logger,
                cloud=cloud,
                proxies=proxies
            )

            # Write to Splunk only new events
            now = datetime.now(timezone.utc)
            latest_timestamp = adjusted_ts
            sourcetype = "flows"

            for flow in flows:
                env_time_str = flow.get("properties", {}).get("lastModifiedTime")
                logger.debug(f"Flow: {flow.get('name')} | Modified: {env_time_str} | Checkpoint: {last_checkpoint_ts.isoformat()}")

                if env_time_str:
                    env_ts = dateparser.parse(env_time_str)
                    if env_ts <= last_checkpoint_ts:
                        logger.debug(f"Skipped flow {flow.get('name')} — too old.")
                        continue
                    if env_ts > latest_timestamp:
                        latest_timestamp = env_ts

                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(flow, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                    )
                )

            
            # Safety margin: if the latest timestamp is older than now, save "now"
            if latest_timestamp < now:
                latest_timestamp = now
                logger.debug("Latest event is older than now, updating checkpoint to current time.")

            # Save new checkpoint
            cp.update(cp_key, latest_timestamp.isoformat())
            logger.info(f"Updated checkpoint to {latest_timestamp.isoformat()} for key: {cp_key}")

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(flows),
                input_item.get("index"),
                account=input_item.get("service_account")
            )
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(logger, e, "flow ingestion error", msg_before="Exception while ingesting flows: ")