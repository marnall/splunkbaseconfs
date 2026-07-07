from splunk.persistconn.application import PersistentServerConnectionApplication
from os import environ
from pathlib import Path
from time import sleep
import json
import logging
import sys


SPLUNK_DIR = Path(environ['SPLUNK_HOME']).absolute()
APP_NAME = Path(__file__).absolute().parts[-3]
APP_DIR = Path(
    SPLUNK_DIR /
    'etc' /
    'apps' /
    APP_NAME
)
BIN_DIR = Path(APP_DIR / 'bin')


sys.path.append(
    str(BIN_DIR)
)
import splunklib.client as client
from helpers.logger import setup_logger
import pendulum


# Setup logger
logger = setup_logger(
    logging.INFO,
    'sp6_execute_saved_search_rest_endpoint'
)


class ExecuteSavedSearch(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        self.log_start_message()

        data = json.loads(
            in_string.decode('utf-8')
        )

        for i in data['form']:
            key = i[0]
            value = i[1]

            if key == 'name':
                saved_search_name = value

        service = get_service(
            data['session']['authtoken']
        )

        if not service:
            return {
                'payload': {
                    'status': 'failure',
                    'message': 'An error occurred creating the Splunk service. See the execution log for details:\nindex="_internal" source="*/sp6_execute_saved_search_rest_endpoint.log"'
                },
                'status': 200
            }


        saved_search = service.saved_searches[saved_search_name]

        logger.info(f'message="Executing saved search \'{saved_search_name}\'"')

        job = saved_search.dispatch(
            trigger_actions=True,
            force_dispatch=True,
            now=int(pendulum.now().format('X'))
        )

        job_done = False
        result_count = None

        while not job_done:
            sleep(2)
            job.refresh()

            if job['isDone'] == '1':
                result_count = job['resultCount']
                scan_count = job['scanCount']
                event_count = job['eventCount']
                logger.info(f'message="Saved search \'{saved_search_name}\' execution complete.", scan_count="{scan_count}", event_count="{event_count}", result_count="{result_count}"')
                job_done = True

            
        self.log_stop_message()


        return {
            'payload': {
                'status': 'success',
                'message': f'{saved_search_name.replace("ASCERA Status Check - ", "")} completed with {result_count} results.'
            },
            'status': 200
        }


    def log_stop_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Execute Saved Search REST endpoint execution completed at {timestamp}."')
        return


    def log_start_message(self):
        timestamp = pendulum.now().to_datetime_string()
        logger.info(f'message="Execute Saved Search REST endpoint started at {timestamp}."')
        return


    def handleStream(self, handle, in_string):
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")


    def done(self):
        pass


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
