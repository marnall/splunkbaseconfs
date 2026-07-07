"""Centralized logging configuration for all scripts in the app."""
import logging
import os
import sys
from logging import FileHandler, Logger, StreamHandler, basicConfig, config


def setup_logging(app_name) -> Logger:
    """Configure logging for the application.

    This function should be called at the start of every script.
    It's idempotent - safe to call multiple times.
    """
    # Skip if already configured
    if hasattr(setup_logging, '_configured'):
        return logging.getLogger(app_name)

    try:
        # Ensure log directory exists
        _ensure_log_directory()

        # Load logging configuration
        splunk_home = os.environ.get('SPLUNK_HOME', '')
        logging_conf_path = os.path.join(os.path.dirname(__file__), '..', 'default', 'logging.conf')

        # Resolve to real path
        logging_conf_path = os.path.realpath(logging_conf_path)

        if os.path.exists(logging_conf_path):
            config.fileConfig(logging_conf_path, disable_existing_loggers=False, defaults={'SPLUNK_HOME': splunk_home})
        else:
            # Fallback to basic config if logging.conf not found
            _configure_basic_logging(app_name, splunk_home)

        setup_logging._configured = True
        logger = logging.getLogger(app_name)
        logger.info(f'Logging configured successfully (PID: {os.getpid()})')
        return logger

    except Exception as e:
        # Fallback to basic stderr logging
        basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s - %(message)s', stream=sys.stderr)
        logger = logging.getLogger(app_name)
        logger.error(f'Failed to configure logging: {e}', exc_info=True)
        return logger


def _ensure_log_directory():
    """Ensure the log directory exists with proper permissions."""
    try:
        splunk_home = os.environ.get('SPLUNK_HOME')
        if not splunk_home:
            return

        log_dir = os.path.join(splunk_home, 'var', 'log', 'splunk')
        log_dir = os.path.realpath(log_dir)

        # Security: Ensure log_dir is within SPLUNK_HOME
        splunk_home_real = os.path.realpath(splunk_home)
        if not log_dir.startswith(splunk_home_real):
            return

        # Create directory with proper permissions
        os.makedirs(log_dir, mode=0o755, exist_ok=True)

    except Exception:
        # Fail silently - stderr logging will still work
        pass


def _configure_basic_logging(app_name, splunk_home):
    """Configure basic file + stderr logging if logging.conf is missing."""
    log_file = os.path.join(splunk_home or '/tmp', 'var', 'log', 'splunk', f'{app_name}.log')

    basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s - %(message)s',
                handlers=[StreamHandler(sys.stderr), FileHandler(log_file, mode='a', encoding='utf-8')])
