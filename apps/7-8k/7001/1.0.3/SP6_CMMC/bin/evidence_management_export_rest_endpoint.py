from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
import logging
from time import sleep
from zipfile import ZipFile
import re
import shutil
from uuid import uuid4


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

from helpers.file_utils import (
    read_file_as_base64_string,
    write_bytes_to_file
)
from helpers.evidence_management import (
    get_storage_info,
    get_sharepoint_client_secret,
    update_storage_config
)
from helpers.logger import setup_logger
import pendulum
import splunklib.results as search_results
import splunklib.client as client
from spo.spo import SPO


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_file_explorer_export_rest_endpoint'
)


class ExportEvidence(PersistentServerConnectionApplication):
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

            if key == 'control':
                control = value

            elif key == 'system':
                system = value

            elif key == 'framework':
                framework = value

            elif key == 'export_type':
                export_type = value

            elif key == 'selected_evidence':
                selected_evidence = json.loads(value)

        evidence_kvstore = service.kvstore[EVIDENCE_KVSTORE_NAME]
        storage_config = get_current_storage_config(system)
        storage_method = storage_config['storage_method']

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

                spo.create_cmmc_base_evidence_directory_structure(system, framework)

                if export_type == 'control':
                    evidence = get_evidence_by_control(
                        control, 
                        framework, 
                        system,
                        service,
                        storage_method
                    )

                    directories = create_control_structured_zip(
                        evidence, 
                        system, 
                        framework, 
                        control, 
                        storage_method, 
                        spo
                    )

                    outfile_path = Path(
                        directories['exports_directory'],
                        str(uuid4())
                    )

                elif export_type == 'custom':
                    evidence = get_custom_evidence(
                        selected_evidence,
                        evidence_kvstore
                    )

                    directories = create_custom_structured_zip(
                        evidence, 
                        framework, 
                        system, 
                        storage_method, 
                        spo
                    )

                    outfile_path = Path(
                        directories['exports_directory'],
                        str(uuid4())
                    )


        elif storage_method == 'local':
            if export_type == 'control':
                evidence = get_evidence_by_control(
                    control, 
                    framework, 
                    system,
                    service,
                    storage_method
                )

                directories = create_control_structured_zip(
                    evidence, 
                    system, 
                    framework, 
                    control, 
                    storage_method, 
                    None
                )

                outfile_path = Path(
                    directories['exports_directory'],
                    str(uuid4())
                )

            elif export_type == 'custom':
                evidence = get_custom_evidence(
                    selected_evidence,
                    evidence_kvstore
                )

                directories = create_custom_structured_zip(
                    evidence, 
                    framework, 
                    system,
                    storage_method,
                    None
                )

                outfile_path = Path(
                    directories['exports_directory'],
                    str(uuid4())
                )


        shutil.make_archive(
            str(outfile_path),
            'zip',
            str(directories['structured_directory'])
        )

        export_zip_base64 = read_file_as_base64_string(f'{str(outfile_path)}.zip')

        cleanup(
            outfile_path,
            directories['structured_directory']
        )

        return {
            'payload': {
                'zip': export_zip_base64,
                'name': 'export.zip',
                'status': 200
            },
            'status': 200
        }


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: export REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="File Explorer: export REST endpoint started at {timestamp}."')
        return


def cleanup(outfile_path, structured_directory):
    Path(
        f'{str(outfile_path)}.zip'
    ).unlink()

    shutil.rmtree(
        str(structured_directory),
        ignore_errors=True
    )

    return


def create_custom_structured_zip(evidence, framework, system, storage_method, spo):
    exports_directory = Path(
        APP_DIR /
        'evidence' /
        framework /
        system /
        'exports'
    )

    structured_directory = Path(
        exports_directory /
        str(uuid4())
    )

    for evidence_file in evidence:
        if isinstance(evidence_file['tags'], str):
            evidence_file['tags'] = [evidence_file['tags']]

        for tag in evidence_file['tags']:
            objective_letter = get_objective_letter_from_tag(tag)
            control = get_control_from_tag(tag)

            domain_directory = Path(
                structured_directory /
                control[:2]
            )

            control_directory = Path(
                domain_directory /
                control
            )

            control_directory.mkdir(
                parents=True,
                exist_ok=True
            )

            if objective_letter:
                objective_directory = Path(
                    control_directory,
                    objective_letter
                )

                objective_directory.mkdir(
                    parents=True,
                    exist_ok=True
                )

                if storage_method == 'local':
                    shutil.copy(
                        str(evidence_file['file_path']),
                        str(objective_directory)
                    )

                else:
                    response = spo.download_file(
                        path=str(Path(evidence_file['file_path']).parent),
                        file_to_download=evidence_file['file_name']
                    )

                    write_bytes_to_file(
                        str(
                            Path(
                                objective_directory / 
                                evidence_file['file_name']
                            )
                        ),
                        response['data']
                    )

            else:
                if storage_method == 'local':
                    shutil.copy(
                        str(evidence_file['file_path']),
                        str(control_directory)
                    )

                else:
                    response = spo.download_file(
                        path=str(Path(evidence_file['file_path']).parent),
                        file_to_download=evidence_file['file_name']
                    )
                    
                    write_bytes_to_file(
                        str(
                            Path(
                                control_directory / 
                                evidence_file['file_name']
                            )
                        ),
                        response['data']
                    )

    return {
        'exports_directory': exports_directory,
        'structured_directory': structured_directory
    }


