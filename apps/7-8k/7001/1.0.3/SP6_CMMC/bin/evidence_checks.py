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
EVIDENCE_DIR = Path(
    APP_DIR /
    'evidence'
)
AUDIT_INDEX_NAME = 'sp6_audit'
STATUS_KVSTORE_NAME = 'sp6_control_status'
AUDIT_RECORD_AUTHOR = 'splunk-system-user'
AUDIT_SOURCE = 'sp6_cmmc'
AUDIT_SOURCETYPE = 'sp6_cmmc:audit'
AUDIT_RECORD_SEARCH_NAME = 'sp6-evidence-check'
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
import splunklib.client as client
import splunklib.results as search_results
from helpers.logger import setup_logger
from helpers.indexes import get_index
from helpers.evidence_management import get_storage_info
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_evidence_checks_input'
)


class EvidenceChecks(Script):
    def get_scheme(self):
        scheme = Scheme("ASCERA Evidence Checks")
        scheme.description = 'Generates sp6_audit events showing the uploaded evidence status for all controls.'
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

        systems_list = get_systems_list(service)

        if not systems_list:
            return

        check_for_audit_index(service)

        for input_name, _ in list(inputs.inputs.items()):
            for system in systems_list:
                control_list = get_control_list(service, system)
                storage_config = get_current_storage_config(system)
                storage_method = storage_config['storage_method']
                check_for_evidence(
                    system,
                    service,
                    control_list,
                    storage_method,
                    control_status_kvstore,
                    input_name,
                    ew
                )

        log_stop_message()


def check_for_evidence(system, service, control_list, storage_method, status_kvstore, input_name, ew):
    for control in control_list:
        control_evidence_found = False

        control_status_record = get_control_status_record(
            control,
            status_kvstore,
            system
        )
        
        evidence = get_evidence_by_control(
            control,
            'cmmc',
            system,
            service,
            storage_method
        )

        if evidence:
            control_evidence_found = True

            for evidence_file in evidence:
                if isinstance(evidence_file['tags'], str):
                    evidence_file['tags'] = [evidence_file['tags']]

                for tag in evidence_file['tags']:
                    if tag == control or f'{control} - ' in tag:
                        create_audit_record(
                            review_title=f'{tag} has evidence uploaded',
                            review_description=f'{tag} has evidence uploaded: {evidence_file["file_name"]}',
                            control_status_record=control_status_record,
                            control=control,
                            evidence_available=True,
                            system_name=system,
                            assessment_objective_letter=get_objective_letter_from_tag(tag),
                            evidence_file=evidence_file["file_name"],
                            input_name=input_name,
                            ew=ew
                        )

        else:
            create_audit_record(
                review_title='Missing Evidence',
                review_description=f'Control {control} is missing evidence',
                control_status_record=control_status_record,
                control=control,
                evidence_available=False,
                system_name=system,
                assessment_objective_letter=None,
                evidence_file=None,
                input_name=input_name,
                ew=ew
            )

        update_control_status_record(
            control_status_record,
            control_evidence_found,
            status_kvstore
        )


def get_objective_letter_from_tag(tag):
    assessment_objective_letter_match = re.match('.*?\s-\s([a-z])$', tag)
    assessment_objective_letter = None

    if assessment_objective_letter_match:
        assessment_objective_letter = assessment_objective_letter_match.group(1)

    return assessment_objective_letter


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


def get_control_list(service, system):
    query = f'| inputlookup {STATUS_KVSTORE_NAME} | search status_type="control", {SPLUNK_SYSTEM_ID_NAME}="{system}" | fields control'

    try:
        search_job = service.jobs.create(
            query
        )

    except Exception as e:
        logger.error(f'status="ERROR", message="Cannot create controls list search: {query}", exception="{str(e)}"')
        return None

    while not search_job.is_done():
        sleep(.2)

    if int(search_job['resultCount']) == 0:
        logger.warning(f'status="WARN", message="{STATUS_KVSTORE_NAME} contains 0 controls, cannot proceed."')
        return None
    
    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    control_list = []

    for result in search_result:
        if isinstance(result, dict):
            control_list.append(result['control'])

        elif isinstance(result, search_results.Message):
            logger.warning(f'status="WARN", message="Received message instead of search result: {str(result)}"')

    return control_list


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


def create_audit_record(review_title, review_description, control_status_record, control, evidence_available, system_name, assessment_objective_letter, evidence_file, input_name, ew):
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
        SPLUNK_SYSTEM_ID_NAME: system_name,
        'control_owner': control_status_record['control_owner'],
        'control_operator': control_status_record['control_operator'],
        'control_reviewer': AUDIT_RECORD_AUTHOR,
        'control_status': control_status_record['control_status'],
        'record_author': AUDIT_RECORD_AUTHOR,
        'record_time': epoch_s,
        'review_description': review_description,
        'control_review_time': epoch_s,
        'review_title': review_title,
        'evidence_file': evidence_file,
        'evidence_available': evidence_available
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
        logger.error(f'status="ERROR", message="An error occurred while creating the audit entry record.", error="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", search_name="{AUDIT_RECORD_SEARCH_NAME}", assessment_objective_letter="{assessment_objective_letter}", control="{control}"')

    else:
        logger.info(f'message="Added audit entry record to \'{AUDIT_INDEX_NAME}\' index for control \'{control}\': {review_title}.", control="{control}", evidence_available="{evidence_available}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", assessment_objective_letter="{assessment_objective_letter}"')

    return


def update_control_status_record(control_status_record, control_evidence_found, status_kvstore):
    _key = control_status_record['_key']
    control_status_record['control_evidence_found'] = control_evidence_found
    status_kvstore.data.update(
        _key,
        json.dumps(control_status_record)
    )

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


def log_stop_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Evidence Checks input execution completed at {timestamp}."')
    return


def log_start_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Evidence Checks input started at {timestamp}."')
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


if __name__ == "__main__":
    sys.exit(
        EvidenceChecks().run(sys.argv)
    )
