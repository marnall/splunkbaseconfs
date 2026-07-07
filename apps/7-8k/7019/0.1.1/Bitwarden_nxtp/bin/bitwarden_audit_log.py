import json
import logging
import sys
import traceback

import import_declare_test  # noqa # pylint: disable=unused-import

assert import_declare_test

from datetime import datetime, timedelta
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
from bitwarden import ManagementConnection, Request

ADDON_NAME = "Bitwarden_nxtp"


def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")


def get_config_property(session_key: str, config: str, identifier: str, key: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-{config}",
    )
    conf_file = cfm.get_conf(f"{config}")
    return conf_file.get(identifier).get(key)


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("bitwarden_audit_log")
        scheme.description = "bitwarden_audit_log input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument("name", title="Name", description="Name", required_on_create=True)
        )
        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
                required_on_edit=False,
            )
        )
        scheme.add_argument(
            smi.Argument(
                "start_from",
                title="Start From",
                description="",
                required_on_create=False,
                required_on_edit=False,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        session_key = self._input_definition.metadata["session_key"]
        sourcetype = "bitwarden:audit"
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            # try:
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME.lower()}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            checkpoint = checkpointer.KVStoreCheckpointer(input_name, session_key, ADDON_NAME)
            last_fetch = checkpoint.get("last_fetch_commit")
            logger.info(f"Last fetch: {last_fetch}")
            if last_fetch is None:
                start_from_config = get_config_property(
                    session_key, "inputs", input_name, "start_from"
                )
                start_from = (
                    datetime.strptime(str(start_from_config), "%Y-%m-%d %H:%M:%S")
                    if start_from_config is not None
                    else datetime.now() - timedelta(days=30)
                )
            else:
                start_from = datetime.fromtimestamp(last_fetch)
            new_start_from = datetime.now().timestamp()
            try:
                base_url = get_config_property(
                    session_key=session_key,
                    config=f"{ADDON_NAME.lower()}_account",
                    identifier=input_item.get("account"),
                    key="base_url",
                )
                host = base_url.split("://")[-1]
                api_manager = ManagementConnection(
                    logger=logger,
                    base_url=base_url,
                    auth_url=get_config_property(
                        session_key=session_key,
                        config=f"{ADDON_NAME.lower()}_account",
                        identifier=input_item.get("account"),
                        key="auth_url",
                    ),
                    client_id=get_config_property(
                        session_key=session_key,
                        config=f"{ADDON_NAME.lower()}_account",
                        identifier=input_item.get("account"),
                        key="client_id",
                    ),
                    client_secret=get_config_property(
                        session_key=session_key,
                        config=f"{ADDON_NAME.lower()}_account",
                        identifier=input_item.get("account"),
                        key="client_secret",
                    ),
                )
                event_count = 0
                for event in Request(
                    management_connection=api_manager,
                    endpoint="/public/events",
                    http_request="GET",
                    input_params={"start": datetime.strftime(start_from, "%Y-%m-%d %H:%M:%S")},
                ).execute():
                    del event["object"]
                    timestamp = datetime.timestamp(
                        datetime.strptime(event["date"][:19], "%Y-%m-%dT%H:%M:%S")
                    )
                    if int(timestamp) < int(start_from.timestamp()):
                        continue
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                            source=f"{base_url}/public/events",
                            host=host,
                        )
                    )
                    event_count += 1
                log.events_ingested(logger, normalized_input_name, sourcetype, event_count)
                log.modular_input_end(logger, normalized_input_name)
                checkpoint.update("last_fetch_commit", new_start_from)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"{normalized_input_name}: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
