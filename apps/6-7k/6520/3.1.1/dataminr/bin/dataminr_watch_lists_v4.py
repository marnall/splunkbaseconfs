import os
import traceback
import import_declare_test    # noqa: F401
import splunk.admin as admin
from splunktaucclib.rest_handler import util
from dataminr_client import DataminrClientV4
from log_helper import setup_logging


util.remove_http_proxy_env_vars()
logger = setup_logging(os.path.splitext(os.path.basename(__file__))[0].lower())


class WatchLists(admin.MConfigHandler):
    """Get the Watch Lists data."""

    def setup(self):
        """To setup the variables to access in list."""
        self.supportedArgs.addReqArg("dataminr_account")

    def handleList(self, conf_info):
        """Populate the Watch Lists."""
        session_key = self.getSessionKey()
        dataminr_account = self.callerArgs.data.get("dataminr_account")[0]
        try:
            logger.info(f"Fetching Watchlists from account {dataminr_account}.")
            dataminr_client = DataminrClientV4(session_key, dataminr_account)
            watchlist_list = dataminr_client.get_all_watchlists()
            logger.info(f"Successfully fetched Watchlists from account {dataminr_account}.")

        # add "All" option
            conf_info["All"]
            for wl in watchlist_list:
                conf_info[wl["name"]].append("id", wl["id"])
        except Exception as e:
            logger.error(
                f"Error occured when fetching Watchlists: {e}."
                f" {traceback.format_exc()}"
            )
            raise Exception("Error occurred while fetching Watchlists. Please check the logs."
                            " Also, make sure to use valid v4 Dataminr account")


if __name__ == "__main__":
    """Driving function."""
    admin.init(WatchLists, admin.CONTEXT_NONE)
