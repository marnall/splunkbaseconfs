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
BIN_DIR = Path(APP_DIR / 'bin')
PREREQ_FILE = Path(
    APP_DIR /
    'appserver' /
    'static' /
    'utils' /
    'json' /
    'prereqs-checks-template.json'
)


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_get_prereqs_json_rest_endpoint'
)


class GetPrereqsJson(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        try:
            if PREREQ_FILE.is_file():
                with open(str(PREREQ_FILE), 'r') as prereqs:
                    payload = {
                        'prereqs': json.load(prereqs),
                        'status': 200,
                        'error': None,
                        'message': 'success'
                    }

                logger.info(f'status="success", message="Successfully loaded prereqs-checks.json, preparing response."')

            else:
                payload = {
                    'prereqs': None,
                    'status': 404,
                    'error': 'No prereqs-checks.json file found.',
                    'message': 'prereqs-checks.json does not exist yet.'
                }

                logger.warning(f'status="WARN", message="The prereqs file, prereqs-checks.json, is missing."')

        except Exception as e:
            payload = {
                'error': str(e),
                'message': f'An error occurred while loading prereqs-checks.json: {str(e)}',
                'config': None,
                'status': 500
            }

            logger.error(f'status="ERROR", message="An error occurred while loading prereqs-checks.json: {str(e)}"')

            
        self.log_stop_message()


        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Prereqs JSON REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Prereqs JSON REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass
