import os
import sys
import json
import sys
import splunk.bundle as bundle

splunk_home = os.getenv("SPLUNK_HOME")
sys.path.append(splunk_home + "/etc/apps/Endgame/bin")

from logger import setup_logging as create_logger

logger = create_logger("endgame_logger", "endgame.log")


class ConfigReader(object):
    def __init__(self, session_token, username, app_name=None):
        self.session_token = session_token
        self.username = username
        if app_name is None:
            self.app_name = self.get_appname_from_path(os.path.abspath(__file__))
        else:
            self.app_name = app_name

    def readConfFile(self, confname, stanza=None):
        confFileObj = None
        confFileDict = {}

        try:
            confFileObj = bundle.getConf(
                confname, sessionKey=self.session_token, namespace=self.app_name, owner=self.username
            )
            for s in confFileObj:
                confFileDict[s] = {}
                confFileDict[s].update(confFileObj[s].items())
        except Exception as exp:
            logger.error(str(exp))
        if stanza is None:
            return confFileDict
        elif stanza in confFileDict.keys():
            return confFileDict[stanza]
        return confFileDict

    def get_appname_from_path(self, absolute_path):
        absolute_path = os.path.normpath(absolute_path)
        parts = absolute_path.split(os.sep)
        parts.reverse()
        for key in ("apps", "slave-apps", "master-apps"):
            try:
                idx = parts.index(key)
            except ValueError:
                continue
            else:
                try:
                    if parts[idx + 1] == "etc":
                        return parts[idx - 1]
                except IndexError:
                    pass
                continue
        #return None
        return "-"