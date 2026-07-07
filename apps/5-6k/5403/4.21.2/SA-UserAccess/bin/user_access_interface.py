# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.

import sys
import json

from splunk.clilib.bundle_paths import make_splunkhome_path

# SA-UserAccess imports
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib']))
from user_access_utils import UserAccess
from setup_logging import setup_logging
from base_splunkd_rest import BaseSplunkdRest
from user_access_errors import BadRequest, UserAccessError

logger = setup_logging("user_access_interface.log", "useraccess.controllers.useraccess_interface")
LOG_PREFIX = "[SA-UserAccess]"
logger.info("Initialized user access log")

def handle_path_terms(f):
    def wrapper(self, *args, **kwargs):
        '''
        path must one of these values:
        * user_access_interface
        * user_roles
        '''
        if len(self.pathParts) < 3:
            raise UserAccessError(status=404, message=_("Insufficient arguments provided."))
        return f(self, *args, **kwargs)
    return wrapper

def parse_splunkd_payload(f) :
    """
    Decorator to handle application/json content type for splunkd
    rest endpoints

    no-op if content type is not application/json, else
    convert json to a dict and put that dict in the kwargs
    data argument.
    """
    def wrapper(self, *args, **kwargs):
        if 'content-type' in self.request['headers'] and \
                'application/json' in self.request['headers']['content-type']:
            self.request_payload = json.loads(self.request['payload'])

        return f(self, *args, **kwargs)
    return wrapper

