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
LOCAL_DIR = Path(
    APP_DIR /
    'local'
)
CONFIG_FILE = Path(
    LOCAL_DIR /
    'security_stack_config.json'
)


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_security_stack_config_save_config_rest_endpoint'
)


class SaveSecurityStackConfig(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        data = json.loads(
            in_string.decode('utf-8')
        )

        # Assignments from submitted data
        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'security_stack_config':
                security_stack_config = json.loads(value)


        # Create local directory if it doesn't exist
        LOCAL_DIR.mkdir(
            parents=True,
            exist_ok=True
        )


        try:
            with open(str(CONFIG_FILE), 'w+') as config_file:
                json.dump(
                    security_stack_config, 
                    config_file, 
                    indent=2
                )

            payload = {
                'status': 200,
                'error': None,
                'message': 'success'
            }

            logger.info(f'status="success", message="Successfully saved security_stack_config.json to {str(CONFIG_FILE)}, preparing response."')
                

        except Exception as e:
            payload = {
                'error': str(e),
                'message': f'An error occurred while saving the security stack config file: {str(e)}',
                'status': 500
            }

            logger.error(f'status="ERROR", message="An error occurred while saving the security stack config file: {str(e)}"')


        self.log_stop_message()
            

        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Security Stack Config: save_config REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Security Stack Config: save_config REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass
