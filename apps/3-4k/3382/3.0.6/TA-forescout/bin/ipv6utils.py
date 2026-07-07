# Copyright 2018 ForeScout Technologies

from __future__ import absolute_import
import platform
import sys
import socket
import logging.handlers
import fsct_defaults

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# Define a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
setup_log_filename = make_splunkhome_path(['var', 'log', 'splunk', fsct_defaults.FS_TA_APP_NAME + '_setup.log'])
handler = logging.handlers.RotatingFileHandler(setup_log_filename, maxBytes=25000000, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Only import for windows platform and when the python version is lower than 2.7.16
# Should tak the following out when 2.7 phase out. Python 3 should includes inet_pton and int_ntop
try:
    from socket import inet_pton, inet_ntop
except ImportError:
    currPlatform = platform.system()
    logger.debug('Current OS: [%s]', currPlatform)
    if('Windows' == currPlatform):
        currPythonVer = sys.version_info
        logger.debug('Current python version: [%s]', currPythonVer)
        if(currPythonVer < (2,7,16)):
            try:
                import win_inet_pton
                #logger.debug('Import win_inet_pton succeeded.')
            except ImportError:
                logger.debug('Problem importing win_inet_pton.')

# This works for python 2.7.16 and above
def is_valid_ipv6_address(ip_tocheck):
    """
    This works for python 2.7. Only check if the address is ipv6.
    Input has to be ipv6 address
    :param ip_tocheck:
    :return: If ip is an ipv6 address, return true, otherwise, return false
    """

    try:
        socket.inet_pton(socket.AF_INET6, ip_tocheck)
        return True
    except socket.error as socket_error:  # not a valid ipv6 address
        #logger.debug('Invalid IPv6 address: [%s]. Message: ', ip_tocheck, socket_error.message)
        pass
    except Exception as error:
        logger.critical('Validate IPv6 error: %s', error.message)

    return False

def get_compact_ipv6(ipv6_address):
    """
    Gets IPv6 address in compat format. It might throw exception
    but this method will let caller method to catch them.
    :param ipv6_addr: ipv6 address
    :return: ipv6 address in compat format
    """
    return socket.inet_ntop(socket.AF_INET6,
                            socket.inet_pton(socket.AF_INET6, ipv6_address))
