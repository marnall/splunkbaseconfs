from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from os.path import join as join_path
from pathlib import Path
import json
import sys
import logging


app_name = Path(__file__).absolute().parts[-3]
app_dir = join_path(
    environ['SPLUNK_HOME'],
    'etc',
    'apps',
    app_name
)

sys.path.append(
    join_path(
        app_dir,
        'bin'
    )
)


from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_prereq_system_update_rest_endpoint'
)


prereq_file_path = join_path(
    app_dir,
    'appserver',
    'static',
    'utils',
    'json',
    'prereqs-checks.json'
)


class PrereqSystemUpdate(PersistentServerConnectionApplication):
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

            if key == 'prereq_object':
                prereq_object = json.loads(value)

        
        is_error = False
        error_msg = None


        # Open Prereq JSON File
        logger.info(f'Saving updated prereq file: {prereq_file_path}')

        try:
            with open(str(prereq_file_path), 'w') as prereq_file:
                json.dump(
                    prereq_object, 
                    prereq_file,
                    indent=2,
                    sort_keys=False
                )

        except Exception as e:
            logger.error(f'status="ERROR", message="An error occurred while saving the prereq file to {prereq_file_path}: {str(e)}"')

            is_error = True
            error_msg = str(e)
            payload = {
                'error': is_error, 
                'message': error_msg, 
                'status': 'failure'
            }

            return {
                'payload': payload,
                'status': 500
            }


        logger.info(f'status="success", message="Successfully saved prereq file to {prereq_file_path}."')
        

        # Return Successful Response
        payload = {
            'error': is_error,
            'message': error_msg,
            'status': 200
        }

        self.log_stop_message()

        return {
            'payload': payload,
            'status': 200
        }


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Prereq Editor REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Prereq Editor REST endpoint started at {timestamp}."')
        return


    def done(self):
        pass
