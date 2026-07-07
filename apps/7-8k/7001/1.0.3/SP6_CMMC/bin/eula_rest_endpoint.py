from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import logging
import sys


SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(
    SPLUNK_DIR /
    'etc' /
    'apps' /
    APP_NAME
)
LOCAL_DIR = Path(
    APP_DIR /
    'local'
)
BIN_DIR = Path(APP_DIR / 'bin')
EULA_FILE = Path(
    LOCAL_DIR /
    'eula_accepted.txt'
)


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_eula_rest_endpoint'
)


class EULA(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        data = json.loads(
            in_string.decode('utf-8')
        )

        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'action':
                action = value

        LOCAL_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        if action == 'get':
            if EULA_FILE.is_file():
                payload = {
                    'eula_accepted': True,
                    'status': 200,
                    'error': None,
                    'message': None
                }

            else:
                payload = {
                    'eula_accepted': False,
                    'status': 200,
                    'error': None,
                    'message': None
                }

        elif action == 'write':
            try:
                with open(str(EULA_FILE), 'w+'):
                    pass

            except Exception as e:
                logger.error(f'message="An error occurred while creating the EULA accpeted file", error="{str(e)}"')

                payload = {
                    'eula_accepted': False,
                    'status': 200,
                    'error': str(e),
                    'message': "An error occurred while creating the EULA accpeted file"
                }

            else:
                payload = {
                    'eula_accepted': True,
                    'status': 200,
                    'error': None,
                    'message': None
                }


        self.log_stop_message()


        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="EULA REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="EULA REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass
