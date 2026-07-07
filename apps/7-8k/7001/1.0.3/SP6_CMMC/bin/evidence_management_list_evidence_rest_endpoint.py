from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import sys
import json
import logging
from time import sleep
import re


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
EVIDENCE_KVSTORE_NAME = 'sp6_evidence'
SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'


sys.path.append(
    str(
        Path(
            APP_DIR /
            'bin'
        )
    )
)

from spo.spo import SPO
import splunklib.client as client
import splunklib.results as search_results
import pendulum
from helpers.evidence_management import (
    get_storage_info,
    get_service
)
from helpers.logger import setup_logger


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_file_explorer_get_directory_contents_rest_endpoint'
)


class FileExplorer(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        # Load data submitted by browser (in bytes)
        data = json.loads(
            in_string.decode('utf-8')
        )

        service = get_service(
            client=client,
            session_key=data['session']['authtoken'],
            app_name=APP_NAME
        )['service']

        # Assignments from submitted data
        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'system':
                system = value

            if key == 'framework':
                framework = value

            if key == 'control':
                control = value   

        
        storage_config = get_current_storage_config(system)
        storage_method = storage_config['storage_method'] 
        evidence = get_evidence_by_control(
            control, 
            framework, 
            system,
            service,
            storage_method
        )
        processed_evidence = process_evidence(
            evidence,
            control
        )

        self.log_stop_message()

        # Return the response
        return {
            'payload': {
                'status': 200,
                'evidence': processed_evidence
            },
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: get_directory_contents REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: get_directory_contents REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


def process_evidence(evidence, control):
    if evidence:
        for file in evidence:
            if isinstance(file['tags'], str):
                file['tags'] = [file['tags']]

            for tag in file['tags']:
                if control in tag:
                    if re.match(f'^{control}\s-\s(\w)$', tag):
                        file['objective'] = re.match(f'^{control}\s-\s(\w)$', tag).group(1)

                    else:
                        file['objective'] = None

            file['created_date'] = pendulum.from_timestamp(int(file['created_date'])).format('MM/DD/YYYY HH:mm:ss')
            
            file['last_modified'] = pendulum.from_timestamp(int(file['last_modified'])).format('MM/DD/YYYY HH:mm:ss')

    return evidence


def get_evidence_by_control(control, framework, system, service, storage_method):
    query = f'| inputlookup {EVIDENCE_KVSTORE_NAME} | mvexpand tags | search (tags="{control}" OR tags="{control} -*"), framework="{framework}", storage_method="{storage_method}", {SPLUNK_SYSTEM_ID_NAME}="{system}"'

    try:
        search_job = service.jobs.create(
            query
        )

    except Exception as e:
        logger.error(f'status="ERROR", message="Cannot create systems list search: {query}", exception="{str(e)}"')
        return None

    while not search_job.is_done():
        sleep(.2)

    if int(search_job['resultCount']) == 0:
        logger.warning(f'status="WARN", message="{EVIDENCE_KVSTORE_NAME} contains 0 systems, cannot proceed."')
        return []
    
    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    evidence_list = []

    for result in search_result:
        if isinstance(result, dict):
            evidence_list.append(result)

        elif isinstance(result, search_results.Message):
            logger.warning(f'status="WARN", message="Received message instead of search result: {str(result)}"')

    return evidence_list


def get_current_storage_config(system):
    complete_storage_info = get_storage_info(CONFIG_FILE)
    default_config = {
        'storage_method': 'local'
    }

    if complete_storage_info:
        try:
            return complete_storage_info[system]

        except KeyError:
            return default_config

    else:
        return default_config


def get_service(client, session_key, app_name):
    logger.info(f'message="Creating Splunk service.", session_key="{session_key}", app_name="{app_name}"')

    service_data = {
        'service': None,
        'error': None
    }

    try:
        service = client.connect(
            **{
                'token': session_key, 
                'owner': 'nobody', 
                'app': app_name
            }
        )

    except Exception as e:
        service_data['error'] = str(e)
        logger.error(f'status="ERROR", message="An error occurred creating the Splunk service: {str(e)}"')

    else:
        service_data['service'] = service
        logger.info(f'status="success", message="Successfully created Splunk service."')
    
    return service_data
