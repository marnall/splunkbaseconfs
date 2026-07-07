import json
import sys
from os import environ
from socket import gethostname
from uuid import uuid4
from pathlib import Path
import logging
from time import sleep
import re


# Constants
APP_NAME = Path(__file__).absolute().parts[-3]
SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
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
EVIDENCE_DIR = Path(
    APP_DIR /
    'evidence'
)
AUDIT_INDEX_NAME = 'sp6_audit'
STATUS_KVSTORE_NAME = 'sp6_control_status'
AUDIT_RECORD_AUTHOR = 'splunk-system-user'
AUDIT_SOURCE = 'sp6_cmmc'
AUDIT_SOURCETYPE = 'sp6_cmmc:audit'
AUDIT_RECORD_SEARCH_NAME = 'sp6-evidence-mod-time-check'
SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'
EVIDENCE_KVSTORE_NAME = 'sp6_evidence'
BUILD = 1

sys.path.insert(
    0, 
    str(Path(
        APP_DIR / 
        'bin'
    ))
)

from splunklib.modularinput import *
from helpers.logger import setup_logger
from helpers.indexes import get_index
import splunklib.client as client
import splunklib.results as search_results
from spo.spo import SPO
import pendulum
from helpers.evidence_management import (
    update_storage_config,
    get_sharepoint_client_secret,
    get_storage_info,
    get_sharepoint_path
)


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_evidence_mod_time_checks_input'
)


class EvidenceModTimeChecks(Script):
    def get_scheme(self):
        scheme = Scheme("ASCERA Evidence Mod Time Checks")
        scheme.description = 'Generates sp6_audit events showing the latest mod time for all uploaded evidence.'
        scheme.use_external_validation = True
        return scheme
    

    def validate_input(self, validation_definition):
        pass


    def stream_events(self, inputs, ew):
        log_start_message()

        service = get_service(
            self._input_definition.metadata['session_key']
        )

        if not service:
            return
        
        control_status_kvstore = service.kvstore[STATUS_KVSTORE_NAME]

        if not control_status_kvstore:
            return
        
        evidence_kvstore = service.kvstore[EVIDENCE_KVSTORE_NAME]

        if not evidence_kvstore:
            return

        systems_list = get_systems_list(service)

        if not systems_list:
            return

        check_for_audit_index(service)

        for input_name, _ in list(inputs.inputs.items()):
            for system in systems_list:
                storage_config = get_current_storage_config(system)
                storage_method = storage_config['storage_method']
                evidence = get_current_evidence(
                    'cmmc',
                    storage_method,
                    system,
                    service
                )

                check_evidence_mod_times(
                    evidence=evidence,
                    storage_method=storage_method,
                    storage_config=storage_config,
                    status_kvstore=control_status_kvstore,
                    system=system,
                    service=service,
                    framework='cmmc',
                    evidence_kvstore=evidence_kvstore,
                    input_name=input_name,
                    ew=ew
                )


        log_stop_message()


