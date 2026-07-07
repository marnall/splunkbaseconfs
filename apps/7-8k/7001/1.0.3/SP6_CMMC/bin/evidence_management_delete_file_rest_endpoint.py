from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
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
CONTROL_STATUS_KVSTORE_NAME = 'sp6_control_status'
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
from helpers.evidence_management import (
    update_storage_config,
    get_sharepoint_client_secret,
    get_storage_info,
    get_service
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_file_explorer_delete_file_rest_endpoint'
)


class DeleteEvidenceFile(PersistentServerConnectionApplication):
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

            if key == '_key':
                _key = value

            elif key == 'system':
                system = value


        evidence_kvstore = service.kvstore[EVIDENCE_KVSTORE_NAME]
        control_status_kvstore = service.kvstore[CONTROL_STATUS_KVSTORE_NAME]
        storage_config = get_current_storage_config(system)
        storage_method = storage_config['storage_method']
        evidence = get_evidence_by_key(
            _key,
            evidence_kvstore
        )
        evidence_file_path = evidence['file_path']

        evidence_kvstore.data.delete(
            json.dumps({
                '_key': _key
            })
        )

        if storage_method == 'cloud':
            if storage_config['cloud_config']['provider'] == 'SharePoint':
                storage_config['cloud_config']['client_secret'] = get_sharepoint_client_secret(service, system)

                spo = SPO(
                    spo_site_domain=storage_config['cloud_config']['site_domain'],
                    site=storage_config['cloud_config']['site_name'],
                    site_root_dir=storage_config["cloud_config"]["site_root_dir"],
                    site_list_name=storage_config["cloud_config"]["site_list_name"],
                    client_id=storage_config['cloud_config']['client_id'],
                    client_secret=storage_config['cloud_config']['client_secret'],
                    tenant_id=storage_config['cloud_config'].get('tenant_id'),
                    resource=storage_config['cloud_config'].get('resource'),
                    service=service,
                    logger=logger
                )

                if spo.init_error:
                    self.log_stop_message()

                    return {
                        'payload': {
                            'status': spo.init_error['status_code'],
                            'files': [],
                            'error': spo.init_error['error'],
                            'message': spo.init_error['message']
                        },
                        'status': 200
                    }

                update_storage_config(
                    storage_config=storage_config,
                    config_file_path=CONFIG_FILE,
                    tenant_id=spo.tenant_id,
                    resource=spo.resource,
                    system_name=system
                )

                spo.create_cmmc_base_evidence_directory_structure(system, evidence['framework'])

                response = spo.delete_item(
                    path=str(Path(evidence_file_path).parent),
                    item_to_delete=evidence['file_name']
                )

                if not response['ok']:
                    logger.error(f'status="ERROR", message="An error occurred while attempting to delete the file: {response["message"]}", status_code="{response["status_code"]}", {SPLUNK_SYSTEM_ID_NAME}="{system}"')

                    return {
                        'payload': {
                            'status': response['status_code'],
                            'error': response['message'],
                            'message': f'An error occurred while attempting to delete the file. Status code = {response["status_code"]}'
                        },
                        'status': 200
                    }

                self.log_stop_message()

                return {
                    'payload': {
                        'status': 200
                    },
                    'status': 200
                }

        Path(evidence_file_path).unlink()

        for tag in evidence['tags']:
            existing_control_evidence = get_evidence_by_control(
                get_control_from_tag(tag),
                'cmmc',
                system,
                service,
                storage_method
            )

            if not existing_control_evidence:
                set_control_evidence_found_for_control(
                    system,
                    tag, 
                    control_status_kvstore
                )

        self.log_stop_message()

        # Return the response
        return {
            'payload': {
                'status': 200,
            },
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: delete_file REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: delete_file REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


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


def set_control_evidence_found_for_control(system, tag, control_status_kvstore):
    control = get_control_from_tag(tag)

    query = json.dumps(
        {
            SPLUNK_SYSTEM_ID_NAME: system,
            'status_type': 'control',
            'control': control
        },
        indent=1
    )

    status_record = control_status_kvstore.data.query(query=query)[0]

    if status_record['control_evidence_found'] != False:
        status_record['control_evidence_found'] = False

        control_status_kvstore.data.update(
            status_record['_key'],
            json.dumps(status_record)
        )

    return


def get_control_from_tag(tag):
    return re.match('([A-Z]{2}\.L\d-\d+\.\d+\.\d+).*', tag).group(1)


def get_evidence_by_key(_key, evidence_kvstore):
    kvstore_initialized = False
    evidence = None

    query = json.dumps(
        {
            '_key': _key
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            evidence = evidence_kvstore.data.query(query=query)[0]

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    if not evidence:
        return None

    return evidence


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
