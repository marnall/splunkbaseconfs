import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

import json
import logging
from datetime import datetime, timezone
from dateutil import parser as dateparser

import import_declare_test
from solnlib import conf_manager, log
from spex_m365_automation import auth
from spex_m365_automation.checkpoint import Checkpoint
from spex_m365_automation.settings import get_appreg_config, get_svc_account_config, get_proxy_settings
from spex_m365_automation.orchestrators.flow_runs_collector import collect_flow_runs
from splunklib import modularinput as smi

ADDON_NAME = "spex_add_on_for_microsoft_m365_automation"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def validate_input(definition: smi.ValidationDefinition):
    return

def stream_events(inputs: smi.InputDefinition, ew: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:
            start_time = datetime.now(timezone.utc)

            session_key = inputs.metadata["session_key"]
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # Credentials
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

            include_actions = input_item.get("include_actions", "0") in ("1", "true", "True")

            # Auth
            mgmt_token = auth.get_client_credentials_token(client_id, client_secret, tenant_id, cloud=cloud, proxies=proxies)
            flow_token = auth.get_password_grant_token(client_id, username, password, tenant_id, cloud=cloud, proxies=proxies)

            cp = Checkpoint(session_key, normalized_input_name, ADDON_NAME)

            # Retrieve and write runs
            runs, action_count, env_count, flow_count = collect_flow_runs(
                env_token=mgmt_token,
                run_token=flow_token,
                checkpoint=cp,
                logger=logger,
                include_actions=include_actions,
                cloud=cloud,
                proxies=proxies
            )


            logger.info(f"[{normalized_input_name}] Ingested {len(runs)} runs, {action_count} actions")

            for run in runs:
                ew.write_event(smi.Event(
                    data=json.dumps(run, ensure_ascii=False, default=str),
                    index=input_item.get("index"),
                    sourcetype="flow_runs"
                ))

            # Emit summary event
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()

            summary_event = {
                "input": "flow_runs",
                "run": input_name,
                "timestamp": end_time.isoformat(),
                "environments_checked": env_count,
                "flows_checked": flow_count,
                "flow_runs_ingested": len(runs),
                "flow_actions_ingested": action_count,
                "include_actions": include_actions,
                "duration_seconds": duration
            }


            ew.write_event(smi.Event(
                data=json.dumps(summary_event, ensure_ascii=False),
                index=input_item.get("index"),
                sourcetype="flow_run_summary"
            ))

            log.events_ingested(
                logger,
                input_name,
                "flow_runs",
                len(runs),
                input_item.get("index"),
                account=input_item.get("app_registration")
            )
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(logger, e, "flow_runs_error", msg_before="Exception while collecting flow runs:")
