#
# SPDX-FileCopyrightText: 2026 Splunk LLC
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#

import logging
import logging.handlers as handlers
import os
import os.path as op


def make_splunk_path(parts):
    """
    :parm `parts`: path relative to $SPLUNK_HOME
    """

    home = os.environ["SPLUNK_HOME"]
    fullpath = op.normpath(op.join(home, *parts))
    return fullpath


def setup_logging(log_name, level_name="INFO"):
    """
    :param `log_name`: a str of logger file name
    :param `level_name` : a str of log level to be set
    :return: logging object with the log level set
    """

    level_name = level_name.upper() if level_name else "INFO"
    loglevel_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARN,
        "ERROR": logging.ERROR,
        "FATAL": logging.FATAL,
    }

    if level_name in loglevel_map:
        loglevel = loglevel_map[level_name]
    else:
        loglevel = logging.INFO

    logfile = make_splunk_path(["var", "log", "splunk", "%s.log" % log_name])
    logger = logging.getLogger(log_name)

    handler_exists = any([True for h in logger.handlers if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = handlers.RotatingFileHandler(
            logfile, mode="a+", maxBytes=26214400, backupCount=5
        )
        fmt_str = (
            "%(asctime)s %(levelname)s pid=%(process)d tid=%(threadName)s "
            "file=%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
        )
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(loglevel)
        logger.propagate = False

    logger.setLevel(loglevel)
    return logger
