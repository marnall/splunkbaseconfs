#!/usr/bin/env python

import logging
import logging.handlers
import os

BASE_LOGGER_NAME = 'sa-itsi-driftdetection'
DEFAULT_LEVEL = logging.INFO


def get_splunkhome_path():
    return os.path.normpath(os.environ['SPLUNK_HOME'])


def make_splunkhome_path(p):
    return os.path.join(get_splunkhome_path(), *p)


def setup_splunk_logging(logger, has_splunk_home):
    if has_splunk_home:
        try:
            import splunk
            LOGGING_DEFAULT_CONFIG_FILE = make_splunkhome_path(['etc', 'log.cfg'])
            LOGGING_LOCAL_CONFIG_FILE = make_splunkhome_path(['etc', 'log-local.cfg'])
            LOGGING_STANZA_NAME = 'python'
            splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                                     LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME, verbose=False)
        except ImportError:
            logger.warning('Unable to import splunk python module: cannot setup splunk logging.')


def setup_handlers(logger, path, has_splunk_home, formatter):
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=1000000, backupCount=5 if has_splunk_home else 0
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except FileNotFoundError:
        logger.warning(f"Log file {path} not found. Logging to console only.")
    except Exception as e:
        logger.warning(f"Error setting up log file at {path}: {str(e)}. Logging to console only.")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def get_logger(name=BASE_LOGGER_NAME, level=DEFAULT_LEVEL, formatter=None):
    """Returns a general-purpose logger instance.

    The logger is configured to write to both:
      * A (rotated) file in $SPLUNK_HOME/var/log/splunk/<name>.log
      * Standard error.

    Additionally, it consults $SPLUNK_HOME/etc/log.cfg and
    log-local.cfg for default log-levels. You can configure per-logger
    log-levels by adding a property to log-local.cfg that looks like:

        [python]
        myloggername = DEBUG

    For DEBUG messages to show up in search.log as well, you will need
    to modify $SPLUNK_HOME/etc/log-searchprocess-local.cfg to contain:

        category.ChunkedExternProcessor=DEBUG

    Idiomatic usage is:

        #!/usr/bin/env python
        import setup_logging
        logger = setup_logging.get_logger()

        def foo():
            logger.warning("Red Alert, report to battle stations")

    """
    logger = logging.getLogger(name)

    # Initial setup
    if len(logger.handlers) == 0:
        logger.setLevel(level)
        logger.propagate = False

        # Determine if SPLUNK_HOME is set, and define the log file path accordingly
        has_splunk_home = 'SPLUNK_HOME' in os.environ
        path = make_splunkhome_path(['var', 'log', 'splunk', name + '.log']) if has_splunk_home else os.path.normpath(
            os.path.join(os.getcwd(), name + '.log'))

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        default_formatter = logging.Formatter(
            '%(created)f PID %(process)d %(asctime)s %(levelname)s [%(name)s] [%(funcName)s] %(message)s')

        used_formatter = formatter if formatter else default_formatter

        setup_handlers(logger, path, has_splunk_home, used_formatter)
        setup_splunk_logging(logger, has_splunk_home)

    return logger
