import json
import logging
import logging.handlers
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import requests
import splunklib.client as client
from splunk.clilib import cli_common as cli
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib.control_exceptions import ParsingError

SPLUNK_HOME = os.environ['SPLUNK_HOME']
APP_NAME = __file__.split(os.sep)[-3]
ALERT_ATTRIBUTE_FLAGS = ["enable_name", "enable_description", "enable_alert_link", "enable_search",
                         "enable_trigger_time"]
DEFAULT_LOG_LEVEL = logging.INFO
SECRET_NAME_API_KEY = "api_key"
SECRET_NAME_PROXY_PASS = "proxy_password"
logger = None

def setup_logging():
    """
    Set-up logger
    """
    global logger
    logger = logging.getLogger('splunk.moog')
    logging_default_config_file = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    logging_local_config_file = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    logging_stanza_name = 'python'
    logging_file_name = "AIOps_Incident_Management_Integration.log"
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


def is_https_url(url):
    """
    This function checks if the URL starts with https:// or not.
    :param url: URL to check
    :return: True if URL starts with https://
    """
    return url.lower().startswith("https://")


def is_http_url(url):
    """
    This function checks if the URL starts with http:// or not.
    :param url: URL to check
    :return: True if URL starts with http://
    """
    return url.lower().startswith("http://")


def get_enforce_https():
    """
    Get the enforce_https value from moogsoft.conf
    :return: boolean value configured for enforce_https. By default, it returns true.
    """
    try:
        moogsoft_conf = cli.getConfStanza('moogsoft', 'https')
        if moogsoft_conf:
            enforce_https = str(moogsoft_conf.get('enforce_https'))
            if enforce_https.lower() == "false" or enforce_https.lower() == "0":
                return False
    except ParsingError:
        pass
    return True


def send_req(url, headers, req_json, proxies=None, verify=False):
    """
    Send POST request to the AIOps Incident Management
    :param url: AIOps Incident Management Integration URL
    :param req_json: Request payload
    :param verify: Certificate verification
    :return: Response from AIOps Incident Management
    """

    # Only https url is permitted from Setup page and Alert Actions.
    # From backend, one can disable 'enforce_https' flag in https stanza of moogsoft.conf for unsecure connection.
    res = requests.post(url, data=req_json, headers=headers, proxies=proxies, verify=verify, timeout=60)
    logger.info("Successfully sent the event data to AIOps Incident Management")
    logger.info("Response received from AIOps Incident Management: {}".format(str(res)))
    return res

def decrypt_secrets(settings):
    """
    If the credentials are not overriden through alert action, decrypt them using
    storage/password api and set them in the given object
    :param settings: splunk settings object
    """
    session_key = settings['session_key']
    host = settings['server_host']

    service = client.connect(host=host, token=session_key)
    passwords = service.storage_passwords.list(owner="nobody", app="AIOps_Incident_Management", sharing="app")

    api_key = settings['configuration']['api_key']
    proxy_password = settings['configuration']['proxy_password']

    for p in passwords:
        # decrypt if the user hasn't overriden the secrets, else they are already in plain text
        # Note: the alert action field is not able to pass $something$ so $7$ part of the encrypted value is
        # removed for or condition check. If splunk fixes the issue, the condition should work
        if p.name == "{}:{}:".format(APP_NAME, SECRET_NAME_API_KEY) and api_key != "" and \
            (api_key == p.encr_password or api_key == p.encr_password[3:]):
            logger.debug("decrypting api key")
            settings['configuration']['api_key'] = p.clear_password

        if p.name == "{}:{}:".format(APP_NAME, SECRET_NAME_PROXY_PASS) and proxy_password != "" and \
            (proxy_password == p.encr_password or proxy_password == p.encr_password[3:]):
            logger.debug("decrypting proxy pass")
            settings['configuration']['proxy_password'] = p.clear_password

