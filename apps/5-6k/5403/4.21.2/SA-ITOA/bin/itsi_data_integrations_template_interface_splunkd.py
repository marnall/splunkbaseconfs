import sys
import json
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))

from ITOA.itoa_exceptions import ItoaValidationError
from ITOA.controller_utils import ITOAError
from ITOA.setup_logging import getLogger
from itsi.itoa_rest_interface_provider.itoa_rest_interface_provider import ItoaInterfaceProvider
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from splunk.persistconn.application import PersistentServerConnectionApplication
from ITOA.itoa_common import is_feature_enabled
import http

logger = getLogger()


class DataIntegrationsTemplateInterfaceProviderSplunkd(ItoaInterfaceProvider):
    def __init__(self, session_key, current_user, rest_method):
        """
        The decorator invoked wrapper for the decorated function (REST handler)
        This wrapper does the access check on the REST request and throws an exception if access is denied

        @type: string
        @param session_key: the splunkd session key for the request

        @type: string
        @param current_user: current user invoking the request

        @type: string
        @param: type of REST method of this request, GET/PUT/POST/DELETE
        """
        self._setup(session_key, current_user, rest_method)

    def get_all_templates(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of ITOA object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the REST method results
        """
        if self._rest_method == 'GET':
            return self._get_bulk(owner, object_type, **kwargs)

    def get_template(self, owner, object_type, template_name, **kwargs):

        results = self._get_by_id('nobody', 'data_integration_template', template_name)
        if results:
            return results
        else:
            # if template not found return a 404
            raise ITOAError(status=404, message=f'Template {template_name} not found in KV store')


class DataIntegrationsTemplateInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    This wrapper class for the REST provider in EventManagementRestProvider which
    handles all access check decorators and passes on to provider to serve
    rest of the request
    """

    def __init__(self, command_line, command_arg):
        '''
        Basic constructor

        @type: string
        @param command_line: command line invoked for handler

        @type: string
        @param command_arg: args for invoked command line for handler
        '''
        super(DataIntegrationsTemplateInterfaceSplunkd, self).__init__()

    def migration_check(self, session_key):
        '''
        Override migration_check in SplunkdRestInterfaceBase
        MigrationInterfaceSplunkd should be accessible during migration and serve request regardless of migration
        running
        Thus override migration_check of SplunkdRestInterfaceBase
        '''
        pass

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
        if not isinstance(args, dict):
            message = f'Invalid REST args received by Data Integrations Template Interface - {args}'
            raise ItoaValidationError(message=message, logger=logger)

        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']
        owner = 'nobody'

        rest_path = args['rest_path']

        path_parts = rest_path.strip().strip('/').split('/')

        interface_provider = DataIntegrationsTemplateInterfaceProviderSplunkd(session_key, current_user, rest_method)

        if len(path_parts) == 3 and path_parts[2] == "template":
            return interface_provider.get_all_templates(owner, 'data_integration_template')

        if len(path_parts) == 4 and path_parts[2] == "template":
            return interface_provider.get_template(owner, 'data_integration_template', path_parts[3])

        raise ITOAError(status=404, message=f'Specified REST url/path is invalid - {rest_path}.')
