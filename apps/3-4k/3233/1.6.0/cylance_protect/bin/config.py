"""
Description:
    Configuration data handling.

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.

Notes:
    Troubleshooting: check splunkd.log and cylance.log in Splunk's var/log/splunk folder.
"""


import logging
import logging.handlers
import os
import re


def get_logger(logger_name):
    cylogger = logging.getLogger(logger_name)
    return Redactor(cylogger, {'': 0})


import splunkutil


class Redactor(logging.LoggerAdapter):
    """
    This adapter redacts strings that look like a token.
    """
    def process(self, msg, kwargs):
        redacted_msg = re.sub(r"[0-9A-F]{32}", 'X'*32, msg, flags=re.IGNORECASE)
        return '[%s] %s' % (self.extra[''], redacted_msg), kwargs


class Configurator(object):
    """
    This class contains parameters, created by setup.xml, for tenant access, logging
    Tenant(s) info:
      - Tenant Name + Threat Data Report Token + Threat Data Report URL
    Logging:
      - log_size is the max size in bytes of a log file before rotating to next log file
      - log_rotations is the number of log file backups retained before the earliest log file is overwritten
    """

    def __init__(self, session_key):

        self.name = 'cylance'
        self.app_path = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', 'cylance_protect')
        self.log_path = os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk')
        self.log_filename = self.name + '.log'
        self.session_key = session_key
        self.log_level = 'WARNING'
        self.log_size = 1000000
        self.log_rotations = 7
        self.tenants = []
        self.log_format = '[%(asctime)s] %(levelname)-8s - %(message)s'
        self.log_format_debug = '[%(asctime)s] %(levelname)-8s - %(message)s p%(process)s ' +\
                                '{%(pathname)s:%(lineno)d} %(funcName)s - %(message)s'
        self.get_setup_data()
        self.set_up_logging()

        logging.debug(self.__str__())


    def __str__(self):
        info_files = 'App Path: {}\nLog Path: {}\nLog File: {}\n' +\
                     'Log Level: {}\nLog Size: {}\nLog Rotations: {}\n'
        info = info_files.format(self.app_path, self.log_path, self.log_filename,
                                 self.log_level, self.log_size, self.log_rotations)
        info += 'Tenants:'
        if self.tenants:
            for tenant in self.tenants:
                info_tenant = '\n\t{}, {}, {}'
                info += info_tenant.format(tenant['TenantName'], tenant['ThreatDataReportToken'], tenant['ThreatDataReportURL'])
            info = info.rstrip(',')

        return str(info)

    def get_setup_data(self):
        self.tenants = splunkutil.get_tenants(self.session_key)
        self.log_filename = 'cylance.log'
        self.log_level = 'WARNING'
        self.log_size = 1000000
        self.log_rotations = 7

    def set_up_logging(self):
        cylogger = logging.getLogger(self.name)
        log_absolute_filename = os.path.join(self.log_path, self.log_filename)
        cylogger.setLevel(self.log_level)
        formatter = logging.Formatter(self.log_format)
        if (self.log_level == 'DEBUG'):
            formatter = logging.Formatter(self.log_format_debug)

        rhandler = logging.handlers.RotatingFileHandler(
            log_absolute_filename, maxBytes=int(self.log_size), backupCount=int(self.log_rotations))
        rhandler.setFormatter(formatter)
        cylogger.addHandler(rhandler)

        # so as not to write to stdout (i.e. do not send to Splunk)
        cylogger.propagate = False

        # to restrict logging from the requests module to WARNING or higher, thus avoid all the INFO logs,
        # could .setLevel(logging.WARNING)
        logging.getLogger('requests').disabled = True
        logging.getLogger('requests.packages.urllib3').disabled = True

