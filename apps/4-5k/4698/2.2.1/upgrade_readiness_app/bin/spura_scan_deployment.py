import os
import re
import sys
import json
import time
import shlex
import subprocess
import splunk.rest as sr
from itertools import groupby
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


class ScanDeploymentHandler(PersistentServerConnectionApplication):
    """
    This is a REST handler base-class that makes implementing a REST handler easier.

    This works by resolving a name based on the path in the HTTP request and calls it.
    This class will look for a function that includes the HTTP verb followed by the path.abs

    For example, if a GET request is made to the endpoint is executed with the path /scan_deployment,
    then this class will attempt to run a function named get_scan_deployment().
    Note that the root path of the REST handler is removed. If a POST request is made to the endpoint
    is executed with the path /scan_deployment, then this class will attempt to execute post_scan_deployment().
    """

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

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
            self.scan_key = None

            # Get the method
            method = args['method']

            # Get the path and the args
            if 'rest_path' in args:
                path = args['rest_path']
            else:
                return utils.render_error_json(MESSAGE_NO_PATH_PROVIDED, 403)

            # Get the request body
            if 'payload' in args:
                request_body = json.loads(args['payload'])
            else:
                return utils.render_error_json(MESSAGE_NO_REQUEST_BODY, 400)

            # Execute the function
            start_time = int(time.time()*1000)

            # Check for existing scan
            existing_status, existing_message = self.check_existing_scan()
            if existing_status:
                return utils.render_error_json(existing_message)
            logging.info(existing_message)

            # Remove previous entries
            entry_status, entry_message = self.remove_existing_entry()
            if not entry_status:
                return utils.render_error_json(entry_message)
            logging.info(entry_message)

            # Creating new scan report
            scan_report = dict()
            results = dict()
            scan_report['status'] = PROGRESS_INIT
            scan_report['results'] = results
            scan_report['message'] = MESSAGE_NO_SCAN_RESULTS
            scan_report['progress'] = 0

            proceed = self.first_progress(scan_report)
            if not proceed:
                logging.info(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))
                return utils.render_error_json(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))

            logging.info("Starting scan process")

            arg_vars = dict()
            arg_vars["session_key"] = self.session_key
            arg_vars["user"] = self.user
            arg_vars["host"] = self.host
            arg_vars["request_body"] = request_body

            DEVNULL_PATH = open(os.devnull, 'wb')
            if six.PY2:
                command = "\"{}\" cmd python \"{}\"".format(SPLUNK_PATH, PROCESS_PATH)
            elif six.PY3:
                command = "\"{}\" cmd python3 \"{}\"".format(SPLUNK_PATH, PROCESS_PATH)
            if os.name == "nt":
                scan_process = subprocess.Popen(shlex.split(command), stdin=subprocess.PIPE,
                                                stdout=DEVNULL_PATH, stderr=DEVNULL_PATH, shell=False,
                                                creationflags=DETACHED_PROCESS)
            else:
                scan_process = subprocess.Popen(shlex.split(command), stdin=subprocess.PIPE,
                                                stdout=DEVNULL_PATH, stderr=DEVNULL_PATH, shell=False)
            scan_process.stdin.write((json.dumps(arg_vars).encode('utf-8')))
            scan_process.stdin.close()
            DEVNULL_PATH.close()
            # Return main thread to acknowledge successful trigger
            return utils.render_msg_json(MESSAGE_SCAN_CALLED)

        except Exception as exception:
            logging.exception(MESSAGE_FAILED_HANDLE_REQUEST)
            return utils.render_error_json(str(exception))

    def check_existing_scan(self):
        """
        Check if any existing scan is going on for given user on the host.

        :return Status(true/false), Message
        """
        logging.info(MESSAGE_CHECK_EXISTING_SCAN)
        try:
            response, content = sr.simpleRequest('{}?output_mode=json'.format(kvstore_endpoint),
                                                 sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_SCAN_STATUS.format(self.user, self.host))
            return True, MESSAGE_EXCEPTION_SCAN_STATUS.format(self.user, self.host)
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_READING_SCAN_STATUS.format(self.user, self.host))
            return True, MESSAGE_ERROR_READING_SCAN_STATUS.format(self.user, self.host)
        else:
            for entry in json.loads(content):
                if (self.host == entry['host']) and (self.user == entry['user']):
                    if (entry['status'] != PROGRESS_COMPLETE) and (entry['status'] != PROGRESS_ERROR):
                        logging.info(MESSAGE_SCAN_IN_PROGRESS.format(self.user, self.host))
                        return True, MESSAGE_SCAN_IN_PROGRESS.format(self.user, self.host)
            return False, MESSAGE_NO_EXISTING_SCAN

    def get_keys_for_removal(self):
        """
        Get key for user and host.

        :return List of keys
        """

        logging.info(MESSAGE_RETRIEVING_REMOVAL_KEY)
        try:
            response, content = sr.simpleRequest('{}?output_mode=json'.format(kvstore_endpoint),
                                                 sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_WRITE_KVSTORE.format(self.user, self.host))
            return []
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))
            return []
        else:
            keys = list()
            for entry in json.loads(content):
                if self.host == entry['host'] and self.user == entry['user']:
                    if entry['cancelled'] and entry['returned']:
                        logging.info("Found key for cancelled entry: {}".format(str(entry['_key'])))
                        keys.append(entry['_key'])
                    elif not entry['cancelled'] and not entry['returned']:
                        if entry['status'] == PROGRESS_COMPLETE or entry['status'] == PROGRESS_ERROR:
                            logging.info(MESSAGE_FOUND_COMPLETED_KEY.format(str(entry['_key'])))
                            keys.append(entry['_key'])
            return keys

    def remove_existing_entry(self):
        """
        Remove existing entry from KV store.

        :return Status(True/False), Message
        """

        logging.info(MESSAGE_REMOVING_ENTRIES)
        keys = self.get_keys_for_removal()
        for key in keys:
            try:
                response, _ = sr.simpleRequest('{}/{}?output_mode=json'.format(kvstore_endpoint, key),
                                               sessionKey=self.session_key, method='DELETE')
            except Exception as e:
                logging.exception(MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host))
                return False, MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host)
            if response['status'] not in success_codes:
                logging.error(MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host))
                return False, MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host)
            logging.info(MESSAGE_ENTRY_REMOVED.format(str(key)))
        return True, MESSAGE_ALL_ENTRIES_REMOVED

    def first_progress(self, scan_report):
        """
        Write first progress in KV store.

        :param scan_report: current scan report

        :return Proceed(True/False) based on whether scan is cancelled or not
        """

        data = {
            'process_id': os.getpid(),
            'host': self.host,
            'user': self.user,
            'progress': 0,
            'status': PROGRESS_NEW,
            'message': "Running new scan",
            'cancelled': False,
            'returned': False
        }

        data.update({
            'progress': scan_report['progress'],
            'status': scan_report['status'],
            'message': scan_report['message']
        })

        try:
            response, _ = sr.simpleRequest('{}?output_mode=json'.format(kvstore_endpoint),
                                           sessionKey=self.session_key, jsonargs=json.dumps(data), method='POST',
                                           raiseAllErrors=True)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_WRITE_KVSTORE.format(self.user, self.host))
            return False
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))
            return False

        return True
