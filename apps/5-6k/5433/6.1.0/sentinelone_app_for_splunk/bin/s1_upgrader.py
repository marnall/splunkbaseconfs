#
#
import sys
import logging
import os
from Utilities import KennyLoggins, Thanos
from ModularInput import ModularInput
from splunk.clilib.bundle_paths import make_splunkhome_path

__author__ = 'ksmith'
_APP_NAME = "sentinelone_app_for_splunk"
app_home = make_splunkhome_path(["etc", "apps", _APP_NAME, ])

kl = KennyLoggins()
log = kl.get_logger(_APP_NAME, "sentinelone-system-upgrader", logging.INFO)
log.info("action=instantiated")

files_to_remove = [["appserver", "static", "dashboard.js"]]


class S1UpgraderModInput(ModularInput):

    def __init__(self, **kwargs):
        ModularInput.__init__(self, **kwargs)
        self.thanos = Thanos(app_name=_APP_NAME,
                             session_key=self.get_config("session_key"),
                             files_to_remove=files_to_remove,
                             logger=log)

    def snap(self):
        self.thanos.snap()


modular_input = S1UpgraderModInput(app_name=_APP_NAME, scheme={
    "title": "SentinelOne",
    "description": "Provides Upgrade automated scripts.",
    "args": []
})


def run():
    log.info("action=start_modular_input name=sentinelone-upgrader")
    try:
        modular_input.start()
        modular_input.set_logger(log)
        modular_input.sourcetype("sentinelone:informational")
        modular_input.source("sentinelone:input:s1_upgrader")
        modular_input.snap()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        log.error("action=script_exection status=failed exception_line={} msg={}".format(exc_tb.tb_lineno, e))
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
