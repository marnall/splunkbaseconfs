import os
import re
import splunk.appserver.mrsparkle.controllers as controllers  # noqa: F401
from splunk.appserver.mrsparkle.lib.decorators import expose_page  # noqa: F401

# Above imports are necessary to proparly work rest handler

import splunk
import utils
from splunk.clilib import cli_common as cli
import splunk.version as ver
import sys
import splunk.rest

URI = "/servicesNS/nobody/system/apps/local/" + utils.APP_NAME + "/_reload"
logger = utils.get_logger("dtexubi_conf_service")

version = float(re.search(r"(\d+.\d+)", ver.__version__).group(1))

try:
    if version >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError:
    sys.exit(3)


class load_configuration(splunk.rest.BaseRestHandler):
    """Class for Load configuration."""

    def handle_POST(self):
        """Handle post method for rest handler."""
        # get conf_file name from ajax call
        conf_file = self.request["form"]["conf_file"]
        # get conf_stanza name from ajax call
        conf_stanza = self.request["form"]["conf_stanza"]

        # Validate the configuration file name and stanza name
        if conf_file is None and conf_stanza is None:
            logger.error("load_configuration: Configuration not found.")
            response = utils.return_object("", "Error", "Configuration not found.")
            return response

        # get values from configuration file
        try:
            conf_value = cli.getConfStanza(conf_file, conf_stanza)
            response = utils.return_object(conf_value, "Ok", "")
        except Exception as e:
            logger.error("load_configuration: Configuration not found. Error: %s" % (str(e)))
            response = utils.return_object("", "Error", "Configuration not found.")

        # handle verbs, otherwise Splunk will throw an error
        return response


class save_configuration(splunk.rest.BaseRestHandler):
    """Class for save configuration."""

    def handle_POST(self):
        """Handle post method for rest handler."""
        # get threshold value from ajax call
        threshold = self.request["form"]["threshold"]
        # get zscore value from ajax call
        zscore = self.request["form"]["zScore"]

        # validate threshold value
        thresholdValidate = utils.validate_threshold(threshold)
        # validate zscore value
        zscoreValidate = utils.validate_zscore(zscore)

        dir_path = make_splunkhome_path(["etc", "apps", utils.APP_NAME, "local"])
        file_path = make_splunkhome_path(["etc", "apps", utils.APP_NAME, "local", "dtexubi.conf"])
        try:
            # Validate the configuration values and write to configuration file
            if zscore and zscoreValidate and threshold and thresholdValidate:
                stanzaData = {"configuration": {"zscore": zscore, "threshold": threshold}}
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                cli.writeConfFile(file_path, stanzaData)
                splunk.rest.simpleRequest(
                    URI,
                    sessionKey=self.sessionKey,
                    postargs=None,
                    method="POST",
                    timeout=180,
                    raiseAllErrors=True,
                )
                return utils.return_object("true", "Ok", "")
            else:
                logger.error("save_configuration:Configurations settings are not validated.")
                return utils.return_object(
                    "false", "Error", "Configurations settings are not validated."
                )
        except Exception as e:
            logger.error(
                "save_configuration:Could not get Configuration from splunk. Error: %s" % (str(e))
            )
            return utils.return_object("false", "Error", "Configurations Not Found.")
