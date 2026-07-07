import os
import io
import re
import sys
import csv
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
from builtins import range

logging = logger_manager.setup_logging('upgrade_readiness')

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class ExportReportHandler(PersistentServerConnectionApplication):
    """
    This is a REST handler base-class that makes implementing a REST handler easier.

    This works by resolving a name based on the path in the HTTP request and calls it.
    This class will look for a function that includes the HTTP verb followed by the path.abs

    For example, if a GET request is made to the endpoint is executed with the path /export_report,
    then this class will attempt to run a function named get_export_report().
    Note that the root path of the REST handler is removed. If a POST request is made to the endpoint
    is executed with the path /export_report, then this class will attempt to execute post_export_report().
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
            self.file_format = FILE_FORMAT_JSON
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

            query_params = args['query_parameters']

            # If no scan_id is provided, the endpoint will return with 404 error
            if query_params.get('id'):
                scan_id = query_params['id']
            else:
                return utils.render_error_json(MESSAGE_ERROR_NO_SCAN_ID, 404)

            # If no format is provided, the endpoint will set JSON as default
            if query_params.get('format'):
                self.file_format = query_params['format']
                if self.file_format != FILE_FORMAT_JSON and self.file_format != FILE_FORMAT_CSV:
                    return utils.render_error_json(MESSAGE_INVALID_FILE_FORMAT, 500)

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
                return function_to_call(scan_id)

            else:
                logging.warn("A request could not be executed since the associated function is missing, name={}"
                             .format(function_name))
                return utils.render_error_json(MESSAGE_PATH_NOT_FOUND, 404)

        except Exception as exception:
            logging.exception(MESSAGE_FAILED_HANDLE_REQUEST)
            return utils.render_error_json(str(exception))

    def get_export_report(self, scan_id):
        """
        Get report of scan results and export as JSON.

        :param scan_id: Id of the report

        :return scan results for given id
        """

        # Check for reports in /local/reports directory
        results = dict()
        list_reports = os.listdir(REPORT_PATH)

        for report in list_reports:
            # Fetch file for given scan_id
            if (".").join([scan_id, "json"]) == report:
                report_file = os.path.join(REPORT_PATH, report)
                with open(report_file, 'r') as file_handler:
                    results = json.load(file_handler)
                break

        if results:
            results = self.filter_report(results)
            if self.file_format == FILE_FORMAT_JSON:
                return utils.render_json(results)
            else:
                results = self.csv_conversion(results)
                return utils.render_csv(results)
        else:
            return utils.render_error_json(MESSAGE_ERROR_EXPORT_REPORT.format(scan_id), 404)

    def filter_report(self, report):
        """
        Filter report by removing additional fields.

        :param report: Report in JSON

        :return Updated report
        """

        for app in report['apps']:
            for check in app['checks']:
                for message in check['messages']:
                    if 'line' in message:
                        del message['line']
                    if 'filename' in message:
                        del message['filename']

        return report

    def csv_conversion(self, report):
        """
        Convert JSON report into CSV results

        :param report: Report in JSON

        :return Updated report
        """

        if six.PY2:
            output = io.BytesIO()
        elif six.PY3:
            output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CSV_REPORT_HEADERS)
        csv_data = list()
        for app in report['apps']:
            name = app['label']
            status = app['summary']['Status']
            source = app['summary']['type']
            xml_list = list()
            cherry_list = list()
            cherry_syntax_list = list()
            mako_list = list()
            mako_syntax_list = list()
            libraries_list = list()
            test_list = list()
            weblegacy_list = list()
            pyfiles_list = list()
            pyfiles_syntax_list = list()
            for check in app['checks']:
                for entry in check['messages']:
                    if entry['message_filename'] is not None:
                        if check['name'] == 'Advanced XML':
                            xml_list.append(entry['message_filename'])
                        elif check['name'] == 'Custom CherryPy endpoints':
                            cherry_list.append(entry['message_filename'])
                            cherry_syntax_list.append(self.get_syntax(entry['code']))
                        elif check['name'] == 'Python in custom Mako templates':
                            mako_list.append(entry['message_filename'])
                            mako_syntax_list.append(self.get_syntax(entry['code']))
                        elif check['name'] == 'Removed libraries':
                            libraries_list.append(entry['message_filename'])
                        elif check['name'] == 'Files named test.py':
                            test_list.append(entry['message_filename'])
                        elif check['name'] == 'Splunk web legacy mode':
                            weblegacy_list.append(entry['message_filename'])
                        elif check['name'] == 'Python scripts':
                            pyfiles_list.append(entry['message_filename'])
                            pyfiles_syntax_list.append(self.get_syntax(entry['code']))

            app_row_list = [xml_list, cherry_list, cherry_syntax_list, mako_list, mako_syntax_list, libraries_list,
                            test_list, weblegacy_list, pyfiles_list, pyfiles_syntax_list]

            app_rows = self.write_columns(name, status, source, app_row_list)
            csv_data.extend(app_rows)

        writer.writerows(csv_data)
        return output.getvalue()

    def get_syntax(self, code):
        """
        Get syntax issues if available for a check

        :param code: List of syntax issues

        :return Stringified value for code
        """

        if not code or code is None:
            return "~"

        return str(code)

    def write_columns(self, name, status, source, row_list):
        """
        Write individual columns as per check value list

        :param row_list: List of lists containing file entries for individual check
        :param name: Name of the app
        :param status: Status of the app
        :param source: Source/type of the app

        :return app_rows: List of list containing row values for given app
        """

        app_rows = list()

        xml_list = row_list[0]
        cherry_list = row_list[1]
        cherry_syntax_list = row_list[2]
        mako_list = row_list[3]
        mako_syntax_list = row_list[4]
        libraries_list = row_list[5]
        test_list = row_list[6]
        weblegacy_list = row_list[7]
        pyfiles_list = row_list[8]
        pyfiles_syntax_list = row_list[9]

        max_rows = max(len(xml_list), len(cherry_list), len(cherry_syntax_list), len(mako_list), len(mako_syntax_list),
                       len(libraries_list), len(test_list), len(weblegacy_list), len(pyfiles_list),
                       len(pyfiles_syntax_list))

        if max_rows == 0:
            app_rows.append([name, status, source, "~", "~", "~", "~", "~", "~", "~", "~", "~", "~"])
            return app_rows

        for index in range(0, max_rows):
            row = [name, status, source]
            for position, value in enumerate(row_list):
                try:
                    row.append(value[index])
                except IndexError:
                    row.append("~")

            app_rows.append(row)

        return app_rows
