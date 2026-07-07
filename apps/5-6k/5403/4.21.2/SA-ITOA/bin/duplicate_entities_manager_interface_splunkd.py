# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import json
import sys
import http.client

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import CheckUserAccess

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from itsi.itsi_utils import CAPABILITY_MATRIX, ITOAInterfaceUtils
from itsi.duplicate_entities_manager.duplicate_entities_manager_rest_provider import \
    DuplicateEntitiesManagerRestProvider
from itsi.duplicate_entities_manager.constants import SUPPORTED_URL_PATHS

logger = getLogger()
logger.debug("Initialized Entities Duplicate Manager REST splunkd handler interface log")


class DuplicateEntitiesManagerInterfaceProviderSplunkd(DuplicateEntitiesManagerRestProvider):
    """
    This wrapper class for the REST provider in DuplicateEntitiesManagerRestProvider which
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
        self.is_in_operator_supported = ITOAInterfaceUtils.check_for_in_operator_support(self._session_key)

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

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='duplicate_entities_job_queue', logger=logger)
    def job_status_crud(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on job_status
        """
        return self._job_status_crud(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='duplicate_entities_job_queue', logger=logger)
    def job_status_crud_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Routes CRUD operations on job_status with keyid
        """
        return self._job_status_crud_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='duplicate_aliases_cache', logger=logger)
    def duplicate_aliases(self, owner, object_type, **kwargs):
        """
        Fetch the duplicates aliases and entity details linked to them
        """
        return self._get_duplicate_alias_entity_details(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='duplicate_aliases_cache', logger=logger)
    def remediate_retire_entities(self, owner, object_type, **kwargs):
        """
        This will add a retire flag in duplicate_entities_cache collection,
        for the entities which needs to be remediated.
        """
        return self._remediate_retired_entities(owner, object_type, **kwargs)


class DuplicateEntitiesManagerInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for DuplicatesEntitiesManger.
    """

    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        """
        super(DuplicateEntitiesManagerInterfaceSplunkd, self).__init__()

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
        to DuplicateEntitiesManagerInterfaceProviderSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        """

        if not isinstance(args, dict):
            message = 'Invalid REST args received by duplicate entities manager interface - {}.'.format(args)
            raise ItoaValidationError(message=message, logger=logger, uid='IIM-ENTTY-NMZ_001', context={
                'args': args
            })
        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)

        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))
        interface_provider = DuplicateEntitiesManagerInterfaceProviderSplunkd(session_key, current_user, rest_method)
        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by duplicate entities manager interface - {}.'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger, uid='IIM-ENTTY-NMZ_002',
                                      context={'path': rest_path})

        # Double check this is ITOA interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if ((not isinstance(path_parts, list))
                or (len(path_parts) < 2)
                or (path_parts[0] != 'itoa_interface')):
            raise ITOAError(status=http.client.NOT_FOUND,
                            message='Specified REST url/path is invalid - {}.'.format(rest_path),
                            uid='IIM-ENTTY-NMZ_003',
                            context={'path': rest_path})
        path_parts.pop(0)

        # Version check the API. It should be in the second part of URL if specified. Samples:
        # /itoa_interface/vLatest/... where vLatest implies latest ITSI version
        # /itoa_interface/<Latest ITSI version>/...
        # Currently only latest version of ITSI is supported for all APIs
        if len(path_parts) < 1:
            raise ITOAError(status=http.client.NOT_FOUND,
                            message='Specified REST url/path is invalid - {}.'.format(rest_path),
                            uid='IIM-ENTTY-NMZ_003',
                            context={'path': rest_path}
                            )

        if path_parts[0] in ['vLatest', 'v' + ITOAInterfaceUtils.get_app_version(session_key, app='itsi')]:
            path_parts.pop(0)

        if len(path_parts) < 1:
            raise ITOAError(status=http.client.NOT_FOUND,
                            message='Specified REST url/path is invalid - {}.'.format(rest_path),
                            uid='IIM-ENTTY-NMZ_003',
                            context={'path': rest_path}
                            )

        # Double check this is duplicate_entities_manager interface path
        if path_parts[0] != 'duplicate_entities_manager':
            raise ITOAError(status=http.client.NOT_FOUND,
                            message='Specified REST url/path is invalid - {}.'.format(rest_path),
                            uid='IIM-ENTTY-NMZ_003',
                            context={'path': rest_path}
                            )
        path_parts.pop(0)

        first_path_part = path_parts[0]
        if first_path_part in SUPPORTED_URL_PATHS:
            owner = self.extract_request_owner(args, rest_method_args)
            object_type = first_path_part
            if len(path_parts) == 1:
                if object_type == 'job_status':
                    return interface_provider.job_status_crud(owner, 'duplicate_entities_job_queue', **rest_method_args)
                elif object_type == 'duplicate_aliases':
                    return interface_provider.duplicate_aliases(owner, object_type='duplicate_aliases_cache',
                                                                **rest_method_args)
            if len(path_parts) == 2:
                if object_type == 'job_status':
                    object_id = path_parts[1]
                    if rest_method in ['GET', 'PUT']:
                        return interface_provider.job_status_crud_by_id(owner, 'duplicate_entities_job_queue',
                                                                        object_id,
                                                                        **rest_method_args)
                    else:
                        raise ITOAError(status=http.client.METHOD_NOT_ALLOWED,
                                        message="Unsupported HTTP method %s."
                                                % rest_method,
                                        uid='IIM-ENTTY-NMZ_006',
                                        context={'method': rest_method})
                if object_type == 'duplicate_aliases' and path_parts[1] == "remediate":
                    return interface_provider.remediate_retire_entities(owner, object_type='duplicate_entities_cache',
                                                                        **rest_method_args)
        # No takers so far implies REST path is crazy, error out
        raise ITOAError(status=http.client.NOT_FOUND,
                        message='Specified REST url/path is invalid - {}.'.format(rest_path),
                        uid='IIM-ENTTY-NMZ_003',
                        context={'path': rest_path}
                        )
