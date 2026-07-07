import os
import logging
from configparser import ConfigParser
from logging.handlers import RotatingFileHandler

import splunk


def init_logger(config_path):
    """Given a `config` path to the app configuration, returns a
    configured logger.
    """
    # Read in app configuration
    with open(config_path) as f:
        config = ConfigParser(
            defaults={
                'splunk_home': os.environ.get('SPLUNK_HOME', '/opt/splunk')
            })
        config.readfp(f)
        # Setup the logger
        logger = logging.getLogger('splunk.avalon')
        handler = RotatingFileHandler(config.get('logging', 'log_path'))
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'))
        logger.addHandler(handler)
        splunk.setupSplunkLogger(
            logger,
            config.get('logging', 'config_file'),
            config.get('logging', 'config_file_local'),
            config.get('logging', 'stanza'))
        return logger

