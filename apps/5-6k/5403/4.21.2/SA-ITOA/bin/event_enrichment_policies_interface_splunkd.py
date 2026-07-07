# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import http
import sys
from urllib.parse import unquote

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path  # noqa
import itsi_py3

from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.itoa_common import is_feature_enabled
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.setup_logging import getLogger
from itsi.access_control.splunkd_controller_rbac_utils import EnforceRBACSplunkd
from itsi.event_management.event_enrichment_policies_rest_provider import EventEnrichmentPoliciesRestProvider
from itsi.itsi_utils import CAPABILITY_MATRIX, ITOAInterfaceUtils
from user_access_utils import CheckUserAccess

logger = getLogger(logger_name="itsi.event_enrichment_policies", logger_file="itsi_event_enrichment_policies.log")
logger.debug("Initialized SA-ITOA splunkd event management rest services log...")


class EventEnrichmentPoliciesInterfaceProviderSplunkd(EventEnrichmentPoliciesRestProvider):
    """
    This wrapper class for the REST provider in EventEnrichmentPoliciesInterfaceProviderSplunkd
    handles all access check decorators and passes requests to the provider to serve
    the rest of the request.
    """
    def __init__(self, session_key, current_user, rest_method):
        """
        Constructor initializing splunkd specific info

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        """
        self._setup(session_key, current_user, rest_method)

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
        elif method in ['POST', 'PUT']:
            operation = 'write'
        elif method == 'DELETE':
            operation = 'delete'
        else:
            message = 'Unsupported operation - {0}.'.format(method)
            raise Exception(message)

        return user, session_key, object_type, operation, owner

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type="event_enrichment_policies", logger=logger)
    @EnforceRBACSplunkd(is_bulk_op=True)
    def bulk_crud(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the REST method results
        """
        return self._bulk_crud(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type="event_enrichment_policies", logger=logger)
    @EnforceRBACSplunkd()
    def crud_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Routes CRUD operations per object

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: string
        @param object_id: id of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the REST method
        """
        return self._crud_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type="event_enrichment_policies", logger=logger)
    @EnforceRBACSplunkd(is_bulk_op=True)
    def get_object_count(self, owner, object_type, **kwargs):
        """
        Gets count of objects with filters applied

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the count of objects
        """
        return self._get_object_count(owner, object_type, **kwargs)


class EventEnrichmentPoliciesInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    REST handler providing services for enrichment policies interface endpoints.
    """
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(EventEnrichmentPoliciesInterfaceSplunkd, self).__init__()

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
        to EventEnrichmentPoliciesInterfaceProviderSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        """
        logger.info("Dispatching to provider with args: %s", args)

        if not isinstance(args, dict):
            message = 'Invalid REST args received by enrichment policies interface - {}'.format(args)
            logger.error(message)
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        logger.debug("Processing request for user: %s, method: %s", current_user, rest_method)

        # Check if the feature is enabled
        if not is_feature_enabled('itsi-ea-integration-enrichment', session_key=session_key, reload=True):
            logger.warning("Feature 'itsi-ea-integration-enrichment' is not enabled.")
            raise ITOAError(status=http.HTTPStatus.METHOD_NOT_ALLOWED,
                            message='Alert enrichment policies feature is not enabled.')

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)
        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))

        interface_provider = EventEnrichmentPoliciesInterfaceProviderSplunkd(session_key, current_user, rest_method)
        rest_path = args['rest_path']

        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by enrichment policies interface - {}'.format(rest_path)
            logger.error(message)
            raise ItoaValidationError(message=message, logger=logger)

        logger.debug("Parsed REST path: %s", rest_path)

        # Double check this is enrichment policies interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'event_management_interface'):
            message = 'Specified REST url/path is invalid - {}.'.format(rest_path)
            logger.error(message)
            raise ITOAError(status=404, message=message)
        path_parts.pop(0)

        if path_parts[0] in ['vLatest', 'v' + ITOAInterfaceUtils.get_app_version(session_key, app='itsi')]:
            path_parts.pop(0)

        logger.info("Path parts after processing: %s", path_parts)

        first_path_part = path_parts[0]

        owner = self.extract_request_owner(args, rest_method_args)

        # First check for helper methods which would occur as the first term in the path
        if first_path_part == 'enrichment_policies':
            if len(path_parts) == 2 and path_parts[1] is not None:
                object_type = path_parts[1]
                logger.info("Routing to bulk CRUD for object type: %s", object_type)
                return interface_provider.bulk_crud(owner, object_type, **rest_method_args)

            elif len(path_parts) == 3:
                object_type = path_parts[1]
                if path_parts[2] == 'count':
                    logger.info("Getting object count for type: %s", object_type)
                    return interface_provider.get_object_count(owner, object_type, **rest_method_args)
                # Path is for object CRUD by id
                object_id = unquote(path_parts[2])
                logger.info("Routing to CRUD by ID for object type: %s, id: %s", object_type, object_id)
                return interface_provider.crud_by_id(owner, object_type, object_id, **rest_method_args)

        # No takers so far implies REST path is crazy, error out
        message = 'Specified REST url/path is invalid - {}.'.format(rest_path)
        logger.error(message)
        raise ITOAError(status=404, message=message)
