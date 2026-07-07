import splunk
import logging, logging.handlers
import os

logger = None

LOG_MAX_SIZE_BYTES = 1024 ** 2 * 100
LOG_MAX_ROTATIONS = 5


def setup_logging(logger_name=None, log_file=None):
    if log_file is None or log_file in "":
        log_file = "app.log"
    if logger_name is None or logger_name in "":
        logger_name = "app_logger"

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    SPLUNK_HOME = os.environ["SPLUNK_HOME"]
    LOGGING_DEFAULT_CONFIG_FILE = SPLUNK_HOME + "/etc/log.cfg"
    LOGGING_LOCAL_CONFIG_FILE = SPLUNK_HOME + "/etc/log-local.cfg"
    LOGGING_STANZA_NAME = "python"
    BASE_LOG_PATH = SPLUNK_HOME + "/var/log/splunk/"
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, log_file),
        maxBytes=LOG_MAX_SIZE_BYTES,
        backupCount=LOG_MAX_ROTATIONS,
        mode="a",
    )
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(
        logger,
        LOGGING_DEFAULT_CONFIG_FILE,
        LOGGING_LOCAL_CONFIG_FILE,
        LOGGING_STANZA_NAME,
    )
    return logger


def main():
    global logger
    logger = setup_logging("endgame_logger", "endgame.log")


if __name__ == "__main__":
    main()
