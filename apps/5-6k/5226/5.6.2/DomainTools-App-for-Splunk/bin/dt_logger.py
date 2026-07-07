from __future__ import absolute_import
import splunk
from splunk.clilib import cli_common as cli
import logging
import logging.handlers
import os
import time


class DTLogger:
    """This class sets up a logger to audit DomainTools python scripts

        Attributes:
            product (str): API product you want to log a message for (iris_investigate, iris_enrich, iris_detect, account_information)
            file (str): file you want to log a message for (log_enrichment, lookup)
            user (str): user who generated the error
            feature (str): where in the app the error was generated
            logger (Logger): Python logger object
    """
    def __init__(self, product, filename, user, feature):
        self.product = product
        self.file = filename
        self.user = user
        self.feature = feature
        self.logger = logging.getLogger("splunk.domaintools")
        try:
            self.config = cli.getConfStanza("domaintools", "domaintools")
        except Exception:
            self.config = {}

        if self.config.get("logging_on") == "1":
            self.setup()


    def setup(self):
        splunk_home = os.environ["SPLUNK_HOME"]

        log_path = os.path.join(splunk_home, "var", "log", "splunk", "domaintools.log")
        log_format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

        logging.Formatter.converter = time.gmtime
        splunk_log_handler = logging.handlers.RotatingFileHandler(log_path, mode="a")
        splunk_log_handler.setFormatter(logging.Formatter(log_format))
        self.logger.addHandler(splunk_log_handler)

        splunk.setupSplunkLogger(
            self.logger,
            os.path.join(splunk_home, "etc", "log.cfg"),
            os.path.join(splunk_home, "etc", "log-local.cfg"),
            "python",
        )

    def debug(self, message, params=None):
        """Write debug level message to domaintools.log.

            :param message: message to log
            :param params: optional dictionary of additional key value pairs to log

            example:
            logger.debug("my message", {"status": "up"})
        """
        self.log("debug", message, params)

    def info(self, message, params=None):
        """Write info level message to domaintools.log.

            :param message: message to log
            :param params: optional dictionary of additional key value pairs to log

            example:
            logger.info("my message", {"status": "up"})
        """
        self.log("info", message, params)

    def warning(self, message, params=None):
        """Write warning level message to domaintools.log.

            :param message: message to log
            :param params: optional dictionary of additional key value pairs to log

            example:
            logger.warning("my message", {"status": "up"})
        """
        self.log("warning", message, params)

    def error(self, message, params=None):
        """Write error level message to domaintools.log.

            :param message: message to log
            :param params: optional dictionary of additional key value pairs to log

            example:
            logger.error("my message", {"status": "up"})

        """
        self.log("error", message, params)

    def log(self, level, message, params):
        """Write message to domaintools.log.

            :param level: log level (debug, info, warning, error)
            :param message: message to log
            :param params: optional dictionary of additional key value pairs to log

            example:
            logger.log("error", "my message", {"status": "up"})

        """
        if self.config.get("logging_on") != "1":
            return
        
        params_string = ""
        if params:
            for key, value in params.items():
                params_string += '{0}="{1}",'.format(key, value)

        method_to_call = getattr(self.logger, level)
        method_to_call(
            'product=%s, file=%s, log_level=%s, feature="%s" user=%s, %s message="%s"',
            self.product,
            self.file,
            level,
            self.feature,
            self.user,
            params_string,
            message,
        )
