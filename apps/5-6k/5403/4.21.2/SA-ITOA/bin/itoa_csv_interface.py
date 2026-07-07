# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import json
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
import itsi_py3


from itsi.csv_import.itoa_bulk_import_common import spool_dirloc
from itsi.csv_import.itoa_bulk_import_preview_utils import ServicePreviewer, EntityPreviewer, TemplatePreviewer, RowPreviewer
from itsi.csv_import.itoa_bulk_import_rest_interface_provider import ItsiBulkImportInterfaceProvider
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from ITOA.setup_logging import getLogger


logger = getLogger()
logger.debug("Initialized csv interface log...")


class ItoaCSVInterfaceProviderSplunkd(ItsiBulkImportInterfaceProvider):
    """
    ITOA CSV Interface Provider provides the functionality for uploading, previewing, and committing
    bulk imports to the spool for import to KVStore
    """
    def __init__(self, session_key, current_user, rest_method):
        """
        Constructor initializing splunkd specific info

        @param session_key: Splunkd session key for the request
        @type: string
        @param current_user: Current user invoking the request
        @type: string
        @param: REST method of this request, GET/PUT/POST/DELETE
        @type: string
        """
        super(ItoaCSVInterfaceProviderSplunkd, self).__init__()
        # Sets up `self._session_key`, `self._current_user`, `self._rest_method`, `self._instrumentation`
        self._setup(session_key, current_user, rest_method)

    def csv_upload(self, **kwargs):
        # type: (*Any, **Any) -> Text
        """
        Loads entities/services into w/e backend storage is currently defined

        @param **kwargs: Keyword arguments extracted from the request.  Expected keywords: transaction_id, csvfile

        @return dict of metadata derived from upload: CSV headers, array of sample rows, total data length
        @type json string
        """
        self._confirm_contract(['POST'], kwargs, ['transaction_id', 'csvfile'])
        file_name = 'csv_import_{}.csv'.format(kwargs['transaction_id'])
        return self._csv_upload(kwargs['transaction_id'], kwargs['csvfile'], spool_dirloc(), file_name)

    def from_search(self, *args, **kwargs):
        # type: (*Any, **Any) -> Text
        """
        Loads entities/services into w/e backend storage is currently defined

        @param *args: unused
        @param **kwargs: Keyword arguments extracted from the request

        @return created keys or error message.
        @type json string
        """
        kwargs = kwargs['data']
        self._confirm_contract(['POST'], kwargs, ['transaction_id', 'search'])
        return self._csv_from_search(kwargs['transaction_id'], kwargs['search'], kwargs['index_earliest'], kwargs['index_latest'])

    def service_preview(self, owner, *args, **kwargs):
        # type: (Text, *Any, **Any) -> Text
        """
        Provide preview of service objects in the spool, given a bulk import specification.

        @param owner: The owner of the transaction
        @param args: unused
        @param **kwargs: Keyword arguments extracted from the request.  Required field: transaction_id, columns

        @return A JSON list of the requested objects, or an error message.
        @type unicode
        """
        self._confirm_contract(['GET'], kwargs, ['transaction_id', 'columns'])
        return self._csv_object_preview(kwargs['transaction_id'], json.loads(kwargs['columns']), owner, ServicePreviewer)

    def template_preview(self, owner, *args, **kwargs):
        # type: (Text, *Any, **Any) -> Text
        """
        Provide a preview of which services will be linked to templates.

        @param owner: The owner of the transaction
        @param args: unused
        @param **kwargs: Keyword arguments extracted from the request.  Required field: transaction_id, columns

        @return: A JSON list of ImportTemplate objects
        @type: unicode
        """
        try:
            data = json.loads(kwargs.get('data', None))
        except (TypeError, ValueError):
            data = {}

        self._confirm_contract(['GET'], data, ['transaction_id', 'columns'])

        import_type = kwargs.get('import_type', '').strip()
        if import_type == 'search':
            return self._csv_template_preview(data['transaction_id'], data['columns'], owner, TemplatePreviewer)

        return self._csv_object_preview(data['transaction_id'], data['columns'], owner, TemplatePreviewer)

    def entity_preview(self, owner, *args, **kwargs):
        # type: (Text, *Any, **Any) -> Text
        """
        Provide preview of entity objects in the spool, given a bulk import specification

        @param owner: The owner of the transaction
        @param args: unused
        @param **kwargs: Keyword arguments extracted from the request.  Required field: transaction_id, columns

        @return A JSON list of the requested objects, or an error message.
        @type unicode
        """
        self._confirm_contract(['GET'], kwargs, ['transaction_id', 'columns'])
        return self._csv_object_preview(kwargs['transaction_id'], json.loads(kwargs['columns']), owner, EntityPreviewer)

    def row_preview(self, owner, *args, **kwargs):
        # type: (Text, *Any, **Any) -> Text
        """
        Provides preview of rows of data from CSV.

        @param owner: The owner of the transaction
        @param args: unused
        @param **kwargs: Keyword arguments extracted from the request.  Required field: transaction_id, spec

        @return A JSON list of the requested objects, or an error message.
        @type unicode
        """
        self._confirm_contract(['GET'], kwargs, ['transaction_id', 'spec'])

        try:
            spec = json.loads(kwargs['spec'])
        except (TypeError, ValueError):
            spec = {}

        return self._csv_object_preview(kwargs['transaction_id'], spec, owner, RowPreviewer)

    def finalize(self, owner, *args, **kwargs):
        # type: (Text, *Any, **Any) -> Text
        """
        Accept the final version of the Bulk Import Specification from the customer, and write
        it to the spool directory to begin the bulk import asynchronous process.

        @param owner: The owner of the transaction
        @param args: unused
        @param **kwargs: Keyword arguments extracted from the request.  Required field: transaction_id, columns

        @return Either a JSON success message, or a JSON error message.
        @type unicode
        """
        self._confirm_contract(['POST'], kwargs.get('data', {}), ['transaction_id', 'columns'])

        data = kwargs['data']
        return self._csv_commit_upload(data['transaction_id'], data['columns'], owner)

    def upload_csv_lookup(self, **kwargs):
        # type: (*Any, **Any) -> Text
        """

        @param **kwargs: Keyword arguments extracted from the request.  Expected keywords: transaction_id, csvfile

        @return dict of responses that include:
            Transaction ID
            Metadata derived from CSV upload: CSV headers, array of sample rows, total data length
            `transforms.conf` stanza creation response
        @type json string
        """
        self._confirm_contract(['POST'], kwargs, ['name', 'csvfile'])
        return json.dumps(self._upload_csv_lookup(kwargs))


class ItoaCSVInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
    """
    Class implementation for REST handler providing services for CSV bulk import
    """
    def __init__(self, command_line, command_arg):
        """
        Basic constructor

        @param command_line: Command invoked for handler
        @type: string

        @param command_arg: Command arguments invoked for handler
        @type: string
        """
        super(ItoaCSVInterfaceSplunkd, self).__init__()

    def handle(self, args):
        """
        Blanket handler for all REST calls on the interface routing the GET/POST/PUT/DELETE requests.
        Derived implementation from PersistentServerConnectionApplication.

        @param args: A JSON string representing a dictionary of arguments to the REST call
        @type args: string

        @return: A valid REST response
        @type: json
        """
        return self._default_handle(args)

    def _dispatch_to_provider(self, args):
        """
        Parses the REST path on the interface to help route to respective handlers
        This handler's thin layer parses the paths and routes actual handling for the call
        to ItoaCSVInterfaceProviderSplunkd

        @param args: Arguments routed for the REST method
        @type: dict

        @return: Results of the REST method
        @type: dict
        """
        if not isinstance(args, dict):
            message = 'Invalid REST args received by ITOA CSV interface - {}'.format(args)
            raise ItoaValidationError(message=message, logger=logger)
        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']
        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)
        SplunkdRestInterfaceBase.extract_force_delete_header(args, rest_method_args)
        # if data field is included in the request args, no need to extract any payload
        if 'data' not in rest_method_args:
            rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))
        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by ITOA CSV interface - {}'.format(rest_path)
            raise ItoaValidationError(message=message, logger=logger)

        # Double check this is ITOA CSV interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'itoa_csv_interface'):
            raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
        path_parts.pop(0)

        # This is the action name that we need to handle
        action_path = path_parts[0]
        # Don't want to send param 'action' twice to handlers
        rest_method_args.pop("action", None)

        owner = self.extract_request_owner(args, rest_method_args)
        interface_provider = ItoaCSVInterfaceProviderSplunkd(session_key, current_user, rest_method)

        if action_path == 'csv_upload':
            return interface_provider.csv_upload(**rest_method_args)
        elif action_path == 'finalize':
            return interface_provider.finalize(owner, **rest_method_args)
        elif action_path == 'from_search':
            return interface_provider.from_search(**rest_method_args)
        elif action_path == 'service_preview':
            return interface_provider.service_preview(owner, **rest_method_args)
        elif action_path == 'template_preview':
            return interface_provider.template_preview(owner, **rest_method_args)
        elif action_path == 'entity_preview':
            return interface_provider.entity_preview(owner, **rest_method_args)
        elif action_path == 'row_preview':
            return interface_provider.row_preview(owner, **rest_method_args)
        elif action_path == 'csv_lookup_upload':
            return interface_provider.upload_csv_lookup(**rest_method_args)

        raise ITOAError(status=404, message='Specified REST url/path is invalid - {}.'.format(rest_path))
