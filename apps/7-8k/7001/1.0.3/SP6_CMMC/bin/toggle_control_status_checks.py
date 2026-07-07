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
AUDIT_RECORD_SEARCH_NAME = 'sp6-toggle-control-status-check'
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
    'sp6_toggle_control_status_checks_input'
)


class ToggleControlStatusChecks(Script):
    def get_scheme(self):
        scheme = Scheme("ASCERA Toggle Control Status Checks")
        scheme.description = 'Toggles a control\'s status based on the statuses of the control\'s objectives.'
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
                toggle_control_statuses(
                    status_kvstore=control_status_kvstore,
                    service=service,
                    system_name=system_name,
                    input_name=input_name,
                    ew=ew
                )

        log_stop_message()


def toggle_control_statuses(status_kvstore, service, system_name, input_name, ew):
    all_control_records = get_all_control_records_for_system(
        system_name,
        status_kvstore
    )

    for control_record in all_control_records:
        control = control_record['control']

        control_not_met_objectives = get_not_met_obj_for_control(
            control,
            status_kvstore,
            system_name
        )

        if control_not_met_objectives:
            if control_record['control_status'] != 'Not Met':
                logger.info(f'message="Found \'Not Met\' objectives for control {control}, setting the control\'s status to \'Not Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

                control_record['control_status'] = 'Not Met'
                update_control_status_record(
                    control_record,
                    status_kvstore
                )

                logger.info(f'message="Updated control {control}\'s status to \'Not Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

                audit_message = f'Updated control {control}\'s status to \'Not Met\' due to at least 1 objective status of \'Not Met\'.'

                create_audit_record(
                    review_title=audit_message,
                    review_description=audit_message,
                    control_status_record=control_record,
                    control=control,
                    system_name=system_name,
                    input_name=input_name,
                    ew=ew
                )

        else:
            if control_record['control_status'] != 'Met':
                logger.info(f'message="Found all \'Met\' objectives for control {control}, setting the control\'s status to \'Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

                control_record['control_status'] = 'Met'
                update_control_status_record(
                    control_record,
                    status_kvstore
                )

                logger.info(f'message="Updated control {control}\'s status to \'Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

                audit_message = f'Updated control {control}\'s status to \'Met\' due to all of the control\'s objectives having a \'Met\' status.'

                create_audit_record(
                    review_title=audit_message,
                    review_description=audit_message,
                    control_status_record=control_record,
                    control=control,
                    system_name=system_name,
                    input_name=input_name,
                    ew=ew
                )


def create_audit_record(review_title, review_description, control_status_record, control, system_name, input_name, ew):
    timestamp = pendulum.now()
    epoch_s = int(timestamp.format('X'))
    _time = timestamp.to_atom_string()
    host = gethostname()

    audit_entry_json = {
        '_time': _time,
        'audit_id': str(uuid4()),
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
        'toggled_status': True,
        'search_name': AUDIT_RECORD_SEARCH_NAME
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
        logger.info(f'message="Added audit entry record to \'{AUDIT_INDEX_NAME}\' index for control \'{control}\': {review_title}", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')

    return


def get_not_met_obj_for_control(control, status_kvstore, system_name):
    kvstore_initialized = False
    not_met_objective_records = []

    query = json.dumps(
        {
            'control': control,
            'control_status': 'Not Met',
            'status_type': 'objective',
            SPLUNK_SYSTEM_ID_NAME: system_name
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            status_records_results = status_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

            for record in status_records_results:
                not_met_objective_records.append(record)

    return not_met_objective_records


def get_all_control_records_for_system(system_name, status_kvstore):
    kvstore_initialized = False
    control_records = None

    query = json.dumps(
        {
            'status_type': 'control',
            SPLUNK_SYSTEM_ID_NAME: system_name
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            control_records = status_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    return control_records


def update_control_status_record(control_record, status_kvstore):
    status_kvstore.data.update(
        control_record['_key'],
        json.dumps(control_record)
    )

    return


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
    logger.info(f'message="Toggle Control Status input execution completed at {timestamp}."')
    return


def log_start_message():
    timestamp = pendulum.now().to_datetime_string()
    logger.info(f'message="Toggle Control Status Checks input started at {timestamp}."')
    return
       

if __name__ == "__main__":
    sys.exit(
        ToggleControlStatusChecks().run(sys.argv)
    )
