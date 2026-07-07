import os
import logging
import sys
import re
import json
import urllib2
from logging.handlers import RotatingFileHandler

import splunk.entity as entity
import splunk.version as ver
import splunk.rest as rest

APP_NAME = "crowdstrike"

version = float(re.search("(\d+.\d+)", ver.__version__).group(1))

try:
    if version >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError as e:
    sys.exit(3)
    
    
#create logger file to log error and other information
def get_logger(log_name, loglevel=logging.INFO):
    """
    To setup logger.
    
    :param log_name: name for logger
    :param loglevel: log level, a string
    :return: a logger object
    """

    logfile = make_splunkhome_path(["var", "log", APP_NAME,
                                    "%s.log" % log_name])
    logdir = os.path.dirname(logfile)
    if not os.path.exists(logdir):
        os.makedirs(logdir)
    logger = logging.getLogger(log_name)
    logger.propagate = False
    logger.setLevel(loglevel)

    handler_exists = any([True for h in logger.handlers
                          if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(logfile, mode="a",
                                                            maxBytes=10485760,
                                                            backupCount=10)
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        if loglevel is not None:
            file_handler.setLevel(loglevel)

    return logger   

_LOGGER = get_logger('crowdstrike_app_utils')


def return_object(data, status, error):
    """
    Common method to create dictionary of passed parameters
    
    :param data: response data
    :param status: response status
    :param error: error message
    :return: dictionary of passed parameters
    """
    
    return json.dumps({"data": data, "status": status, "error": error})

addon_name = "TA-crowdstrike"

def get_credentials(session_key):
    """ Get Query type of credentials of falcon platform

    :param session_key: Splunk session key
    :return: username and password of Query type
    """
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=addon_name, owner='nobody', sessionKey=session_key, count=-1, search=addon_name)
    except Exception, e:
        _LOGGER.exception("Crowdstrike Error: Could not get %s credentials from splunk." % (addon_name))
        raise Exception("Crowdstrike Error: Could not get %s credentials from splunk." % (addon_name))

    # Iterate set of credentials and match stanza name with account conf entry and fetch credentials of only Query type
    for stanza, value in entities.items():
        #realm_template: "__REST_CREDENTIAL__#{baseApp}#{endpoint}#{stanzaName}"
        node = value['realm'].split('#')[-1] if value['realm'].split('#') else value['realm']
        node = urllib2.quote(node)
        try:
            resp, content = rest.simpleRequest(
                '/servicesNS/nobody/' + addon_name + '/properties/crowdstrike_falcon_host_accounts/' + node,
                sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
            
            entry = json.loads(content)['entry']
            api_type = None
            username = None
            for item in entry:
                if item.get('name')=='api_type':
                    api_type = item.get('content')
                if item.get('name')=='api_uuid':
                    username = item.get('content')  

            if api_type=="Query":
                sep = "``splunk_cred_sep``"
                clear_password = value['clear_password'].split(sep)[-1]
                return username, clear_password
            
        except Exception as e:
            _LOGGER.exception("Crowdstrike Error: While fetching api type from account config")

    _LOGGER.error("Crowdstrike Error: No credentials found for Query Type. Please configure by going to 'Configuration' page of Add-On")
    return None, None




def is_valid_ip(ip_str):
    """ Validates if the provided value is valid ipv4 or not

    :param ip_str: input value
    :return: True/False
    """

    ip_rex = '^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$'
    m = re.match(ip_rex, ip_str)
    if m is None:
        return False
    else:
        return True


def is_valid_ipv6(ip_str):
    """ Validates if the provided value is valid ipv6 or not

    :param ip_str: input value
    :return: True/False
    """

    ip_rex = '^(?:(?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:)' \
             '{5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}' \
             '(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::' \
             '(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:)' \
             '{,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|' \
             '(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}' \
             '|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]' \
             '{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]' \
             '|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::' \
             '(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}' \
             '(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::' \
             '[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)$'

    m = re.match(ip_rex, ip_str)
    if m is None:
        return False
    else:
        return True


def is_valid_domain(hostname):
    """ Validates if the provided value is valid domain or not

    :param hostname: input value
    :return: True/False
    """

    if len(hostname) > 255:
        return False
    if is_valid_ip(hostname):
        return False
    if is_valid_ipv6(hostname):
        return False
    if hostname[-1] == '.':
        hostname = hostname[:-1]
    allowed = re.compile('@', re.IGNORECASE | re.UNICODE)
    return not any((allowed.search(x) for x in hostname.split('.')))


def is_valid_md5(input_str):
    """ Validates if the provided value is valid md5 or not

    :param input_str: input value
    :return: True/False
    """

    regex = '^[0-9a-fA-F]{32}$'
    m = re.match(regex, input_str)
    if m is None:
        return False
    else:
        return True


def is_valid_sha256(input_str):
    """ Validates if the provided value is valid sha256 or not

    :param input_str: input value
    :return: True/False
    """

    regex = '^[0-9a-fA-F]{64}$'
    m = re.match(regex, input_str)
    if m is None:
        return False
    else:
        return True


def is_valid_sha1(input_str):
    """ Validates if the provided value is valid sha1 or not

    :param input_str: input value
    :return: True/False
    """

    regex = '^[0-9a-fA-F]{40}$'
    m = re.match(regex, input_str)
    if m is None:
        return False
    else:
        return True
    
def validate_ioc_value(ioc_type, ioc_value):
    """ Validates IOC value according to passed type

    :param ioc_type: IOC type
    :param ioc_value: IOC value
    :return: validation message
    """
    error_message= None
    if ioc_type=="sha1" and not is_valid_sha1(ioc_value):
        error_message = "Invalid IOC value for sha1"
    elif ioc_type=="sha256" and not is_valid_sha256(ioc_value):
        error_message = "Invalid IOC value for sha256"
    elif ioc_type=="md5" and not is_valid_md5(ioc_value):
        error_message = "Invalid IOC value for md5"
    elif ioc_type=="domain" and not is_valid_domain(ioc_value):
        error_message = "Invalid IOC value for domain"
    elif ioc_type=="ipv4" and not is_valid_ip(ioc_value):
        error_message = "Invalid IOC value for ipv4"
    elif ioc_type=="ipv6" and not is_valid_ipv6(ioc_value):
        error_message = "Invalid IOC value for ipv6"
        
    return error_message

def get_proxy_info(session_key):
        """ Get proxy information.

        :param session_key: Splunk session key
        :return: dictionary containing proxy details or None
        """

        # Retrieve proxy configurations
        try:
            resp, content = rest.simpleRequest(
                '/servicesNS/nobody/' + addon_name + '/ta_crowdstrike/ta_crowdstrike_settings/crowdstrike_proxy',
                sessionKey=session_key, getargs={"output_mode": "json", "--get-clear-credential--": "1"})
            # Parse response
            proxy_info = json.loads(content)['entry'][0]['content']
        except Exception:
            _LOGGER.exception("CrowdStrike Error: Error while fetching proxy configurations")
            return None

        # Prepare dict containing proxy details
        proxy_info_dict = {
            'proxy_enabled': bool(int(proxy_info.get('proxy_enabled', '0'))),
            'proxy_hostname': proxy_info.get('proxy_url', ''),
            'proxy_port': proxy_info.get('proxy_port', ''),
            'proxy_username': proxy_info.get('proxy_username', ''),
            'proxy_password': proxy_info.get('proxy_password', ''),
            'proxy_rdns': proxy_info.get('proxy_rdns', 'false'),
            'proxy_type': proxy_info.get('proxy_type', 'http')
        }

        # Return None if proxy_enabled is false or proxy hostname or proxy port is not found
        if not proxy_info_dict.get("proxy_enabled") or not proxy_info_dict.get('proxy_port')\
                or not proxy_info_dict.get('proxy_hostname'):
            return None

        # Quote username and password if available
        user_pass = ''
        if proxy_info_dict.get('proxy_username') and proxy_info_dict.get('proxy_password'):
            username = urllib2.quote(proxy_info_dict['proxy_username'], safe='')
            password = urllib2.quote(proxy_info_dict['proxy_password'], safe='')
            user_pass = '{user}:{password}@'.format(user=username, password=password)

        # Prepare proxy string
        proxy = '{proxy_type}://{user_pass}{host}:{port}'.format(proxy_type=proxy_info_dict["proxy_type"],
                                                                 user_pass=user_pass,
                                                                 host=proxy_info_dict['proxy_hostname'],
                                                                 port=proxy_info_dict['proxy_port'])
        proxies = {
            'http': proxy,
            'https': proxy,
        }
        return proxies
