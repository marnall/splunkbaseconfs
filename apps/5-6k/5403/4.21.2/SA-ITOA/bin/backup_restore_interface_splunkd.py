# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import base64

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import CheckUserAccess

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
import itsi_py3

from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, ItoaValidationError
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase
from itsi.backup_restore.backup_restore_rest_provider import BackupRestoreRestProvider
from itsi.itsi_utils import CAPABILITY_MATRIX, ITOAInterfaceUtils

logger = getLogger()
logger.debug("Initialized Backup/Restore REST splunkd handler interface log")


class BackupRestoreInterfaceProviderSplunkd(BackupRestoreRestProvider):
    """
    This wrapper class for the REST provider in BackupRestoreRestProvider which
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

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def bulk_crud(self, owner, object_type, **kwargs):
        """
        Routes CRUD operations on objects

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of backup/restore object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the REST method results
        """
        return self._bulk_crud(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def crud_by_id(self, owner, object_type, object_id, **kwargs):
        """
        Routes CRUD operations per object

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of backup/restore object

        @type: string
        @param object_id: id of backup/restore object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the results of the REST method
        """
        return self._crud_by_id(owner, object_type, object_id, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def get_objects_count(self, owner, object_type, **kwargs):
        """
        Gets count of objects with filters applied

        @type: object
        @param self: the self reference

        @type: string
        @param owner: owner making the request

        @type: string
        @param object_type: type of backup/restore object

        @type: dict
        @param **kwargs: key word arguments extracted from request

        @rtype: json
        @return: json of the count of objects
        """
        return self._get_object_count(owner, object_type, **kwargs)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def file_ops(self, owner, object_type, object_id, **kwargs):
        """
        @type owner: basestring
        @param owner: owner who is performing this operation

        @type object_type: basestring
        @param object_type: Target action type

        @type object_id: basestring
        @param object_id: file identifier

        @return: file contents (for GET), text (for POST)
        @rtype: binary
        """
        return self._file_ops(owner, object_type, object_id, **kwargs)

    def preview(self, fileloc, include_conf_files=False):
        """
        Generate a preview of the of backup, optionally including
        configuration files.

        @type fileloc: str
        @param fileloc: The file location of backup.

        @type include_conf_files: boolean (optional)
        @param include_conf_files: If True, include configuration files in the preview. Defaults to False.

        @rtype: str
        @return: A json formatted preview of the contents present in the backup file.
        """
        return self._preview(fileloc, include_conf_files)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='backup_restore', logger=logger)
    def get_backup_preview(self, owner, include_conf_files=False, include_other_app_conf_files=False):
        """
        Generate a preview of the environment with objects to include in the backup.

        @type owner: basestring
        @param owner: owner who is performing this operation

        @type object_type: basestring
        @param object_type: Target action type

        @rtype: str
        @return: A json formatted missing objects found in the backup file.
        """
        return self._get_backup_preview(owner, include_conf_files, include_other_app_conf_files)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type='backup_restore', logger=logger)
    def get_splunk_objects(self, owner, object_category, is_partial_backup, include_conf_files, include_other_app_conf_files):
        """
        Generate a preview of the splunk objects that will be include in the backup.

        @type owner: basestring
        @param owner: owner who is performing this operation

        @type object_category: string
        @param object_category: object type of which objects need to fetch

        @rtype: str
        @return: A json formatted splunk objects that will be part of the backup file.
        """
        return self._get_splunk_objects(owner, object_category, is_partial_backup, include_conf_files, include_other_app_conf_files)

    def get_missing_objects(self, fileloc, include_conf_files=False):
        """
        Retrieve a list of missing objects based on the provided file location.

        @type fileloc: str
        @param fileloc: The file location to check for missing objects in backup.

        @type include_conf_files: boolean (optional)
        @param include_conf_files: If True, include configuration files in the
            search for missing objects. Defaults to False.

        @rtype: str
        @return: A json formatted missing objects found in the backup file.
        """
        return self._get_missing_objects(fileloc, include_conf_files)

    @CheckUserAccess(capability_matrix=CAPABILITY_MATRIX, object_type=None, logger=logger)
    def migration_ops(self, owner, object_type, **kwargs):
        return self._migration_ops(owner, object_type, **kwargs)

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


class BackupRestoreInterfaceSplunkd(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):
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
        super(BackupRestoreInterfaceSplunkd, self).__init__()

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
        to BackupRestoreInterfaceProviderSplunkd

        @type: dict
        @param args: the args routed for the REST method

        @rtype: dict
        @return: results of the REST method
        """
        if not isinstance(args, dict):
            message = 'Invalid REST args received by backup restore interface - {}.'.format(args)
            raise ItoaValidationError(message=message,
                                      logger=logger,
                                      uid='SI-BR_0029',
                                      context={
                                          'args': args
                                      })
        session_key = args['session']['authtoken']
        current_user = args['session']['user']
        rest_method = args['method']
        include_conf_files = [value.lower() == 'true' for key, value in args['query'] if key == 'include_conf_files']
        include_other_app_conf_files = [value.lower() == 'true' for key, value in args['query'] if key == 'include_other_app_conf_files']
        object_category = next((value for key, value in args['query'] if key == 'object_category'), None)
        is_partial_backup = [value.lower() == 'true' for key, value in args['query'] if key == 'is_partial_backup']

        rest_method_args = {}
        SplunkdRestInterfaceBase.extract_rest_args(args, 'query', rest_method_args)

        rest_method_args.update(SplunkdRestInterfaceBase.extract_data_payload(args))
        interface_provider = BackupRestoreInterfaceProviderSplunkd(session_key, current_user, rest_method)
        rest_path = args['rest_path']
        if not isinstance(rest_path, itsi_py3.string_type):
            message = 'Invalid REST path received by backup restore interface - {}.'.format(rest_path)
            raise ItoaValidationError(message=message,
                                      logger=logger,
                                      uid='SI-BR_0030',
                                      context={
                                          'path': rest_path
                                      })

        # Double check this is maintenance services interface path
        path_parts = rest_path.strip().strip('/').split('/')
        if (not isinstance(path_parts, list)) or (len(path_parts) < 2) or (path_parts[0] != 'backup_restore_interface'):
            raise ITOAError(status=404,
                            message='Specified REST URL/path is invalid - {}.'.format(rest_path),
                            uid='SI-BR_0031',
                            context={
                                'path': rest_path
                            })
        path_parts.pop(0)

        # Version check the API. It should be in the second part of URL if specified. Samples:
        # /backup_restore_interface/vLatest/... where vLatest implies latest ITSI version
        # /backup_restore_interface/<Latest ITSI version>/...
        # Currently only latest version of ITSI is supported for all APIs
        if len(path_parts) < 1:
            raise ITOAError(status=404,
                            message='Specified REST URL/path is invalid - {}.'.format(rest_path),
                            uid='SI-BR_0031',
                            context={
                                'path': rest_path
                            })

        if path_parts[0] in ['vLatest', 'v' + ITOAInterfaceUtils.get_app_version(session_key, app='itsi')]:
            path_parts.pop(0)

        if len(path_parts) < 1:
            raise ITOAError(status=404,
                            message='Specified REST URL/path is invalid - {}.'.format(rest_path),
                            uid='SI-BR_0031',
                            context={
                                'path': rest_path
                            })

        first_path_part = path_parts[0]
        if first_path_part in interface_provider.SUPPORTED_OBJECT_TYPES:
            owner = self.extract_request_owner(args, rest_method_args)

            object_type = first_path_part
            if object_type in interface_provider.SUPPORTED_OBJECT_TYPES_FOR_CRUD:
                if len(path_parts) == 1:
                    return interface_provider.bulk_crud(owner, object_type, **rest_method_args)
                elif len(path_parts) == 2:
                    if path_parts[1] == 'count':
                        return interface_provider.get_objects_count(owner, object_type, **rest_method_args)
                    elif path_parts[1] == 'backup_preview':
                        return interface_provider.get_backup_preview(owner, include_conf_files[0], include_other_app_conf_files[0])
                    elif path_parts[1] == 'get_splunk_objects':
                        if object_category is None:
                            message = 'Invalid REST path received by backup restore interface - {}.'.format(rest_path)
                            raise ItoaValidationError(
                                message=message,
                                logger=logger,
                                uid='SI-BR_0030',
                                context={'path': rest_path})
                        return interface_provider.get_splunk_objects(owner, object_category, is_partial_backup[0], include_conf_files[0], include_other_app_conf_files[0])
                    else:
                        # Path is for object CRUD by id
                        object_id = path_parts[1]
                        return interface_provider.crud_by_id(owner, object_type, object_id, **rest_method_args)
                elif len(path_parts) == 3:
                    if path_parts[1] == 'preview':
                        filename = path_parts[2] + '.zip'
                        fileloc = make_splunkhome_path(['var', 'itsi', 'backups', filename])
                        return interface_provider.preview(fileloc, include_conf_files[0])
                    elif path_parts[1] == 'missing_objects':
                        filename = path_parts[2] + '.zip'
                        fileloc = make_splunkhome_path(['var', 'itsi', 'backups', filename])
                        missing_objects = interface_provider.get_missing_objects(fileloc, include_conf_files[0])
                        missing_objects_json = json.loads(missing_objects)
                        if missing_objects_json["macros"]["count"] != 0 or missing_objects_json["savedsearches"]["count"] != 0:
                            logger.info('For the backup with preview id: {} found missing splunk knowledge objects: {}'.format(filename, missing_objects_json))
                        return missing_objects

            # if not a CRUD object, then this must be a file operation
            elif object_type == 'files':
                object_id = path_parts[1]
                return interface_provider.file_ops(owner, object_type, object_id, **rest_method_args)
            elif object_type == 'migration':
                migration_args = json.loads(base64.b64decode(args.get('payload_base64')))
                return interface_provider.migration_ops(owner, object_type, **migration_args)
        # No takers so far implies REST path is crazy, error out
        raise ITOAError(status=404,
                        message='Specified REST url/path is invalid - {}.'.format(rest_path),
                        uid='SI-BR_0031',
                        context={
                            'path': rest_path
                        })