def create_control_structured_zip(evidence, system, framework, control, storage_method, spo):
    exports_directory = Path(
        APP_DIR /
        'evidence' /
        framework /
        system /
        'exports'
    )

    structured_directory = Path(
        exports_directory /
        str(uuid4())
    )

    domain_directory = Path(
        structured_directory /
        control[:2]
    )

    control_directory = Path(
        domain_directory /
        control
    )

    control_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    for evidence_file in evidence:
        if isinstance(evidence_file['tags'], str):
            evidence_file['tags'] = [evidence_file['tags']]

        for tag in evidence_file['tags']:
            objective_letter = get_objective_letter_from_tag(tag)
            _control = get_control_from_tag(tag)

            if objective_letter:
                if control == _control:
                    objective_directory = Path(
                        control_directory,
                        objective_letter
                    )

                    objective_directory.mkdir(
                        parents=True,
                        exist_ok=True
                    )

                    if storage_method == 'local':
                        shutil.copy(
                            str(evidence_file['file_path']),
                            str(objective_directory)
                        )

                    else:
                        response = spo.download_file(
                            path=str(Path(evidence_file['file_path']).parent),
                            file_to_download=evidence_file['file_name']
                        )

                        write_bytes_to_file(
                            str(
                                Path(
                                    objective_directory / 
                                    evidence_file['file_name']
                                )
                            ),
                            response['data']
                        )

            else:
                if storage_method == 'local':
                    shutil.copy(
                        str(evidence_file['file_path']),
                        str(control_directory)
                    )

                else:
                    response = spo.download_file(
                        path=str(Path(evidence_file['file_path']).parent),
                        file_to_download=evidence_file['file_name']
                    )
                    
                    write_bytes_to_file(
                        str(
                            Path(
                                control_directory / 
                                evidence_file['file_name']
                            )
                        ),
                        response['data']
                    )

    return {
        'exports_directory': exports_directory,
        'structured_directory': structured_directory
    }


def get_control_from_tag(tag):
    return re.match('([A-Z]{2}\.L\d-\d+\.\d+\.\d+).*', tag).group(1)


def get_objective_letter_from_tag(tag):
    assessment_objective_letter_match = re.match('.*?\s-\s([a-z])$', tag)
    assessment_objective_letter = None

    if assessment_objective_letter_match:
        assessment_objective_letter = assessment_objective_letter_match.group(1)

    return assessment_objective_letter


def make_export_zip(file_path_list, system, framework):
    exports_dir = Path(
        APP_DIR /
        'evidence' /
        framework /
        system /
        'exports'
    )

    exports_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    export_zip = Path(
        exports_dir,
        f'export.zip'
    )

    with ZipFile(str(export_zip), 'w') as zip_archive:
        for file in file_path_list:
            file_name = re.match('.*/(.*)', file).group(1)
            zip_archive.write(file, file_name)

    return export_zip


def get_file_path_list(evidence):
    file_path_list = []

    for file in evidence:
        if file['file_path'] not in file_path_list:
            file_path_list.append(file['file_path'])

    return file_path_list


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


def get_custom_evidence(selected_evidence, evidence_kvstore):
    evidence = []

    for _key in selected_evidence:
        query = json.dumps(
            {
                '_key': _key
            },
            indent=1
        )

        evidence_record = evidence_kvstore.data.query(query=query)[0]
        evidence.append(evidence_record)

    return evidence


def create_exports_directory(app_directory, system):
    exports_directory = Path(
        app_directory /
        'evidence' /
        system /
        'exports'
    )

    try:
        exports_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    except Exception as e:
        logger.error(f'status="ERROR", message="An error occurred while creating the exports directory: {str(e)}"')
        return None

    else:
        logger.info(f'status="success", message="Created exports directory: {str(exports_directory)}.", system="{system}"')
        return exports_directory
    

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
