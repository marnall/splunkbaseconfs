import import_declare_test  # noqa: F401
from splunk.clilib import cli_common as cli
from solnlib import log

DEFAULT_LOG_LEVEL = "INFO"


def setup_logging(logger_name):
    """
    Set up Logger.

    :param logger_name: name for logger

    :return: logger object
    """
    logger = log.Logs().get_logger(logger_name)
    cfg = cli.getConfStanza("ta_cisco_thousandeyes_settings", "logging")
    log_level = cfg.get("loglevel")
    try:
        logger.setLevel(log_level)
    except Exception:
        logger.setLevel(DEFAULT_LOG_LEVEL)
    return logger
