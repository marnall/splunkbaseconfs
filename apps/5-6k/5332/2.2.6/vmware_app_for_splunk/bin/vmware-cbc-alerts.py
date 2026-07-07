# - VMware Alert Inputs
#     - Use this page to configure inputs that will pull alerts using the Carbon Black Cloud APIs. If you configure alert input on this page do not also configure alerts using AWS. Doing so may result in duplicate events.
#     - Ref: `CBC Alerts API <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/alerts-api/#alert-search>`_
#     - ``Name``: The generic name this input should be named.
#     - ``Disabled``: This is a checkbox if the input is disabled.
#     - ``Severity``: This is the minimum severity that will be pulled from the API
#     - ``Type``: The Types of alerts to pull from the API.
#     - ``API Configuration``: The API Configuration API Key to use for the API authorization.
#     - ``Proxy``: The proxy configuration, if needed.
#     - ``Lookback (days)``: The number of historical days to pull from the API.
#     - ``Index``: The Splunk Index in which to store the data
#     - ``Interval``: The frequency (in seconds) that the API should poll for data. Range: 60-86400
#     - ``Query``: The Carbon Black Cloud compatible query to limit the alert results.
import logging as logger
import sys
import os
from VMWUtilities import KennyLoggins
from vmware_cbc_client import VmwareCBCModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from vmware_paths import __app_name__

__author__ = 'ksmith'
_MI__app_name__ = 'VMWare Security Alerts Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
kl = KennyLoggins()
log = kl.get_logger(__app_name__, "vmware-cbc-alerts-modularinput", logger.INFO)

modular_input = VmwareCBCModularInput(app_name=__app_name__, scheme={
    "title": "VMWare Security",
    "description": "Provides a view into VMWare SBU",
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
        {"name": "enrich_events",
         "description": "ability to enrich the events",
         "title": "Enrich Events"},
        {"name": "severity",
         "description": "the severity level to pull",
         "title": "Severity",
         "required": True
         },
        {"name": "lookback",
         "description": "how many days to lookback on initial ingest",
         "title": "Lookback",
         "required": True
         },
        {"name": "query",
         "description": "String Query filter",
         "title": "Query"
         },
        {"name": "alert_type",
         "description": "The alert type to pull",
         "title": "Alert Type",
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
    log.info("action=start_modular_input name=vmware-cbc-alerts path={}".format(sys.path))
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_cb()
        modular_input.sourcetype("vmware:cbc:informational")
        modular_input.source("vmware:cbc:input:{}".format(modular_input.get_config("guid")))
        # modular_input.print_event(json.dumps(modular_input.get_config()))
        # UNCOMMENT THIS OUT TO ENABLE additional debug information about the API configuration.
        # modular_input.print_event(json.dumps(tmp_mi_config))
        modular_input.get_alerts()
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
