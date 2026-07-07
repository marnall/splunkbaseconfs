# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

import itsi_path
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider
from feature_flagging.license_retriever import LicenseRetriever

logger = getLogger()
logger.debug('Initialized Feature Flagging REST splunkd handler interface log')


class FeatureFlaggingProviderSplunkd(ItoaInterfaceProvider):
    '''
    This wrapper class for the REST provider in internal FeatureFlaggingProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    '''
    def __init__(self, system_auth_token):
        '''
        Constructor for provider for the interface

        @type: string
        @param system_auth_token: the splunkd system level authorization token

        '''
        self._system_auth_token = system_auth_token

    def get_features(self):
        license_retriever = LicenseRetriever(self._system_auth_token)
        features = license_retriever.get_features(license_retriever.get_suite())
        return self.render_json(features)


class FeatureFlaggingInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):

    '''
    Class implementation for REST handler for Feature Flagging
    '''
    def __init__(self, command_line, command_arg):
        '''
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        '''
        super(FeatureFlaggingInterfaceSplunkd, self).__init__()

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
        to FeatureFlaggingInterfaceSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        '''
        if not isinstance(args, dict):
            message = 'Invalid REST args received by Feature Flagging interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)

        system_auth_token = args['system_authtoken']

        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by Feature Flagging interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'feature_flagging'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))

        operation = path_parts[1]
        if operation == 'features':
            interface_provider = FeatureFlaggingProviderSplunkd(system_auth_token)
            return interface_provider.get_features()
