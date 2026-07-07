import splunk.rest as rest
import splunk
import sys
from os.path import dirname, abspath

sys.path.append(dirname(abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
from logger import Logger
from common import Common


class AppInstallation(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)
        self._session_key = None

    def handle(self, in_string):
        params = Common().parse_in_string(in_string)
        self._session_key = params["session"]["authtoken"]
        try:
            Logger().info("AddOn Installed status checker class handle method called")
            is_add_on_installed = self._check_installation_status()
            return {
                "payload": {
                    "message": "AddOn Installation status checked successfully",
                    "is_installed": is_add_on_installed,
                },
                "status": 200,
            }
        except Exception as e:
            Logger().error(f"Error in AddOnInstallation handle method: {str(e)}")
            return {"payload": {"message": str(e)}, "status": 500}

    def _check_installation_status(self):
        try:
            rest.simpleRequest(
                "/services/apps/local/TA-cisco-cloud-security-addon",
                sessionKey=self._session_key,
                method="GET",
                getargs={"output_mode": "json", "count": 1, "offset": 0},
                raiseAllErrors=True,
            )
            return True
        except splunk.ResourceNotFound:
            return False
        except Exception:
            raise 