def check_evidence_mod_times(evidence, storage_method, storage_config, status_kvstore, system, service, framework, evidence_kvstore, input_name, ew):
    if evidence:
        if storage_method == 'local':
            for evidence_file in evidence:
                if evidence_file.get('tags'):
                    file_path = evidence_file['file_path']
                    mod_time_epoch = int(Path(file_path).stat().st_mtime)
                    mod_time_pretty = pendulum.from_timestamp(mod_time_epoch).format('MM/DD/YYYY HH:mm:ss')

                    if isinstance(evidence_file['tags'], str):
                        evidence_file['tags'] = [evidence_file['tags']]

                    for tag in evidence_file['tags']:
                        assessment_objective_letter = get_objective_letter_from_tag(tag)
                        control = get_control_from_tag(tag)

                        control_status_record = get_control_status_record(
                            control,
                            status_kvstore,
                            system
                        )

                        create_audit_record(
                            review_title=f'{tag} evidence file {evidence_file["file_name"]} last modified {mod_time_pretty}',
                            review_description=f'{tag} evidence file {evidence_file["file_name"]} last modified {mod_time_pretty}',
                            filename=evidence_file["file_name"],
                            last_mod_time=mod_time_pretty,
                            last_mod_time_epoch=mod_time_epoch,
                            control_status_record=control_status_record,
                            control=control,
                            system_name=system,
                            assessment_objective_letter=assessment_objective_letter,
                            input_name=input_name,
                            ew=ew
                        )

                        evidence_file['last_modified'] = mod_time_epoch

                        evidence_kvstore.data.update(
                            evidence_file['_key'],
                            json.dumps(evidence_file)
                        )

        elif storage_method == 'cloud':
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

            update_storage_config(
                storage_config=storage_config,
                config_file_path=CONFIG_FILE,
                tenant_id=spo.tenant_id,
                resource=spo.resource,
                system_name=system
            )

            spo.create_cmmc_base_evidence_directory_structure(system, framework)

            spo_evidence_contents_response = spo.get_directory_contents(
                path=get_sharepoint_path(
                    storage_config=storage_config,
                    framework=framework,
                    system=system
                )
            )

            spo_evidence_file_data = get_spo_files_from_directory_content(
                spo_evidence_contents_response['contents']
            )

            for evidence_file in evidence:
                for data in spo_evidence_file_data:
                    if evidence_file['file_name'] == data['name']:
                        if evidence_file.get('tags'):
                            mod_time_pretty = data['last_modified']
                            mod_time_epoch = pendulum.from_format(
                                mod_time_pretty,
                                'MM/DD/YYYY HH:mm:ss'
                            ).format('X')

                            if isinstance(evidence_file['tags'], str):
                                evidence_file['tags'] = [evidence_file['tags']]

                            for tag in evidence_file['tags']:
                                assessment_objective_letter = get_objective_letter_from_tag(tag)
                                control = get_control_from_tag(tag)

                                control_status_record = get_control_status_record(
                                    control,
                                    status_kvstore,
                                    system
                                )

                                create_audit_record(
                                    review_title=f'{tag} evidence file {evidence_file["file_name"]} last modified {mod_time_pretty}',
                                    review_description=f'{tag} evidence file {evidence_file["file_name"]} last modified {mod_time_pretty}',
                                    filename=evidence_file["file_name"],
                                    last_mod_time=mod_time_pretty,
                                    last_mod_time_epoch=mod_time_epoch,
                                    control_status_record=control_status_record,
                                    control=control,
                                    system_name=system,
                                    assessment_objective_letter=assessment_objective_letter,
                                    input_name=input_name,
                                    ew=ew
                                )

                                evidence_file['last_modified'] = mod_time_epoch

                                evidence_kvstore.data.update(
                                    evidence_file['_key'],
                                    json.dumps(evidence_file)
                                )

                            break


def get_spo_files_from_directory_content(contents):
    files = []

    if contents:
        for file in contents['files']:
            files.append({
                'name': file['name'],
                'creation': pendulum.parse(file['created_on']).format('MM/DD/YYYY HH:mm:ss'),
                'last_modified': pendulum.parse(file['last_modified']).format('MM/DD/YYYY HH:mm:ss'),
                'type': 'file'
            })


    return files


def get_control_from_tag(tag):
    return re.match('([A-Z]{2}\.L\d-\d+\.\d+\.\d+).*', tag).group(1)


def get_objective_letter_from_tag(tag):
    assessment_objective_letter_match = re.match('.*?\s-\s([a-z])$', tag)
    assessment_objective_letter = None

    if assessment_objective_letter_match:
        assessment_objective_letter = assessment_objective_letter_match.group(1)

    return assessment_objective_letter


def get_current_evidence(framework, storage_method, system, service):
    query = f'| inputlookup {EVIDENCE_KVSTORE_NAME} | search framework="{framework}", storage_method="{storage_method}", {SPLUNK_SYSTEM_ID_NAME}="{system}"'

    try:
        search_job = service.jobs.create(
            query
        )

    except Exception as e:
        logger.error(f'status="ERROR", message="Cannot create evidence list search: {query}", exception="{str(e)}"')
        return None

    while not search_job.is_done():
        sleep(.2)

    if int(search_job['resultCount']) == 0:
        logger.warning(f'status="WARN", message="{EVIDENCE_KVSTORE_NAME} contains 0 evidence for system \'{system}\', cannot proceed.", {SPLUNK_SYSTEM_ID_NAME}="{system}"')
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


