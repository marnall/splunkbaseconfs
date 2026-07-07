# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import logging
import sys

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import CheckUserAccess

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_py3

from ITOA.setup_logging import setup_logging
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from itsi.admin_console.admin_console_rest_provider import AdminConsoleRestProvider
from itsi.itsi_utils import CAPABILITY_MATRIX, ITOAInterfaceUtils

logger = setup_logging("itsi_admin_console.log", "itsi.admin_console", level=logging.DEBUG)
logger.debug("Initialized Admin Console REST splunkd handler interface log")


class AdminConsoleInterfaceProviderSplunkd(AdminConsoleRestProvider):
    """
    This wrapper class for the REST provider in AdminConsoleRestProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    """
    def __init__(self, session_key, current_user, rest_method):
        """
        Constructor for provider for the interface

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        """
        self._setup(session_key, current_user, rest_method)
        self.logger = logger

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def get_kpi_insights(self, owner, object_type, **kwargs):
        """
        Gets KPI threshold statistics

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: object type for access check

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the count of objects
        """
        return self._get_kpi_insights(**kwargs)

    def get_rest_request_info(self, args, kwargs):
        """
        Invoked by access check (CheckUserAccess decorator) in SA-UserAccess
        to get splunkd request specific information

        @type: object
        @param self: the self reference

        @type: tuple
        @param args: args of the decorated REST handler function being processed

        @type: dict
        @param kwargs: kwargs of the decorated REST handler function being processed

        @rtype: tuple
        @return: tuple containing (user, session_key, object_type, operation, owner) for this request
        """
        owner = args[0] if len(args) > 0 else None
        object_type = args[1] if len(args) > 1 else None

        session_key = self._session_key
        user = self._current_user
        method = self._rest_method

        if method == 'GET':
            operation = 'read'
        elif method in ['POST']:
            operation = 'write'
        else:
            message = 'Unsupported operation - {0}.'.format(method)
            raise Exception(message)

        return user, session_key, object_type, operation, owner


class AdminConsoleInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for maintenance services interface endpoints.
    """
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(AdminConsoleInterfaceSplunkd, self).__init__()

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        """
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        """
        Parses the REST path on the interface to help route to respective handlers
        This handler's thin layer parses the paths and routes actual handling for the call
        to AdminConsoleInterfaceProviderSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        """
        if not isinstance(args, dict):
            message = 'Invalid REST args received by admin console interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)
        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)

        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))
        interface_provider = AdminConsoleInterfaceProviderSplunkd(session_key, current_user, rest_method)
        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by admin console interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        # Double check this is admin console interface path
        path_parts = rest_path.strip().strip('/').split('/')
        logger.info("Path parts identified from the URL: %s" % (path_parts))
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'admin_console_interface'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
        path_parts.pop(0)

        # Version check the API. It should be in the second part of URL if specified. Samples:
        # /admin_console_interface/vLatest/... where vLatest implies latest ITSI version
        # /admin_console_interface/<Latest ITSI version>/...
        # Currently only latest version of ITSI is supported for all APIs
        if len(path_parts) < 1:
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        if path_parts[0] in ['vLatest', 'v' + ITOAInterfaceUtils.get_app_version(session_key, app='itsi')]:
            path_parts.pop(0)

        if len(path_parts) < 1:
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        first_path_part = path_parts[0]
        if first_path_part in interface_provider.SUPPORTED_OPERATION_TYPES:
            if first_path_part == 'kpi_insights':
                if len(path_parts) > 1:
                    second_path_part = path_parts[1]
                    if second_path_part not in interface_provider.SUPPORTED_THRESHOLD_TYPES:
                        raise ITOAError(status=404, message='Specified REST url/path is invalid, not a supported threshold type - {}.'.format(rest_path))
                    else:
                        rest_method_args['threshold_type'] = second_path_part
                return interface_provider.get_kpi_insights(current_user, 'admin_console', **rest_method_args)
        # No takers so far implies REST path is invalid, error out
        raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
