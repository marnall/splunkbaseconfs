import json
import logging
import logging.handlers
import sys
import os
import requests
from splunk.clilib import cli_common as cli
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib.control_exceptions import ParsingError


SPLUNK_HOME = os.environ['SPLUNK_HOME']
APP_NAME = __file__.split(os.sep)[-3]
ALERT_ATTRIBUTE_FLAGS = ["enable_name", "enable_description", "enable_alert_link", "enable_search",
                         "enable_trigger_time"]
DEFAULT_LOG_LEVEL = logging.INFO
logger = None


def setup_logging(log_name):
    """
    Setup logger.
    :param log_name: name for logger
    """
    global logger

    # Make path till log file
    log_file = make_splunkhome_path(["var", "log", APP_NAME, "%s.log" % log_name])

    # Get directory in which log file is present
    log_dir = os.path.dirname(log_file)

    # Create directory at the required path to store log file, if not found
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Read log level from conf file
    cfg = cli.getConfStanza('alert_actions', 'Moog_Integration')
    log_level = str(cfg.get('log_level'))

    logger = logging.getLogger(log_name)
    logger.propagate = False

    # Set log level
    try:
        logger.setLevel(log_level)
    except (TypeError, ValueError):
        logger.setLevel(DEFAULT_LOG_LEVEL)

    handler_exists = any([True for h in logger.handlers if h.baseFilename == log_file])

    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(log_file, mode="a", maxBytes=10485760, backupCount=10)

        # Format logs
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        try:
            file_handler.setLevel(log_level)
        except (TypeError, ValueError):
            file_handler.setLevel(DEFAULT_LOG_LEVEL)

    return logger


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


def send_req(url, req_json, verify=False):
    """
    Send POST request to the Moogsoft Enterprise
    :param url: Moogsoft Integration URL
    :param req_json: Request payload
    :param verify: Certificate verification
    :return: Response from Moogsoft Enterprise
    """
    headers = {
        'Content-Type': 'application/json'
    }

    # Only https url is permitted from Setup page and Alert Actions.
    # From backend, one can disable 'enforce_https' flag in https stanza of moogsoft.conf for unsecure connection.
    res = requests.post(url, data=req_json, headers=headers, verify=verify, timeout=60)
    logger.info("Successfully sent the event data to Moogsoft Enterprise")
    logger.info("Response received from Moogsoft Enterprise: {}".format(str(res)))
    return res


def execute(rest_url, req_data, moog_cert=None):
    """
    Execute the POST request on the Moogsoft Enterprise
    :param rest_url: Moogsoft Enterprise URL
    :param req_data: Payload of the request
    :param moog_cert: Moogsoft SSL certificate
    :return: None
    """
    req_json = json.dumps({'events': [req_data]})

    try:
        if is_https_url(rest_url):
            verify = moog_cert if moog_cert else False
            send_req(rest_url, req_json, verify)

        elif is_http_url(rest_url):
            enforce_https = get_enforce_https()

            if enforce_https:
                raise Exception(
                    "HTTP support is disabled for the app {}, configure the app with a HTTPS URL".format(APP_NAME))
    
            send_req(rest_url, req_json)

        else:
            raise Exception("Configured Moogsoft Integration URL '{}' is not valid".format(rest_url))

    except requests.exceptions.SSLError:
        exception_msg = "SSL certificate verification failed"
        raise Exception(
            "An error has occurred while executing POST request with Moogsoft Enterprise. Error message:"
            " {}".format(exception_msg))

    except Exception as exception:
        exception_msg = str(exception)
        raise Exception(
            "An error has occurred while executing POST request with Moogsoft Enterprise. Error message:"
            " {}.".format(exception_msg))


def keep_required_config(config):
    """
    Keep only selected alert attributes from the setup page in config which will be push to the Moogsoft Enterprise.
    :param config: Alert Action Configuration
    :return: None
    """
    for alert_attribute in ALERT_ATTRIBUTE_FLAGS:
        if alert_attribute in config and config[alert_attribute] == "0":
            del config[alert_attribute.replace("enable_", "")]
        del config[alert_attribute]


def main():
    """
    This function initialises TA-Splunk-Moogsoft add-on
    """
    setup_logging("Moog_Integration")
    if len(sys.argv) < 2 or sys.argv[1] != "--execute":
        logger.error("FATAL Unsupported execution mode (expected --execute flag) for Add-on: {}".format(APP_NAME))
        sys.exit(1)

    logger.info("Execution started for Add-on: {}".format(APP_NAME))
    try:
        settings = json.loads(sys.stdin.read())
        config = settings['configuration']
        keep_required_config(config)
        rest_url = config['url']
        logger.info("Moogsoft Integration url is: {}".format(rest_url))

        if is_https_url(rest_url) and 'moogcertificate' in config.keys():
            try:
                moog_cert = config['moogcertificate']
                execute(rest_url, settings, moog_cert)
            except Exception as exception:
                logger.warning(str(exception))
                logger.warning("Trying to connect to Moogsoft Enterprise without client certificate from Add-on: {}"
                               .format(APP_NAME))
                execute(rest_url, settings)
        else:
            execute(rest_url, settings)

        logger.info("Execution completed successfully for Add-on: {}".format(APP_NAME))
    except Exception as exception:
        logger.error("Moogsoft Enterprise alert script execution failed: {}".format(str(exception)))
        sys.exit(3)


if __name__ == '__main__':
    main()
