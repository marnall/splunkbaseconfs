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


sys.path.append(
    str(BIN_DIR)
)
from helpers.logger import setup_logger
import splunklib.client as client
import splunklib.results as search_results
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_get_poam_rest_endpoint'
)


class GetPoam(PersistentServerConnectionApplication):
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

            if key == 'query_method':
                query_method = value

            elif key == 'tags':
                tags = json.loads(value)

            elif key == 'control':
                control = value

            elif key == 'poam_id':
                poam_id = value


        poam_kvstore = service.kvstore[POAM_KVSTORE_NAME]


        if query_method == 'id':
            poam_record = get_poam_record_by_id(poam_id, poam_kvstore)

            payload = {
                'status': 'success',
                'message': 'A Message for You!',
                'poams': poam_record
            }

            self.log_stop_message()

            return {
                'payload': payload,
                'status': 200
            }
        

        elif query_method == 'tags':
            poam_records = get_poam_records_by_tags(tags, poam_kvstore)

            payload = {
                'status': 'success',
                'message': 'A Message for You!',
                'poams': poam_records
            }

            self.log_stop_message()

            return {
                'payload': payload,
                'status': 200
            }
        

        elif query_method == 'control':
            poam_records = get_poam_records_by_control(control, service)

            payload = {
                'status': 'success',
                'message': 'A Message for You!',
                'poams': poam_records
            }

            self.log_stop_message()

            return {
                'payload': payload,
                'status': 200
            }

        
        return {
            'payload': {},
            'status': 200
        }

    


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get POA&M REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Get POA&M REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass


def get_poam_records_by_control(control, service):
    poam_records = []
    regex_formatted_control = control.replace(".", "\.")
    query = f'|inputlookup {POAM_KVSTORE_NAME} | regex tags="{regex_formatted_control}.*"'

    search_job = service.jobs.create(query)

    while not search_job.is_done():
        sleep(.2)

    search_result = search_results.JSONResultsReader(
        search_job.results(output_mode='json')
    )

    for result in search_result:
        poam_records.append(result)

    search_job.cancel()

    return poam_records


def get_poam_records_by_tags(tags, poam_kvstore):
    kvstore_initialized = False
    poam_records = []

    for tag in tags:
        query = json.dumps(
            {
                'tags': tag
            },
            indent=1
        )

        while not kvstore_initialized:
            try:
                poam_records_results = poam_kvstore.data.query(query=query)

            except Exception as e:
                if 'Service Unavailable -- KV Store is initializing' in str(e):
                    logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                    sleep(3)

                else:
                    logger.error(f'status="ERROR", message="An error occurred while querying the POA&M KV Store", exception="{str(e)}"')
                    return None

            else:
                kvstore_initialized = True
                for record in poam_records_results:
                    poam_records.append(record)

    if not poam_records:
        logger.error(f'status="ERROR", message="The poam with tags \'{tags}\' was not found in the \'{POAM_KVSTORE_NAME}\' KV Store."')
        return None

    return poam_records


def get_poam_record_by_id(poam_id, poam_kvstore):
    kvstore_initialized = False
    poam_record = None

    query = json.dumps(
        {
            '_key': poam_id
        },
        indent=1
    )

    while not kvstore_initialized:
        try:
            poam_record = poam_kvstore.data.query(query=query)[0]

        except Exception as e:
            if 'Service Unavailable -- KV Store is initializing' in str(e):
                logger.info(f'message="KV Store is initializing, waiting 3 seconds..."')
                sleep(3)

            else:
                logger.error(f'status="ERROR", message="An error occurred while querying the POA&M KV Store", exception="{str(e)}"')
                return None

        else:
            kvstore_initialized = True

    if not poam_record:
        logger.error(f'status="ERROR", message="The poam with id \'{poam_id}\' was not found in the \'{POAM_KVSTORE_NAME}\' KV Store."')
        return None

    return poam_record


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
