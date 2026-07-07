# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import os
import time
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import CheckUserAccess

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase

from itsi.itsi_utils import CAPABILITY_MATRIX
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider

from migration.supervisor import MigrationSupervisor
from SA_ITOA_app_common.splunklib.client import Service

logger = getLogger()
logger.debug('Initialized Migration REST splunkd handler interface log')

APP_NAME = 'SA-ITOA'


class MigrationInterfaceProviderSplunkd(ItoaInterfaceProvider):
    '''
    This wrapper class for the REST provider in internal MigrationInterfaceProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    '''
    def __init__(self, session_key, current_user, rest_method):
        '''
        Constructor for provider for the interface

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        '''
        self._session_key = session_key if isinstance(session_key, itsi_py3.string_type) else None
        self._current_user = current_user if isinstance(current_user, itsi_py3.string_type) else None
        self._rest_method = rest_method.upper() if isinstance(rest_method, itsi_py3.string_type) else None
        self.service = Service(token=self._session_key, app=APP_NAME)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def get_migration_info(self, owner, object_type, **kwargs):

        def _expand_timestamp(record, timestamp_key, new_key):
            if timestamp_key not in record:
                return
            ts_value = record.pop(timestamp_key)
            if ts_value:
                record[new_key] = MigrationInterfaceProviderSplunkd.parse_timestamp(ts_value)

        if self._rest_method == 'GET':
            migration_checker = MigrationSupervisor(self._session_key)
            migration_status_info = migration_checker.is_migration_running(should_return_verbose=True)
            _expand_timestamp(migration_status_info, 'start_timestamp', 'start_time')
            _expand_timestamp(migration_status_info, 'end_timestamp', 'end_time')
            return self.render_json(migration_status_info)

    def get_rest_request_info(self, args, kwargs):
        '''
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
        '''
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

    @staticmethod
    def parse_timestamp(timestamp):
        '''
        @type: number
        @param timestamp: time as a floating point number expressed in seconds since the epoch, in UTC
        :return object, human readable date and time in UTC
        '''
        if not timestamp:
            return None
        struct_time = time.gmtime(timestamp)
        return {'since_unix_epoch': timestamp,
                'utc': '{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{min:02d}:{sec:02d}Z'.format(
                    year=struct_time.tm_year,
                    month=struct_time.tm_mon,
                    day=struct_time.tm_mday,
                    hour=struct_time.tm_hour,
                    min=struct_time.tm_min,
                    sec=struct_time.tm_sec)}


class MigrationInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):

    '''
    Class implementation for REST handler providing accessible interface endpoints during migration.
    '''
    def __init__(self, command_line, command_arg):
        '''
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        '''
        super(MigrationInterfaceSplunkd, self).__init__()

    def migration_check(self, session_key):
        '''
        Override migration_check in SplunkdRestInterfaceBase
        MigrationInterfaceSplunkd should be accessible during migration and serve request regardless of migration running
        Thus override migration_check of SplunkdRestInterfaceBase
        '''
        pass

    def handle(self, args):
        '''
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @type args: json
        @param args: a JSON string representing a dictionary of arguments to the REST call.

        @rtype: json
        @return: a valid REST response
        '''
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        '''
        Parses the REST path on the interface to help route to respective handlers
        This handler's thin layer parses the paths and routes actual handling for the call
        to MigrationNonBlockedInterfaceSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        '''
        if not isinstance(args, dict):
            message = 'Invalid REST args received by migration non blocked interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)
        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)

        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))
        interface_provider = MigrationInterfaceProviderSplunkd(session_key, current_user, rest_method)
        owner = self.extract_request_owner(args, rest_method_args)

        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by migration interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        # Double check this is maintenance services interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'migration'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
        path_parts.pop(0)

        object_type = path_parts[0]
        if object_type == 'info':
            return interface_provider.get_migration_info(owner, object_type, **rest_method_args)
