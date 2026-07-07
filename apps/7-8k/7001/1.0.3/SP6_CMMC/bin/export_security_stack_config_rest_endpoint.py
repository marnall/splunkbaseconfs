from splunk.persistconn.application import PersistentServerConnectionApplication
from pathlib import Path
from os import environ
import sys
import base64
import json
import logging


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
HTML_TO_PDF_LIBS_DIR = Path(BIN_DIR / 'html_to_pdf_libs')
CONFIG_JSON = Path(APP_DIR / 'local' / 'security_stack_config.json')


sys.path.append(
    str(BIN_DIR)
)
from helpers.file_utils import (
    get_mimetype
)
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_export_security_stack_config_rest_endpoint'
)


class ExportSecurityStackConfig(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()


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

            if key == 'system':
                system = value


        config_json_data = load_config_json(system)

        config_json_b64 = None
        mimetype = None

        if config_json_data['config']:
            config_json_b64 = self.convert_to_base64(
                json.dumps(
                    config_json_data['config'],
                    indent=4,
                    default=str
                )
            )

            mimetype = get_mimetype(str(CONFIG_JSON.suffix.lower()))['mimetype']

        self.log_stop_message()

        return {
            'payload': {
                'mimetype': mimetype,
                'status': 'success' if not config_json_data['error'] else 'error',
                'config_json_b64': config_json_b64,
                'error': config_json_data['error']
            },
            'status': 200
        }


    def convert_to_base64(self, content):
        logger.info(f'message="Converting Security Stack Config JSON to base 64 encoded string for download."')

        try:
            string_bytes = content.encode('utf-8')
            base64_bytes = base64.b64encode(string_bytes)
            base64_string = base64_bytes.decode('utf-8')

        except Exception as e:
            logger.error(f'status="ERROR", message="An error occurred while converting Security Stack Config JSON to base 64 encoded string: {str(e)}"')
            return None

        else:
            logger.info(f'status="success", message="Successfully converted Security Stack Config JSON to base 64 encoded string."')
            return base64_string


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Export Security Stack Config REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Export Security Stack Config REST endpoint started at {timestamp}."')
        return


def load_config_json(system):
    return_data = {
        'config': None,
        'error': None
    }

    logger.info(f'message="Loading Security Stack Config JSON document from {str(CONFIG_JSON)}"')

    try:
        with open(CONFIG_JSON, 'r') as f:
            return_data['config'] = json.load(f)[system]

            logger.info(f'status="success", message="Successfully loaded Security Stack Config JSON document from {str(CONFIG_JSON)}"')

    except Exception as e:
        return_data['error'] = str(e)

        logger.error(f'status="ERROR", message="An error occurred while loading the Security Stack Config JSON document from {str(CONFIG_JSON)}", error="{str(e)}"')

    return return_data
