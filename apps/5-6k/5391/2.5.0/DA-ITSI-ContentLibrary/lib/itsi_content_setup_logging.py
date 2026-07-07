import os
import logging
import logging.handlers

# import splunk


LOG_DEFAULT_FMT = (
    "%(asctime)s process:%(process)d thread:%(threadName)s %(levelname)s "
    "[%(name)s] [%(module)s:%(lineno)d] [%(funcName)s] %(message)s"
)
ITSI_CONTENT_LOGGER = "itsicontent"
ITSI_CONTENT_LOG_FILE = "itsi_content_packs_itsicontent.log"

try:
    SPLUNK_HOME = os.environ["SPLUNK_HOME"]
except KeyError:
    SPLUNK_HOME = None

if SPLUNK_HOME is None:
    home_dir = os.path.expanduser("~")
    LOGGING_FILE_NAME = os.path.join(home_dir, ITSI_CONTENT_LOG_FILE)

    print(
        "-----> itsicontent log file is created at {}".format(
            os.path.abspath(LOGGING_FILE_NAME)
        )
    )

else:
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log.cfg")
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, "etc", "log-local.cfg")

    LOGGING_STANZA_NAME = "python"
    BASE_LOG_PATH = os.path.join("var", "log", "splunk")
    LOGGING_FILE_NAME = os.path.join(SPLUNK_HOME, BASE_LOG_PATH, ITSI_CONTENT_LOG_FILE)


def setupSplunkLogger(
    baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose=True
):
    """
    Cloned from splunk.setupSplunkLogger

    Takes the base logging.logger instance, and scaffolds the splunk logging namespace
    and sets up the logging levels as defined in the config files
    """

    levels = getSplunkLoggingConfig(
        baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose
    )

    for item in levels:
        loggerName = item[0]
        level = item[1]
        if hasattr(logging, level):
            logging.getLogger(loggerName).setLevel(getattr(logging, level))
        if verbose and (
            loggerName == "appender.python.maxFileSize"
            or loggerName == "appender.python.maxBackupIndex"
        ):
            baseLogger.info(
                "Python log rotation is not supported. Ignoring %s" % loggerName
            )


def getSplunkLoggingConfig(
    baseLogger, defaultConfigFile, localConfigFile, loggingStanzaName, verbose
):
    """
    Cloned from splunk.getSplunkLoggingConfig
    """

    loggingLevels = []

    # read in config file and set logging levels
    if os.access(localConfigFile, os.R_OK):
        if verbose:
            baseLogger.info("Using local logging config file: %s" % localConfigFile)
        logConfig = open(localConfigFile, "r")
    else:
        if verbose:
            baseLogger.info("Using default logging config file: %s" % defaultConfigFile)
        logConfig = open(defaultConfigFile, "r")

    try:
        inStanza = False
        for line in logConfig:

            # strip comments
            line = line.strip()
            if "#" in line:
                line = line[: (line.index("#"))]

            # skip blank lines
            line = line.strip()
            if not line:
                continue

            # # # skip malformatted lines: stanza, key=value, or WTF?
            if line.startswith("["):
                if not line.endswith("]") or line.index("]") != (len(line) - 1):
                    continue
            elif "=" in line:
                key_test, value_test = line.split("=")
                if not key_test or not value_test:
                    continue
            else:
                continue

            # # # validation done, now we finally have parsing logic proper
            if not inStanza and line.startswith("[%s]" % loggingStanzaName):
                inStanza = True
                continue
            elif inStanza:
                if line.startswith("["):
                    break
                else:
                    name, level = line.split("=", 1)
                    if verbose:
                        baseLogger.info(
                            "Setting logger=%s level=%s" % (name.strip(), level.strip())
                        )
                    loggingLevels.append((name.strip(), level.strip().upper()))
    except Exception as e:
        baseLogger.exception(e)
    finally:
        if logConfig:
            logConfig.close()

    return loggingLevels


def setup_logging():

    _logger = logging.getLogger(ITSI_CONTENT_LOGGER)

    splunk_log_handler = logging.handlers.RotatingFileHandler(
        LOGGING_FILE_NAME, maxBytes=5000000, backupCount=5
    )
    splunk_log_handler.setFormatter(logging.Formatter(LOG_DEFAULT_FMT))
    _logger.addHandler(splunk_log_handler)

    if SPLUNK_HOME is not None:
        # splunk.setupSplunkLogger
        setupSplunkLogger(
            _logger,
            LOGGING_DEFAULT_CONFIG_FILE,
            LOGGING_LOCAL_CONFIG_FILE,
            LOGGING_STANZA_NAME,
        )

    _logger.setLevel(logging.INFO)
    return _logger


logger = setup_logging()