def execute(rest_url, req_data, moog_cert=None):
    """
    Execute the POST request on the AIOps Incident Management
    :param rest_url: AIOps Incident Management Integration URL
    :param req_data: Payload of the request
    :param moog_cert: AIOps Incident Management SSL certificate
    :return: None
    """
    req_json = json.dumps({'events': [req_data]})
    headers = {
        'Content-Type': 'application/json'
    }
    proxies = None
    http_proxy_str = "http://{user}:{password}@{host}:{port}"
    https_proxy_str = "https://{user}:{password}@{host}:{port}"

    try:
        logger.debug("Sending data : {}".format(str(req_data)))

        decrypt_secrets(req_data)

        if 'is_moogsoft_on_prem_edition' in req_data['configuration'] and (req_data['configuration']['is_moogsoft_on_prem_edition'] == "0" or req_data['configuration']['is_moogsoft_on_prem_edition'] == "false") and 'api_key' in req_data['configuration']:
            headers['apiKey'] = req_data['configuration']['api_key']

        if 'is_proxy_config' in req_data['configuration'] and (req_data['configuration']['is_proxy_config'] == "1" or req_data['configuration']['is_proxy_config'] == "true"):
            proxy_host = req_data['configuration']['proxy_host']
            proxy_port = req_data['configuration']['proxy_port']
            proxy_user = req_data['configuration']['proxy_user']
            proxy_password = req_data['configuration']['proxy_password']

            if proxy_host is None or proxy_host == '':
                raise Exception("Proxy Host is required if proxy based configuration is enabled")

            if proxy_port is None or proxy_port == '':
                raise Exception("Proxy Port is required if proxy based configuration is enabled")

            if (proxy_user is None or proxy_user == '') or (proxy_password is None or proxy_password == ''):
                https_proxy_str = "https://{host}:{port}"
                http_proxy_str = "http://{host}:{port}"
                proxies = {
                    'http': http_proxy_str.format(host=proxy_host, port=proxy_port),
                    'https': https_proxy_str.format(host=proxy_host, port=proxy_port)
                }
            else:
                proxies = {
                    'http': http_proxy_str.format(user=proxy_user, password=proxy_password, host=proxy_host,
                                                  port=proxy_port),
                    'https': https_proxy_str.format(user=proxy_user, password=proxy_password, host=proxy_host,
                                                    port=proxy_port)
                }

        if is_https_url(rest_url):
            verify = moog_cert if moog_cert else True
            send_req(rest_url, headers, req_json, proxies=proxies, verify=verify)

        elif is_http_url(rest_url):
            enforce_https = get_enforce_https()

            if enforce_https:
                raise Exception(
                    "HTTP support is disabled for the app {}, configure the app with a HTTPS URL".format(APP_NAME))

            send_req(rest_url, headers, req_json, proxies=proxies, verify=False)

        else:
            raise Exception("Configured AIOps Incident Management Integration URL '{}' is not valid".format(rest_url))

    except requests.exceptions.SSLError:
        exception_msg = "SSL certificate verification failed"
        raise Exception(
            "An error has occurred while executing POST request with AIOps Incident Management Integration. Error message:"
            " {}".format(exception_msg))

    except Exception as exception:
        exception_msg = str(exception)
        raise Exception(
            "An error has occurred while executing POST request with AIOps Incident Management Integration. Error message:"
            " {}.".format(exception_msg))


def keep_required_config(config):
    """
    Keep only selected alert attributes from the setup page in config which will be push to the AIOps Incident Management.
    :param config: Alert Action Configuration
    :return: None
    """
    for alert_attribute in ALERT_ATTRIBUTE_FLAGS:
        if alert_attribute in config and config[alert_attribute] == "0":
            del config[alert_attribute.replace("enable_", "")]
        del config[alert_attribute]


def main():
    """
    This function initialises AIOps Incident Management App
    """
    setup_logging()
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.error("FATAL Unsupported execution mode (expected --execute flag) for App: {}".format(APP_NAME))
        sys.exit(1)

    logger.info("Execution started for App: {}".format(APP_NAME))
    try:
        settings = json.loads(sys.stdin.read())

        config = settings['configuration']
        keep_required_config(config)
        rest_url = config['url']
        logger.info("AIOps Incident Management Integration url is: {}".format(rest_url))

        if is_https_url(rest_url) and 'moogcertificate' in config.keys():
            try:
                moog_cert = config['moogcertificate']
                execute(rest_url, settings, moog_cert)
            except Exception as exception:
                logger.warning(str(exception))
                logger.warning("Trying to connect to AIOps Incident Management Integration without client certificate from App: {}"
                               .format(APP_NAME))
                execute(rest_url, settings)
        else:
            execute(rest_url, settings)

        logger.info("Execution completed successfully for App: {}".format(APP_NAME))
    except Exception as exception:
        logger.error("AIOps Incident Management alert script execution failed: {}".format(str(exception)))
        logger.exception(exception)
        sys.exit(3)


if __name__ == '__main__':
    main()
