import import_declare_test
import sys
import requests
import base64
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration
from cymru_helpers.conf_helper import get_conf_file
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.rest_helper import RestHelper

logger = setup_logging("ta_team_cymru_account_usage_command")


@Configuration()
class TeamCymruAccountUsage(GeneratingCommand):
    """Account Usage Custom Command."""

    def fetch_account_information(self, session_key):
        """Fetch Account Information."""
        stanza = get_conf_file(
            file="teamcymruscoutappforsplunk_account",
            session_key=session_key,
        )
        account_info = stanza.get_all(only_current_app=True)
        return account_info

    def generate(self):
        """Generate Method."""
        logger.info("Team Cymru Scout Info: Started Custom Command Script Execution.")
        self.session_key = self._metadata.searchinfo.session_key
        accounts_information = self.fetch_account_information(self.session_key)
        cymru_config = {
            "session_key": self.session_key
        }
        for account_stanza, account_info in accounts_information.items():
            cymru_config.update(account_info)

            try:
                cymru_rest_helper = RestHelper(cymru_config, logger)
                data = cymru_rest_helper.get_usage()
                if data['query_limit'] == 0:
                    percentage_used_queries = 0
                    data['query_limit'] = "Unlimited"
                    data['remaining_queries'] = "Unlimited"
                else:
                    percentage_used_queries = round((data['used_queries'] / data['query_limit']) * 100, 3)

                if data['foundation_api_usage']['query_limit'] == 0:
                    percentage_foundation_used_queries = 0
                    data['foundation_api_usage']['query_limit'] = "Unlimited"
                    data['foundation_api_usage']['remaining_queries'] = "Unlimited"
                else:
                    percentage_foundation_used_queries = round((data['foundation_api_usage']['used_queries'] / data['foundation_api_usage']['query_limit']) * 100, 3)  # noqa:E501
                account_details = {
                    "Account Name": account_stanza,
                    "Account Type": account_info.get("auth_type"),
                    'Used Queries': data['used_queries'],
                    'Remaining Queries': data['remaining_queries'],
                    "Used Queries (%)": percentage_used_queries,
                    'Query Limit': data['query_limit'],
                    'Used Foundation Queries': data['foundation_api_usage']['used_queries'],
                    'Remaining Foundation Queries': data['foundation_api_usage']['remaining_queries'],
                    'Foundation Query Limit': data['foundation_api_usage']['query_limit'],
                    "Used Foundation Queries (%)": percentage_foundation_used_queries
                }
                yield account_details
            except Exception as e:
                logger.error("Team Cymru Scout Error: Error occured while fetching usage information: {}".format(e))
                raise e
        logger.info("Team Cymru Scout Info: Completed Custom Command Script Execution.")


dispatch(TeamCymruAccountUsage, sys.argv, sys.stdin, sys.stdout, __name__)
