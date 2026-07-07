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
CONFIG_FILE = Path(
    APP_DIR /
    'local' /
    'file_explorer_settings.json'
)
BIN_DIR = Path(APP_DIR / 'bin')


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum

from helpers.evidence_management import  get_storage_info


SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_file_explorer_setup_get_config_rest_endpoint'
)


class GetStorageConfig(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()
        logger.info(f'message="Loading config file from {str(CONFIG_FILE)}"')

        # Load data submitted by browser (in bytes)
        data = json.loads(
            in_string.decode('utf-8')
        )


        # Assignments from submitted data
        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'system':
                system_name = value


        storage_info = get_storage_info(CONFIG_FILE)

        if storage_info:
            logger.info(f'status="success", message="Successfully loaded storage config file from {str(CONFIG_FILE)}.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

            try:
                config = storage_info[system_name]

            except KeyError:
                config = {
                    'storage_method': 'local'
                }

            payload = {
                'config': config,
                'status': 200,
                'error': None,
                'message': 'success'
            }

        else:
            logger.warning(f'status="WARN", message="Storage config does not exist yet. Default storage config is local. Save a storage configuration to create the storage config file.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

            payload = {
                'config': None,
                'status': 404,
                'error': 'No storage config file.',
                'message': 'Storage config does not exist yet. Default storage config is local.'
            }
        

        self.log_stop_message()
            

        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer Setup: get_config REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer Setup: get_config REST endpoint started at {timestamp}."')
        return



    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass
