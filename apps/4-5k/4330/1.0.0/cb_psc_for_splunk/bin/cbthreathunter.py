import logging as logger
import sys
from Utilities import KennyLoggins, Utilities
from cb_client import cb_client
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from ModularInput import ModularInput
import os
import time

__author__ = 'ksmith'

_MI_APP_NAME = 'Cb ThreatHunter For Splunk Modular Input'
_APP_NAME = 'cb_psc_for_splunk'

_SPLUNK_HOME = make_splunkhome_path([""])

kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "modularinput", logger.INFO)


def current_milli_time():
    return float(time.time())


class cb_psc_for_splunkModularInput(ModularInput):
    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)

    def _validate_arguments(self, val_data):
        """
        :param val_data: The data that requires validation.
        :return:
        RAISE an error if the arguments do not validate correctly. The default is just "True".
        """
        self.log.debug("action=validate_arguments arguments={}".format(val_data))
        return True


MI = cb_psc_for_splunkModularInput(app_name=_APP_NAME, scheme={
    "title": "Cb ThreatHunter For Splunk",
    "description": "CarbonBlack ThreatHunter integration for Splunk.",
    "args": [
        {"name": "hostname",
         "description": "This is the CarbonBlack host to connect with.",
         "title": "Hostname",
         "required": True
         },
        {"name": "connector_id",
         "description": "This is the connector ID configured within CarbonBlack",
         "title": "Connector ID",
         "required": True
         },
        {"name": "verify_ssl", "description": "SSL Should verify REST Calls", "title": "Verify SSL",
         "required": False},
        {"name": "proxy_name", "description": "Set to 'not_configured' if no proxy", "title": "Proxy Name", "required": False}
    ]
})


def run():
    MI.start()
    start_mod_input = current_milli_time()
    try:
        MI.config()
        log.info("action=starting logic=modular_input")
        use_proxy = False
        verify_ssl = MI.get_config("verify_ssl")
        proxy_name = MI.get_config("proxy_name")
        log.info("proxy_name={} verify_ssl={}".format(proxy_name, verify_ssl))
        if proxy_name is not None:
            if len(proxy_name) > 0 and proxy_name != "not_configured":
                use_proxy = True
        else:
            log.info("action=variable_check use_proxy={} skipping test")
        if verify_ssl is None:
            verify_ssl = True
        else:
            if verify_ssl == "false" or verify_ssl == "0":
                verify_ssl = False
            else:
                verify_ssl = True
        log.info("action=variable_check use_proxy={} verify_ssl={}".format(use_proxy, verify_ssl))

        utils = Utilities(app_name=_APP_NAME, session_key=MI.get_config("session_key"))

        MI.host(MI.get_config("hostname"))
        MI.source(MI.get_config("name"))

        RESTConfiguration = {
            "auth":
                {"type": "token",
                 "token": "{1}/{0}".format(MI.get_config("connector_id"),
                                           utils.get_credential(_APP_NAME, MI.get_config("connector_id"))),
                 "authorization_string": "%s"
                 },
            "hostname": MI.get_config("hostname"),
            "verify_certificate": verify_ssl
        }
        if use_proxy:
            RESTConfiguration["proxy"] = utils.get_proxy_configuration(MI.get_config("proxy_name"))
        rest_client = cb_client(_APP_NAME, RESTConfiguration, MI)

        current_endpoints = {"notifications": rest_client.get_notifications}
        checkpoint_time = time.time()

        for endpoint, func in current_endpoints.items():
            try:
                base_chk = {"checkpoint_name": endpoint, "modular_input": _APP_NAME}
                chk = MI._get_checkpoint(endpoint)
                if chk is None:
                    chk = {}
                if "last_time" not in chk:
                    chk["last_time"] = 1
                chk.update({x: y for x, y in base_chk.items() if x not in chk})
                last_checkpoint_time = chk["last_time"]
                chk["last_time"] = checkpoint_time
                start_endpoint = current_milli_time()
                if func():
                    MI._set_checkpoint(endpoint, object=chk)
                end_endpoint = current_milli_time()
                log.info("endpoint={} duration={}".format(endpoint, end_endpoint - start_endpoint))
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                jsondump = {"message": str((e)),
                            "exception_type": "%s" % type(e).__name__,
                            "exception_arguments": "%s" % e,
                            "filename": fname,
                            "exception_line": exc_tb.tb_lineno,
                            "input": MI.get_config("name"),
                            "endpoint": endpoint
                            }
                log.error("action=endpoint_error endpoint={} {} {}".format(endpoint, e, jsondump))
        end_mod_input = current_milli_time()
        log.info("action=ending logic=modular_input duration={}".format(end_mod_input - start_mod_input))
    except Exception, e:
        end_mod_input = current_milli_time()
        log.info("action=error_global_ending logic=modular_input duration={}".format(end_mod_input - start_mod_input))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        jsondump = {"message": str((e)),
                    "exception_type": "%s" % type(e).__name__,
                    "exception_arguments": "%s" % e,
                    "filename": fname,
                    "exception_line": exc_tb.tb_lineno,
                    "input": MI.get_config("name")
                    }
        log.error("action=endpoint_error {} {}".format(e, jsondump))
    MI.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            MI.scheme()
        elif sys.argv[1] == "--validate-arguments":
            MI.validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        run()

    sys.exit(0)
