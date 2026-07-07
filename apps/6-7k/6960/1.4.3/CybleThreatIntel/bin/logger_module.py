import logging.handlers
import os

class Logger:
    def __init__(self, log_file_name, log_level=logging.INFO):
        self.log_file_name = log_file_name
        self.log_level = log_level
        self.logger = self.setup_logger()

    def setup_logger(self):
        logger = logging.getLogger('custom_rest')
        logger.propagate = False
        logger.setLevel(self.log_level)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', self.log_file_name),
            maxBytes=25000000,
            backupCount=5
        )
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def get_logger(self):
        return self.logger
