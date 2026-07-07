from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
import logging
from time import sleep


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


sys.path.append(
    str(
        Path(
            APP_DIR /
            'bin'
        )
    )
)

from helpers.file_utils import (
    write_base64_string_to_file,
    convert_base64_string_to_binary
)
from helpers.evidence_management import (
    update_storage_config,
    get_sharepoint_client_secret,
    get_storage_info,
    get_service
)
from spo.spo import SPO
import splunklib.client as client
from helpers.logger import setup_logger
import pendulum
import re


SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_file_explorer_upload_file_rest_endpoint'
)


class FileUpload(PersistentServerConnectionApplication):
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


        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'system':
                system = value

            if key == 'evidence_files':
                evidence_files = json.loads(value)


        evidence_kvstore = service.kvstore[EVIDENCE_KVSTORE_NAME]
        control_status_kvstore = service.kvstore[CONTROL_STATUS_KVSTORE_NAME]
        storage_config = get_current_storage_config(system)
        storage_method = storage_config['storage_method']
        created_date = int(pendulum.now().format('X'))


        if storage_method == 'cloud':
            if storage_config['cloud_config']['provider'] == 'SharePoint':
                storage_config['cloud_config']['client_secret'] = get_sharepoint_client_secret(service, system)
                framework = evidence_files[0]['framework']

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

                spo.create_cmmc_base_evidence_directory_structure(system, framework)

                for file in evidence_files:
                    tags = file['tags']
                    file['name'] = get_dest_sharepoint_file_name(
                        evidence_kvstore,
                        file['name'],
                        framework,
                        storage_method
                    )
                    base_file_path = f'{storage_config["cloud_config"]["site_root_dir"]}/evidence/{framework}/{system}'

                    response = spo.upload_file(
                        path=base_file_path,
                        file_bytes=convert_base64_string_to_binary(file['file']),
                        file_name=file['name']
                    )

                    if not response['ok']:
                        logger.error(f'status="ERROR", message="An error occurred while uploading the file to SharePoint: {response["message"]}", status_code="{response["status_code"]}", {SPLUNK_SYSTEM_ID_NAME}="{system}"')

                        self.log_stop_message()

                        return {
                            'payload': {
                                'status': response['status_code'],
                                'error': response['message'],
                                'message': f'An error occurred while uploading the file. Status code = {response["status_code"]}'
                            },
                            'status': 200
                        }

                    kv_store_entry = {
                        'cui_system_splunk_id': system,
                        'framework': framework,
                        'file_name': file['name'],
                        'file_path': f'{base_file_path}/{file["name"]}',
                        'tags': tags,
                        'created_date': created_date,
                        'last_modified': created_date,
                        'storage_method': storage_config['storage_method'],
                        'cloud_provider': None if storage_config['storage_method'] == 'local' else storage_config['cloud_config']['provider']
                    }

                    evidence_kvstore.data.insert(
                        json.dumps(kv_store_entry)
                    )

                    for tag in tags:
                        set_control_evidence_found_for_control(
                            system,
                            tag,
                            control_status_kvstore
                        )

                self.log_stop_message()

                return {
                    'payload': {
                        'status': 200,
                        'error': None,
                        'message': 'success'
                    },
                    'status': 200
                }


        for file in evidence_files:
            file_name = file['name']
            framework = file['framework']
            system = file['system']
            file_contents_as_base64 = file['file']
            tags = file['tags']

            dest_directory = Path(
                APP_DIR /
                'evidence' /
                framework /
                system
            )

            dest_save_path = get_dest_save_path(
                dest_directory,
                file_name
            )

            Path(
                dest_directory
            ).mkdir(
                parents=True,
                exist_ok=True
            )

            save_status = write_base64_string_to_file(
                str(dest_save_path),
                file_contents_as_base64
            )

            kv_store_entry = {
                'cui_system_splunk_id': system,
                'framework': framework,
                'file_name': re.match('.*/(.*)', str(dest_save_path)).group(1),
                'file_path': str(dest_save_path),
                'tags': tags,
                'created_date': created_date,
                'last_modified': created_date,
                'storage_method': storage_config['storage_method'],
                'cloud_provider': None if storage_config['storage_method'] == 'local' else storage_config['cloud_config']['provider']
            }

            evidence_kvstore.data.insert(
                json.dumps(kv_store_entry)
            )

            for tag in tags:
                set_control_evidence_found_for_control(
                    system,
                    tag,
                    control_status_kvstore
                )

        self.log_stop_message()

        return {
            'payload': {
                'status': 200,
                'save_status': save_status
            },
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: upload_file REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: upload_file REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass

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

    if status_record['control_evidence_found'] != True:
        status_record['control_evidence_found'] = True

        control_status_kvstore.data.update(
            status_record['_key'],
            json.dumps(status_record)
        )

    return


def get_control_from_tag(tag):
    return re.match('([A-Z]{2}\.L\d-\d+\.\d+\.\d+).*', tag).group(1)


def get_dest_sharepoint_file_name(evidence_kvstore, file_name, framework, storage_method):
    def get_query(file_name_check):
        return json.dumps(
            {
                'file_name': file_name_check,
                'framework': framework,
                'storage_method': storage_method
            },
            indent=1
        )

    kvstore_initialized = False
    evidence_record = None
    query = get_query(file_name)

    while not kvstore_initialized:
        try:
            evidence_record = evidence_kvstore.data.query(query=query)[0]

        except IndexError:
            logger.info(f'message="File name \"{file_name}\", is unique, leaving fine name unaltered."')
            kvstore_initialized = True
            pass

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Evidence KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    counter = 1

    while evidence_record:
        extension = re.match('.*\.(.*)', file_name).group(1)
        base_file_name = re.match('(.*)\..*', file_name).group(1)
        updated_file_name = f'{base_file_name}-{counter}.{extension}'
        query = get_query(updated_file_name)

        try:
            evidence_record = evidence_kvstore.data.query(query=query)[0]

        except IndexError:
            evidence_record = None
            file_name = updated_file_name

        counter+=1

    return file_name


def get_dest_save_path(dest_directory, file_name):
    dest_save_path = Path(
        dest_directory /
        file_name
    )

    base_file_name = Path(file_name).stem
    extension = dest_save_path.suffix

    counter = 1

    while dest_save_path.exists():
        updated_base_file_name = f'{base_file_name}-{counter}'
        counter+=1
        dest_save_path = Path(
            dest_directory /
            f'{updated_base_file_name}{extension}'
        )

    return dest_save_path


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
