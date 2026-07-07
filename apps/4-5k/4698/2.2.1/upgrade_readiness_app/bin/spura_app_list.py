import os
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

logging = logger_manager.setup_logging('upgrade_readiness')

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class AppListHandler(PersistentServerConnectionApplication):
    """
    This is a REST handler base-class that makes implementing a REST handler easier.

    This works by resolving a name based on the path in the HTTP request and calls it.
    This class will look for a function that includes the HTTP verb followed by the path.abs

    For example, if a GET request is made to the endpoint is executed with the path /app_list,
    then this class will attempt to run a function named get_app_list().
    Note that the root path of the REST handler is removed. If a POST request is made to the endpoint
    is executed with the path /app_list, then this class will attempt to execute post_app_list().
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

            query_params = args['query_parameters']

            # If no scan_type is provided, the endpoint will return with 404 error
            if query_params.get('type'):
                scan_type = query_params['type']
            else:
                return utils.render_error_json(MESSAGE_ERROR_NO_SCAN_TYPE, 404)

            accepted_types = [TYPE_DEPLOYMENT, TYPE_PARTIAL, TYPE_SPLUNKBASE, TYPE_PRIVATE]
            if scan_type not in accepted_types:
                return utils.render_error_json(MESSAGE_INVALID_SCAN_TYPE, 400)
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
                self.start_time = int(time.time()*1000)
                return function_to_call(scan_type)

            else:
                logging.warn("A request could not be executed since the associated function is missing, name={}"
                             .format(function_name))
                return utils.render_error_json(MESSAGE_PATH_NOT_FOUND, 404)

        except Exception as exception:
            logging.exception(MESSAGE_FAILED_HANDLE_REQUEST)
            return utils.render_error_json(str(exception))

    def get_app_list(self, scan_type):
        """
        Fetch the App list and return the App list as JSON

        :param scan_type: Type of scan

        :return List of Apps containing name, label, type and link
        """

        try:
            response_role, content_role = sr.simpleRequest('{}?output_mode=json&count=0'.format(user_role_endpoint),
                                                           sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_REST_CALL.format(str(e)))
            return utils.render_error_json(MESSAGE_EXCEPTION_REST_CALL.format(self.user), 404)

        if response_role['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_FETCHING_ROLES.format(self.user))
            return utils.render_error_json(MESSAGE_ERROR_FETCHING_ROLES.format(self.user), 404)

        try:
            response_apps, content_apps = sr.simpleRequest('{}?output_mode=json&count=0'.format(user_check_endpoint),
                                                           sessionKey=self.session_key)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_REST_CALL.format(str(e)))
            return utils.render_error_json(MESSAGE_EXCEPTION_REST_CALL.format(self.user), 404)

        if response_apps['status'] not in success_codes:
            logging.error(MESSAGE_ERROR_FETCHING_APPS.format(self.user))
            return utils.render_error_json(MESSAGE_ERROR_FETCHING_APPS.format(self.user), 404)

        # Get list of apps for current user
        user_app_list = self.get_user_apps(content_role, content_apps)

        # Skip all the system apps
        all_app_list = [value for value in user_app_list if value[0] not in SYSTEM_APPS]

        # List only apps present in etc/apps path
        app_list = [value for value in all_app_list if value[0] in os.listdir(OTHER_APPS_DIR)]

        if not app_list:
            logging.error(MESSAGE_NO_APPS_FOUND.format(self.user))
            return utils.render_error_json(MESSAGE_NO_APPS_FOUND.format(self.user), 404)

        # Get type of app and app link
        app_type_list = self.get_app_type(app_list)

        if scan_type == TYPE_SPLUNKBASE:
            app_type_list = self.filter_apps(app_type_list, TYPE_SPLUNKBASE)
            if not app_type_list:
                logging.error(MESSAGE_NO_SPLUNKBASE_APPS_FOUND.format(self.user))
                return utils.render_error_json(MESSAGE_NO_SPLUNKBASE_APPS_FOUND.format(self.user), 404)
        elif scan_type == TYPE_PRIVATE:
            app_type_list = self.filter_apps(app_type_list, TYPE_PRIVATE)
            if not app_type_list:
                logging.error(MESSAGE_NO_PRIVATE_APPS_FOUND.format(self.user))
                return utils.render_error_json(MESSAGE_NO_PRIVATE_APPS_FOUND.format(self.user), 404)

        final_app_list = list()
        for app in app_type_list:
            app_json = dict()
            app_json['name'] = app[0][0]
            app_json['label'] = app[0][1]
            app_json['type'] = self.get_compatibility_type(app[1][0], app[2][1])
            app_json['link'] = app[1][1]
            app_json['visible'] = app[3]
            final_app_list.append(app_json)

        return utils.render_json(final_app_list)

    def get_compatibility_type(self, app_type, compatibility):
        """
        Returns the compatibilty based type of app

        :param apps: Type of app
        :param compatibility: Compatibility with version

        :return Compatibility type
        """

        if app_type == CONST_SPLUNKBASE or app_type == CONST_SPLUNKSUPPORTED:
            if compatibility == CONST_QUAKE:
                return CONST_SPLUNKBASE_QUAKE
            elif compatibility == CONST_DUAL:
                return CONST_SPLUNKBASE_DUAL
            elif compatibility == CONST_UPDATE:
                return CONST_SPLUNKBASE_UPDATE
            else:
                return CONST_SPLUNKBASE_NONE
        else:
            return app_type

    def get_user_apps(self, response_role, response_apps):
        """
        Returns the list of apps for the user.

        :param response_role: Dict containing apps entries with user roles
        :param response_apps: Dict containing user entries with user permissions

        :return List of apps for the user (name, label, version, visible)
        """

        user_apps = list()
        user_roles = list()

        try:
            rolelist = json.loads(response_role)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_ROLELIST.format(self.user))
            return user_apps

        for user in rolelist.get('entry', []):
            if user['name'] == self.user:
                user_roles = user['content']['roles']
                break
        if not user_roles:
            return utils.render_error_json(MESSAGE_ERROR_FETCHING_ROLES.format(self.user), 404)

        try:
            applist = json.loads(response_apps)
        except Exception as e:
            logging.exception(MESSAGE_EXCEPTION_APPLIST.format(self.user))
            return user_apps

        for app in applist.get('entry', []):

            visible = CONST_ENABLED
            try:
                read_permission = app['acl'].get('perms').get('read')
                if not read_permission:
                    read_permission = []
                    visible = CONST_ALL_PERM
            except Exception as e:
                read_permission = []
                visible = CONST_ALL_PERM

            # Check if app is disabled or a premium app
            if app['content']['disabled']:
                visible = CONST_DISABLED
            elif read_permission:
                if app['name'] in PREMIUM_APPS:
                    visible = CONST_PREMIUM
                else:
                    visible = CONST_ENABLED

            # Check if app got version
            if not app.get('content').get('version'):
                version = None
            else:
                version = app['content']['version']

            if not read_permission:
                user_apps.append((app['name'], app['content']['label'], version, visible))
            elif '*' in read_permission:
                user_apps.append((app['name'], app['content']['label'], version, visible))
            elif set(user_roles).intersection(set(read_permission)):
                user_apps.append((app['name'], app['content']['label'], version, visible))
            else:
                visible = CONST_USER_PERM
                user_apps.append((app['name'], app['content']['label'], version, visible))

        return user_apps

    def get_compatibility(self, version, compatibility):
        """
        Returns the compatibilty based on installed version

        :param apps: App version
        :param compatibility: Compatibility mapping

        :return Compatibility
        """

        all_versions = compatibility.split(";")

        if version is None:
            return CONST_NONE

        quake_support_flag = False
        version_found = False
        for item in all_versions:
            app_version, splunk_support = item.split("#")
            splunk_support = splunk_support.split("|")
            if not splunk_support[-1]:
                splunk_support = splunk_support[:-1]
            if '8.0' in splunk_support:
                quake_support_flag = True
            if version == app_version:
                version_found = True
                if '8.0' in splunk_support and len(splunk_support) == 1:
                    return CONST_QUAKE
                elif '8.0' in splunk_support and len(splunk_support) > 1:
                    return CONST_DUAL
                else:
                    continue
        else:
            if quake_support_flag and version_found:
                return CONST_UPDATE
            else:
                return CONST_NONE

    def get_app_type(self, app_list):
        """
        Returns the list of tuples containing app along with its type.

        :param apps: List of apps

        :return App List of tuples ((appname, app-label), (type, link), (version, compatibility), visible)
        """

        updated_list = []
        splunkbase_apps = []
        splunksupported_apps = []

        splunkbase_path = os.path.join(CSV_PATH, 'splunkbaseapps.csv')
        splunksupported_path = os.path.join(CSV_PATH, 'splunksupportedapps.csv')

        with open(splunkbase_path, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                splunkbase_apps.append(row)

        with open(splunksupported_path, 'r') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                splunksupported_apps.append(row)

        for app in app_list:
            for item in splunkbase_apps:
                if app[0] == item[0]:
                    if not item[3] == "-":
                        compatibility = self.get_compatibility(app[2], item[3])
                        updated_list.append(((app[0], app[1]), (CONST_SPLUNKBASE, item[2]),
                                             (app[2], compatibility), app[3]))
                    else:
                        updated_list.append(((app[0], app[1]), (CONST_SPLUNKBASE, item[2]),
                                             (app[2], CONST_NONE), app[3]))
                    break
            else:
                for item in splunksupported_apps:
                    if app[0] == item[0]:
                        if not item[3] == "-":
                            compatibility = self.get_compatibility(app[2], item[3])
                            updated_list.append(((app[0], app[1]), (CONST_SPLUNKSUPPORTED, item[2]),
                                                 (app[2], compatibility), app[3]))
                        else:
                            updated_list.append(((app[0], app[1]), (CONST_SPLUNKSUPPORTED, item[2]),
                                                 (app[2], CONST_NONE), app[3]))
                        break
                else:
                    updated_list.append(((app[0], app[1]), (CONST_PRIVATE, ""), (app[2], CONST_NONE), app[3]))

        return updated_list

    def filter_apps(self, app_list, type_of_apps):
        """
        Returns the list of app as per the type required.

        :param app_list: List of apps
        :param type_of_apps: Type of apps required

        :return Filtered list of apps
        """

        filtered_list = list()
        if type_of_apps == TYPE_SPLUNKBASE:
            for app in app_list:
                if app[1][0] != CONST_PRIVATE:
                    filtered_list.append(app)
        else:
            for app in app_list:
                if app[1][0] == CONST_PRIVATE:
                    filtered_list.append(app)

        return filtered_list