class UserAccessInterface(BaseSplunkdRest):

    def __init__(self, method, requestInfo, responseInfo, sessionKey):
        super(UserAccessInterface, self).__init__(method, requestInfo, responseInfo, sessionKey)
        self.request_payload = {}

    def _get_username(self, user):
        # query splunkd for current user OR "user" if that is present
        current_user = self.request.get('userName', None)
        username = user if user is not None else current_user
        if username is None:
            message = 'Expecting a valid username instead of "{}".'.format(username)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(400, message)
        return username

    def _get_user_all_roles(self):
        '''
        This method fetches all the roles of the current user unless a 'user' key is specified.
            payload: key value arguments *optional*
            {
                "user" : <string>
            }
        @return json data
        @raise UserAccessError on Errors
        '''
        data = self.args  # for query params
        if len(self.request_payload) > 0:
            data = self.request_payload
        LOG_PREFIX = '[user_all_roles] '
        username = self._get_username(data.get('user'))
        all_imported_roles = []
        try:
            all_imported_roles = UserAccess.fetch_all_user_roles(username, self.sessionKey, logger)
        except BadRequest as e:
            message = str(e)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        except Exception as e:
            message = 'Exception while polling splunkd for user {}. - {}.'.format(username, str(e))
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=500, message=message)
        return all_imported_roles

    def _get_user_roles(self):
        '''
        This method fetches the roles of the current user unless a 'user' key is specified.
            payload: key value arguments *optional*
            {
                "user" : <string>
            }
        @return json data
        @raise UserAccessError on Errors
        '''
        data = self.args  # for query params
        if len(self.request_payload) > 0:
            data = self.request_payload
        LOG_PREFIX = '[user_roles] '
        username = self._get_username(data.get('user'))
        user_roles = []
        try:
            user_roles = UserAccess.fetch_user_roles(username, self.sessionKey, logger)
        except BadRequest as e:
            message = str(e)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        except Exception as e:
            message = 'Exception while polling splunkd for user {}. - {}.'.format(username, str(e))
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=500, message=message)
        return user_roles

    def _get_user_capabilities(self):
        '''
        This method fetches the capabilities of the current user unless a user is specified
        @param self: the self param
            payload: key value arguments *optional*
            {
                "user":<string>
            }
        '''
        data = self.args  # for query params
        if len(self.request_payload) > 0:
            data = self.request_payload
        LOG_PREFIX = '[user_capabilities] '
        username = self._get_username(data.get('user'))
        user_capabilities = []
        try:
            user_capabilities = UserAccess.fetch_user_capabilities(username, self.sessionKey, logger)
        except BadRequest as e:
            message = str(e)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        except Exception as e:
            message = 'Exception while polling splunkd for user {}. - {}.'.format(username, str(e))
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=500, message=message)
        return user_capabilities

    def _is_user_capable_all_ops(self):
        '''
        This method checks if a user is capable to access a certain ITOA object
        If a 'user' key is present in payload, use that else, work on "current user"
        @param self: The self param
            mandatory keys: 'app_name', 'object_type'
            optional keys: 'user'
            Ex:
            {
                'user': string, # OPTIONAL
                    # username we need to work on
                'owner': string, # OPTIONAL
                    # owner of the object we'd like to use for reference
                'app_name': string, # MANDATORY
                    # app name i.e. itsi, es etc... We will use this as a key against the capability super matrix
                'object_type': string, # MANDATORY
                    # object type under consideration i.e "glass_table", "deep_dive" etc...
            }
        '''
        LOG_PREFIX = '[is_user_capable_all_ops] '

        # check if mandatory keys are present..
        data = self.args # for query params
        if len(self.request_payload) > 0:
            data = self.request_payload
        mandatory_keys = ['app_name', 'object_type']
        for key in mandatory_keys:
            obj = data.get(key)
            if obj is None:
                message = 'Missing mandatory key "{0}" from "{1}".'.format(key, json.dumps(data))
                logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=400, message=message)

        username = self._get_username(data.get('user'))
        session_key = self.sessionKey

        object_type = data.get('object_type')
        app_name = data.get('app_name')
        object_owner = data.get('owner')

        try:
            app_capabilities = json.loads(UserAccess.get_app_capabilities(app_name, session_key, logger))
        except BadRequest as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=400, message=str(e))

        if not app_capabilities:
            message = '{0} has not registered itself yet. Make sure your app calls UserAccess.register_app_capabilities().'.format(
                app_name)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)

        # given object type and requested op, fetch capability name
        capabilities_names, message = UserAccess.fetch_capabilities_names_all_ops(app_capabilities, object_type,
                                                                                  logger)
        if capabilities_names is None:
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        try:
            capabilities = UserAccess.is_user_capable_all_ops(username, object_type, capabilities_names,
                                                              session_key, logger, owner=object_owner)
        except BadRequest as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=400, message=str(e))
        except Exception as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=500, message=str(e))
        render_msg = {
            'username': username,
            'permissions': {
                'read': True,
                'write': True,
                'delete': True
            },
            'object_type': object_type,
            'message': 'User "{0}" capabilities on objects of type "{1}".'.format(username, object_type)
        }
        if not capabilities['read']:
            render_msg['permissions']['read'] = False
        if not capabilities['write']:
            render_msg['permissions']['write'] = False
        if not capabilities['delete']:
            render_msg['permissions']['delete'] = False

        return render_msg

    def is_user_capable(self):
        '''
        This method checks if a user is capable to access a certain ITOA object
        If a 'user' key is present in payload, use that else, work on "current user"
        @param self: The self param
            mandatory keys: 'app_name', 'operation', 'object_type'
            optional keys: 'user'
            Ex:
            {
                'user': string, # OPTIONAL
                    # username we need to work on
                'owner': string, # OPTIONAL
                    # owner of the object we'd like to use for reference
                'app_name': string, # MANDATORY
                    # app name i.e. itsi, es etc... We will use this as a key against the capability super matrix
                'object_type': string, # MANDATORY
                    # object type under consideration i.e "glass_table", "deep_dive" etc...
                'operation': string # MANDATORY
                    # 'read/write'/'delete'
            }
        '''
        LOG_PREFIX = '[is_user_capable] '

        # check if mandatory keys are present..
        data = self.args  # for query params
        if len(self.request_payload) > 0:
            data = self.request_payload
        mandatory_keys = ['app_name', 'object_type', 'operation']
        for key in mandatory_keys:
            obj = data.get(key)
            if obj is None:
                message = 'Missing mandatory key "{0}" from "{1}".'.format(key, json.dumps(data))
                logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=400, message=message)

        username = self._get_username(data.get('user'))
        session_key = self.sessionKey

        object_type = data.get('object_type')
        operation = data.get('operation')
        app_name = data.get('app_name')
        object_owner = data.get('owner')

        try:
            app_capabilities = json.loads(UserAccess.get_app_capabilities(app_name, session_key, logger))
        except BadRequest as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=400, message=str(e))

        if not app_capabilities:
            message = '{0} has not registered itself yet. Make sure your app calls UserAccess.register_app_capabilities().'.format(
                app_name)
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)

        # given object type and requested op, fetch capability name
        capability_name, message = UserAccess.fetch_capability_name(app_capabilities, object_type, operation,
                                                                    logger)
        if capability_name is None:
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        try:
            user_is_capable = UserAccess.is_user_capable(username, capability_name, session_key, logger,
                                                         owner=object_owner)
        except BadRequest as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=400, message=str(e))
        except Exception as e:
            logger.error('%s %s', LOG_PREFIX, str(e))
            raise UserAccessError(status=500, message=str(e))
        render_msg = {
            'username': username,
            'is_capable': True,
            'operation': operation,
            'object_type': object_type,
            'message': 'User "{0}" has the capability "{1}" on object type "{2}".'.format(username, operation,
                                                                                          object_type)
        }
        if user_is_capable:
            render_msg['is_capable'] = True
            render_msg['message'] = 'User "{0}" has the capability "{1}" on object type "{2}".'.format(username,
                                                                                                       operation,
                                                                                                       object_type)
        else:
            message = 'User "{0}" does not have the capability "{1}" on object type "{2}".'.format(username,
                                                                                                   operation,
                                                                                                   object_type)
            render_msg['is_capable'] = False
            render_msg['message'] = message

        return render_msg

    """
    Provides splunkd endpoints for deep dive operations
    """

    @handle_path_terms
    def handle_GET(self):

        if self.pathParts[2] == 'user_all_roles':
            user_roles = self._get_user_all_roles()
            return self.response.write(self.render_json(user_roles))

        if self.pathParts[2] == 'user_roles':
            user_roles = self._get_user_roles()
            return self.response.write(self.render_json(user_roles))

        if self.pathParts[2] == 'user_capabilities':
            user_capabilities = self._get_user_capabilities()
            return self.response.write(self.render_json(user_capabilities))

        if self.pathParts[2] == 'is_user_capable_all_ops':
            render_msg = self._is_user_capable_all_ops()
            return self.response.write(self.render_json(render_msg))

        if self.pathParts[2] == 'is_user_capable':
            render_msg = self.is_user_capable()
            return self.response.write(self.render_json(render_msg))

    @parse_splunkd_payload
    @handle_path_terms
    def handle_POST(self):

        if self.pathParts[2] == 'user_roles':
            user_roles = self._get_user_roles()
            return self.response.write(self.render_json(user_roles))

        if self.pathParts[2] == 'user_capabilities':
            user_capabilities = self._get_user_capabilities()
            return self.response.write(self.render_json(user_capabilities))

        if self.pathParts[2] == 'is_user_capable_all_ops':
            render_msg = self._is_user_capable_all_ops()
            return self.response.write(self.render_json(render_msg))

        if self.pathParts[2] == 'is_user_capable':
            render_msg = self.is_user_capable()
            return self.response.write(self.render_json(render_msg))