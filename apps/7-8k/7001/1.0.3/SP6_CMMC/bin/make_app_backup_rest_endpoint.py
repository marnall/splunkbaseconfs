from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
from zipfile import ZipFile
import sys
import logging
import os


APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(environ['SPLUNK_HOME']).absolute() / 'etc' / 'apps' / APP_NAME
BIN_DIR = Path(APP_DIR / 'bin')
LOCAL_DIR = Path(APP_DIR / 'local')
TEMP_BACKUP_DIR = Path(LOCAL_DIR / 'app_backup')


sys.path.append(
    str(BIN_DIR)
)

from helpers.logger import setup_logger
import pendulum

from helpers.file_utils import (
    read_file_as_base64_string
)


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_make_app_backup_rest_endpoint'
)


class MakeAppBackup(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        TEMP_BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        backup_base_name = f'{APP_NAME}_backup_{int(pendulum.now().format("X"))}'
        backup_file_name = f'{backup_base_name}.zip'

        outfile_path = Path(
            TEMP_BACKUP_DIR /
            backup_file_name
        )

        logger.info(f'message="Creating app backup {backup_file_name}"')

        with ZipFile(outfile_path, 'w') as zip_archive:
            for dirname, subdirs, files in os.walk(str(APP_DIR)):
                if 'app_backup' in subdirs:
                    subdirs.remove('app_backup')

                if '.git' in subdirs:
                    subdirs.remove('.git')

                zip_archive.write(dirname)

                for filename in files:
                    zip_archive.write(os.path.join(dirname, filename))

        logger.info(f'message="Retrieving app backup {backup_file_name} as base 64 string"')
        zip_b64_data = read_file_as_base64_string(str(outfile_path))

        logger.info(f'message="Deleting app backup file {backup_file_name} from local Splunk sever."')
        Path(outfile_path).unlink()

        self.log_stop_message()

        return {
            'payload': {
                'zip': zip_b64_data,
                'name': backup_file_name,
                'error': None,
                'message': '',
                'status': 200
            },
            'status': 200
        }


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Make App Backup REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Make App Backup REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass
