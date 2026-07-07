import json
import sys
from os import environ
from socket import gethostname
from uuid import uuid4
from pathlib import Path
import logging
from time import sleep


# Constants
APP_NAME = Path(__file__).absolute().parts[-3]
SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
APP_DIR = Path(
    SPLUNK_DIR /
    'etc' /
    'apps' /
    APP_NAME
)
AUDIT_INDEX_NAME = 'sp6_audit'
STATUS_KVSTORE_NAME = 'sp6_control_status'
AUDIT_RECORD_AUTHOR = 'splunk-system-user'
AUDIT_SOURCE = 'sp6_cmmc'
AUDIT_SOURCETYPE = 'sp6_cmmc:audit'
AUDIT_RECORD_SEARCH_NAME = 'sp6-review-overdue-check'
SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'
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
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_review_overdue_checks_input'
)


class ReviewOverdueChecks(Script):
    def get_scheme(self):
        scheme = Scheme("ASCERA Review Overdue Checks")
        scheme.description = 'Generates a sp6_audit event for a control if the control review is overdue.'
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
            for system_name in systems_list:
                controls_list = get_controls_list(
                    system_name, 
                    control_status_kvstore
                )

                check_if_review_overdue(
                    practices_list=controls_list,
                    status_kvstore=control_status_kvstore,
                    service=service,
                    system_name=system_name,
                    input_name=input_name,
                    ew=ew
                )

        log_stop_message() 


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


def check_if_review_overdue(practices_list, status_kvstore, service, system_name, input_name, ew):
    for practice in practices_list:
        now_epoch_s = int(pendulum.now().format('X'))

        control_status_record = get_control_status_record(
            practice,
            status_kvstore,
            system_name
        )

        if control_status_record:
            # Test that control_review_due is an integer
            try:
                int(control_status_record['control_review_due'])

            except Exception as e:
                logger.warning(f'status="WARN", message="A non-integer value was found in the \'control_review_due\' field of the \'{STATUS_KVSTORE_NAME}\' KV Store for control {practice}. The value has been set to 0 and the control will be marked as \'Review Overdue\' until modified.", practice="{practice}", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                control_status_record['control_review_due'] = 0


            if int(control_status_record['control_review_due']) < now_epoch_s:
                control_review_due_pretty = pendulum.from_format(
                    str(control_status_record["control_review_due"]),
                    "X"
                ).to_datetime_string()
                audit_desc = f'Control was marked for review on {control_review_due_pretty} UTC.'

                update_control_status_record(
                    control_status_record,
                    True,
                    status_kvstore
                )

                create_audit_record(
                    review_title='Review Overdue',
                    review_description=audit_desc,
                    control_status_record=control_status_record,
                    control=practice,
                    system_name=system_name,
                    input_name=input_name,
                    ew=ew
                )

            else:
                update_control_status_record(
                    control_status_record,
                    False,
                    status_kvstore
                )

        else:
            logger.error(f'status="ERROR", message="A sp6_control_status record was not found for {practice}.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

    return


def create_audit_record(review_title, review_description, control_status_record, control, system_name, input_name, ew):
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
        'review_overdue': True
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
        logger.error(f'status="ERROR", message="An error occurred while executing the audit entry search string.", error="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", search_name="{AUDIT_RECORD_SEARCH_NAME}", control="{control}"')

    else:
        logger.info(f'message="Added audit entry record to \'{AUDIT_INDEX_NAME}\' index for control \'{control}\': {review_title}.", control="{control}", review_overdue="True", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

    return


def update_control_status_record(control_status_record, control_review_overdue, status_kvstore):
    _key = control_status_record['_key']
    control_status_record['control_review_overdue'] = control_review_overdue
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
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", practice="{practice}", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
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


def get_controls_list(system_name, status_kvstore):
    kvstore_initialized = False
    controls_list = []
    query = json.dumps(
        {
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'status_type': 'control'
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            results = status_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds...", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                return None

        else:
            kvstore_initialized = True

    if not results:
        logger.error(f'status="ERROR", message="No controls for system \'{system_name}\' were found in the \'{STATUS_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
        return None
    
    for result in results:
        controls_list.append(result['control'])

    return controls_list


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
    logger.info(f'message="Review Overdue Checks input execution completed at {timestamp}."')
    return


def log_start_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Review Overdue Checks input started at {timestamp}."')
    return


if __name__ == '__main__':
    sys.exit(
        ReviewOverdueChecks().run(sys.argv)
    )
