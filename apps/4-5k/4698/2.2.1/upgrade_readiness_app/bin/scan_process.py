from __future__ import division
import os
import re
import sys
import copy
import json
import time
import splunk.rest as sr
from itertools import groupby
from threading import Thread, ThreadError

from telemetry import Telemetry

if sys.version_info.major == 2:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py2'))
elif sys.version_info.major == 3:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'libs_py3'))

import logger_manager
from consts import *
import utils
import six
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div

import splunk_appinspect
import splunk_py2to3.lib2to3Runner as lib2to3Runner

logging = logger_manager.setup_logging('upgrade_readiness')

class ScanProcess(object):
    """
    This is a process class which does the execution of scan and process the response.
    """

    def __init__(self, scan_args):

        self.session_key = scan_args['session_key']
        self.user = scan_args['user']
        self.host = scan_args['host']
        self.request_body = scan_args["request_body"]

        self.scan_key = None
        self.start_time = int(time.time())
        self.telemetry_handler = Telemetry(self.session_key, self.request_body)

    def py_2to3_check(self, app_name, app_path=None, scan_report=None, message=None):
        """
        Python files check.
        Walks through all python files of the app and returns the report for the script
        if it is python 3 compatible or not.

        :param app_name: Name of the app
        :param app_path: Path of the app (For Mako Template check)
        :param scan_report: Current scan report
        :param message: Scan message

        :return Dict containing python check results
        """

        def add_warning_message(warn_lines):
            """
            Adds a warning message to the result

            :param warn_lines: Warning lines for python file
            """

            report["messages"].append({
                "line": None,
                "message_filename": file_abs_path,
                "code": warn_lines,
                "result": "warning",
                "message_line": None,
                'filename': file_abs_path,
                'message': "{}\nFile: {}".format(warn_lines, file_abs_path),
            })

        def parseFuturize(lines):
            """
            Parse the futurize library response

            :param lines: Lines to be checked for python issues
            """

            report_lines = []
            for line in lines:
                if not line.startswith("RefactoringTool:"):
                    if not line.startswith("---") and not line.startswith("+++"):
                        report_lines.append(line)

            report_lines = "\n".join(report_lines)
            # Generate Report
            add_warning_message(report_lines)

        report = {
            'description': CHECK_CONST_DESCRIPTION,
            'name': CHECK_CONST_NAME,
            'result': AI_RESULT_WARNING,
            'messages': []
        }
        if app_path is None:
            dir_path = os.path.join(OTHER_APPS_DIR, app_name)
        else:
            dir_path = app_path
        for dirs, subdirs, files in os.walk(dir_path):
            cancelled, _ = self.is_cancelled(self.scan_key)
            if cancelled or self.complete_flag:
                logging.debug("stopping the py_2to3_check")
                self.cancel_flag = True
                return report
            logging.info("Scanning directory: {}".format(dirs))
            for file_obj in files:
                if self.cancel_flag:
                    return report
                if file_obj[-3:] == ".py":
                    file_abs_path = os.path.join(dirs, file_obj)
                    if app_path is None:
                        file_original_path = file_abs_path.split(app_name, 1)
                        msg_file = "...{}".format(file_original_path[-1])
                        scan_report.update({
                            'message': "{}. Scanning file: {}".format(message, msg_file)
                        })

                        proceed = self.write_progress(scan_report)
                        if not proceed:
                            logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                            self.cancel_flag = True
                            return report

                    try:
                        parseFuturize(lib2to3Runner.runFuturize(file_abs_path))
                    except Exception as e:
                        logging.error(str(e))
                        add_warning_message("failed to parse the file")

        return report

    def process_mako(self, check_list):
        """
        Process Mako templates found and search for issues found in related python code

        :param app: List of checks

        :return Updated list of checks
        """

        mako_msg = None

        def create_temp_dir():
            """
            Create a temp directory for Mako files
            """

            # Check if local directory exists
            if not os.path.isdir(LOCAL_DIR):
                os.makedirs(LOCAL_DIR)

            if not os.path.isdir(MAKO_PATH):
                os.makedirs(MAKO_PATH)

        def create_mako_file(message, line, file_path):
            """
            Create a mako python file from the code found in html files

            :param message: Message for Mako file check
            :param line: Line number
            :param file_path: Actual path of html file
            """

            content = re.split(" Python code: \"|\" File: | Line Number: ", message)
            mako_msg = content[0]
            py_file = file_path.split(separator, 1)[1]
            py_file = py_file.replace(separator, "$").replace(".html", ".py")
            py_file_path = os.path.join(MAKO_PATH, py_file)

            for entry in file_path_list:
                if entry.get('file', None) == py_file_path:
                    entry['content'].update({
                        line: content[1]
                    })
                    break
            else:
                code_dict = dict()
                code_dict['file'] = py_file_path
                code_dict['content'] = {line: content[1]}
                file_path_list.append(code_dict)

        def code_file_writer(filename, line_map, first_line_number=1):
            """
            function to write specific lines to a file

            :param filename: absolute path of the file
            :param line_map: Key value pair of line number and line
            """

            current_line = first_line_number
            file_content = ""
            for line_no, str_line in sorted(list(line_map.items()), key=lambda kv: kv[0]):
                # Assert line_no
                line_no = int(line_no)
                if not (line_no > 0 and (current_line == first_line_number or current_line < line_no)):
                    logging.error(MESSAGE_MAKO_FILE_LINE_NO)

                # Prepare the string
                new_line_count = line_no - current_line
                logging.debug("new_line_count = {}".format(new_line_count))
                line_to_add = "\n" * new_line_count
                line_to_add += str_line.strip()
                current_line = line_no + str_line.strip().count("\n")

                # Add to content
                file_content += line_to_add

            with open(filename, "w") as f:
                f.write(file_content)

        def format_mako(mako_list, python_list):
            """
            Formatting mako content

            :param mako_list: List of mako templates
            :param python_list: List of python files

            :return Filtered list of files
            """

            if not python_list:
                return python_list

            filtered_list = []
            mako_list = sorted(mako_list, key=lambda i: i['message_filename'])
            for _, grouped_list in groupby(mako_list, lambda i: i['message_filename']):
                filtered_list.append(list(grouped_list)[0])

            for item in python_list:
                file_path = item['message_filename']
                file_path = "...{}{}".format(separator, file_path.rsplit(separator, 1)[1])
                file_path = file_path.replace("$", separator).replace(".py", ".html")
                item['message_filename'] = file_path

            for entry in filtered_list:
                for item in python_list:
                    if entry['message_filename'] == item['message_filename']:
                        entry['code'] = item['code']
                        entry['message'] = mako_msg
                        break
                else:
                    entry['code'] = []

            filtered_list = list([i for i in filtered_list if len(i['code']) > 0])
            return filtered_list

        if os.name == "nt":
            separator = '\\'
        else:
            separator = '/'
        file_path_list = list()
        for check in check_list:
            if check['name'] == "Python in custom Mako templates":
                create_temp_dir()
                if not check['messages']:
                    break
                try:
                    for entry in check['messages']:
                        create_mako_file(entry['message'], entry['message_line'], entry['message_filename'])
                except Exception as e:
                    logging.exception(MESSAGE_EXCEPTION_MAKO_FILE_CREATION)
                    check['messages'] = []
                    check['result'] = CHECK_CONST_SKIPPED
                    check['required_action'] = CHECK_CONST_SKIPPED_MSG
                    return check_list
                try:
                    for entry in file_path_list:
                        code_file_writer(entry['file'], entry['content'])
                except Exception as e:
                    logging.exception(MESSAGE_EXCEPTION_MAKO_FILE_WRITE)
                    check['messages'] = []
                    check['result'] = CHECK_CONST_SKIPPED
                    check['required_action'] = CHECK_CONST_SKIPPED_MSG
                    return check_list

                # Create python script report by running fixers over it
                py_report = self.py_2to3_check(app_name=SELF_DIR_NAME, app_path=MAKO_PATH)
                app_checks = [py_report]
                app_checks = self.fixer_results(app_checks)
                py_report = app_checks[0]
                check['messages'] = format_mako(check['messages'], py_report['messages'])
                if not check['messages']:
                    check['result'] = CHECK_CONST_PASSED
                    check['required_action'] = CHECK_CONST_PASSED_MSG
                break

        try:
            if os.path.exists(MAKO_PATH):
                temp_files = os.listdir(MAKO_PATH)
                for entry in temp_files:
                    os.remove(os.path.join(MAKO_PATH, entry))
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_MAKO_FILE_DELETE)
            for check in check_list:
                if check['name'] == "Python in custom Mako templates":
                    check['messages'] = []
                    check['result'] = CHECK_CONST_SKIPPED
                    check['required_action'] = CHECK_CONST_SKIPPED_MSG

        return check_list

    def cancel_monitor(self):
        """
        Cancellation thread which monitors for cancel flag for given scan
        """
        for _ in range(10000):
            logging.debug("calling cancel_monitor")
            cancelled, _ = self.is_cancelled(self.scan_key)
            if cancelled or self.complete_flag:
                logging.debug("stopping the py_2to3_check")
                self.cancel_flag = True
                break
            time.sleep(10)

    def post_scan_deployment(self):
        """
        Runs the scan deployment to start scan for all the apps for given user.

        :return Scan results
        """

        # Creating new scan report
        scan_report = dict()
        results = dict()
        scan_report['status'] = PROGRESS_INIT
        scan_report['results'] = results
        scan_report['message'] = MESSAGE_NO_SCAN_RESULTS
        scan_report['progress'] = 0

        proceed = self.write_progress(scan_report)
        if not proceed:
            logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
            return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

        # Initialize telemetry data
        self.telemetry_handler.init_telemetry()

        self.cancel_flag = False
        self.complete_flag = False
        cancel_monitor = Thread(target=self.cancel_monitor)
        cancel_monitor.start()

        try:
            results = scan_report['results']

            if 'apps' not in self.request_body or not self.request_body['apps']:
                logging.error(MESSAGE_NO_APPS_FOUND.format(self.user))
                scan_report.update({
                    'status': PROGRESS_ERROR,
                    'message': MESSAGE_NO_APPS_FOUND.format(self.user)
                })

                proceed = self.write_progress(scan_report)
                if not proceed:
                    logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                    return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                return utils.render_error_json(MESSAGE_NO_APPS_FOUND.format(self.user), 404)

            apps = self.request_body['apps']

            app_type_list = list()
            for app in apps:
                app_type_list.append(((app['name'], app['label']), (app['type'], app['link'])))
            list_size = len(app_type_list)
            logging.info(MESSAGE_TOTAL_APPS_FOUND.format(str(list_size), self.user))
            scan_report.update({
                'status': PROGRESS_INPROGRESS,
                'message': MESSAGE_TOTAL_APPS_FOUND.format(str(list_size), self.user)
            })

            proceed = self.write_progress(scan_report)
            if not proceed:
                logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

            if self.telemetry_handler.telemetry_data:
                self.telemetry_handler.telemetry_data.update({
                    'apps': list()
                })

            # list of apps for scan results
            results['apps'] = list()
            passed_apps = 0
            blocker_apps = 0
            warning_apps = 0
            unknown_apps = 0
            splunk_base_app_count = 0
            splunk_support_app_count = 0
            private_app_count = 0

            for index, app in enumerate(app_type_list):
                current_scan_message = MESSAGE_SCANNING_APP.format(str(index), str(list_size), app[0][1])
                logging.info(current_scan_message)
                if six.PY2:
                    current_progress = int(((index)*100)/list_size)
                elif six.PY3:
                    current_progress = int(((index)*100)/list_size)
                scan_report.update({
                    'status': PROGRESS_INPROGRESS,
                    'progress': current_progress,
                    'message': current_scan_message
                })

                proceed = self.write_progress(scan_report)
                if not proceed:
                    logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                    return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

                if app[1][0] == CONST_SPLUNKBASE_QUAKE or app[1][0] == CONST_SPLUNKBASE_DUAL:
                    # Get static report and status PASSED for this app
                    updated_app_report, app_result = self.quake_response(app[0], app[1])

                    if self.telemetry_handler.telemetry_data:
                        self.telemetry_handler.update_telemetry_data(updated_app_report, app_result, app[0], app[1], default=True)
                else:
                    logging.info("start: app_inspect")
                    # Get app report for the given app
                    app_report = self.invoke_app_inspect(app[0][0])
                    logging.info("stop : app_inspect")

                    proceed = self.write_progress(scan_report)
                    if not proceed:
                        logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                        return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

                    logging.debug("start: py2to3_check")
                    # Check for python 3 compatible code using lib2to3
                    py_2to3_report = self.py_2to3_check(app_name=app[0][0], scan_report=scan_report,
                                                        message=current_scan_message)
                    logging.debug("stop : py2to3_check")

                    proceed = self.write_progress(scan_report)
                    if not proceed:
                        logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                        return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

                    # Get formatted report and status of app
                    updated_app_report, app_result = self.parse_response(app[0], app[1], app_report, py_2to3_report)

                    if self.telemetry_handler.telemetry_data:
                        self.telemetry_handler.update_telemetry_data(updated_app_report, app_result, app[0], app[1], default=False)

                # Add app report to results
                results['apps'].append(updated_app_report)

                if app_result == CHECK_CONST_PASSED:
                    passed_apps += 1
                elif app_result == CHECK_CONST_BLOCKER:
                    blocker_apps += 1
                elif app_result == CHECK_CONST_WARNING:
                    warning_apps += 1
                elif app_result == CHECK_CONST_UNKNOWN:
                    unknown_apps += 1

                if app[1][0] == CONST_PRIVATE:
                    private_app_count += 1
                else:
                    splunk_base_app_count += 1

            scan_completion_time = int(time.time())
            results['summary'] = {
                "splunkbase": splunk_base_app_count,
                "splunk_supported": splunk_support_app_count,
                "private": private_app_count,
                "passed": passed_apps,
                "blocker": blocker_apps,
                "warning": warning_apps,
                "unknown": unknown_apps,
                "scan_completion_time": scan_completion_time
            }

            logging.info(MESSAGE_SCAN_SUCCESS.format(self.user))
            results['scan_id'] = "{}_{}".format(self.user, str(scan_completion_time))

            scan_report.update({
                'status': PROGRESS_COMPLETE,
                'results': results,
                'progress': 100,
                'message': MESSAGE_SCAN_SUCCESS.format(self.user)
            })

            proceed = self.write_progress(scan_report)
            if not proceed:
                logging.info(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))
                return utils.render_error_json(MESSAGE_SCAN_CANCELLED.format(self.user, self.host))

            if self.telemetry_handler.telemetry_data:
                # Set execution time of the scan
                self.telemetry_handler.telemetry_data['statistics']['data'].update({
                    'executionTime': int((scan_completion_time - self.start_time)/60)
                })
                # Make a call to telemetry endpoint
                self.telemetry_handler.send_telemetry()

            # Write scan report to a file
            self.write_to_file(scan_report)
            self.complete_flag = True

            return utils.render_json(scan_report)
        except Excpetion as e:
            logging.exception("{}: {}".format(MESSAGE_EXCEPTION_SCAN_DEPLOYMENT, str(e)))
            return utils.render_error_json(MESSAGE_EXCEPTION_SCAN_DEPLOYMENT)
        finally:
            self.complete_flag = True

    def invoke_app_inspect(self, app):
        """
        Returns app_inspect report.

        :param app: The app for which report needs to be fetched

        :return JSON report from app_inspect
        """

        app_package = os.path.join(OTHER_APPS_DIR, app)
        app_package_handler = splunk_appinspect.app_package_handler.AppPackageHandler(app_package)
        formatter = splunk_appinspect.formatters.ValidationReportJSONFormatter()
        groups_to_validate = splunk_appinspect.checks.groups(included_tags=['py3_migration'])
        validation_report = splunk_appinspect.validator.validate_packages(app_package_handler,
                                                                          groups_to_validate=groups_to_validate)
        if six.PY2:
            json_report = formatter.format(validation_report, sys.maxint)
        elif six.PY3:
            json_report = formatter.format(validation_report, sys.maxsize)

        return json.loads(json_report)

    def write_progress(self, scan_report):
        """
        Write progress in KV store.

        :param scan_report: current scan report

        :return Proceed(True/False) based on whether scan is cancelled or not
        """

        data = {
            'process_id': os.getpid(),
            'host': self.host,
            'user': self.user,
            'progress': 0,
            'status': PROGRESS_NEW,
            'message': "Run new scan",
            'cancelled': False,
            'returned': False
        }

        data.update({
            'progress': scan_report['progress'],
            'status': scan_report['status'],
            'message': scan_report['message']
        })

        # Check if key for given scan exists
        if not self.scan_key:
            self.scan_key = self.get_key_for_write()
        key = self.scan_key

        if key is not None:

            # Check if cancelled flag is set to true
            cancelled, entry = self.is_cancelled(key)
            if cancelled:
                logging.info("Scan has been cancelled. Setting flag in KV store.")
                entry_status, entry_message = self.set_returned(key, entry)
                if not entry_status:
                    logging.error(entry_message)
                    return True
                logging.info(entry_message)
                return False

            try:
                response, _ = sr.simpleRequest('{}/{}?output_mode=json'.format(kvstore_endpoint, key),
                                               sessionKey=self.session_key, jsonargs=json.dumps(data), method='POST',
                                               raiseAllErrors=True)
            except Exception as e:
                logging.exception(MESSAGE_EXCEPTION_WRITE_KVSTORE.format(self.user, self.host))
                return False
            if response['status'] not in success_codes:
                logging.error(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))
                return False
        else:
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

    def get_key_for_write(self):
        """
        Get key for user and host to write progress.

        :return Key value
        """

        logging.info("Retrieving key to write progress")
        try:
            response, content = sr.simpleRequest('{}?output_mode=json'.format(kvstore_endpoint),
                                                 sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_WRITE_KVSTORE.format(self.user, self.host))
            return None
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_WRITING_PROGRESS.format(self.user, self.host))
            return None
        else:
            for entry in json.loads(content):
                if self.host == entry['host'] and self.user == entry['user']:
                    if not entry['cancelled'] and not entry['returned']:
                        logging.info("Found key for existing entry: {}".format(str(entry['_key'])))
                        return entry['_key']
        return None

    def write_session_file(self, key):
        """
        Write session time-out entry in file when KV store could not be reached

        :param key: Entry key for session time-out
        """

        # Check if local directory exists
        local_dir = LOCAL_DIR
        if not os.path.isdir(local_dir):
            os.makedirs(local_dir)

        session_dir = SESSION_PATH
        if not os.path.isdir(session_dir):
            os.makedirs(session_dir)

        try:
            session_file = os.path.join(session_dir, key)
            with open(session_file, 'a') as f:
                current_error = "{}: {}".format(str(int(time.time()*1000)), MESSAGE_UNAUTHORIZED_KV_STORE)
                f.write(current_error)
        except Exception as e:
            logging.exception("{}: {}".format(MESSAGE_ERROR_CREATING_SESSION_FILE.format(self.user, self.host),
                                              str(e)))

    def is_cancelled(self, key):
        """
        Check for cancelled status for user and host.

        :param key: the key of the entry

        :return True/False, Dict of entry
        """
        try:
            response, content = sr.simpleRequest('{}/{}?output_mode=json'.format(kvstore_endpoint, key),
                                                 sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_READ_KVSTORE.format(self.user, self.host))
            self.write_session_file(key)
            return True, {}
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_READING_PROGRESS.format(self.user, self.host))
            self.write_session_file(key)
            return True, {}
        else:
            entry = json.loads(content)
            if entry['cancelled']:
                return True, entry
        return False, {}

    def set_returned(self, key, entry):
        """
        The entry will not be removed but returned flag would be set to True

        :param key: Key of entry to be set with returned flag
        :param entry: Entry to be updated with return flag

        :return Status(True/False), Message
        """

        logging.info("Setting return flag True for given entry due to cancelled flag")
        entry['returned'] = True
        try:
            response, _ = sr.simpleRequest('{}/{}?output_mode=json'.format(kvstore_endpoint, key),
                                           sessionKey=self.session_key, jsonargs=json.dumps(entry), method='POST',
                                           raiseAllErrors=True)
        except Exception as e:
            logging.exception(MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host))
            return False, MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host)
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host))
            return False, MESSAGE_ERROR_REMOVE_ENTRY.format(self.user, self.host)
        return True, "Entry with key: {} halted".format(str(key))

    def write_to_file(self, report):
        """
        Write progress in files.

        :param report: JSON report of App inspect results
        """

        # Check if local directory exists
        local_dir = LOCAL_DIR
        if not os.path.isdir(local_dir):
            os.makedirs(local_dir)

        report_dir = REPORT_PATH
        if not os.path.isdir(report_dir):
            os.makedirs(report_dir)

        scan_id = report['results']['scan_id']
        report_filename = "{}.json".format(scan_id)
        report_file = os.path.join(report_dir, report_filename)
        with open(report_file, 'w') as file_handler:
            json.dump(report['results'], file_handler)

        self.remove_previous_scans(report_dir, report_filename)

    def remove_previous_scans(self, report_dir, report_filename):
        """
        Remove previous scan results.

        :param report_dir: Report directory path
        :param report_filename: filename of current report
        """

        list_reports = os.listdir(report_dir)

        for report in list_reports:
            if self.user in report and report_filename != report:
                report_path = os.path.join(report_dir, report)
                if os.path.exists(report_path):
                    os.remove(report_path)

    def quake_response(self, app, app_meta):
        """
        Prepare response for Quake supported apps.

        :param app: Name and label of the app
        :param app_meta: Type of app and external link of app

        :return app report, status of app
        """

        app_report = dict()
        app_report['name'] = app[0]
        app_report['label'] = app[1]
        app_report['summary'] = {
            'Passed': 7,
            'Blocker': 0,
            'Warning': 0,
            'Skipped': 0,
            'Status': CHECK_CONST_PASSED,
            'type': app_meta[0],
            'app_link': app_meta[1]
        }

        app_report['checks'] = []
        return app_report, CHECK_CONST_PASSED

    def parse_response(self, app, app_meta, report, py_2to3_report):
        """
        Parse response of app inspect.

        :param app: Name of the app
        :param app_meta: Type of app and external link of app
        :param report: app inspect report of given app

        :return updated app report, status of app
        """

        app_report = dict()
        app_report['name'] = app[0]
        app_report['label'] = app[1]
        app_report['summary'] = {
            'Passed': 0,
            'Blocker': 0,
            'Warning': 0,
            'Skipped': 0,
            'type': app_meta[0],
            'app_link': app_meta[1]
        }

        checks_list = report['reports'][0]
        check_groups = checks_list['groups']

        for checks in check_groups:
            if "py3_migration" in checks['name']:
                app_report['checks'] = checks['checks']
                app_report['checks'].append(py_2to3_report)
                break
        else:
            app_report['checks'] = []

        app_report['checks'] = self.fixer_results(app_report['checks'])

        app_report['checks'] = self.set_file_paths(app_report['checks'], app[0])

        app_report['checks'] = self.set_status(app_report['checks'])
        app_report = self.set_check_name(app_report)

        # Set message for Advanced XML check as per flag value
        app_report['checks'] = self.set_axml_message(app_report['checks'])

        # Filter cherrypy checks from python scripts check
        app_report['checks'] = self.filter_cherrypy(app_report['checks'])

        # Process Mako templates for Python script
        app_report['checks'] = self.process_mako(app_report['checks'])

        app_report['checks'] = self.filter_checks(app[0], app_report['checks'])
        updated_app_report = self.get_check_count(app_report)

        app_result = updated_app_report['summary']['Status']
        return updated_app_report, app_result

    def fixer_results(self, checks):
        """
        Format fixer results for Python syntax check.

        :param checks: List of checks

        :return Updated checklist
        """

        for check in checks:
            if check['name'] == CHECK_CONST_NAME:
                messages = [files_paths for files_paths in check['messages'] if files_paths['code']]
                for message_dict in messages:
                    message_dict['code'] = self.format_code(message_dict['code'])
                check['messages'] = messages
            else:
                continue

        return checks

    def format_code(self, syntax_errors):
        """
        Convert syntax error string into list of separate errors

        :param syntax_errors: String of results containing syntax errors

        :return List of separate syntax errors
        """

        code_list = syntax_errors.split("\n@@")
        if len(code_list) > 1:
            new_list = ["@@" + item for item in code_list[1:]]
            new_list.insert(0, code_list[0])
            return new_list
        else:
            return code_list

    def set_file_paths(self, checklist, app_folder):
        """
        Set relative file paths for all entries in checks.

        :param checklist: List of checks for app
        :param app_folder: Folder name of the app

        :return Updated checklist
        """

        for check in checklist:
            for entry in check['messages']:
                entry['full_path'] = entry['message_filename']
                if entry['message_filename'] is not None:
                    old_path = entry['message_filename'].split(app_folder, 1)
                    new_path = "...{}".format(old_path[-1])
                    entry['message_filename'] = new_path

        return checklist

    def get_check_count(self, app_report):
        """
        Get check count for app.

        :param app_report: The app report for which check count is to be calculated

        :return Updated app report
        """

        passed = app_report['summary']['Passed']
        blocker = app_report['summary']['Blocker']
        warning = app_report['summary']['Warning']
        skipped = app_report['summary']['Skipped']

        for check in app_report['checks']:
            if check['result'] == CHECK_CONST_PASSED:
                passed += 1
            elif check['result'] == CHECK_CONST_BLOCKER:
                blocker += 1
            elif check['result'] == CHECK_CONST_WARNING:
                warning += 1
            elif check['result'] == CHECK_CONST_SKIPPED:
                skipped += 1

        status = CHECK_CONST_PASSED
        if skipped > 0:
            status = CHECK_CONST_UNKNOWN
        elif blocker > 0:
            status = CHECK_CONST_BLOCKER
        elif blocker == 0 and warning > 0:
            status = CHECK_CONST_WARNING
        else:
            status = CHECK_CONST_PASSED

        app_report['summary'].update({
            'Passed': passed,
            'Blocker': blocker,
            'Warning': warning,
            'Skipped': skipped,
            'Status': status
        })

        return app_report

    def set_status(self, app_checks):
        """
        Set status for app checks.

        :param app_checks: List of checks

        :return Updated check list with status set
        """

        for check in app_checks:
            if (check['result'] == AI_RESULT_SUCCESS or check['result'] == AI_RESULT_MANUAL or
                    check['result'] == AI_RESULT_NA):
                check['result'] = CHECK_CONST_PASSED
            elif (check['result'] == AI_RESULT_ERROR or check['result'] == AI_RESULT_FAILURE or
                    check['result'] == AI_RESULT_WARNING):
                if check['name'] == CHECK_CONST_NAME:
                    check['result'] = CHECK_CONST_WARNING
                else:
                    check['result'] = CHECK_CONST_BLOCKER
            elif check['result'] == AI_RESULT_SKIPPED:
                check['result'] = CHECK_CONST_SKIPPED

        return app_checks

    def set_check_name(self, app_report):
        """
        Update check names and set required action.

        :param app_report: The app report for which checks should be updated

        :return Updated app report
        """
        checks_list = app_report['checks']
        for check in checks_list:
            if check['name'] in CHECK_NAME_MAPPING:
                check['name'] = CHECK_NAME_MAPPING[check['name']]
                if check['result'] == CHECK_CONST_PASSED:
                    check['required_action'] = CHECK_CONST_PASSED_MSG
                elif check['result'] == CHECK_CONST_SKIPPED:
                    check['required_action'] = CHECK_CONST_SKIPPED_MSG
                else:
                    check['required_action'] = CHECK_ACTION_MAPPING[check['name']]

        app_report['checks'] = checks_list
        return app_report

    def filter_cherrypy(self, app_checks):
        """
        Filter cherrypy python files from python script files.

        :param app_checks: List of checks for app

        :return Updated checklist
        """

        cherry_py_list = []
        python_script_list = []

        for check in app_checks:
            if check['name'] == "Custom CherryPy endpoints":
                cherry_py_list = check['messages']
            if check['name'] == "Python scripts":
                python_script_list = check['messages']

        for e, entry in enumerate(cherry_py_list):
            for i, item in enumerate(python_script_list):
                if entry['message_filename'] == item['message_filename']:
                    entry['code'] = item['code']
                    del python_script_list[i]
                    break
            else:
                entry['code'] = []

        cherry_py_list = list([i for i in cherry_py_list if len(i['code']) > 0])

        for check in app_checks:
            if check['name'] == "Custom CherryPy endpoints":
                check['messages'] = cherry_py_list
                if not cherry_py_list:
                    check['result'] = CHECK_CONST_PASSED
                    check['required_action'] = CHECK_CONST_PASSED_MSG
            if check['name'] == "Python scripts":
                check['messages'] = python_script_list
                if not python_script_list:
                    check['result'] = CHECK_CONST_PASSED
                    check['required_action'] = CHECK_CONST_PASSED_MSG

        return app_checks

    def set_axml_message(self, app_checks):
        """
        Set required action message for Advanced XML check as per flag value

        :param app_checks: List of checks for app

        :return Updated checklist
        """

        for check in app_checks:
            if check['name'] == "Advanced XML":
                for msg in check['messages']:
                    if "WARNING TYPE A" in msg['message']:
                        new_action = msg['message'].split("File:")[0]
                        new_message = new_action.split("WARNING TYPE A:")[1]
                        new_message = new_message.strip()
                        check['required_action'] = new_message
                        check['result'] = CHECK_CONST_WARNING
                        break

        return app_checks

    def filter_checks(self, app_name, checklist):
        """
        Filter checks to show.

        :param app_name: Name of the app
        :param checklist: List of checks for app

        :return Updated checklist
        """

        dismissed_checks = self.fetch_dismissed_checks(app_name)
        for _dc in dismissed_checks:
            for checks in checklist:
                if checks['name'] == _dc['check']:
                    checks['messages'] = list([i for i in checks['messages']
                                              if i['message_filename'] != _dc['file_path']])
                    break

        for checks in checklist:
            if not checks['messages']:
                checks['result'] = CHECK_CONST_PASSED
                checks['required_action'] = CHECK_CONST_PASSED_MSG

        return checklist

    def fetch_dismissed_checks(self, app_name):
        """
        Fetch dismissed checks from kvstore.

        :param app_name: Name of the app

        :return List of dismissed checks
        """

        query_string = "{{\"$and\":[{{\"app\":\"{}\"}},{{\"host\":\"{}\"}},{{\"user\":\"{}\"}}]}}".format(
                        app_name, self.host, self.user)

        try:
            response, content = sr.simpleRequest('{}?output_mode=json&query={}'.format(
                                                 dismiss_coll_endpoint, query_string), sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_FETCHING_DISMISS_ENTRY.format(self.user, self.host, app_name))
            return []
        if response['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_FETCHING_DISMISS_ENTRY.format(self.user, self.host, app_name))
            return []

        return json.loads(content)


if __name__ == '__main__':

    logging.info("Scan initiated")
    if six.PY2:
        scan_args = json.loads(sys.stdin.read())
    elif six.PY3:
        scan_args = json.loads(str(sys.stdin.read()))
    scanner = ScanProcess(scan_args)
    scanner.post_scan_deployment()
