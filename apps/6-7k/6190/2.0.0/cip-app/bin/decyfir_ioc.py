import os
import json
import sys
(path, _) = os.path.split(os.path.realpath(__file__))
sys.path.insert(0, path)
sys.path.insert(0, os.path.join(path, '../lib'))
import requests
from requests.models import Response
from requests import Session, Request
from splunk.persistconn.application import PersistentServerConnectionApplication
import logging
import logging.handlers
import splunk
import certifi
import traceback
import urllib3
# Add the lib and current directory to the python path

# from splunk_service import create_splunk_service
# from splunklib.client import StoragePassword
# from splunklib.binding import HTTPError


if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

# Setup logging
logger = logging.getLogger('splunk.cyfirma_splunk')
SPLUNK_HOME = os.environ['SPLUNK_HOME']

LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
LOGGING_STANZA_NAME = 'python'
LOGGING_FILE_NAME = "cip_app_additional_ioc.log"
BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
splunk_log_handler = logging.handlers.RotatingFileHandler(
    os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
logger.addHandler(splunk_log_handler)
splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                         LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)


def format_proxy_uri(proxy_dict):
    """
    Get Function to get proxy uri in format of.

    <protocol>://<user_name>:<password>@<proxy_server_ip>:<proxy_port>

    :param proxy_dict: dict, Dictionary containing proxy information
    :return: proxy_uri: str, proxy uri in standard format
    """
    try:
        uname = requests.compat.quote_plus(
            proxy_dict.get("proxy_username", ""))
        passwd = requests.compat.quote_plus(
            proxy_dict.get("proxy_password", ""))
        proxy_url = proxy_dict.get("proxy_host")
        proxy_port = proxy_dict.get("proxy_port")
        proxy_type = proxy_dict.get("proxy_type")
        if uname and passwd:
            proxy_uri = f"{uname}:{passwd}@{proxy_url}:{proxy_port}"
        else:
            proxy_uri = f"{proxy_url}:{proxy_port}"

        if proxy_url:
            proxy_settings = {
                "http": f"{proxy_type}://{proxy_uri}",
                "https": f"{proxy_type}://{proxy_uri}",
            }
        else:
            proxy_settings = {}

        return proxy_settings
    except Exception as e:
        logger.info(e)


class Send(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def parse_form_data(self, form_data):
        parsed = {}
        for [key, value] in form_data:
            parsed[key] = value
        return parsed

    def create_send_resp(self, response, status_code):
        logger.info("response={}".format(status_code))
        return {
            'payload': response,
            'status': status_code,
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    def send_request(self, url, params, proxy_settings):
        """Send an API request to the URL provided with api token and proxy sets the error message in UI and Log.

        :param url: API URL to send request
        :type url: str
        :param api_token: API token for authentication
        :type params: str
        :param proxy_settings: proxy details to be included in the request
        :type proxy: dict
        :return: True if of status code is 200 else False
        :rtype: bool
        """
        global response
        try:
            if proxy_settings:
                files = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'cip-app', 'certs')
                pem_files = [f"{files}/{file}" for file in os.listdir(path=files) if (file.endswith('.pem') or file.endswith('.crt'))]
                if pem_files:
                    logger.info(f"Certificate used: {pem_files[0]}")
                    response = requests.request(
                        'GET', url, params=params, verify=certifi.where(), proxies=proxy_settings
                    )
                    response.raise_for_status()
            else:
                logger.info(f"No Certificate used")
                response = requests.request(
                    'GET', url, params=params, verify=certifi.where()
            )
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as error:
            # return_resp = Response()
            if response.status_code == 401:
                logger.info("Unauthorised request")
            elif response.status_code == 403:
                logger.info("Unauthorised request")
            elif response.status_code == 404:
                logger.info("Got status code 404!")
            # return_resp.status_code = response.status_code
            # # return_resp._content = b'{}'
            return response
        except requests.exceptions.SSLError as error:
            logger.error("ssl error.")
            logger.error(error)
            return response
        except requests.exceptions.ConnectionError as error:
            logger.error("connection error.")
            logger.error(error)
            resp = Response()
            resp.status_code = 404
            return resp
        except Exception as error:
            logger.error(error)
            return response

    def handle(self, in_string):
        try:
            logger.info("Request Received")
            in_dict = json.loads(in_string)
            # logger.info(in_dict)
            # get variables from the request payload
            payload = self.parse_form_data(in_dict['form'])
            url = payload["url"]
            proxy = {}
            if payload['proxy_enable'] == "1":
                proxy = format_proxy_uri(payload)
            response = self.send_request(url, None, proxy)
            if response and response.status_code == 200:
                logger.info(response.status_code)
                try:
                    content = json.loads(response.content)
                except Exception:
                    content = {}
                return self.create_send_resp(content, 200)
            elif (response != {} or response is not None):
                logger.info(response.status_code)
                response.raise_for_status()
            else:       
                status_code = 500
                response = {"msg": "Internal Server Error"}
                return self.create_send_resp(response, status_code)
        except Exception as e:
            logger.info(e)
            status_code = int(str(e).split(" ")[0])
            response = {"msg": "Invalid Credentials"}
            return self.create_send_resp(response, status_code)


