"""This file defines custom  command."""
import ta_jupiterone_declare  # noqa F401
from ta_jupiterone_log_manager import setup_logging
import sys
import time
import copy
import traceback
import requests
import json
import ta_jupiterone_constants as constants
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from solnlib import conf_manager
from ta_jupiterone_utils import get_proxy, post_api_expiration_msg

logger = setup_logging('jupiteronesearch')


@Configuration()
class JupiterOneSearchCommand(GeneratingCommand):
    """jupiterone search custom command class."""

    query = Option(require=True)
    account_name = Option(require=True)
    retry_count = 3

    def fetch_account_information(self, session_key):
        """Fetch Account Information."""
        try:
            cfm = conf_manager.ConfManager(
                session_key,
                'TA-JupiterOne',
                realm="__REST_CREDENTIAL__#TA-JupiterOne#configs/conf-ta_jupiterone_account"
            )
            conf = cfm.get_conf('ta_jupiterone_account')
            stanza = conf.get(self.account_name)
            AccountId = stanza.get('account_id', None)
            ApiKey = stanza.get('api_key', None)
            BaseUrl = stanza.get('base_url', None)
            if not BaseUrl:
                BaseUrl = constants.BASE_URL
        except Exception:
            logger.error("JupiterOne Error: Error Occured While Fetching Account Information")
            logger.debug(
                "JupiterOne Debug: Error Occured While Fetching Account Information : {}"
                .format(traceback.format_exc())
            )
            return None, None

        return AccountId, ApiKey, BaseUrl

    def get_parameter(self, query, AccountId, ApiKey):
        """Parameters which will use in API call."""
        api_key = "Bearer {}".format(ApiKey)

        temp_query = """
        query J1QL(
        $query: String!
        $cursor: String
        ) {
        queryV1(
            query: $query
            cursor: $cursor
        ) {
            type
            data
            cursor
        }
        }
        """
        variables = {
            "query": "{}".format(query)
        }

        header = {
            "JupiterOne-Account": AccountId,
            "Authorization": api_key,
        }

        return temp_query, variables, header

    def get_data(self, url, query, variables, header, proxy):
        """Get Data from JupiterOne via REST API call."""
        try:
            response = requests.post(
                url,
                json={"query": query, "variables": variables},
                headers=header,
                proxies=proxy,
            )
            if response.status_code == 200:
                if response.text:
                    content = json.loads(response.text)
                    # check that still any error come after getting 200 response
                    if 'errors' in content:
                        errors = content['errors']
                        # check specific error related to Rate limit exceeded
                        if len(errors) == 1 and '429' in errors[0]['message']:
                            logger.error(
                                "JupiterOne Error: Error occurred while fetching data. API rate limit exceeded."
                            )
                            logger.debug(
                                "JupiterOne Debug: Started retry mechanism as API rate limit exceeded"
                            )
                            # retry mechanism
                            if self.retry_count == constants.RETRY_COUNT:
                                while self.retry_count > 0:
                                    logger.debug(
                                        "JupiterOne Debug: Started retry mechanism and retry count is {} "
                                        .format(
                                            (constants.RETRY_COUNT - self.retry_count) + 1)
                                    )
                                    time.sleep(10)
                                    self.retry_count -= 1
                                    res = self.get_data(url, query, variables, header, proxy)
                                    if res:
                                        break
                                self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
                                return res
                        else:
                            logger.error(
                                "JupiterOne Error: Error occurred while fetching data. "
                                "Status code: 200 and Error: {}".format(errors))
                    else:
                        return response.json()
                else:
                    logger.error(
                        "JupiterOne Error: Error occurred while fetching data. "
                        "Status code: 200 and Error: Received empty response."
                    )
            elif response.status_code == 400:
                logger.error(
                    "JupiterOne Error: Error occurred while fetching data. Error in GraphQL payload."
                    "Status code: 400 and Response: {}".format(response.text))
            elif response.status_code == 401:
                logger.error(
                    "JupiterOne Error: Error occurred while fetching data. "
                    "Status code: 401 and Response: {}".format(response.text))
                logger.debug("JupiterOne Debug: Please verify that API key token is expired or not"
                             " for account: {}".format(self.account_name))
                post_api_expiration_msg(self.session_key, self.account_name)
            elif response.status_code == 429 or response.status_code in [500, 600]:
                logger.error("JupiterOne Error: Error occurred while fetching data."
                             "Status code: {} and "
                             "Response: {}".format(response.status_code, response.text))
                # retry mechanism
                if self.retry_count == constants.RETRY_COUNT:
                    while self.retry_count > 0:
                        logger.debug(
                            "JupiterOne Debug: Started retry mechanism and retry count is {} "
                            .format((constants.RETRY_COUNT - self.retry_count) + 1)
                        )
                        time.sleep(10)
                        self.retry_count -= 1
                        res = self.get_data(url, query, variables, header, proxy)
                        if res:
                            break
                    self.retry_count = copy.deepcopy(constants.RETRY_COUNT)
                    return res
            else:
                logger.error("JupiterOne Error: Error occurred while fetching data. "
                             "Status code: {} and "
                             "Response: {}".format(response.status_code, response.text))
        except (requests.HTTPError, requests.exceptions.ConnectionError) as e:
            logger.error(
                "JupiterOne Error: HTTPError or ConnectionError occurred while fetching data. "
                "Error: {}".format(str(e)))
            logger.debug(
                "JupiterOne Debug: HTTPError or ConnectionError occurred while fetching alert data. "
                "Error trace: {}".format(traceback.format_exc()))
        except Exception as e:
            logger.error(
                "JupiterOne Error: Exception occurred while fetching data. "
                "Error: {}".format(str(e)))
            logger.debug(
                "JupiterOne Debug: Unexpected error occured. "
                "Error trace: {}".format(traceback.format_exc()))

    def process_response(self, response, url, query, variables, header, proxy):
        """Process the reponse if Pagination."""
        cursor = response["data"].get("queryV1").get("cursor")
        main_response = []
        main_response.append(response["data"].get("queryV1").get("data"))
        while cursor:
            variables["cursor"] = cursor
            logger.debug("JupiterOne Debug: Started the pagination to get more data.")
            response_temp = self.get_data(url, query, variables, header, proxy)
            if response_temp and len(response_temp["data"].get("queryV1").get("data")) > 0:
                logger.info("JupiterOne Info: Received the data while pagination.")
                cursor = response_temp["data"].get("queryV1").get("cursor")
                main_response.append(response_temp["data"].get("queryV1").get("data"))
            else:
                logger.debug("JupiterOne Debug: While pagination error occured in fetching data.")
                break
        return main_response

    def generate(self):
        """Generate Events Function."""
        logger.info("JupiterOne Info: Started Custom Command Script Execution.")
        logger.debug("Generating Events")
        start_time = time.time()
        self.session_key = self.search_results_info.auth_token

        # These are used in API call
        AccountId, ApiKey, BaseUrl = self.fetch_account_information(self.session_key)

        if AccountId is None or ApiKey is None or BaseUrl is None:
            logger.error("JupiterOne Error: Error Occured While Fetching Account Information")
            logger.debug(
                "JupiterOne Debug: Error Occured While Fetching Account Information : {}"
                .format(traceback.format_exc()))
            return False

        query, variables, header = self.get_parameter(self.query, AccountId, ApiKey)
        url = BaseUrl

        proxy = get_proxy(self, self.session_key)

        response = self.get_data(url, query, variables, header, proxy)

        if response:
            event_data = self.process_response(response, url, query, variables, header, proxy)
            for events in event_data:
                for event in events:
                    yield {'_time': time.time(), '_raw': event}
            logger.info(
                "JupiterOne Info: Completed the Execution of Custom Command Script. "
                "Time Taken: {} miniutes".format((time.time() - start_time) / 60)
            )
        else:
            logger.error("JupiterOne Error: Error occured while fetching data.")


dispatch(JupiterOneSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
