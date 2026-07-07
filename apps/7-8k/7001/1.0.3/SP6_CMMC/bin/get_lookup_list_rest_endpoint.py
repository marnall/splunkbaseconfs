from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import logging
import sys
import json
from time import sleep


SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(
    SPLUNK_DIR /
    'etc' /
    'apps' /
    APP_NAME
)
BIN_DIR = Path(APP_DIR / 'bin')
LOOKUP_DIR = Path(
    APP_DIR /
    'lookups'
)


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import pendulum
import splunklib.client as client
import splunklib.results as search_results
import pendulum
from helpers.evidence_management import (
    get_service
)


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_get_lookup_list_rest_endpoint'
)


class GetLookupList(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        data = json.loads(
            in_string.decode('utf-8')
        )

        service = get_service(
            client=client,
            session_key=data['session']['authtoken'],
            app_name=APP_NAME
        )['service']

        lookup_list = []
        sample_prefix = 'SAMPLE_'
        kv_stores = {
            'SAMPLE_ascera_control_status.csv': {
                'initialized': False,
                'prod_name': 'sp6_control_status'
            },
            'SAMPLE_sp6_odps.csv': {
                'initialized': False,
                'prod_name': 'sp6_odps'
            },
            'SAMPLE_ascera_automation_event_searches.csv': {
                'initialized': False,
                'prod_name': 'sp6_automation_event_searches'
            }
        }

        for _, kv_store_data in kv_stores.items():
            kv_store_data['initialized'] = get_kv_store_init_status(
                kv_store_data['prod_name'],
                service
            )

        try:
            for file in LOOKUP_DIR.iterdir():
                if file.is_file() and file.name.startswith(sample_prefix):
                    prod_name = file.name.replace(sample_prefix, '')

                    lookup_list.append({
                        'sample_name': file.name,
                        'prod_name': prod_name if not kv_stores.get(file.name) else kv_stores[file.name]['prod_name'],
                        'initialized': Path(LOOKUP_DIR / prod_name).is_file() if not kv_stores.get(file.name) else kv_stores[file.name]['initialized'],
                        'lookup_type': 'File' if not kv_stores.get(file.name) else 'KV Store'
                    })

            payload = {
                'status': 200,
                'error': None,
                'message': 'success',
                'lookup_list': lookup_list
            }

        except Exception as e:
            message = 'An error occurred while compliling the lookup list.'
            logger.error(f'message="{message}", error="{str(e)}"')

            payload = {
                'status': 500,
                'error': str(e),
                'message': message,
                'lookup_list': None
            }

            
        self.log_stop_message()

        return {
            'payload': payload,
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Lookup List REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get Lookup List REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


def get_kv_store_init_status(prod_name, service):
    try:
        _ = service.kvstore[prod_name]

    except:
        return False
    
    try:
        search_job = service.jobs.create(
            f'| inputlookup {prod_name} | head 1'
        )

    except:
        return False
    
    while not search_job.is_done():
        sleep(.2)

    if int(search_job['resultCount']) == 0:
        return False

    else:
        return True
