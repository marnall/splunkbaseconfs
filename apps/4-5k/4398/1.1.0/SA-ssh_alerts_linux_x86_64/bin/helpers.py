'''
Provide helper functions for reuse in alert actions
'''
import os
import sys
import logging
import logging.handlers

#pylint: disable=import-error
from splunk import setupSplunkLogger
#pylint: enable=import-error

def check_known_hosts():
    '''
    Used to check for existing known hosts file and create if needed with perms
    '''
    home_dir = os.path.expanduser('~')
    ssh_dir = os.path.join(home_dir,'.ssh')
    if not os.path.exists(ssh_dir):
        os.mkdir(ssh_dir, 0o700)
    known_hosts = os.path.join(ssh_dir,'known_hosts')
    if not os.path.exists(known_hosts):
        with open(known_hosts,'a'):
            os.utime(known_hosts, None)
            os.chmod(known_hosts, 0o644)

def load_paramiko():
    '''
    Find the correct directory for loading paramiko
    Load modules from paramkio, set logging, and return modules
    '''
    base_dir = os.path.dirname(os.path.realpath(__file__))
    if sys.version_info >= (3, 0):
        sys.path.insert(0, os.path.join(base_dir,'lib3'))
    else:
        sys.path.insert(0, os.path.join(base_dir,'lib2'))

    #pylint: disable=import-outside-toplevel
    from paramiko import SSHClient,AutoAddPolicy,common
    #pylint: enable=import-outside-toplevel

    common.logging.basicConfig(level=common.ERROR)
    return SSHClient, AutoAddPolicy

#http://dev.splunk.com/view/logging/SP-CAAAFCN
def setup_logging():
    '''
    Used to standard method to setup app logging
    '''
    logger = logging.getLogger('splunk.ssh_alerts')
    splunk_home = os.environ['splunk_home']

    logging_default_config_file = os.path.join(splunk_home, 'etc', 'log.cfg')
    logging_local_config_file = os.path.join(splunk_home, 'etc', 'log-local.cfg')
    logging_stanza_name = 'python'
    base_log_path = os.path.join('var', 'log', 'splunk')
    logging_file_name = "ssh_alerts.log"
    logging_format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(
            splunk_home,
            base_log_path,
            logging_file_name
        ), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(logging_format))
    logger.addHandler(splunk_log_handler)
    setupSplunkLogger(
        logger,
        logging_default_config_file,
        logging_local_config_file,
        logging_stanza_name
    )
    return logger
