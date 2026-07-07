import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option
from config_reader import ConfigReader
import json
import logging
import logging.handlers
import requests
import time

ALERT_ACTIONS_CONFIG = "alert_actions"
MOOG_SERVER_CONFIG = "moogsoft"
MOOG_STANZA_NAME = "Moog_Integration"
SEARCH_PARAM_LIST = ['param.is_moogsoft_on_prem_edition', 'param.is_proxy_config', 'param.url',
                    'param.api_key', 'param.proxy_host', 'param.proxy_port', 'param.proxy_user',
                    'param.proxy_password', 'param.Severity', 'param.moog_certificate', 'param.max_batch_size']
SEVERITY_LIST = ['Minor', 'Major', 'Critical', 'Clear', 'Info', 'Warning']

SECRET_NAME_API_KEY = "api_key"
SECRET_NAME_PROXY_PASS = "proxy_password"

HTTP_REQUEST_TIMEOUT = 180
PAYLOAD_CONTAINER_SIZE = sys.getsizeof(json.dumps({"events": []}))
COMMA_SIZE = sys.getsizeof(",")
WHITESPACE_SIZE = sys.getsizeof(" ")
APP_NAME = __file__.split(os.sep)[-3]
SPLUNK_HOME = os.environ['SPLUNK_HOME']
logger = None
enforce_https = None


def setup_logging():
    """
    Set-up logger
    """
    global logger
    logger = logging.getLogger('splunk.moog')
    logging_default_config_file = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    logging_local_config_file = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    logging_stanza_name = 'python'
    logging_file_name = "Moog_Stream_Integration.log"
    base_log_path = os.path.join('var', 'log', 'splunk')
    directory = os.path.join(SPLUNK_HOME, base_log_path)

    if not os.path.exists(directory):
        os.makedirs(directory)

    logging_format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, base_log_path, logging_file_name), mode='a', maxBytes=1048576, backupCount=100)
    splunk_log_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(splunk_log_handler)
    setup_splunk_logger(logging_default_config_file, logging_local_config_file, logging_stanza_name)


def setup_splunk_logger(default_config_file, local_config_file, logging_stanza_name, verbose=True):
    """
    Takes the base logging.logger instance, and scaffolds the splunk logging namespace
    and sets up the logging levels as defined in the config files
    :param default_config_file: Default logging conf file
    :param local_config_file: Local logging conf file
    :param logging_stanza_name: Logging stanza name
    :param verbose: True if verbose mode
    """
    levels = get_splunk_logging_config(default_config_file, local_config_file, logging_stanza_name, verbose)

    for item in levels:
        logger_name = item[0]
        level = item[1]
        logging.getLogger(logger_name).setLevel(getattr(logging, level))


def get_splunk_logging_config(default_config_file, local_config_file, logging_stanza_name, verbose):
    """
    Get the logging conf of Splunk
    :param default_config_file: Default logging conf file
    :param local_config_file: Local logging conf file
    :param logging_stanza_name: Logging stanza name
    :param verbose: True if verbose mode
    """
    logging_levels = []

    # Read in config file and set logging levels
    if os.access(local_config_file, os.R_OK):

        if verbose:
            logger.info("Using local logging config file: {}".format(local_config_file))
        log_config = open(local_config_file, 'r')
    else:
        if verbose:
            logger.info("Using default logging config file: {}".format(default_config_file))
        log_config = open(default_config_file, 'r')

    try:
        in_stanza = False
        for line in log_config:

            # Strip comments
            line = line.strip()
            if '#' in line:
                line = line[:(line.index('#'))]

            # Skip blank lines
            line = line.strip()
            if not line:
                continue

            # Skip mal-formatted lines: stanza, key=value
            if line.startswith('['):
                if not line.endswith(']') or line.index(']') != (len(line) - 1):
                    continue
            elif '=' in line:
                key_test, value_test = line.split('=')
                if not key_test or not value_test:
                    continue
            else:
                continue

            # Validation done, now we finally have parsing logic proper
            if not in_stanza and line.startswith('[%s]' % logging_stanza_name):
                in_stanza = True
                continue
            elif in_stanza:

                if line.startswith('['):
                    break
                else:
                    name, level = line.split('=', 1)
                    if verbose:
                        logger.info("Setting logger={} level={}".format(name.strip(), level.strip()))
                    logging_levels.append((name.strip(), level.strip().upper()))

    except Exception as exception:
        logger.error(exception)

    finally:
        if log_config:
            log_config.close()

    return logging_levels


