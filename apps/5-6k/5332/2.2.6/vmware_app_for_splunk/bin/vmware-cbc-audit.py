# - VMware Audit Log Inputs
#     - Use this tab to configure inputs that will pull the CBC Console audit logs.
#     - Ref: `CBC Audit Log Events <https://developer.carbonblack.com/reference/carbon-black-cloud/cb-defense/latest/rest-api/#audit-log-events>`_
#     - ``Name``: The generic name this input should be named.
#     - ``Disabled``: This is a checkbox if the input is disabled.
#     - ``API Token``: The API Configuration API Key to use for the API authorization.
#     - ``Proxy``: The proxy configuration, if needed.
#     - ``Index``: The Splunk Index in which to store the data
#     - ``Interval``: The frequency (in seconds) that the API should poll for data. Range: 60-86400

import logging as logger
import sys
import os
from VMWUtilities import KennyLoggins
from vmware_cbc_client import VmwareCBCModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from vmware_paths import __app_name__

__author__ = 'ksmith'
_MI__app_name__ = 'VMWare Security Audit Logs Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
kl = KennyLoggins()
log = kl.get_logger(__app_name__, "vmware-cbc-auditlogs-modularinput", logger.INFO)

modular_input = VmwareCBCModularInput(app_name=__app_name__, scheme={
    "title": "VMWare Audit Logs Ingest",
    "description": "Gathers the Queue-like logs from the Audit Logs",
    "args": [
        {"name": "guid",
         "description": "distinct guid",
         "title": "GUID",
         "required": True
         },
        {"name": "input_name",
         "description": "descriptive name",
         "title": "Name",
         "required": True
         },
        {"name": "credential_guid",
         "description": "The tenant guid for authentication.",
         "title": "Tenant Guid",
         "required": True
         }
    ]
})


def run():
    log.info("action=start_modular_input name=vmware-cbc-audit path={}".format(sys.path))
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_cb()
        modular_input.sourcetype("vmware:cbc:informational")
        modular_input.source("vmware:cbc:input:{}".format(modular_input.get_config("guid")))
        modular_input.get_audit()
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
