import logging as logger
import sys
import os
from Utilities import KennyLoggins
from google_constants import app_name as _APP_NAME
from google_client import GSuiteModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

__author__ = 'ksmith'
_MI_APP_NAME = 'GoogleWorkspaceForSplunk Admin Reports Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
sys.path.insert(0, make_splunkhome_path(["etc", "apps", _APP_NAME, "lib"]))
kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "admin-reports-modularinput", logger.INFO)

modular_input = GSuiteModularInput(app_name=_APP_NAME, scheme={
    "title": "Google Workspaces Admin Reports",
    "description": "Consumes Admin Reports from GWorkspaces",
    "args": [
        {"name": "guid",
         "description": "distinct guid",
         "title": "GUID",
         "required": True
         },
        {"name": "input_name",
         "description": "The unique input name",
         "title": "Input Name",
         "required": True
         },
        {"name": "lookback",
         "description": "how many days to lookback on initial ingest",
         "title": "Lookback"
         },
        {"name": "application_name",
         "description": "Google Workspaces Admin SDK Application Name to consume",
         "title": "Application Name",
         "required": True
         },
        {"name": "credential",
         "description": "The API Key guid for authentication.",
         "title": "API Key Guid",
         "required": True
         }
    ]
})


def run():
    log.info("action=start_modular_input path={}".format(sys.path))
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_gw("admin_sdk_report")
        modular_input.sourcetype("google:workspaces:informational")
        modular_input.source("google:workspaces:input:{}".format(modular_input.get_config("guid")))
        applications = modular_input.get_config("application_name").split(",")
        if not isinstance(applications, list):
            applications = [applications]
        for application in applications:
            try:
                modular_input.get_admin_report(app_name=application)
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
                            "application_name=\"{}\"" \
                            "input_name=\"{}\" " \
                    .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno,
                            modular_input.get_config("guid"),
                            application,
                            modular_input.get_config("input_name"))
                log.error("{}".format(error_msg))
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
