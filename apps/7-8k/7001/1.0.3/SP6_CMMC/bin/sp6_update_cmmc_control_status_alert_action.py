import sys
import json
import logging
from helpers.logger import setup_logger
from helpers.kvstore import (
    get_kvstore
)
from helpers.indexes import get_index
import splunklib.client as client
from pathlib import Path
import pendulum
from time import sleep
from uuid import uuid4
import requests
import urllib.parse

# Constants
APP_NAME = Path(__file__).absolute().parts[-3]
AUDIT_INDEX_NAME = 'sp6_audit'
STATUS_KVSTORE_NAME = 'sp6_control_status'
GRC_INTEGRATION_KVSTORE_NAME = 'sp6_grc_tools'
AUTOMATION_EVENT_SEARCH_KVSTORE_NAME = 'sp6_automation_event_searches'
AUDIT_RECORD_AUTHOR = 'splunk-system-user'
AUDIT_SOURCE = 'sp6_cmmc'
AUDIT_SOURCETYPE = 'sp6_cmmc:audit'
BUILD = 1
SPLUNK_SYSTEM_ID_NAME = 'cui_system_splunk_id'


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_update_cmmc_control_status_alert_action'
)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # Get the current timestamp in appropriate formats
        current_time = pendulum.now()
        epoch_s = int(current_time.format('X'))
        _time = current_time.to_atom_string()


        # Get the data sent from the alert action
        payload = json.loads(sys.stdin.read())


        # Get the session key & create service object
        session_key = payload.get('session_key')
        service = client.connect(
            **{
                'token': session_key,
                'owner': 'nobody',
                'app': APP_NAME
            }
        )


        # The event data that triggered the alert action
        triggering_event = clean_triggering_event(payload.get('result'))
        system_splunk_id = triggering_event.get(SPLUNK_SYSTEM_ID_NAME)
        assessment_objective = triggering_event.get('assessment_objective_letter')
        uuid = triggering_event.get('uuid')


        if not system_splunk_id:
            logger.error(f'message="Cannot continue with alert action without a {SPLUNK_SYSTEM_ID_NAME} field in the search result.", search_result="{json.dumps(triggering_event)}"')
            return

        if not assessment_objective:
            logger.error(f'message="Cannot continue with alert action without an \'assessment_objective_letter\' field in the search result. ACE saved searches must apply to an assessment objective.", search_result="{json.dumps(triggering_event)}"')
            return


        include_search_results_values = ['true', '1']

       # Get the custom form field & other important values
        config_dict = payload.get('configuration')
        control = config_dict.get('control')
        review_title = config_dict.get('title').replace('\\', '\\\\').replace('"', '')
        review_description = config_dict.get('description').replace('\\', '\\\\').replace('"', '')
        control_status = config_dict.get('status')
        host = payload.get('server_host')
        search_name = payload.get('search_name')
        include_search_results = True if config_dict.get('include_search_results') in include_search_results_values else False

        logger.info(f'include_search_results="{include_search_results}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}"')


        # Retrieve the control's record from the sp6_control_status KV Store
        status_kvstore = get_kvstore(
            service,
            STATUS_KVSTORE_NAME
        )


        if not status_kvstore:
            logger.error(f'message="The \'{STATUS_KVSTORE_NAME}\' KV Store was not found.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}"')
            return


        kvstore_control_record = get_control_status_record(control, status_kvstore, system_splunk_id, assessment_objective, search_name)


        if not kvstore_control_record:
            logger.error(f'status="ERROR", message="The control \'{control}\' was not found in the \'{STATUS_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}"')
            return

        # Get system name from control status lookup
        system_name = kvstore_control_record['cui_system_name']

        # Update the control's KV Store record
        kvstore_control_record_key = kvstore_control_record['_key']
        kvstore_control_record['control_update_message'] = review_title
        kvstore_control_record['control_status'] = control_status
        kvstore_control_record['control_update_time'] = epoch_s
        status_kvstore.data.update(
            kvstore_control_record_key,
            json.dumps(kvstore_control_record)
        )
        logger.info(f'message="Updated \'{STATUS_KVSTORE_NAME}\' KV Store record for control \'{control}\'.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", status="{control_status}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}", control="{control}"')

        # Check if audit index is available on local Splunk instance
        if not get_index(service, AUDIT_INDEX_NAME):
            logger.warning(f'message="\'{AUDIT_INDEX_NAME}\' index was not found on this local Splunk instance; attempting record insert regardless.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}", control="{control}"')


        # Must clean the triggering event to produce a valid JSON event
        if include_search_results:
            for k,v in triggering_event.items():
                if type(v) == list:
                    triggering_event[k] = [i.replace('"', '').replace('\\', '\\\\') for i in v]

                if type(v) == str:
                    triggering_event[k] = v.replace('"', '').replace('\\', '\\\\')


            triggering_event_json = triggering_event

        else:
            triggering_event_json = {}


        audit_entry_json = {
            '_time': _time,
            'audit_id': str(uuid4()),
            'search_name': search_name,
            'build': BUILD,
            'control': control,
            SPLUNK_SYSTEM_ID_NAME: system_splunk_id,
            'assessment_objective_letter': assessment_objective,
            'control_owner': kvstore_control_record['control_owner'],
            'control_operator': kvstore_control_record['control_operator'],
            'control_reviewer': AUDIT_RECORD_AUTHOR,
            'control_status': control_status,
            'record_author': AUDIT_RECORD_AUTHOR,
            'record_time': epoch_s,
            'review_description': review_description,
            'control_review_time': epoch_s,
            'review_title': review_title,
            'search_result': triggering_event_json
        }

        audit_entry_string = json.dumps(audit_entry_json).replace('"', '\\"')

        search_string = f'| makeresults 1 | eval _raw="{audit_entry_string}" | collect addtime=true index={AUDIT_INDEX_NAME} source={AUDIT_SOURCE} sourcetype={AUDIT_SOURCETYPE} host={host}'

        try:
            service.search(search_string)

        except Exception as e:
            logger.error(f'status="ERROR", message="An error occurred while executing the audit entry search string.", error="{str(e)}", search_string="{search_string}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}", assessment_objective_letter="{assessment_objective}", control="{control}"')

        else:
            logger.info(f'message="Added audit entry record to \'{AUDIT_INDEX_NAME}\' index for control \'{control}\'.", control="{control}", assessment_objective_letter="{assessment_objective}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}"')


        # Set control status to 'Not Met' if any of the contorl's objectives are 'Not Met',
        # Set control status to 'Met' if all of the contorl's objectives are 'Met',
        not_met_objectives = get_not_met_obj_for_control(
            control,
            status_kvstore,
            system_splunk_id
        )

        control_record = get_control_status_record_for_control(
            control,
            status_kvstore,
            system_splunk_id
        )

        if not_met_objectives:
            if control_record['control_status'] != 'Not Met':
                logger.info(f'message="Found \'Not Met\' objectives for control {control}, setting the control\'s status to \'Not Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}"')

                control_record['control_status'] = 'Not Met'
                status_kvstore.data.update(
                    control_record['_key'],
                    json.dumps(control_record)
                )

                logger.info(f'message="Updated control {control}\'s status to \'Not Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}"')

        else:
            if control_record['control_status'] != 'Met':
                logger.info(f'message="Found all \'Met\' objectives for control {control}, setting the control\'s status to \'Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}"')

                control_record['control_status'] = 'Met'
                status_kvstore.data.update(
                    control_record['_key'],
                    json.dumps(control_record)
                )

                logger.info(f'message="Updated control {control}\'s status to \'Met\'.", control="{control}", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}", search_name="{search_name}"')



        # Retrieve the control's record from the sp6_control_status KV Store
        grc_kvstore = get_kvstore(
            service,
            GRC_INTEGRATION_KVSTORE_NAME
        )

        if not grc_kvstore:
            logger.error(f'message="The \'{GRC_INTEGRATION_KVSTORE_NAME}\' KV Store was not found.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')
            return

        kvstore_grc_status = get_status_webhooks(grc_kvstore, system_splunk_id)
        kvstore_grc_evidence = get_evidence_webhooks(grc_kvstore, system_splunk_id)

        if not kvstore_grc_status and not kvstore_grc_evidence:
            logger.error(f'status="ERROR", message="Could not fetch status and evidence webhooks in the \'{GRC_INTEGRATION_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')
            return

        # Retrieve the search for the automation record from the sp6_automation_event_searches KV Store
        automation_event_kvstore = get_kvstore(
            service,
            AUTOMATION_EVENT_SEARCH_KVSTORE_NAME
        )

        if not automation_event_kvstore:
            logger.error(f'message="The \'{AUTOMATION_EVENT_SEARCH_KVSTORE_NAME}\' KV Store was not found.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')
            return

        kvstore_automation_search = get_automation_event_search(automation_event_kvstore, system_splunk_id, uuid)

        if not kvstore_automation_search:
            logger.error(f'status="ERROR", message="No data drilldown search found for saved search with uuid=\'{uuid}\' from \'{AUTOMATION_EVENT_SEARCH_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')

        # Iterate through status urls
        for webhook in kvstore_grc_status:
            url = webhook['webhook_url']
            body = {
                'timestamp': epoch_s,
                'frameworkName': 'CMMC 2.0',
                'controlId': control,
                'objective': assessment_objective,
                'newStatus': control_status,
                'reason': review_description,
                'reasonTitle': review_title,
                'author': AUDIT_RECORD_AUTHOR,
                'systemId': system_splunk_id,
                'systemName': system_name,
                'messageType': 'Status'
            }
            # triggering_event_json can be empty if search results are not included
            if triggering_event_json:
                body['oldStatus'] = triggering_event_json['control_status_current']
            if uuid:
                body['uuid'] = uuid
            if kvstore_automation_search and kvstore_automation_search[0] and webhook.get('host'):
                body['url'] = generateSearchUrl(webhook['host'], kvstore_automation_search[0]['search'])
            try:
                successful_status_webhook = post_webhook_data(body, url, token=webhook['webhook_token'], system_splunk_id=system_splunk_id)
                if successful_status_webhook:
                    update_status_search_string = f'| inputlookup {GRC_INTEGRATION_KVSTORE_NAME} where _key={webhook["_key"]} | eval active="Active" | eval last_contact="{epoch_s}" | outputlookup {GRC_INTEGRATION_KVSTORE_NAME} append=True'
                else:
                    update_status_search_string = f'| inputlookup {GRC_INTEGRATION_KVSTORE_NAME} where _key={webhook["_key"]} | eval active="Inactive" | outputlookup {GRC_INTEGRATION_KVSTORE_NAME} append=True'
                service.search(update_status_search_string)
            except:
                logger.error(f'status="ERROR", message="Unsuccessful POST to status webhook.", url="{url}", body={body}')

        # Iterate through evidence urls
        for webhook in kvstore_grc_evidence:
            url = webhook['webhook_url']
            body = {
                'name': search_name,
                'controlId': control,
                'objective': assessment_objective,
                'frameworkName': 'CMMC 2.0',
                'author': AUDIT_RECORD_AUTHOR,
                'reason': review_description,
                'reasonTitle': review_title,
                'value': triggering_event_json,
                "timestamp": epoch_s,
                'systemId': system_splunk_id,
                'systemName': system_name,
                'messageType': 'Evidence'
            }
            if uuid:
                body['uuid'] = uuid
            if kvstore_automation_search and kvstore_automation_search[0] and webhook.get('host'):
                body['url'] = generateSearchUrl(webhook['host'], kvstore_automation_search[0]['search'])
            try:
                successful_evidence_webhook = post_webhook_data(body, url, token=webhook['webhook_token'], system_splunk_id=system_splunk_id)
                if successful_evidence_webhook:
                    update_evidence_search_string = f'| inputlookup {GRC_INTEGRATION_KVSTORE_NAME} where _key={webhook["_key"]} | eval active="Active" | eval last_contact="{epoch_s}" | outputlookup {GRC_INTEGRATION_KVSTORE_NAME} append=True'
                else:
                    update_evidence_search_string = f'| inputlookup {GRC_INTEGRATION_KVSTORE_NAME} where _key={webhook["_key"]} | eval active="Inactive" | outputlookup {GRC_INTEGRATION_KVSTORE_NAME} append=True'
                service.search(update_evidence_search_string)
            except:
                logger.error(f'status="ERROR", message="Unsuccessful POST to evidence webhook.", url="{url}", body={body}')


