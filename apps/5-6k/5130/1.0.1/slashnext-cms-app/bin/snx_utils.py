import logging
import logging.handlers
import os
import splunk
from splunk.clilib import cli_common as cli


def setup_logging():
    """Setup the Logger for our App's dedicated logging file (slashnext_cms.log)"snx"""
    logger = logging.getLogger('splunk.slashnext_cms')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "slashnext_cms.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                             LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


def get_config(conf_filename, stanza_name):
    """Get the App's configurations from the custom conf file declared (in our case slashnext.conf)"""
    appdir = os.path.dirname(os.path.dirname(__file__))

    default_confpath = os.path.join(appdir, "default", conf_filename)
    apikeyconf = cli.readConfFile(default_confpath)

    # Check if any key in default conf file is declared again in local conf file, then update it
    # because local configuration has high preference
    local_confpath = os.path.join(appdir, "local", conf_filename)
    if os.path.exists(local_confpath):
        localconf = cli.readConfFile(local_confpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content

    # return the requested stanza in the conf file
    return apikeyconf[stanza_name]