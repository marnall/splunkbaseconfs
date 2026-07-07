import logging as logger
import sys
import os
from Utilities import KennyLoggins
from google_constants import app_name as _APP_NAME
from google_client import GSuiteModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

__author__ = 'ksmith'
_MI_APP_NAME = 'GoogleWorkspaceForSplunk Big Query Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "bigquery-modularinput", logger.INFO)

modular_input = GSuiteModularInput(app_name=_APP_NAME, scheme={
    "title": "Google Workspaces Big Query Data",
    "description": "Consumes Big Query Data from GWorkspaces",
    "args": [
        {"name": "guid",
         "description": "distinct guid",
         "title": "GUID",
         "required": True
         },
        {"name": "max_rows", "description": "The Big Query Number of rows to pull per interval", "title": "Max Rows"},
        {"name": "project", "description": "The Big Query Project", "title": "Project", "required": True},
        {"name": "table", "description": "The Big Query table", "title": "Table", "required": True},
        {"name": "dataset", "description": "The Big Query dataset", "title": "Dataset", "required": True},
        {"name": "start_row", "description": "The row number to start from", "title": "Starting Row"},
        {"name": "ingest_type", "description": "The ingest type. row or time", "title": "Ingest Type"},
        {"name": "credential",
         "description": "The API Key guid for authentication.",
         "title": "API Key Guid",
         "required": True
         }
    ]
})


def run():
    log.info("action=start_modular_input name=ga_bigquery")
    modular_input.set_logger(log)
    modular_input.start()
    try:

        modular_input.sourcetype("google:workspaces:informational")
        modular_input.source("google:workspaces:input:{}".format(modular_input.get_config("guid")))
        modular_input.setup_gw("bigquery")
        my_table = modular_input.get_config("table")
        if my_table == "*" or modular_input.get_config("ingest_type") == "vrow":
            modular_input.bigquery_ingest_all_tables()
        else:
            it = modular_input.get_config("ingest_type")
            activities_log = False
            if it == "activities_log":
                it = "row"
                activities_log = True
            modular_input.get_table_results(modular_input.get_config("table"), it, activity_logs=activities_log)

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, modular_input.get_config("guid"),
                    modular_input.get_config("input_name"))
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
