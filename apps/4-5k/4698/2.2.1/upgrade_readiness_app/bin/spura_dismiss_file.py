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


class DismissFileHandler(PersistentServerConnectionApplication):
    """
    This is a REST handler base-class that makes implementing a REST handler easier.

    This works by resolving a name based on the path in the HTTP request and calls it.
    This class will look for a function that includes the HTTP verb followed by the path.abs

    For example, if a GET request is made to the endpoint is executed with the path /dismiss_file,
    then this class will attempt to run a function named get_dismiss_file().
    Note that the root path of the REST handler is removed. If a POST request is made to the endpoint
    is executed with the path /dismiss_file, then this class will attempt to execute post_dismiss_file().
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

            # Get the request body
            if 'payload' in args:
                request_body = json.loads(args['payload'])
            else:
                return utils.render_error_json(MESSAGE_NO_REQUEST_BODY, 400)

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
                return function_to_call(request_body)

            else:
                logging.warn("A request could not be executed since the associated function is missing, name={}"
                             .format(function_name))
                return utils.render_error_json(MESSAGE_PATH_NOT_FOUND, 404)

        except Exception as exception:
            logging.exception(MESSAGE_FAILED_HANDLE_REQUEST)
            return utils.render_error_json(str(exception))

    def post_dismiss_file(self, query_params):
        """
        Write dismiss file entry in KV store for given parameters.

        :param query_params: Dict of parameters

        :return JSON response for dismiss file call
        """

        if 'app' not in query_params or not query_params['app']:
            logging.error(MESSAGE_DISMISS_APP_READ_ERROR)
            return utils.render_error_json(MESSAGE_DISMISS_APP_READ_ERROR, 404)
        if 'check' not in query_params or not query_params['check']:
            logging.error(MESSAGE_DISMISS_CHECK_READ_ERROR)
            return utils.render_error_json(MESSAGE_DISMISS_CHECK_READ_ERROR, 404)
        if 'file_path' not in query_params or not query_params['file_path']:
            logging.error(MESSAGE_DISMISS_FILEPATH_READ_ERROR)
            return utils.render_error_json(MESSAGE_DISMISS_FILEPATH_READ_ERROR, 404)

        status, message = self.write_entry(query_params)

        if not status:
            return utils.render_error_json(message)
        logging.info(message)

        latest_report, filename = self.get_latest_results()
        if not filename or not latest_report:
            return utils.render_error_json(MESSAGE_DISMISS_ERROR_FILE_READ)

        updated_report = self.remove_check_from_results(latest_report, query_params)

        proceed = self.write_file(updated_report, filename)
        if not proceed:
            return utils.render_error_json(MESSAGE_DISMISS_ERROR_FILE_WRITE)

        return utils.render_msg_json(message)

    def write_file(self, report, filepath):
        """
        Write updated report in files.

        :param report: JSON report after dismissing file_path from checks
        :param filepath: File path including filename

        :return True/False
        """
        try:
            with open(filepath, 'w') as file_handler:
                json.dump(report, file_handler)
            return True
        except Exception as e:
            logging.exception(str(e))
            return False

    def write_entry(self, entry):
        """
        Write entry in KV store for given parameters.

        :param entry: Dict of parameters

        :return status (True/False), message
        """

        entry.update({
            'host': self.host,
            'user': self.user
        })

        try:
            response, _ = sr.simpleRequest('{}?output_mode=json'.format(dismiss_coll_endpoint),
                                           sessionKey=self.session_key, jsonargs=json.dumps(entry), method='POST',
                                           raiseAllErrors=True)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_WRITING_DISMISS_ENTRY.format(self.user, self.host))
            return False, MESSAGE_EXCEPTION_WRITING_DISMISS_ENTRY.format(self.user, self.host)
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_WRITING_DISMISS_ENTRY.format(self.user, self.host))
            return False, MESSAGE_ERROR_WRITING_DISMISS_ENTRY.format(self.user, self.host)

        return True, MESSAGE_DISMISS_ENTRY_SUCCESS.format(entry['file_path'], entry['check'],
                                                          entry['app'], self.user, self.host)

    def get_latest_results(self):
        """
        Fetch latest results for the user

        :return latest results for the user based on timestamp, filename for results
        """

        results = dict()
        filepath = ""
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
                filepath = report_file
                break

        return results, filepath

    def remove_check_from_results(self, report, entry):
        """
        Remove file_path from checks of given app.

        :param report: Existing report
        :param entry: Dict containing app, check and file_path

        :return Updated report with check removed
        """

        app = entry['app']
        check = entry['check']
        file_path = entry['file_path']

        for _app in report['apps']:
            if _app['name'] == app:
                old_app_status = _app['summary']['Status']
                for _check in _app['checks']:
                    if _check['name'] == check:
                        _check['messages'] = list([i for i in _check['messages'] if i['message_filename'] != file_path])
                        if not _check['messages']:
                            old_result = _check['result']
                            _check['result'] = CHECK_CONST_PASSED
                            _check['required_action'] = CHECK_CONST_PASSED_MSG
                            _app['summary'] = self.update_check_count(_app['summary'], old_result)
                            report['summary'] = self.update_report_summary(report['summary'],
                                                                           old_app_status,
                                                                           _app['summary']['Status'])
                        break

        return report

    def update_report_summary(self, report_summary, old_app_status, new_app_status):
        """
        Update report summary if app has all the checks passed

        :param report_summary: Existing report summary
        :param old_app_status: Previous app status
        :param new_app_status: Latest app status

        :return Updated report_summary
        """

        passed = report_summary['passed']
        blocker = report_summary['blocker']
        warning = report_summary['warning']
        unknown = report_summary['unknown']

        if new_app_status == CHECK_CONST_PASSED:
            passed += 1
            if old_app_status == CHECK_CONST_BLOCKER:
                blocker -= 1
            elif old_app_status == CHECK_CONST_WARNING:
                warning -= 1
        elif new_app_status == CHECK_CONST_WARNING:
            warning += 1
            if old_app_status == CHECK_CONST_BLOCKER:
                blocker -= 1
        elif new_app_status == CHECK_CONST_BLOCKER:
            blocker += 1
            if old_app_status == CHECK_CONST_WARNING:
                warning -= 1
            elif old_app_status == CHECK_CONST_BLOCKER:
                blocker -= 1

        report_summary['passed'] = passed
        report_summary['blocker'] = blocker
        report_summary['warning'] = warning
        report_summary['unknown'] = unknown

        return report_summary

    def update_check_count(self, summary, result):
        """
        Update app summary based on changed result for check

        :param summary: Existing check summary
        :param result: Previous result of check

        :return Updated check summary for app
        """

        passed = summary['Passed']
        blocker = summary['Blocker']
        warning = summary['Warning']
        skipped = summary['Skipped']
        status = summary['Status']

        if result == CHECK_CONST_BLOCKER:
            blocker -= 1
        elif result == CHECK_CONST_WARNING:
            warning -= 1
        elif result == CHECK_CONST_SKIPPED:
            skipped -= 1

        passed += 1

        if skipped > 0:
            status = CHECK_CONST_UNKNOWN
        elif blocker > 0:
            status = CHECK_CONST_BLOCKER
        elif blocker == 0 and warning > 0:
            status = CHECK_CONST_WARNING
        else:
            status = CHECK_CONST_PASSED

        summary.update({
            'Passed': passed,
            'Blocker': blocker,
            'Warning': warning,
            'Skipped': skipped,
            'Status': status
        })

        return summary
