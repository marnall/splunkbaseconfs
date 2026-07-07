from requests import exceptions
import ta_precrime_threat_intelligence_declare
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import splunk.rest as rest
import os
import json
import traceback
import utils_precrime as utils
import logger_manager as log
from solnlib.utils import is_true

STATUS_FORCELIST = list(range(500, 600)) + [429]
logger = log.setup_logging('ta_precrime_server_validation')
CHECK_LOG_FILES = 'Please check the log files.'


class APIClient():
    """A Client for all PreCrime API related transactions."""

    def __init__(self, session_key, data):
        self.session_key = session_key
        self.data = data
        __URL_FORMAT = "__REST_CREDENTIAL__#TA-precrime-threat-intelligence"\
                       "#configs/conf-ta_precrime_threat_intelligence_settings"\
                       ":proxy``splunk_cred_sep``1:"
        self.__URL_ENCODE = requests.compat.quote_plus(__URL_FORMAT)
        self.validate_account(self.data)
        self.my_app = __file__.split(os.sep)[-3]
        self.proxy_settings = self.get_proxy()
        self.session = self.requests_retry_session()

    @classmethod
    def validate_account(cls, data):
        """Validate the given account."""
        if not (isinstance(data, dict) and data.get('username') and data.get('password')):
            err_msg = (
                'Could not retrieve API Credentials.'
                'Please recheck that API Credentials are configured properly.'
            )
            logger.error(err_msg)
            return False
        return True

    def get_proxy(self):
        """
        Gives information of proxy if proxy is enable.
        :return: dictionary having proxy information
        """
        proxy_settings = None

        _, response_content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-ta_precrime_threat_intelligence_settings/proxy"
            .format(self.my_app),
            sessionKey=self.session_key,
            getargs={"output_mode": "json"},
            raiseAllErrors=True)
        proxy_info = json.loads(response_content)['entry'][0]['content']
        # if int(proxy_info.get("proxy_enabled", 0)) == 0:
        if not is_true(proxy_info.get("proxy_enabled")):
            return proxy_settings

        proxy_port = proxy_info.get('proxy_port')
        proxy_url = proxy_info.get('proxy_url')
        proxy_type = proxy_info.get('proxy_type')
        proxy_username = proxy_info.get('proxy_username', '')
        proxy_password = ''

        if proxy_username:
            try:
                _, response_content = rest.simpleRequest(
                    "/servicesNS/nobody/{}/storage/passwords/".format(
                        self.my_app) + self.__URL_ENCODE,
                    sessionKey=self.session_key,
                    getargs={"output_mode": "json"},
                    raiseAllErrors=True)
                response_dict = json.loads(
                    response_content)['entry'][0]['content']
                cred = json.loads(response_dict.get('clear_password', '{}'))
                proxy_password = cred.get("proxy_password", None)
            except Exception as e:
                logger.exception(
                    "Error While fetching proxy \n Error: {}".format(str(e)))
        proxy_settings = self.get_proxy_setting(proxy_type, proxy_username,
                                                proxy_password, proxy_url,
                                                proxy_port)
        return proxy_settings

    def get_proxy_setting(self, proxy_type, proxy_username, proxy_password,
                          proxy_url, proxy_port):
        """Function To get Proxy Setting."""
        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (proxy_type, proxy_username,
                                              proxy_password, proxy_url,
                                              proxy_port)
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

        return proxy_settings

    def requests_retry_session(self,
                               retries=5,
                               backoff_factor=0.3,
                               status_forcelist=STATUS_FORCELIST,
                               session=None):
        """
        Create and return a session object.

        :param retries: Maximum number of retries to attempt
        :param backoff_factor: Backoff factor used to calculate time between retries.
        :param status_forcelist: A tuple containing the response status codes that should
         trigger a retry.
        :param session: Session object

        :return: Session Object
        """
        session = session or requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def read_verify_ssl(self):
        content_from_conf = utils.read_conf_file(self.session_key,
                                                 'ta_precrime_threat_intelligence_settings',
                                                 'additional_parameters')
        verify_ssl = True if is_true(str(content_from_conf['verify'])) else False
        return verify_ssl

    def api_call_report(self, endpoint, payload, headers):
        """Method to call the endpoint and generate the token."""
        url = "{}".format(endpoint)
        try:
            response = self.session.post(url, data=payload, headers=headers,
                                         proxies=self.proxy_settings,
                                         verify=self.read_verify_ssl())
            logger.info("Precrime URL for getting Token: {}".format(url))
            logger.debug("Status of the Response for the Token : {}".format(response.status_code))
            return response

        except requests.exceptions.ProxyError as e:
            raise requests.exceptions.ProxyError(e)

        except requests.exceptions.SSLError as e:
            raise requests.exceptions.SSLError(e)

        except Exception as e:
            logger.error(
                "Exception occurred while fetching token."
                " Error: {}".format(str(e))
            )
            logger.debug(
                "Unexpected error occured. "
                "Error trace: {}".format(traceback.format_exc())
            )
            raise Exception(e)

    def request_get(self, endpoint, headers, params=None):
        """Method to call the endpoint for data collection of PreCrime."""
        try:
            logger.info('Sending the request for Data Collection for the PreCrime Input.')
            response = self.session.get(endpoint,
                                        headers=headers,
                                        params=params,
                                        proxies=self.proxy_settings,
                                        verify=self.read_verify_ssl())
            logger.info("PreCrime URL for getting data: {}".format(endpoint))
            if response.status_code == 200:
                logger.info('Data Get successfully.')
                return response
            else:
                logger.error("Could not connect to PreCrime Account111. "\
                             "Please recheck PreCrime credentials")
                error_msg = 'Bad Request due to invalid request. Status Code: {}'.format(response.status_code)
                raise Exception(error_msg)
        except Exception as e:
            logger.error("Error occured while fetching PreCrime's input data."
                         "Error: {}".format(str(e)))
            logger.debug(
                "Unexpected error occured. "
                "Error trace: {}".format(traceback.format_exc()))
            raise Exception(e)
