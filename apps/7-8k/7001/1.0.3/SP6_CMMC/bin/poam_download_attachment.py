from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
import json
import sys
import logging


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
    read_file_as_base64_string,
    get_mimetype,
    convert_binary_to_base64_string
)
import splunklib.client as client
from helpers.logger import setup_logger
import pendulum


# Setup logger 
logger = setup_logger(
    logging.INFO,
    'sp6_poam_download_attachment_rest_endpoint'
)



class AttachmentDownload(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        # Load data submitted by browser (in bytes)
        data = json.loads(
            in_string.decode('utf-8')
        )


        # Assignments from submitted data
        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'file_path':
                file_path = value


        dir_path = Path(file_path).parent

        dir_path.mkdir(
            parents=True,
            exist_ok=True
        )

        error = None
        error_message = 'An error occurred while downloading the file or accessing the file\'s mimetype.'

        try:
            data = read_file_as_base64_string(str(file_path))
            mime_type = get_mimetype(Path(file_path.split('/')[-1]).suffix.lower())['mimetype']

        except Exception as e:
            error = str(e)
            data = None
            mime_type = None
            logger.error(f'status="ERROR", message="An error occurred while downloading the file or accessing the file\'s mimetype: {error}"')

        else:
            logger.info(f'status="success", message="Successfully retrieved requested file as base 64 encoded string for download."')
            logger.info(f'status="success", message="Successfully retrieved downloaded file mime type: {mime_type}."')

        self.log_stop_message()

        return {
            'payload': {
                'file': data,
                'error': error,
                'mime_type': mime_type,
                'message': 'success' if not error else error_message,
                'status': 500 if error else 200
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
