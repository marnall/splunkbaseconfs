import flare_constants as const
import logging
import logging.handlers
import os


def setup_logger() -> logging.Logger:
    """Configure a centralized rotating file logger for the Flare integration."""
    logger = logging.getLogger("flare_cron_job")
    # Start at INFO. The cron job will apply the
    # user-configured level dynamically once config is loaded.
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    splunk_home = os.environ.get("SPLUNK_HOME", "")
    if splunk_home:
        log_dir = os.path.join(splunk_home, "var", "log", "splunk")
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))

    log_file = os.path.join(log_dir, const.LOG_FILE_NAME)

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=const.LOG_MAX_BYTES,
        backupCount=const.LOG_BACKUP_COUNT,
    )
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
