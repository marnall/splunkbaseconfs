import splunk
import splunk.admin as admin
import splunk.entity as en
import os, sys
import re

splunk_home = os.getenv("SPLUNK_HOME")
sys.path.append(splunk_home + "/etc/apps/Endgame/bin/")

from logger import setup_logging as create_logger

logger = create_logger("endgame_logger", "endgame.log")


class AppSettings(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for myarg in ["base_url", "native_base_url"]:
                self.supportedArgs.addOptArg(myarg)

    def handleList(self, confInfo):
        global logger
        confDict = self.readConf("appsetup")
        if None != confDict:
            for stanza, settings in confDict.items():
                for key, val in settings.items():

                    try:
                        if key in ["base_url", "native_base_url"] and val in [None, ""]:
                            val = ""
                    except Exception as exp:
                        logger.error(str(exp))
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        base_url = self.callerArgs.data["base_url"][0]
        native_base_url = self.callerArgs.data["native_base_url"][0]

        # https url validation regex
        regex = "^(https:\\/\\/)((([a-z\\d]([a-z\\d-]*[a-z\\d])*)\\.)+[a-z]{2,}|((\\d{1,3}\\.){3}\\d{1,3}))(\\:\\d+)?(\\/[-a-z\\d%_.~+]*)*(\\?[;&a-z\\d%_.~+=-]*)?(\\#[-a-z\\d_]*)?$"

        if not (re.match(regex, base_url) and re.match(regex, native_base_url)):
            logger.error(
                "Endgame API Base URL or Endgame Base URL, Can only be secure(i.e. https) and valid URL"
            )
            raise Exception(
                "Endgame API Base URL or Endgame Base URL, Can only be secure(i.e. https) and valid URL"
            )
        self.writeConf("appsetup", "app_config", self.callerArgs.data)


admin.init(AppSettings, admin.CONTEXT_NONE)
