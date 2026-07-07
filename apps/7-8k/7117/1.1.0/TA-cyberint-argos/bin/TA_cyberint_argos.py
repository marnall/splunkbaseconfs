import http
import json
import sys
import traceback

import import_declare_test
import utils
from argos_client import CyberintClient, get_data_from_api
from requests.cookies import RequestsCookieJar
from rest_client import InvalidResponse
from solnlib import conf_manager, server_info
from splunklib import modularinput as smi


class Input(smi.Script):
    def __init__(self):
        super().__init__()

    def get_scheme(self):
        scheme = smi.Scheme("TA_cyberint_argos")
        scheme.description = "Cyberint Argos input"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                "name",
                title="Name",
                description="Name",
                required_on_create=True
            )
        )

        scheme.add_argument(
            smi.Argument(
                "client_name",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "instance_domain",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "environment",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "types",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "severities",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "statuses",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "start_time",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "max_fetch",
                required_on_create=True,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "include_csv",
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                "account",
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        """
        Validate the input arguments in the application.

        Args:
            definition (smi.ValidationDefinition): Input definition arguments.

        Raises:
            ValueError: In case of error during the connection to Argos API.
        """
        session_key = definition.metadata["session_key"]

        server_information = server_info.ServerInfo(session_key)

        if utils.is_lower_version(version=server_information.version):
            return

        api_key = utils.get_account_api_key(session_key, definition.parameters["account"])

        proxies = utils.get_proxy_settings(session_key)

        app_version = utils.get_version(session_key)

        logger = utils.logger_for_input(definition.metadata["name"])

        logger.info(f"Application version: {app_version}")

        logger.debug(f"Proxy settings: {proxies}")

        try:
            client = CyberintClient(
                version=app_version,
                client_name=definition.parameters["client_name"],
                instance_domain=definition.parameters["instance_domain"],
                access_token=api_key,
                input_name=definition.metadata["name"],
                proxies=proxies,
            )

            logger.info("API client during test connection successfully created")

            # check environment is provided by user in test connection, run the call the environments parameter.
            if "environment" in definition.parameters:
                environments = utils.string_to_list(definition.parameters["environment"])
                client.list_alerts(page=1, page_size=100, environments=environments)
            else:
                # If environment is None, run the call without the environments parameter
                client.list_alerts(page=1, page_size=100)
        except InvalidResponse as err:
            # Log the full error for debugging purposes
            decoded_error = str(err)
            logger.warning(f"API Client Error: {err}")
            # Handle specific HTTP status codes
            if err.response.status_code == http.HTTPStatus.UNAUTHORIZED:
                raise ValueError("Unauthorized: Please check your API key and permissions.")
            elif err.response.status_code == http.HTTPStatus.FORBIDDEN:
                raise ValueError("Forbidden: You do not have permission to perform this action.")
            elif err.response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY:
                raise ValueError("Unprocessable Entity: Please check your input values.")
            elif err.response.status_code == http.HTTPStatus.CONFLICT:
                raise ValueError("Conflict: The requested resource already exists.")
            elif err.response.status_code == http.HTTPStatus.BAD_REQUEST:
                if "environment" in decoded_error:
                    env = utils.extract_environment_value(decoded_error)
                    raise ValueError(
                        f"Bad Request: The environment {env} is unrecognized. "
                        "Please verify your input or consult the documentation."
                    )
                else:
                    raise ValueError(f"Invalid response: {err}")
            else:
                # Raise a generic user-friendly error message for other errors
                raise ValueError(
                    "There was an error validating your inputs during test connection. \
                    Please check application log and try again."
                )
        except Exception as err:
            # Handle unexpected errors.
            logger.error(f"Unexpected error: {str(err)}")
            raise ValueError(
                f"An unexpected error occurred during validation of input parameters for Cyberint data input, \
                    Detailed error: {str(err)}"
            )

    def stream_events(self, inputs, event_writer: smi.EventWriter):
        """
        inputs.inputs is a Python dictionary object like:
        {
        "cyberint://<input_name>": {
            "account": "<account_name>",
            "disabled": "0",
            "host": "$decideOnStartup",
            "index": "<index_name>",
            "interval": "<interval_value>",
            "python.version": "python3",
        }
        """
        for input_name, input_item in inputs.inputs.items():
            normalized_input_name = input_name.split("/")[-1]
            logger = utils.logger_for_input(normalized_input_name)

            logger.debug(f"Initiating event stream for input: {normalized_input_name}.")
            checkpoint_filename = self._get_checkpoint_filename(
                checkpoint_dir=inputs.metadata["checkpoint_dir"],
                input_name=input_name,
            )
            logger.debug(f"Initiating event stream for checkpoint filename: {checkpoint_filename}.")
            try:
                session_key = self._input_definition.metadata["session_key"]
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=utils.ADDON_PATH,
                    conf_name="ta_cyberint_argos_settings",
                )
                logger.setLevel(log_level)
                logger.debug(logger, normalized_input_name)

                # Get last run to fetch data
                input_start_time = input_item.get("start_time")
                last_run = utils.get_last_run(
                    input_start_time=input_start_time, checkpoint_filename=checkpoint_filename, logger=logger
                )
                logger.debug(f"from input last_run is: {input_item.get('start_time')}")
                logger.info(f"Initial last_run: {last_run}")

                # Get data from api
                api_key = utils.get_account_api_key(session_key, input_item.get("account"))
                proxies = utils.get_proxy_settings(session_key)
                app_version = utils.get_version(session_key)

                data = get_data_from_api(
                    logger=logger,
                    version=app_version,
                    api_key=api_key,
                    input_data=input_item,
                    input_name=normalized_input_name,
                    last_run=last_run,
                    proxies=proxies,
                )

                if len(data) > 0:
                    # Check for new last run to update
                    new_last_run = utils.handle_update_last_run(last_run=last_run, alerts=data, logger=logger)
                    logger.info(f"New last_run after fetching data: {new_last_run}")

                    # Start streaming events to splunk
                    sourcetype = utils.ADDON_NAME
                    logger.info(f"Streaming {len(data)} events to Splunk...")
                    for line in data:
                        event_writer.write_event(
                            smi.Event(
                                stanza=normalized_input_name,
                                data=json.dumps(line, ensure_ascii=False, default=str),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                                source=normalized_input_name,
                            )
                        )
                        logger.debug(logger, normalized_input_name, sourcetype, len(data))
                        logger.debug(logger, normalized_input_name)

                    # Try to update new last run
                    try:
                        utils.update_last_run(
                            last_run=new_last_run,
                            start_time=input_start_time,
                            filename=checkpoint_filename,
                            logger=logger,
                        )
                    except Exception as e:
                        logger.error(f"Error while updating last_run: {e}")
                else:
                    logger.info("No events to stream to Splunk.")

            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"Cyberint: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )

    @staticmethod
    def _get_checkpoint_filename(checkpoint_dir: str, input_name: str) -> str:
        filename = checkpoint_dir + "/" + input_name[input_name.find("://") + 3 :].lower().replace(" ", "_")
        return filename


if __name__ == "__main__":
    exit_code = Input().run(sys.argv)
    sys.exit(exit_code)