def get_systems_list(service):
    query = f'| inputlookup {STATUS_KVSTORE_NAME} | fields {SPLUNK_SYSTEM_ID_NAME} | dedup {SPLUNK_SYSTEM_ID_NAME}'

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
        logger.warning(f'status="WARN", message="{STATUS_KVSTORE_NAME} contains 0 systems, cannot proceed."')
        return None


    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    systems_list = []

    for result in search_result:
        if isinstance(result, dict):
            logger.info(f'status="INFO", message="Found new system in {STATUS_KVSTORE_NAME}: {result[SPLUNK_SYSTEM_ID_NAME]}"')
            systems_list.append(result[SPLUNK_SYSTEM_ID_NAME])

        elif isinstance(result, search_results.Message):
            logger.warning(f'status="WARN", message="Received message instead of search result: {str(result)}"')

    logger.info(f'status="INFO", message="{STATUS_KVSTORE_NAME} contains {len(systems_list)} systems."')

    return systems_list


def create_audit_record(review_title, review_description, filename, last_mod_time, last_mod_time_epoch, control_status_record, control, system_name, assessment_objective_letter, input_name, ew):
    timestamp = pendulum.now()
    epoch_s = int(timestamp.format('X'))
    _time = timestamp.to_atom_string()
    host = gethostname()

    audit_entry_json = {
        '_time': _time,
        'audit_id': str(uuid4()),
        'search_name': AUDIT_RECORD_SEARCH_NAME,
        'build': BUILD,
        'control': control,
        'assessment_objective_letter': assessment_objective_letter,
        'evidence_file_name': filename,
        'evidence_file_mod_time': last_mod_time,
        'evidence_file_mod_time_epoch': last_mod_time_epoch,
        SPLUNK_SYSTEM_ID_NAME: system_name,
        'control_owner': control_status_record['control_owner'],
        'control_operator': control_status_record['control_operator'],
        'control_reviewer': AUDIT_RECORD_AUTHOR,
        'control_status': control_status_record['control_status'],
        'record_author': AUDIT_RECORD_AUTHOR,
        'record_time': epoch_s,
        'review_description': review_description,
        'control_review_time': epoch_s,
        'review_title': review_title
    }

    event = Event(
        time=_time,
        stanza=input_name,
        host=host,
        index=AUDIT_INDEX_NAME,
        source=AUDIT_SOURCE,
        sourcetype=AUDIT_SOURCETYPE,
        data=json.dumps(audit_entry_json)
    )

    try:
        ew.write_event(event)

    except Exception as e:
        logger.error(f'status="ERROR", message="An error occurred while executing the audit entry search string.", error="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", search_name="{AUDIT_RECORD_SEARCH_NAME}", assessment_objective_letter="{assessment_objective_letter}", control="{control}"')

    else:
        logger.info(f'message="Added audit entry record to \'{AUDIT_INDEX_NAME}\' index for control \'{control}\': {review_title}.", control="{control}", evidence_file_name="{filename}", evidence_file_mod_time="{last_mod_time}", evidence_file_mod_time_epoch="{last_mod_time_epoch}", assessment_objective_letter="{assessment_objective_letter}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

    return


def get_control_status_record(practice, status_kvstore, system_name):
    kvstore_initialized = False
    kvstore_control_record = None
    query = json.dumps(
        {
            'control': practice,
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'status_type': 'control'
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            kvstore_control_record = status_kvstore.data.query(query=query)[0]

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds...", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", practice="{practice}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    if not kvstore_control_record:
        logger.error(f'status="ERROR", message="The control \'{practice}\' was not found in the \'{STATUS_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
        return None

    return kvstore_control_record


def check_for_audit_index(service):
    if not get_index(service, AUDIT_INDEX_NAME):
        logger.warning(f'status="WARN", message="\'{AUDIT_INDEX_NAME}\' index was not found on this local Splunk instance; attempting record inserts regardless. It is possible that the \'{AUDIT_INDEX_NAME}\' index is configured on an indexer instead of a search head."')

    return


def get_service(session_key):
    try:
        service = client.connect(
            **{
                'token': session_key,
                'owner': 'nobody',
                'app': APP_NAME
            }
        )

    except Exception as e:
        logger.error(f'status="ERROR", message="Could not create Splunk service.", exception="{str(e)}"')
        return None

    else:
        logger.info(f'message="Created service with session key: {session_key}."')
        return service


def log_stop_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Evidence Mod Time Checks input execution completed at {timestamp}."')
    return


def log_start_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Evidence Mod Time Checks input started at {timestamp}."')
    return


if __name__ == '__main__':
    sys.exit(
        EvidenceModTimeChecks().run(sys.argv)
    )
