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
POAM_DIR = Path(
    APP_DIR /
    'poam_attachments'
)
POAM_KVSTORE_NAME = 'sp6_poams'


sys.path.append(
    str(
        Path(
            APP_DIR /
            'bin'
        )
    )
)

from helpers.file_utils import (
    write_base64_string_to_file
)
import splunklib.client as client
from helpers.logger import setup_logger
import pendulum


# Setup logger 
logger = setup_logger(
    logging.INFO,
    'sp6_poam_upload_attachment_rest_endpoint'
)



class AttachmentUpload(PersistentServerConnectionApplication):
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

            if key == 'file':
                base64_str = value

            elif key == 'attachments':
                attachments = json.loads(value)

            elif key == 'internal_id':
                internal_id = value

            elif key == 'poam_id':
                poam_id = value

            elif key == 'system':
                system = value


        dest_dir = Path(POAM_DIR / system / poam_id)

        Path(
            dest_dir
        ).mkdir(
            parents=True,
            exist_ok=True
        )

        attachment_path_list = []

        logger.info(attachments)

        for attachment in attachments:
            base64_str = attachment['file']
            file_name = attachment['file_name']

            file_save_path = str(
                Path(
                    dest_dir /
                    file_name
                )
            )

            attachment_path_list.append(file_save_path)

            save_status = write_base64_string_to_file(
                file_save_path,
                base64_str
            )

        poam_kvstore = service.kvstore[POAM_KVSTORE_NAME]
        poam_record = get_poam_record_by_id(internal_id, poam_kvstore)

        if not poam_record.get('attachments'):
            poam_record['attachments'] = attachment_path_list

        else:
            for attachment in attachment_path_list:
                if attachment not in poam_record['attachments']:
                    poam_record['attachments'].append(attachment)

        poam_kvstore.data.update(
            internal_id,
            json.dumps(poam_record)
        )

        self.log_stop_message()

        # Return the response
        return {
            'payload': {
                'status': None,
                'error': None,
                'message': 'success'
            },
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="POAM upload attachment REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="POAM upload attachment REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


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
