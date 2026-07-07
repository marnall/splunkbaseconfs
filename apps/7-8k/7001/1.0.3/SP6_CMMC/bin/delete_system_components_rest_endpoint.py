from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
from shutil import (
    rmtree
)
import json
import sys
import logging


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
LOCAL_DIR = Path(APP_DIR / 'local')
STORAGE_CONFIG_FILE = Path(LOCAL_DIR / 'file_explorer_settings.json')
CIS_FILE = Path(LOCAL_DIR / 'cis.json')
SECURITY_STACK_CONFIG_FILE = Path(LOCAL_DIR / 'security_stack_config.json')
BASE_EVIDENCE_DIR = Path(APP_DIR / 'evidence')
BASE_ARTIFACT_HASHING_DIR = Path(APP_DIR / 'reporting' / 'artifact_hashing')


sys.path.append(
    str(BIN_DIR)
)

from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_delete_system_components_rest_endpoint'
)


class DeleteSystem(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

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


        # Delete System Hashed Evidence
        hashed_evidence_directory = Path(BASE_ARTIFACT_HASHING_DIR / system_name)

        if hashed_evidence_directory.exists():
            logger.info(f'message="Deleting hashed artifact directory for system \"{system_name}\""')
            rmtree(str(hashed_evidence_directory))


        # Delete System Evidence
        evidence_directory = Path(BASE_EVIDENCE_DIR / system_name)

        if evidence_directory.exists():
            logger.info(f'message="Deleting evidence directory for system \"{system_name}\""')
            rmtree(str(evidence_directory))


        # Delete Security Stack Config
        security_stack_config = load_config_file(SECURITY_STACK_CONFIG_FILE)

        if security_stack_config:
            if security_stack_config.get(system_name):
                logger.info(f'message="Deleting Security Stack Config for system \"{system_name}\""')
                del security_stack_config[system_name]
                save_convig_file(str(SECURITY_STACK_CONFIG_FILE), security_stack_config)


        # Delete System CIS
        cis_file = load_config_file(CIS_FILE)

        if cis_file:
            if cis_file.get(system_name):
                logger.info(f'message="Deleting Control Implementation Statements for system \"{system_name}\""')
                del cis_file[system_name]
                save_convig_file(str(CIS_FILE), cis_file)


        # Delete System Storage Config
        storage_config = load_config_file(STORAGE_CONFIG_FILE)

        if storage_config:
            if storage_config.get(system_name):
                logger.info(f'message="Deleting File Explorer Config for system \"{system_name}\""')
                del storage_config[system_name]
                save_convig_file(str(STORAGE_CONFIG_FILE), storage_config)


        self.log_stop_message()

        return {
            'payload': {
                'message': 'made it',
                'status': 200
            },
            'status': 200
        }


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Delete System Components REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Delete System Components REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass


def load_config_file(file_path):
    try:
        if file_path.is_file():
            logger.info(f'message="Config file ({file_path}) found, retrieving contents."')

            with open(str(file_path), 'r') as config_file:
                return json.load(config_file)

    except Exception as e:
        logger.error(f'status="ERROR", message="An error occurred while loading a config file ({file_path}): {str(e)}"')
        return None
    

def save_convig_file(file_path, new_config):
    logger.info(f'message="Saving updated config: ({file_path})"')

    try:
        with open(str(file_path), 'w') as config_file:
            json.dump(
                new_config,
                config_file,
                indent=2,
                default=str
            )

    except Exception as e:
        logger.error(f'status="ERROR", message="An error occurred while saving a config file ({file_path}): {str(e)}"')
