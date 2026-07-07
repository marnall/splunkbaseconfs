import os
import re
import sys
import json
import time
import splunk.rest as sr
from splunk.persistconn.application import PersistentServerConnectionApplication

if sys.version_info.major == 2:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py2'))
elif sys.version_info.major == 3:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py3'))

import logger_manager
from consts import *
import utils
import six
from builtins import str

logging = logger_manager.setup_logging('upgrade_readiness')

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class ReadProgressHandler(PersistentServerConnectionApplication):
    """
    This is a REST handler base-class that makes implementing a REST handler easier.

    This works by resolving a name based on the path in the HTTP request and calls it.
    This class will look for a function that includes the HTTP verb followed by the path.abs

    For example, if a GET request is made to the endpoint is executed with the path /read_progress,
    then this class will attempt to run a function named get_read_progress().
    Note that the root path of the REST handler is removed. If a POST request is made to the endpoint
    is executed with the path /read_progress, then this class will attempt to execute post_read_progress().
    """

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    @classmethod
    def get_function_signature(cls, method, path):
        """
        Get the function that should be called based on path and request method.

        :param cls: class
        :param method: type of call (get/post)
        :param path: the rest endpoint for which method is to be called

        :return name of the function to be called
        """

        if len(path) > 0:
            components = path.split("spura")
            path = components[1]
            return method + re.sub(r'[^a-zA-Z0-9_]', '_', path).lower()
        else:
            return method

    def handle(self, in_string):
        """
        Handler function to call when REST endpoint is hit and process the call

        :param in_string: string of arguments

        :return Result of REST call
        """
        try:

            logging.info("Handling a request")

            # Parse the arguments
            args = utils.parse_in_string(in_string)

            # Get the user information
            self.session_key = args['session']['authtoken']
            self.user = args['session']['user']
            self.host = args['server']['hostname']

            # Get the method
            method = args['method']

            # Get the path and the args
            if 'rest_path' in args:
                path = args['rest_path']
            else:
                return utils.render_error_json(MESSAGE_NO_PATH_PROVIDED, 403)

            if method.lower() == 'post':
                query = utils.get_forms_args_as_dict(args["form"])
            else:
                query = args['query_parameters']

            # Get the function signature
            function_name = self.get_function_signature(method, path)

            try:
                function_to_call = getattr(self, function_name)
            except AttributeError:
                function_to_call = None

            # Try to run the function
            if function_to_call is not None:
                logging.info("Executing function, name={}".format(function_name))

                # Execute the function
                start_time = int(time.time()*1000)
                return function_to_call()

            else:
                logging.warn("A request could not be executed since the associated function is missing, name={}"
                             .format(function_name))
                return utils.render_error_json(MESSAGE_PATH_NOT_FOUND, 404)

        except Exception as exception:
            logging.exception(MESSAGE_FAILED_HANDLE_REQUEST)
            return utils.render_error_json(str(exception))

    def check_session_is_alive(self, scan_key):
        """
        Function to check if session has timed-out

        :param scan_key: Scan key to fetch entry from KV store

        :return (True/False) Session is alive
        """

        # Check if local directory exists
        if not os.path.isdir(LOCAL_DIR):
            os.makedirs(LOCAL_DIR)

        if not os.path.isdir(SESSION_PATH):
            os.makedirs(SESSION_PATH)

        file_path = os.path.join(SESSION_PATH, scan_key)
        if os.path.exists(file_path):
            logging.info(MESSAGE_SESSION_FILE_EXISTS.format(str(file_path)))
            try:
                os.remove(file_path)
            except Exception as e:
                logging.exception(MESSAGE_ERROR_REMOVING_SESSION_FILE.format(str(e)))
            return False
        return True

    def get_read_progress(self):
        """
        Read progress from KV store.

        :return response for read progress REST call
        """

        scan_report = dict()
        scan_report['status'] = PROGRESS_NEW
        scan_report['results'] = {}
        scan_report['message'] = MESSAGE_NO_SCAN_RESULTS
        scan_report['progress'] = 0

        try:
            response, content = sr.simpleRequest('{}?output_mode=json'.format(kvstore_endpoint),
                                                 sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_READ_KVSTORE.format(self.user, self.host))
            return utils.render_error_json(MESSAGE_EXCEPTION_READ_KVSTORE.format(self.user, self.host))
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_READING_PROGRESS.format(self.user, self.host))
            return utils.render_error_json(MESSAGE_ERROR_READING_PROGRESS.format(self.user, self.host))
        else:
            for entry in json.loads(content):
                if self.host == entry['host'] and self.user == entry['user']:
                    if not entry['cancelled'] and not entry['returned']:
                        scan_key = entry['_key']
                        session_alive = self.check_session_is_alive(scan_key)
                        if session_alive:
                            scan_report.update({
                                'status': entry['status'],
                                'message': entry['message'],
                                'progress': entry['progress']
                            })

                            if scan_report['status'] == PROGRESS_COMPLETE:
                                results = self.get_latest_results()
                                scan_report.update({
                                    'results': results
                                })

                            return utils.render_json(scan_report)
                        else:
                            key = entry['_key']
                            entry['cancelled'] = True
                            entry['progress'] = 100
                            entry['returned'] = True
                            entry['status'] = PROGRESS_COMPLETE
                            try:
                                response, _ = sr.simpleRequest('{}/{}?output_mode=json'.format(kvstore_endpoint, key),
                                                               sessionKey=self.session_key, jsonargs=json.dumps(entry),
                                                               method='POST', raiseAllErrors=True)
                            except Exception as e:
                                logging.exception(MESSAGE_EXCEPTION_DELETE_KVSTORE.format(self.user, self.host))
                                return utils.render_error_json(MESSAGE_EXCEPTION_DELETE_KVSTORE.format(self.user,
                                                                                                       self.host))

                            if response['status'] not in success_codes:
                                logging.error(MESSAGE_ERROR_CANCEL_SCAN.format(self.user, self.host))
                                return utils.render_error_json(MESSAGE_ERROR_CANCEL_SCAN.format(self.user,
                                                                                                self.host))

                            results = self.get_latest_results()
                            scan_report.update({
                                'status': PROGRESS_ERROR,
                                'progress': 100,
                                'results': results,
                                'message': MESSAGE_UNAUTHORIZED_SCAN_TERMINATION})

                            return utils.render_json(scan_report)
            else:
                results = self.get_latest_results()
                scan_report.update({
                    'status': PROGRESS_COMPLETE,
                    'progress': 100,
                    'results': results
                })
                return utils.render_json(scan_report)

        return utils.render_error_json(MESSAGE_NO_ENTRY_FOUND, 404)

    def get_latest_results(self):
        """
        Fetch latest results for given user

        :return latest results for given user based on timestamp
        """

        # Check if local directory exists
        if not os.path.isdir(LOCAL_DIR):
            os.makedirs(LOCAL_DIR)

        results = dict()
        if not os.path.isdir(REPORT_PATH):
            os.makedirs(REPORT_PATH)
        list_reports = os.listdir(REPORT_PATH)

        user_reports = list()
        for report in list_reports:
            if self.user in report:
                user_reports.append(report)

        latest_timestamp = 0
        for report in user_reports:
            timestamp = (report[:-5])[-10:]
            if int(timestamp) > latest_timestamp:
                latest_timestamp = int(timestamp)

        for report in user_reports:
            if str(latest_timestamp) in report:
                report_file = os.path.join(REPORT_PATH, report)
                with open(report_file, 'r') as file_handler:
                    results = json.load(file_handler)
                break

        return results
