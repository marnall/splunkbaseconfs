from splunk.persistconn.application import PersistentServerConnectionApplication
from pathlib import Path
from shutil import rmtree
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
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_delete_poam_rest_endpoint'
)


class DeletePoam(PersistentServerConnectionApplication):
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

            if key == 'poam_id':
                internal_id = value


        poam_kvstore = service.kvstore[POAM_KVSTORE_NAME]
        poam_record = get_poam_record_by_id(internal_id, poam_kvstore)
        poam_id = poam_record['poam_id']
        poam_system = poam_record['cui_system_splunk_id']
        attachments_path = Path(
            APP_DIR /
            'poam_attachments' /
            poam_system /
            poam_id
        )

        if attachments_path.is_dir():
            try:
                rmtree(str(attachments_path))

            except Exception as e:
                logger.error(f'status="ERROR", message="An error occurred while attempting to delete the POAM attachment directory {str(attachments_path)}", error="{str(e)}"')

        poam_kvstore.data.delete(
            json.dumps({
                '_key': internal_id
            })
        )


        self.log_stop_message()


        payload = {
            'status': 'success',
            'message': f'Successfully deleted POAM {internal_id}'
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
        logger.info(f'message="Delete POA&M REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Delete POA&M REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass


def get_poam_record_by_id(internal_id, poam_kvstore):
    kvstore_initialized = False
    poam_record = None

    query = json.dumps(
        {
            '_key': internal_id
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
        logger.error(f'status="ERROR", message="The poam with id \'{internal_id}\' was not found in the \'{POAM_KVSTORE_NAME}\' KV Store."')
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