@Configuration()
class MoogStreamingCommand(StreamingCommand):

    severity = Option(require=False)

    @staticmethod
    def is_https_url(url):
        """
        This function checks if the URL starts with https:// or not.
        :param url: URL to check
        :return: True if URL starts with https://
        """
        return url.lower().startswith("https://")

    @staticmethod
    def is_http_url(url):
        """
        This function checks if the URL starts with http:// or not.
        :param url: URL to check
        :return: True if URL starts with http://
        """
        return url.lower().startswith("http://")

    @staticmethod
    def validate_enforce_https(enforce_https_configured_value):
        """
        Validate the enforce_https value from moog_server.conf
        :param enforce_https_configured_value: Configured value of enforce_https
        :return: boolean value configured for enforce_https
        """
        if enforce_https_configured_value == "1":
            return True

        elif enforce_https_configured_value == "0":
            return False

        else:
            raise Exception(
                "Configured value '{}' of enforce_https in moog_server.conf is invalid.".format(
                    enforce_https_configured_value))

    @staticmethod
    def handle_response(response):
        """
        Verify the response received and raise exception with proper error message if needed.
        :param response: Response received
        :return: None
        """
        # Handle request payload size limitation on Moogsoft
        if response.status_code == 413:
            payload_size_error_msg = "Request rejected by Moogsoft integration URL, " \
                                     "status code 413 is due to the payload size being larger than" \
                                     " what can be accepted by the endpoint, " \
                                     "this could be resolved by changing the 'Max Batch Size' value in " \
                                     "the add-on's configuration."
            logger.error(payload_size_error_msg)
            raise Exception(payload_size_error_msg)

        # Handle timeout error
        elif response.status_code == 504:
            timeout_error_msg = "Http request timeout occurred, status code is - 504." \
                                " Consider lowering the 'max batch size' value to avoid timeouts."
            logger.error(timeout_error_msg)
            raise Exception(timeout_error_msg)

        # Handle other errors
        elif not response.ok:
            raise Exception("An error has occurred while executing HTTP request to Moogsoft. Error code: "
                            "{}".format(str(response)))

    def decrypt_secrets(self, config):
        """
        Decrypt secrets using storage/password api and set them in the given config
        :param settings: splunk settings object
        """
        storage_passwords = self.service.storage_passwords
        passwords = storage_passwords.list(owner="nobody", app="Moogsoft", sharing="app")

        api_key = config['api_key']
        proxy_password = config['proxy_password']

        for p in passwords:
            if p.name == "{}:{}:".format(APP_NAME, SECRET_NAME_API_KEY) and api_key != "":
                logger.debug("decrypting api key")
                config['api_key'] = p.clear_password

            if p.name == "{}:{}:".format(APP_NAME, SECRET_NAME_PROXY_PASS) and proxy_password != "":
                logger.debug("decrypting proxy pass")
                config['proxy_password'] = p.clear_password

    def validate_moog_cert(self, url, moog_cert):
        """
        Validate the certificate path is provided and present at the configured location
        :param url: Moogsoft Integration URL
        :param moog_cert: Moogsoft SSL certificate
        :return: Certificate path if exists else None
        """
        certificate_verify = True
        if self.is_https_url(url):
            if moog_cert:
                if not os.path.exists(moog_cert):
                    raise Exception("Moogsoft certificate file: '{}' not found.".format(moog_cert))

                certificate_verify = moog_cert

        return certificate_verify

    def send_req(self, url, api_key, events, verify=False, proxies=None):
        """
        Send POST request to the Moogsoft
        :param url: Moogsoft Integration URL
        :param events: Request payload
        :param verify: Certificate verification
        :return: Response from Moogsoft
        """
        try:
            headers = {
                'Content-Type': 'application/json'
            }

            if(api_key is not None):
                headers['apiKey'] = api_key

            res = None
            if(proxies is not None):
                res = requests.post(url, data=json.dumps(events), headers=headers, verify=verify,
                                timeout=HTTP_REQUEST_TIMEOUT, proxies=proxies)
            else:
                res = requests.post(url, data=json.dumps(events), headers=headers, verify=verify,
                                timeout=HTTP_REQUEST_TIMEOUT)

            logger.info("Successfully sent {} events to Moogsoft.".format(len(events["events"])))
            logger.info("Response received from Moogsoft: {} with message: {}".format(str(res), str(res.text)))

        except requests.exceptions.SSLError:
            raise Exception(
                "An error has occurred while executing POST request with Moogsoft. Error message: "
                "SSL certificate verification failed")

        except Exception as exception:
            raise Exception(
                "An error has occurred while executing POST request with Moogsoft. Error message:"
                " {}.".format(str(exception)))

        self.handle_response(res)

    def read_from_conf(self, stanza_name, key):
        """
        Read configuration
        :param stanza_name: Stanza name of the conf file
        :param key: Key of configuration
        :return: Value of configuration
        """
        try:
            parsed_config = ConfigReader.read_conf(
                self.search_results_info.auth_token, stanza_name, key)
            logger.debug("Parsed config {}".format(str(parsed_config)))
            search_config = {}
            for param in SEARCH_PARAM_LIST:
                if param in parsed_config:
                    search_config_key = param[len("param."):]
                    search_config[search_config_key] = parsed_config[param]
            logger.debug("Parsed search config {}".format(str(search_config)))
            return search_config
        except Exception as exception:
            raise Exception("Error occurred while reading configuration. Error message: {}".format(str(exception)))

    def stream(self, records):
        """
        Custom command for sending events to Moogsoft
        :param records: input result set to the command
        :return: None
        """
        start_time = time.time()
        moog_configuration = self.read_from_conf(ALERT_ACTIONS_CONFIG, MOOG_STANZA_NAME)
        self.decrypt_secrets(moog_configuration)

        is_proxy_config = moog_configuration['is_proxy_config']
        is_moogsoft_on_prem_edition = moog_configuration['is_moogsoft_on_prem_edition']
        url = moog_configuration['url']
        api_key = moog_configuration['api_key']

        http_proxy_str = "http://{user}:{password}@{host}:{port}"
        https_proxy_str = "https://{user}:{password}@{host}:{port}"
        logger.debug("Parsed config : {}".format(str(moog_configuration)))
        
        if not moog_configuration or moog_configuration['url'] == "":
            raise Exception("Moogsoft configuration is missing. Please setup the Moogsoft App.")

        proxies = None

        if(is_proxy_config == 'true'):
            proxy_host = moog_configuration['proxy_host']
            proxy_port = moog_configuration['proxy_port']
            proxy_user = moog_configuration['proxy_user']
            proxy_password = moog_configuration['proxy_password']

            if((proxy_host is None) or (proxy_host == '')):
                raise Exception("Proxy Host is required if proxy based configuration is enabled")

            if((proxy_port is None) or (proxy_port == '')):
                raise Exception("Proxy Port is required if proxy based configuration is enabled")

            if(((proxy_user is None) or (proxy_user == '')) or ((proxy_password is None) or (proxy_password == ''))):
                https_proxy_str = "https://{host}:{port}"
                http_proxy_str = "http://{host}:{port}"
                proxies = {
                    'http' : http_proxy_str.format(host = proxy_host, port = proxy_port),
                    'https' : https_proxy_str.format(host = proxy_host, port = proxy_port)
                }
            else:
                proxies = {
                    'http' : http_proxy_str.format(user = proxy_user, password = proxy_password, host = proxy_host, port = proxy_port),
                    'https' : https_proxy_str.format(user = proxy_user, password = proxy_password, host = proxy_host, port = proxy_port)
                }
        
        if((is_moogsoft_on_prem_edition is None or is_moogsoft_on_prem_edition == '0') and (api_key is None or api_key == '')):
            raise Exception("Moogsoft API Key is required if 'Configure Moogsoft On_Prem Edition' is disabled")

        moog_cert = self.validate_moog_cert(url, moog_configuration['moog_certificate'])
        batch_size_limit_in_bytes = int(moog_configuration['max_batch_size']) * 1000
        logger.debug("Configured batch size limit in bytes is : {}".format(str(batch_size_limit_in_bytes)))
        total_events = 0
        batch_count = 0

        # Validate whether severity provided in argument or not
        if self.severity:
            # Validate that severity provided in argument must be in defined list of SEVERITY
            if self.severity in SEVERITY_LIST:
                # set provided severity from streammoog in configuration which will be added to the comment
                moog_configuration['Severity'] = self.severity
            else:
                raise Exception("Severity value must be from {}".format(str(SEVERITY_LIST)))
        logger.info("Severity set to {}.".format(str(moog_configuration['Severity'])))

        events = {"events": []}
        request_size_in_bytes = PAYLOAD_CONTAINER_SIZE
        total_events_per_batch = 0
        total_bytes_sent = 0

        for record in records:
            raw_event = dict()
            raw_event['configuration'] = moog_configuration
            raw_event['result'] = record
            event_str = json.dumps(raw_event)

            # Store bytes of list of events excluding current event in loop
            previous_request_size_in_bytes = request_size_in_bytes
            # Calculate total bytes of list of events including current event
            request_size_in_bytes = request_size_in_bytes + sys.getsizeof(event_str) + COMMA_SIZE + WHITESPACE_SIZE

            # Check the total size exceeds the configured batch size if we add new event to the list
            if request_size_in_bytes >= batch_size_limit_in_bytes and len(events["events"]) > 0:

                logger.debug("Sending the following event data to Moogsoft with total events : {}"
                             ", request payload size in bytes : {} ".format(str(total_events_per_batch),
                                                                            str(previous_request_size_in_bytes)))
                # send list of events excluding current event of a loop
                self.execute(url, api_key, events, moog_cert, proxies=proxies)
                # Update to total bytes sent to the Moogsoft
                total_bytes_sent = total_bytes_sent + previous_request_size_in_bytes
                # create new empty batch
                events = {"events": []}
                # Increment number of batch of events send to the Moogsoft
                batch_count = batch_count + 1
                # Reset the counter for total events for the batch
                total_events_per_batch = 0
                request_size_in_bytes = PAYLOAD_CONTAINER_SIZE

            total_events = total_events + 1
            total_events_per_batch = total_events_per_batch + 1

            # Add event to the batch
            events["events"].append(raw_event)

            # Return event/record to the splunk for the further processing
            yield record

        if total_events_per_batch > 0:
            logger.debug(
                "Sending following event data to Moogsoft with total events : {}, request payload size in "
                "bytes : {} ".format(str(total_events_per_batch), str(request_size_in_bytes)))
            self.execute(url, api_key, events, moog_cert, proxies=proxies)
            batch_count = batch_count + 1
            total_bytes_sent = total_bytes_sent + request_size_in_bytes

        if batch_count > 0:
            logger.debug(
                "Script name: {}, Execution time (sec): {}".format(sys.argv[0], str(time.time() - start_time)))
            logger.debug(
                "Summary - Total events: {}, Batch count: {}, Batch size limit in bytes: {}, "
                "Total bytes sent: {}".format(str(total_events), str(batch_count), str(batch_size_limit_in_bytes),
                                              str(total_bytes_sent)))
        logger.info("Moogsoft streaming command execution completed successfully")

    def execute(self, rest_url, api_key, events, moog_cert, proxies=None):
        """
        Send data to Moogsoft
        :param rest_url: Endpoint configured in setup page
        :param events:  Events of Splunk
        :param moog_cert: Moogsoft certificate configured in setup page
        :return: None (Instead send data to Moogsoft)
        """
        if self.is_https_url(rest_url):
            self.send_req(rest_url, api_key, events, moog_cert, proxies=proxies)

        elif self.is_http_url(rest_url):
            # Get configuration to validate http connection is allowed or not
            moog_http_configuration = self.read_from_conf(MOOG_SERVER_CONFIG, 'https')
            logger.debug("Http configuration : {}".format(str(moog_http_configuration)))

            global enforce_https
            if enforce_https is None:
                enforce_https = self.validate_enforce_https(moog_http_configuration['enforce_https'])

            if enforce_https:
                raise Exception("HTTP support is disabled for the app {}, configure the app with a HTTPS URL."
                                .format(APP_NAME))

            self.send_req(rest_url, api_key, events, proxies=proxies)

        else:
            raise Exception("Configured Moogsoft Integration URL '{}' is not valid".format(rest_url))


if __name__ == "__main__":
    setup_logging()
    dispatch(MoogStreamingCommand, sys.argv, sys.stdin, sys.stdout, __name__)
