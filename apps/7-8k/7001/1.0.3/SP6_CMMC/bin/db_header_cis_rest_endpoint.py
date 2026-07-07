from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
import logging
import base64


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
LOCAL_DIR = Path(APP_DIR / 'local')
CIS_FILE_PATH = Path(LOCAL_DIR / 'cis.json')

sys.path.append(
    str(BIN_DIR)
)


from helpers.logger import setup_logger
import pendulum
from helpers.file_utils import (
    get_mimetype
)


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_db_header_cis_rest_endpoint'
)


class CIS(PersistentServerConnectionApplication):
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

            if key == 'request_action':
                request_action = value

            elif key == 'practice':
                practice = value

            elif key == 'new_cis':
                new_cis = value

            elif key == 'system':
                system_name = value

        domain = practice[:2]

        cis_object = get_cis_file(domain, practice, system_name)


        if request_action == 'update_cis':
            logger.info(f'message="Received request to update CIS for {practice}.", practice="{practice}", domain="{domain}"')

            cis_object[domain][practice] = new_cis

            update_cis_file(cis_object, system_name)

            # Return Successful Response
            payload = {
                'message': f'Updated CIS for {practice}.',
                'status': 'success'
            }

            self.log_stop_message()

            return {
                'payload': payload,
                'status': 200
            }


        elif request_action == 'get_cis':
            logger.info(f'message="Received request to retrieve CIS for {practice}.", practice="{practice}", domain="{domain}", system="{system_name}"')

            message = f'{practice} CIS not available yet for system {system_name}.'
            practice_has_cis = False

            if cis_object.get(domain):
                if cis_object[domain].get(practice):
                    practice_has_cis = True
                    message = None


            # Return Successful Response
            payload = {
                'practice_cis': cis_object,
                'message': message,
                'practice_has_cis': practice_has_cis,
                'status': 'success'
            }

            self.log_stop_message()

            return {
                'payload': payload,
                'status': 200
            }




    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="DB Header CIS REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="DB Header CIS REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass


def update_cis_file(new_cis, system_name):
    LOCAL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )
    
    with open(str(CIS_FILE_PATH), 'r') as cis_file:
        cis_object = json.load(cis_file)

    cis_object[system_name] = new_cis

    with open(str(CIS_FILE_PATH), 'w') as cis_file:
        json.dump(
            cis_object,
            cis_file,
            indent=2,
            default=str
        )

    return


def get_cis_file(domain, practice, system_name):
    logger.info(f'Loading CIS file: {CIS_FILE_PATH} for system {system_name}')
    
    LOCAL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    create_cis_file_if_not_esists(domain, practice, system_name)

    with open(str(CIS_FILE_PATH), 'r') as cis_file:
        cis_object = json.load(cis_file)

    if not cis_object.get(system_name):
        cis_object[system_name] = {
            domain: {
                practice: None
            }
        }

    elif not cis_object[system_name].get(domain):
        cis_object[system_name][domain] = {
                practice: None
        }

    return cis_object[system_name]



def create_cis_file_if_not_esists(domain, practice, system_name):
    if not CIS_FILE_PATH.is_file():
        logger.info(f'Creating initial CIS file: {CIS_FILE_PATH}, including system {system_name}')

        initial_data = {
            system_name: {
                domain: {
                    practice: None
                }
            }
        }

        with open(str(CIS_FILE_PATH), 'w+') as cis_file:
            json.dump(initial_data, cis_file, indent=2)

    return
