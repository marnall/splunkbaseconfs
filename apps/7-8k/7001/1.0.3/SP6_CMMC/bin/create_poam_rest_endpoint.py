from splunk.persistconn.application import PersistentServerConnectionApplication
from pathlib import Path
from time import sleep
from os import environ
import sys
import logging
import json


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
POAM_KVSTORE_NAME = 'sp6_poams'
OWNER_DETAILS_KVSTORE = 'sp6_control_owner_details'


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import splunklib.results as search_results
import splunklib.client as client
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_create_poam_rest_endpoint'
)


class CreatePoam(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()


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


        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'new_poam':
                poam = json.loads(value)


        poam_kvstore = service.kvstore[POAM_KVSTORE_NAME]
        epoch_ts = int(pendulum.now().format('X'))

        poam_id = get_new_poam_id(service)
        poam['poam_id'] = poam_id['poam_id']
        poam['id_number'] = poam_id['id_number']
        poam['created_date'] = epoch_ts
        poam['last_modified'] = epoch_ts


        internal_id = poam_kvstore.data.insert(
            json.dumps(poam)
        )

        send_email_to_responsible_party(
            service,
            poam['responsible_party'],
            poam_id,
            poam['title']
        )


        self.log_stop_message()


        payload = {
            'status': 'success',
            'message': f'Created POAM with ID {internal_id["_key"]}',
            'internal_id': internal_id['_key'],
            'poam_id': poam_id
        }

        return {
            'payload': payload,
            'status': 200
        }


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Create POA&M REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Create POA&M REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass


def send_email_to_responsible_party(service, responsible_party_role, poam_id, poam_title):
    # Retrieve responsible party's email address from submitted role
    get_email_address_query = f'| inputlookup {OWNER_DETAILS_KVSTORE} | search role="{responsible_party_role}"'

    search_job = service.jobs.create(get_email_address_query)

    while not search_job.is_done():
        sleep(.2)

    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    to_email_address = None

    for result in search_result:
        if isinstance(result, search_results.Message):
            logger.warning(f'message="Received message instead of result: {str(result)}"')

        elif isinstance(result, dict):
            to_email_address = result['email']

    search_job.cancel()

    if not to_email_address:
        logger.warning(f'message="Unable to retrieve email address for responsible party with the role \'{responsible_party_role}\'"')
        return
    

    # Send the email to the responsible party's email address
    email_message = f'You have been selected as the responsible party on a new POA&M.\nPOA&M Title: {poam_title}\nPOA&M ID: {poam_id["poam_id"]}'
    email_subject = f"New POA&M Assigned: {poam_title}"

    # sendemail cannot be first command with Splunk so the '| makeresults 1 | eval this="that"' nonsense is needed
    send_email_query = f'| makeresults 1 | eval this="that" | sendemail to="{to_email_address}" subject="{email_subject}" message="{email_message}"'

    search_job = service.jobs.create(send_email_query)

    while not search_job.is_done():
        sleep(.2)

    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    for result in search_result:
        if isinstance(result, search_results.Message):
            logger.warning(f'message="Received message instead of result: {str(result)}"')

        elif isinstance(result, dict):
            logger.info(result)

    search_job.cancel()

    return


def get_new_poam_id(service):
    query = f'| inputlookup {POAM_KVSTORE_NAME} | sort +id_number | fields id_number | tail 1'

    search_job = service.jobs.create(query)

    while not search_job.is_done():
        sleep(.2)

    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    last_poam_id_number = None

    for result in search_result:
        if isinstance(result, search_results.Message):
            logger.warning(f'message="Received message instead of result: {str(result)}"')

        elif isinstance(result, dict):
            last_poam_id_number = result['id_number']

    if not last_poam_id_number:
        poam_id = {
            'id_number': 1,
            'poam_id': 'POAM-1'
        }
        

    else:
        id_number = int(last_poam_id_number) + 1
                        
        poam_id = {
            'id_number': id_number,
            'poam_id': f'POAM-{id_number}'
        }

    search_job.cancel()

    return poam_id


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
