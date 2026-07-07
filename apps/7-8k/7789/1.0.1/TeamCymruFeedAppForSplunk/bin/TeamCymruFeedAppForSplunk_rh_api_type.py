
import import_declare_test  # noqa

from splunktaucclib.rest_handler import util
import splunk.admin as admin
from cymru_helpers.conf_helper import get_conf_file
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.rest_helper import RestHelper

util.remove_http_proxy_env_vars()


class GetAPIType(admin.MConfigHandler):
    """Class to get API Types from account."""

    def setup(self):
        """Setup before handling list."""
        self.supportedArgs.addOptArg("account")

    def handleList(self, conf_info):
        """Defined method to handle list."""
        cymru_account = self.callerArgs.get("account")[0]
        logger = setup_logging('ta_team_cymru_feed_input_creation', account_name=cymru_account)
        if cymru_account:
            session_key = self.getSessionKey()
            account_info = get_conf_file(
                session_key=session_key, file="TeamCymruFeedAppForSplunk_account",
                stanza=cymru_account
            )
            account_info["session_key"] = session_key
            try:
                rest_helper = RestHelper(account_info, logger)
                logger.info("Started collecting API Type of account.")
                api_types = rest_helper.get_api_type()
                api_types = api_types.get("categories", [])
                logger.info("API Type collected successfully.")
            except Exception as e:
                logger.error("Something went wrong while fetching API Type. Error: {}".format(e))
                raise admin.ArgValidationException("Something went wrong while fetching API Type. Error: {}".format(e))
            else:
                for id in api_types:
                    conf_info[id].append('label', id)


if __name__ == "__main__":
    admin.init(GetAPIType, admin.CONTEXT_NONE)
