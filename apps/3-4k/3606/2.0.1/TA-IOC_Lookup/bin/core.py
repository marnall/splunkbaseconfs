#   Core pyton file
#

import os
import logging
from logging import handlers


class Processor:
    """Processor Framework Class."""

    def __init__(self):
        """
        Initialize Processor class.

        :returns tons of stuff for all other scripts
        """
        # set working directory to current working directory
        self.base_dir = os.path.dirname(__file__)

        # find paths to log, local parent dirs
        self.log_dir = os.path.join(self.base_dir, '..', "logs")
        self.local_dir = os.path.join(self.base_dir, '..', "local")

        # Default logging options
        # Valid options: DEBUG, INFO, WARN, ERROR, CRITICAL
        self.log_level = "INFO"
        self.log_maxbytes = 1500000
        self.log_backup_count = 5

        # Initialize the logger
        self.logger_init()

    def logger_init(self):
        """
        Initialize the logger globally.

        :returns: True
        """
        # Let's attempt to make the log directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Instantiate a logger
        self.log = logging.getLogger("securitylookup")

        # Set the default logging level
        self.log.setLevel(self.log_level.upper())

        # Define the log filename and path
        log_file = "securitylookup.log"
        self.log_path = os.path.abspath(os.path.join(self.log_dir, log_file))

        # Setup our logfile
        file_handler = logging.handlers.RotatingFileHandler(filename=self.log_path,
                                                            mode='a',
                                                            maxBytes=int(self.log_maxbytes),
                                                            backupCount=int(self.log_backup_count))

        # Setup our STDERR output
        stderr_handler = logging.StreamHandler()

        # Define the format of the log file
        formatter = logging.Formatter
        log_format = formatter("%(asctime)s %(levelname)s %(name)s:%(filename)s:%(lineno)s: "
                               "%(message)s", datefmt='%Y-%m-%d %H:%M:%S')

        stderr_logformat = formatter("[%(asctime)s %(levelname)s] %(name)s: %(message)s")

        file_handler.setFormatter(log_format)
        stderr_handler.setFormatter(stderr_logformat)

        # Attach the handler to the logger
        self.log.addHandler(file_handler)
        self.log.addHandler(stderr_handler)

