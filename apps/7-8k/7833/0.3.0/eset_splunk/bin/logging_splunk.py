import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def set_logger() -> None:
    splunk_home = os.getenv("SPLUNK_HOME")
    log_filename = Path(splunk_home).joinpath("var", "log", "splunk", "eset.log")

    file_handler = TimedRotatingFileHandler(log_filename.as_posix(), when="d", interval=1, backupCount=5)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(module)-8s %(message)s")
    formatter.converter = time.gmtime
    file_handler.setFormatter(formatter)

    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(file_handler)
