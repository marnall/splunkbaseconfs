import import_declare_test
import sys
import json
import logging
import traceback
import io
from pathlib import Path
import os
from contextlib import redirect_stdout
from TA_google_chrome_api_calls import GoogleWorkflowCalls
from TA_google_chrome_api_calls import ADDON_NAME
import logevent

from splunklib import modularinput as smi
from solnlib import conf_manager, log

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


def logger_for_input(input_name) -> logging.Logger:
    normalized_input = input_name.split("/")[-1]
    return log.Logs().get_logger(
        f"ta_google_chrome_{normalized_input}"
    )


def get_account_info(session_key, account_name):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-ta_google_chrome_admin_console_connection",
    )
    account_conf_file = cfm.get_conf("ta_google_chrome_admin_console_connection")
    return account_conf_file.get(account_name)


class GoogleChromeLookupCreate(smi.Script):
    def __init__(self):
        super(GoogleChromeLookupCreate, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('google_chrome_lookup_create')
        scheme.description = 'Getting Chrome extension list'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'saccount',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'type_of_query',
                required_on_create=True,
            )
        )

        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):

        def log_summary():

            event_dict = {
                'type': type_of_query,
                'script_logs': repr(call_output)
            }

            event = json.dumps(event_dict)
            source = os.path.basename(sys.argv[0])
            sourcetype = 'google_chrome_lookup_create'
            host = self._input_definition.metadata['server_host']
            index = '_internal'

            logevent.log_event(self._input_definition.metadata, event, source, sourcetype, host, index)

        for input_name, input_item in inputs.inputs.items():
            # create logger instance
            logger = logger_for_input(input_name)
            try:
                session_key = self._input_definition.metadata["session_key"]
                # get log level based on settings conf file
                log_level = conf_manager.get_log_level(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name=f"{ADDON_NAME}_settings",
                )
                logger.setLevel(log_level)

                logger.info("Start Google Chrome lookup generating script.")
                logger.info("Preparing input data.")

                # get api key json file
                api_key = get_account_info(session_key, input_item.get("saccount"))

                type_of_query = input_item.get("type_of_query")
                customerID = api_key.get('customerID')
                sa_key = json.loads(api_key.get('service_account'))
                admin_email = api_key.get('admin_email')
                parent_path = Path(__file__).parents[1]

                logger.info("Type of request: {}".format(type_of_query))
                logger.info("Account used: {}".format(input_item.get("saccount")))
                logger.info("Begin query")

                api_call = GoogleWorkflowCalls(sa_key=sa_key,
                                               customerID=customerID,
                                               admin_email=admin_email)

                f = io.StringIO()
                with redirect_stdout(f):
                    # captures stdout prints into a variable

                    if type_of_query == 'extensions':

                        output_path = parent_path.joinpath('lookups/gc_extension_list.csv')
                        dev_prof_ext_path = parent_path.joinpath('lookups/gc_dev_prof_ext_list.csv')
                        api_call.get_extensions_list(output_path, dev_prof_ext_path)

                    elif type_of_query == 'orgunit':

                        output_path = parent_path.joinpath('lookups/gc_OU_list.csv')
                        api_call.get_OU_list(output_path)

                call_output = f.getvalue()

                logger.info("Query output: {}".format(repr(call_output)))

                logger.info("End google chrome lookup generating script.")

                log_summary()

            except Exception as e:
                logger.error(
                    f"Exception raised while ingesting data for "
                    f"google_chrome_lookup_create: {e}. Traceback: "
                    f"{traceback.format_exc()}"
                )


if __name__ == '__main__':

    exit_code = GoogleChromeLookupCreate().run(sys.argv)
    sys.exit(exit_code)
