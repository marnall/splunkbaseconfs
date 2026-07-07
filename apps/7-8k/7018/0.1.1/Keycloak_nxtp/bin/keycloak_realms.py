import json
import logging
import sys
import traceback

import import_declare_test  # noqa # pylint: disable=unused-import

assert import_declare_test

from solnlib import conf_manager, log
from splunklib import modularinput as smi
from keycloak import ManagementConnection, Request


ADDON_NAME = "Keycloak_nxtp"


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
        scheme = smi.Scheme("keycloak_realms")
        scheme.description = "keycloak_realms input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False
        scheme.add_argument(
            smi.Argument("name", title="Name", description="Name", required_on_create=True)
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, event_writer: smi.EventWriter):
        session_key = self._input_definition.metadata["session_key"]
        sourcetype = "keycloak:realm"

        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = logger_for_input(normalized_input_name)
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name=f"{ADDON_NAME.lower()}_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
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
                host = api_manager.host.split("://")[-1]
                for realm in Request(
                    management_connection=api_manager,
                    endpoint="realms",
                    http_request="GET",
                ).execute():
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(realm),
                            source=f"{host}:realms",
                            sourcetype=sourcetype,
                            host=host,
                        )
                    )
                    event_count += 1
                log.events_ingested(logger, normalized_input_name, sourcetype, event_count)
                log.modular_input_end(logger, normalized_input_name)
            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"{normalized_input_name}: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