def get_control_status_record_for_control(control, status_kvstore, system_name):
    kvstore_initialized = False
    kvstore_control_record = None

    query = json.dumps(
        {
            'control': control,
            'status_type': 'control',
            SPLUNK_SYSTEM_ID_NAME: system_name
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            kvstore_control_record = status_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    if kvstore_control_record:
        return kvstore_control_record[0]

    else:
        return None


def get_not_met_obj_for_control(control, status_kvstore, system_name):
    kvstore_initialized = False
    obj_status_records = []

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
                obj_status_records.append(record)

    return obj_status_records


def get_control_status_record(control, status_kvstore, system_name, assessment_objective, search_name):
    kvstore_initialized = False
    kvstore_control_record = None
    query = json.dumps(
        {
            'control': control,
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'status_type': 'objective',
            'assessment_objective_letter': assessment_objective
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
                logger.error(f'status="ERROR", message="An error occurred while querying the Control Status KV Store for status webhooks", control="{control}", assessment_objective_letter="{assessment_objective}", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", search_name="{search_name}"')
                return None

        else:
            kvstore_initialized = True

    if not kvstore_control_record:
        logger.error(f'status="ERROR", message="The control \'{control}\' was not found in the \'{STATUS_KVSTORE_NAME}\' KV Store.", assessment_objective_letter="{assessment_objective}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}", search_name="{search_name}"')
        return None

    return kvstore_control_record

def get_status_webhooks(grc_kvstore, system_name):
    kvstore_initialized = False
    kvstore_grc_record = None
    query = json.dumps(
        {
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'type': 'status',
            'enabled': 'true'
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            kvstore_grc_record = grc_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds...", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the GRC Integration KV Store", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                return None

        else:
            kvstore_initialized = True

    if not kvstore_grc_record:
        logger.error(f'status="ERROR", message="Could not fetch status webhooks in the \'{GRC_INTEGRATION_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
        return None

    return kvstore_grc_record

def get_evidence_webhooks(grc_kvstore, system_name):
    kvstore_initialized = False
    kvstore_grc_record = None
    query = json.dumps(
        {
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'type': 'evidence',
            'enabled': 'true'
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            kvstore_grc_record = grc_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds...", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the GRC Integration KV Store for evidence webhooks", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                return None

        else:
            kvstore_initialized = True

    if not kvstore_grc_record:
        logger.error(f'status="ERROR", message="Could not fetch evidence webhooks in the \'{GRC_INTEGRATION_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
        return None

    return kvstore_grc_record

def get_automation_event_search(automation_event_kvstore, system_name, uuid):
    kvstore_initialized = False
    kvstore_automation_event_record = None
    query = json.dumps(
        {
            SPLUNK_SYSTEM_ID_NAME: system_name,
            'uuid': uuid,
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            kvstore_automation_event_record = automation_event_kvstore.data.query(query=query)

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds...", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the Automation Event Search KV Store", exception="{str(e)}", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
                return None

        else:
            kvstore_initialized = True

    if not kvstore_automation_event_record:
        logger.error(f'status="ERROR", message="Could not fetch Automation Event Search in the \'{AUTOMATION_EVENT_SEARCH_KVSTORE_NAME}\' KV Store.", {SPLUNK_SYSTEM_ID_NAME}="{system_name}"')
        return None

    return kvstore_automation_event_record

def clean_triggering_event(triggering_event):
    keys_to_delete = []

    for key, value in triggering_event.items():
        if not value:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del triggering_event[key]

    return triggering_event

def post_webhook_data(body, url, token=None, system_splunk_id=None):
    logger.info(f'message="Posting Event Data to webhook." url="{url}", body={body}, {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')

    if token is not None:
        headers = {'Authorization': f'Bearer {token}'}
    else:
        logger.error(f'message="Expected authentication token but not found" url="{url}", body={body}, {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')
        return

    r = requests.post(
        url,
        json=body,
        headers=headers
    )

    if r.status_code == 200:
        logger.info(f'message="Successful response from webhook endpoint." url="{url}", body={body}, {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')
        return True

    else:
        logger.error(f'message="Received non-200 response from webhook endpoint." url="{url}", body={body}, response={r.text}, {SPLUNK_SYSTEM_ID_NAME}="{system_splunk_id}"')

    return False

def generateSearchUrl(domain: str, search: str):
    return f'https://{domain}:8000/en-US/app/{APP_NAME}/search?q={urllib.parse.quote(search)}'

if __name__ == '__main__':
    main()
