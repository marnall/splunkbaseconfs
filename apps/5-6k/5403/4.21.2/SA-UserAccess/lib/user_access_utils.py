# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
from copy import deepcopy
import sys

if sys.version_info >= (3, 0):
    string_types = str
else:
    string_types = basestring

import json
from uuid import uuid1

# Splunk Core imports
import splunk.rest as rest
from splunk import ResourceNotFound
from splunk.auth import getCurrentUser

# other imports
from user_access_kvstore import KvStoreHandler
from user_access_errors import BadRequest, UserAccessError

# KV Store Collections managed by us
CAPABILITIES_STORE = 'app_capabilities'
ACL_STORE = 'app_acl'
DEFAULT_OWNER = 'nobody'
KV_INITIALIZING = 'KV Store is initializing'


###### Utility methods
######

def intersects(l1, l2):
    '''
    do l1 and l2 intersect?

    @type l1 : list
    @param l1 : list obj

    @type l2: list
    @param l2: other list obj

    @rtype: boolean
    @return True if they intersect, False otherwise
    '''
    intersection = 0

    if not any([isinstance(l1, list), isinstance(l2, list)]):
        return False

    if len(l1) >= len(l2):
        intersection = set(l1).intersection(l2)
    else:
        intersection = set(l2).intersection(l1)
    return len(intersection) > 0


def uber_str_to_list(str_obj, separator=',', dedup=True, strip_spaces=True):
    '''
    Given a string/comma separated string,
        - convert it to a list of strings.
        - dedup
        - strip spaces
        - remove empty strings

    @type str_obj: string
    @param str_obj: string or comma separated string

    @type separator: string
    @param separator: character separating our sub-strings in a string.
        Defaults to `,` comma

    @type dedup: boolean
    @param dedup: does the caller want us to dedup string values in the list?
        defaults to True

    @type strip_spaces: boolean
    @param strip_spaces: does the caller want to strip spaces?
        defaults to True

    @rtype rval: list
    @return rval: list of strings
    '''
    rval = []

    if isinstance(str_obj, string_types):
        rval = str_obj.split(separator)
    elif isinstance(str_obj, list):
        rval = str_obj
    else:
        raise BadRequest(('Expecting input of type string or list and not of'
                          'type: {}').format(type(str_obj).__name__))

    if strip_spaces:
        temp = deepcopy(rval)
        for i, v in enumerate(temp):
            if len(v.strip()) == 0:
                rval.remove(v)
            else:
                rval[i] = v.strip()

    if dedup:
        rval = list(set(rval))

    return rval


def is_valid_str(obj):
    '''
    Return true if obj is a str type object with a len > 0; excludes LWS
    '''
    if isinstance(obj, string_types) and len(obj.strip()) > 0:
        return True
    return False


###### Single pattern enforcer decorator
######
class Singleton(object):
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.
    The decorated class can define an `__init__` function

    To get the singleton instance, use the `getInstance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    Limitations: The decorated class cannot be inherited from itself.

    Note: This class is repeated in SA-ITOA.
    """

    def __init__(self, decorated):
        self._decorated = decorated

    def __call__(self):
        raise TypeError('Use `getInstance()` to access the Singleton')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)

    def getInstance(self, **kwargs):
        """
        returns the singleton instance of the decorated object.
        When called first, call the init method of the decorated object
        Thereafter, return the object that was created first.
        """
        try:
            if hasattr(self._instance, 'update_singleton'):
                self._instance.update_singleton(**kwargs)
            return self._instance
        except AttributeError:
            self._instance = self._decorated(**kwargs)
            return self._instance


@Singleton
class UserAccessStore(object):
    """
    Utility Class whose object can be used to read/write objects from KVStore
    Use the `getInstance()` method on this class to obtain an instance of
    UserAccessStore
    Ex: ua_store = UserAccessStore.getInstance()
    """

    def __init__(self, app_name='SA-UserAccess', ns=DEFAULT_OWNER):
        self.options = {
            'app': app_name,
            'owner': ns
        }
        self.kv = KvStoreHandler()

        # supported operations
        self._op_read = 'read'
        self._op_create = 'create'
        self._op_update = 'update'
        self._op_delete = 'delete'
        self.operations = [self._op_read, self._op_create,
                           self._op_update, self._op_delete]

    def update_singleton(self, **kwargs):
        """
        Update the Singleton version of UserAccessStore with different parameters. This is required because
        UserAccessStore fetches based on `self.options` which differs in each call.

        pwu: To be honest, I don't know why this was designed like this in the first place (the change is from 2016, and
        it's not explained in the ticket or pull request). The old method was working due to a Splunk bug where the
        namespace of apps isn't respected for collections. update_singleton() is probably safer than undoing the
        Singleton nature of these objects though.
        """
        for param, field in [('app_name', 'app'), ('ns', 'owner')]:
            new_value = kwargs.get(param)
            if new_value:
                self.options[field] = new_value

    def is_op_read(self, operation):
        '''
        @type operation: str
        @param operation: intended operation
        '''
        return operation.strip().lower() == self.op_read()

    def is_op_create(self, operation):
        '''
        @type operation: str
        @param operation: intended operation
        '''
        return operation.strip().lower() == self.op_create()

    def is_op_update(self, operation):
        '''
        @type operation: str
        @param operation: intended operation
        '''
        return operation.strip().lower() == self.op_update()

    def is_op_delete(self, operation):
        '''
        @type operation: str
        @param operation: intended operation
        '''
        return operation.strip().lower() == self.op_delete()

    def op_read(self):
        '''
        @rtype: str
        @return str corresponding to read operation
        '''
        return self._op_read

    def op_create(self):
        '''
        @rtype: str
        @return str corresponding to create operation
        '''
        return self._op_create

    def op_update(self):
        '''
        @rtype: str
        @return str corresponding to update operation
        '''
        return self._op_update

    def op_delete(self):
        '''
        @rtype: str
        @return str corresponding to delete operation
        '''
        return self._op_delete

    def _make_query_from_dict(self, query_as_dict, query_type='and'):
        '''
        Make a Store query given a dict. Defaults to an $and type query
        @type query_as_dict: dict
        @param query_as_dict: dictionary to consume for our query

        @type query_type: string
        @param query_type: type of query. `or` / `and` etc...

        @rtype dict
        @return KV Store query
        '''
        query = []
        for k, v in query_as_dict.items():
            query.append({k: v})
        return {"${0}".format(query_type): query}

    def _make_query_from_list(self, query_as_list, field_name='_key', query_type='or'):
        '''
        Make a store query given a list. Defaults to an $or type query
        @type query_as_list: list
        @param query_as_list: ids to build a query with

        @type field_name: str
        @param field_name: field_name to use for our query

        @type query_type: string
        @param query_type: type of query. Either `or` OR `and`

        @rtype dict
        @return KV Store query
        '''
        return {"${0}".format(query_type): [{field_name: i} for i in
                                            query_as_list]}

    def _make_query(self, query, field_name='_key'):
        '''
        Make a Query which can be consumed by our Store
        '''
        if isinstance(query, list):
            return self._make_query_from_list(query, field_name=field_name)
        elif isinstance(query, dict):
            return self._make_query_from_dict(query)
        else:
            return query

    def _generate_response(self, response, content, logger, log_prefix, operation):
        '''
        method that generates a tuple for a response

        @type response: str
        @param response: REST response

        @type content: str
        @param content: response content

        @type logger: logger
        @param logger: caller's logger object

        @type log_prefix: str
        @param log_prefix: caller's prefix str for tracking

        @type operation: str
        @param operation: desired operation from which we deduce response.status

        @rtype: tuple (boolean, str)
        @return (True, content) if success
        (False, error message) if failure
        '''
        success = False
        if operation not in self.operations:
            raise BadRequest('Supported operations are: {}. Received: {}'.format(
                self.operations, operation))

        if any([
            self.is_op_read(operation) and response.status != 200,
            self.is_op_create(operation) and response.status != 201,
            self.is_op_update(operation) and response.status not in [200, 201],
            self.is_op_delete(operation) and response.status not in [200, 202, 204]
        ]):
            message = 'Response: {} Content: {}'.format(
                response, content)
            # If the operation failed due to the KV Store not being initialized yet, this is NOT an error.
            if KV_INITIALIZING in content:
                logger.warn('Failed for now. %s %s', log_prefix, message)
            else:
                logger.error('Failed. %s %s', log_prefix, message)
        else:
            message = 'Success. Content: "{}"'.format(content)
            logger.debug('%s %s', log_prefix, message)
            success = True
        return success, content

    def read(self, store_name, record_id, session_key, logger):
        '''
        Read a record from a UserAccess Store.

        @type store_name: string
        @param store_name: String Indicating name of the Store to access

        @type record_id: string
        @param record_id: ID of the record you wish to read

        @type session_key: string
        @param session_key: Splunkd session key

        @type logger: logger object
        @param logger: Caller's logger

        @rtype: tuple (bool, str)
        @return (True, content) on success
            (False, error str) on Failure
            Empty record if nothing is found or error.
        '''
        LOG_PREFIX = '[UserAccessStore][read] '

        content = ''
        success = False

        logger.debug('%s record_id: %s', LOG_PREFIX, record_id)
        try:
            self.options['collection'] = store_name
            response, content = self.kv.get(record_id, session_key,
                                            self.options)
        except Exception as e:
            failed = ('Unable to find record_id "{0}". ').format(record_id)
            logger.error('%s %s.', LOG_PREFIX, failed)
            logger.exception(e)
            content = failed + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_read())

    def bulk_read(self, store_name, object_ids, session_key, logger,
                  field_name='_key'):
        '''
        Wrapper to make a query on a UserAccess Store. bulk read object ids.
        @type store_name: string
        @param store_name: String indicating name of Store to access

        @type object_ids: list
        @param object_ids: list of `object_id`s from the app_acl store

        @type session_key: string
        @param session_key: splunkd session key

        @type logger: logger object
        @param logger: caller's logger

        @type field_name: str
        @param field_name: field name in record that corresponds to object_ids
        ex: _key or title etc...

        @rtype: tuple (boolean, str)
        @return (True, content) on success
            (False, failure string) on failure
        '''
        LOG_PREFIX = '[UserAccessStore][bulk_read] '
        query = self._make_query(object_ids, field_name=field_name)
        success = False
        content = ''

        logger.debug('%s record_ids: %s\n store_name: %s field_name for query: %s',
                     LOG_PREFIX, object_ids, store_name, field_name)
        try:
            self.options['collection'] = store_name
            response, content = self.kv.query(query, session_key, self.options)
        except Exception as e:
            failed = ('Unable to issue query. record IDs: {0}. ').format(object_ids)
            logger.error('%s {0}. Issued query: {1}'.format(failed, query), LOG_PREFIX)
            logger.exception(e)
            content = failed + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_read())

    def query(self, store_name, session_key, logger, **query_params):
        '''
        Wrapper to make a UserAccess Store query using input query_params
        '''
        LOG_PREFIX = '[UserAccessStore][query] '

        query = self._make_query(query_params)
        success = False
        logger.debug('%s query: %s store_name: %s', LOG_PREFIX, query, store_name)

        try:
            self.options['collection'] = store_name
            response, content = self.kv.query(query, session_key, self.options)
        except Exception as e:
            failed = ('Unable to find records matching query: "{0}".').format(query)
            logger.error('%s %s', LOG_PREFIX, failed)
            logger.exception(e)
            content = failed + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_read())

    def create(self, store_name, record, session_key, logger, record_id=None):
        '''
        Wrapper to write to a UserAccess Store
        @type store_name: string
        @param store_name: String Indicating name of the Store to access

        @type record: dict
        @param record: dictionary indicating record to write

        @type record_id: string
        @param record_id: an ID for this record

        @rtype: tuple of bool & string
        @return (True, content string) if success; (False, message) otherwise
        '''
        LOG_PREFIX = '[UserAccessStore][write] '
        success = False
        content = ''

        record_id = record_id if record_id else str(uuid1())
        logger.debug('%s record_id: %s store_name: %s record: %s', LOG_PREFIX, record_id, store_name, record)
        try:
            self.options['collection'] = store_name
            response, content = self.kv.create(record, record_id, session_key, self.options)
        except Exception as e:
            message = 'Unable to persist record "{0}" in store "{1}". '.format(record, store_name)
            logger.error('%s %s. Exception occurred.', LOG_PREFIX, message)
            logger.exception(e)
            content = message + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_create())

    def single_update(self, store_name, record, session_key, logger, record_id=None):
        '''
        Wrapper to write to a UserAccess Store
        @type store_name: string
        @param store_name: String Indicating name of the Store to access

        @type record: dict
        @param record: dictionary indicating record to write

        @type record_id: string
        @param record_id: an ID for this record

        @rtype: tuple of bool & string
        @return (True, content string) if success; (False, empty string) otherwise
        '''
        LOG_PREFIX = '[UserAccessStore][single_update] '
        success = False
        content = ''

        if not record_id:
            if not record.get('_key'):
                record_id = record_id if record_id else str(uuid1())
            else:
                record_id = record.get('_key')

        logger.debug('%s record_id: %s record: %s store_name: %s',
                     LOG_PREFIX, record_id, record, store_name)
        try:
            self.options['collection'] = store_name
            response, content = self.kv.single_update(record, record_id, session_key, self.options)
        except Exception as e:
            failed = ('Unable to persist record "{0}" in store "{1}".').format(
                record, store_name)
            logger.error('%s %s.', LOG_PREFIX, failed)
            logger.exception(e)
            content = failed + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_update())

    def bulk_update(self, store_name, records, session_key, logger):
        '''
        Wrapper to bulk update to a UserAccess Store
        if a record does not have a '_key' key, kv store will
            create a new record. else it'll try to write to existing record

        @type store_name: str
        @param store_name: name of the UserAccess Store

        @type records: list
        @param records: records to commit

        @type session_key: str
        @param session_key: splunkd session key

        @type logger: logger
        @param logger: caller's logger

        @rtype tuple (bool, str)
        @return (True, committed content keys) on success
            (False, pertinent str) on failure
        @raise BadRequest on malformed request
        '''
        LOG_PREFIX = '[UserAccessStore][bulk_update] '
        success = False
        content = ''

        if not isinstance(records, list):
            raise BadRequest('Expecting `records` to be a list and not {}.'.format(type(records).__name__))

        logger.debug('%s records: %s\nstore_name: %s', LOG_PREFIX, records, store_name)
        try:
            self.options['collection'] = store_name
            response, content = self.kv.batch_create(records,
                                                     session_key, self.options)
        except Exception as e:
            failed = ('Unable to persist records in store `{}`.'
                      ' records: `{}`').format(store_name, records)
            logger.error(LOG_PREFIX + failed)
            logger.exception(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_update())

    def delete(self, store_name, session_key, logger, record_id=None,
               query_params=None):
        '''
        delete a record. record_id or query is mandatory

        @type store_name: string
        @param store_name: name of the store to delete from

        @type record_id: string
        @param record_id: ID of the record to delete

        @type session_key: string
        @param session_key: Splunkd session_key

        @type logger: logger object
        @param logger: Logger object of caller

        @rtype: tuple (boolean, str)
        @return (True, content) if success
            (False, content) otherwise
        '''
        LOG_PREFIX = '[UserAccessStore][delete] '
        success = False
        content = ''

        if not record_id and not query_params:
            raise BadRequest('Expecting either `record_id` or `query`. Both are None')

        try:
            self.options['collection'] = store_name
            if record_id:
                response, content = self.kv.delete(record_id, session_key,
                                                   self.options)
            else:
                query = self._make_query(query_params)
                response, content = self.kv.query(query, session_key,
                                                  self.options, delete=True)
        except Exception as e:
            failed = ('Unable to delete record for ID "{0}" from'
                      ' store "{1}". ').format(record_id, store_name)
            logger.error('%s %s. Exception occurred.', LOG_PREFIX, failed)
            logger.exception(e)
            content = failed + str(e)
            return success, content

        return self._generate_response(response, content, logger, LOG_PREFIX, self.op_delete())


class ACL(object):
    '''
    An instance of this class represents an ACL for an App object
    '''
    STORE_KEY_OBJ_ID = 'obj_id'
    STORE_KEY_OBJ_TYPE = 'obj_type'
    STORE_KEY_OBJ_APP = 'obj_app'
    STORE_KEY_OBJ_STORE = 'obj_storename'
    STORE_KEY_OBJ_SHARED_BY_INCLUSION = 'obj_shared_by_inclusion'
    STORE_KEY_OBJ_OWNER = 'obj_owner'
    STORE_KEY_OBJ_ACL = 'obj_acl'
    STORE_KEY_OBJ_ACL_READ = 'read'
    STORE_KEY_OBJ_ACL_WRITE = 'write'
    STORE_KEY_OBJ_ACL_DELETE = 'delete'
    STORE_KEY_ACL_ID = 'acl_id'
    STORE_KEY_ACL_OWNER = 'acl_owner'
    STORE_KEY_ACL_KEY = '_key'
    SUPPORTED_OPERATIONS = [STORE_KEY_OBJ_ACL_READ, STORE_KEY_OBJ_ACL_WRITE,
                            STORE_KEY_OBJ_ACL_DELETE]
    PERMS_ALLOW_ALL = '*'

    @staticmethod
    def _validate(object_id, object_app, object_storename, object_type, object_owner):
        '''
        incoming params must be str.

        @type object_id: str
        @param object_id:  object id

        @type object_app: str
        @param object_app: app to which the object belongs to

        @type object_storename: str
        @param object_storename: store inside the app to which object belongs to

        @type object_type: str
        @param object_type: type of the object. ex: service

        @type object_owner: str
        @param object_owner: owner of this object

        @return nothing
        @raise BadRequest if invalid
        '''
        if not all([
            is_valid_str(object_id),
            is_valid_str(object_app),
            is_valid_str(object_storename),
            is_valid_str(object_type),
            is_valid_str(object_owner)
        ]):
            raise BadRequest(('Expecting object_id, object_app, object_storename'
                              'object_type and object_owner to be non-empty str types'))

    @staticmethod
    def get_default_acl_blob():
        '''return a dict of default perms
        @returns a valid dict
        '''
        return {
            'read': ['*'],
            'write': ['*'],
            'delete': ['*']
        }

    @staticmethod
    def _validate_acl_blob(acl):
        '''
        Validate the structure of the ACL blob
        @type acl: dict
        @param acl: expected acl is to look as follows:
        {
            'read': [],
            'write': [],
            'delete': []

        }
        @return nothing
        @raise BadRequest if invalid structure
        '''
        usage = ('Expecting ACL to be a dict and contain the following keys:\n'
                 'read : a list of roles\n'
                 'write: a list of roles\n'
                 'delete: a list of roles\n')
        if not all([
            isinstance(acl, dict),
            isinstance(acl.get(ACL.STORE_KEY_OBJ_ACL_READ), list),
            isinstance(acl.get(ACL.STORE_KEY_OBJ_ACL_WRITE), list),
            isinstance(acl.get(ACL.STORE_KEY_OBJ_ACL_DELETE), list)
        ]):
            raise BadRequest('Invalid format of ACL. {}'.format(usage))

    @staticmethod
    def _add_inherited_roles(acl, roles):
        '''
        Add the inherited roles to the lists in the ACL blob
        @type acl: dict
        @param acl: expected acl is to look as follows:
        {
            'read': [],
            'write': [],
            'delete': []

        }
        @return nothing
        '''

        def expand(list, roles):
            '''
            Expand the list by adding its descendant in the role inheritance graph
            @type list: list of roles
            @param list: the input roles list to be expanded.

            @type roles: dict
            @param roles: key is the role name, value is a set of roles that directly inherited from this role.

            @returns list with expanded roles.
            '''

            queue = []
            queue.extend(list)
            expanded_roles = set()
            while len(queue) > 0:
                item = queue.pop(0)
                expanded_roles.add(item)
                if item in roles:
                    for r in roles[item]:
                        if r not in expanded_roles:
                            queue.append(r)
            return expanded_roles

        converted_roles = {}
        for role, role_list in roles.items():
            for r in role_list:
                if r in converted_roles:
                    converted_roles[r].add(role)
                else:
                    converted_roles[r] = {role}

        acl[ACL.STORE_KEY_OBJ_ACL_READ] = list(expand(acl[ACL.STORE_KEY_OBJ_ACL_READ], converted_roles))
        acl[ACL.STORE_KEY_OBJ_ACL_WRITE] = list(expand(acl[ACL.STORE_KEY_OBJ_ACL_WRITE], converted_roles))
        acl[ACL.STORE_KEY_OBJ_ACL_DELETE] = list(expand(acl[ACL.STORE_KEY_OBJ_ACL_DELETE], converted_roles))

    @staticmethod
    def object_shared_by_inclusion(acl_record):
        '''
        Given an ACL record, check if its corresponding object is shared by
        inclusion
        @type acl_record: dict
        @param acl_record: acl blob to inspect

        @rtype boolean
        @return True if `object is shared by inclusion`. False otherwise
        '''
        if not isinstance(acl_record, dict):
            raise BadRequest(('Expecting ACL record to be a dictionary and not '
                              '{}.').format(type(acl_record).__name__))
        return acl_record.get(ACL.STORE_KEY_OBJ_SHARED_BY_INCLUSION) is True

    @staticmethod
    def roles_in_acl(roles, acl_as_list):
        '''
        given a list of roles and an ACL list corresponding to
        one of SUPPORTED_OPERATIONS, check if one of the values in
        `roles` is in `acl_as_list`
        @type roles: list
        @param roles: list of roles to check for

        @type acl_as_list: list
        @param acl_as_list: ACL list to check against

        @rtype: boolean
        @return return True if acl_as_list contains PERMS_ALLOW_ALL
        '''
        if ACL.PERMS_ALLOW_ALL in acl_as_list:
            return True
        return intersects(roles, acl_as_list)

    @staticmethod
    def bulk_update(acl_records, session_key, logger, acl_owner=DEFAULT_OWNER):
        '''
        Given a list of ACL records to commit, commit them all.
        Here as a staticmethod because, it works on a list of ACL records.
        Caller's responsibility to ensure that each ACL record is the
        output of _make_record()

        @type acl_records: list
        @param acl_records: list of ACL records to commit

        @type session_key: str
        @param session_key: splunkd session_key

        @type logger: logger
        @param logger: caller's logger object

        @type acl_owner: str
        @param acl_owner: owner of ACL in store

        @rtype tuple (boolean, str)
        @return (True, written content) on success
            (False, error message) on failure
        '''

        store = UserAccessStore.getInstance(app_name='SA-UserAccess', ns=acl_owner)
        return store.bulk_update(ACL_STORE, acl_records, session_key, logger)

    def __init__(self,
                 object_id,
                 object_app,
                 object_storename,
                 object_type,
                 object_owner,
                 session_key,
                 logger,
                 read=['*'],
                 write=['*'],
                 delete=['*'],
                 object_shared_by_inclusion=True,
                 acl_owner=DEFAULT_OWNER,
                 acl_id=None
                 ):
        '''
        The `__init__` method for this class
        @type object_id: string
        @param object_id: ID of the object

        @type object_app: string
        @param object_app: owner app of this object. ex: itsi

        @type object_storename: string
        @param object_storename: store where this object is originally stored.
            ex: itsi_pages

        @type object_type: string
        @param object_type: type of the object. ex: glass_table

        @type object_owner: string
        @param object_owner: owner of this object. ex: nobody, admin

        @type session_key: string
        @param session_key: splunkd session key

        @type logger: logger
        @param logger: caller's logger

        @type read: list/string/comma separated string
        @param read: list of roles permitted/denied to read the object,
            defaults to * indicating all

        @type write: list/string/comma separated string
        @param write: list of roles permitted/denied to write the object,
            defaults to *, indicating all

        @type delete: list/string/comma separated string
        @param delete: list of roles permitted/denied to delete the object,
            defaults to *, indicating all

        @type object_shared_by_inclusion: boolean
        @param object_shared_by_inclusion: is this object shared by inclusion?
            defaults to true

        @type acl_owner: string
        @param acl_owner: owner of this ACL; defaults to DEFAULT_OWNER

        @type acl_id: string
        @param acl_id: id of the ACL.
        '''
        ACL._validate(object_id, object_app, object_storename, object_type,
                      object_owner)

        self._object_id = object_id.strip()
        self._object_app = object_app.strip()
        self._object_storename = object_storename.strip()
        self.logger = logger
        self.session_key = session_key

        self._object_type = object_type
        self._object_owner = object_owner
        self._object_shared_by_inclusion = object_shared_by_inclusion
        self._object_read = read
        self._object_write = write
        self._object_delete = delete
        self._id = acl_id
        self._owner = acl_owner
        self._kv_initialized = True

        self.store = UserAccessStore.getInstance(ns=acl_owner)
        self.store_name = ACL_STORE

        self._existing = self.get_existing()
        if not self._existing or not len(self._existing):
            self._id = acl_id if is_valid_str(acl_id) else str(uuid1())
        else:
            self._id = self._existing['_key']

    def __str__(self):
        return str(self._make_record())

    def _update_with_record(self, record):
        '''
        update current object with given record
        @type record: dict
        @param record: record to update ourselves with

        @return nothing
        '''
        LOG_PREFIX = '[ACL][_update_with_record] '
        if isinstance(record, list):
            self.logger.warn('%s Using only first record. Ditching the rest from %s',
                             LOG_PREFIX, record)
            record = record[0]
        acl = record.get(ACL.STORE_KEY_OBJ_ACL)

        self._object_type = record.get(ACL.STORE_KEY_OBJ_TYPE).strip()
        self._object_shared_by_inclusion = record.get(
            ACL.STORE_KEY_OBJ_SHARED_BY_INCLUSION)
        self._id = record.get('_key').strip() if record.get('_key') else None
        self._owner = record.get(ACL.STORE_KEY_ACL_OWNER).strip()

        self._object_owner = acl.get(ACL.STORE_KEY_OBJ_OWNER).strip()
        self._object_read = uber_str_to_list(acl.get(
            ACL.STORE_KEY_OBJ_ACL_READ))
        self._object_write = uber_str_to_list(acl.get(
            ACL.STORE_KEY_OBJ_ACL_WRITE))
        self._object_delete = uber_str_to_list(acl.get(
            ACL.STORE_KEY_OBJ_ACL_DELETE))

    def _set_acl_id(self, acl_id):
        '''
        set our acl's id to given id
        @type acl_id: str
        @param acl_id: acl id to set our id to

        @return nothing
        @raise BadRequest on invalid str
        '''
        if not is_valid_str(acl_id):
            raise BadRequest('acl id is invalid.')
        else:
            self._id = acl_id.strip()

    def get_acl_id(self):
        '''
        return our acl id
        @rtype str
        @return our acl'd id
        '''
        return self._id

    def get_object_id(self):
        '''
        return the object's ID
        @rtype str
        @return our ACL object's id
        '''
        return self._object_id

    def _make_record(self):
        '''
        Make a consumable ACL dictionary and return the same
        @rtype dict
        @return a dictionary which can be consumed
        '''
        return {
            ACL.STORE_KEY_OBJ_ID: self._object_id,
            ACL.STORE_KEY_OBJ_TYPE: self._object_type,
            ACL.STORE_KEY_OBJ_APP: self._object_app,
            ACL.STORE_KEY_OBJ_STORE: self._object_storename,
            ACL.STORE_KEY_OBJ_SHARED_BY_INCLUSION: self._object_shared_by_inclusion,
            ACL.STORE_KEY_OBJ_ACL: {
                ACL.STORE_KEY_OBJ_OWNER: self._object_owner,
                ACL.STORE_KEY_OBJ_ACL_READ: self._object_read,
                ACL.STORE_KEY_OBJ_ACL_WRITE: self._object_write,
                ACL.STORE_KEY_OBJ_ACL_DELETE: self._object_delete
            },
            ACL.STORE_KEY_ACL_ID: self._id,
            ACL.STORE_KEY_ACL_OWNER: self._owner,
            ACL.STORE_KEY_ACL_KEY: self._id
        }

    @staticmethod
    def merge_perms(perms1, perms2):
        '''
        merge perms1 & perms2, dedup and then return merged perms
        @type perms1: list
        @param perms1: list of perms

        @type perms2: list
        @param perms2: list of perms

        @rtype list:
        @return merged list
        '''
        if not perms1:
            return perms2
        if not perms2:
            return perms1

        # first dedup
        perms1 = list(set(perms1))
        perms2 = list(set(perms2))

        # if one of the perms contains PERMS_ALLOW_ALL, get rid of it
        if ACL.PERMS_ALLOW_ALL in perms1 and ACL.PERMS_ALLOW_ALL not in perms2:
            perms1.remove(ACL.PERMS_ALLOW_ALL)
        elif ACL.PERMS_ALLOW_ALL in perms2 and ACL.PERMS_ALLOW_ALL not in perms1:
            perms2.remove(ACL.PERMS_ALLOW_ALL)
        else:
            pass  # we dont care when PERMS_ALLOW_ALL isnt in either list
        return list(set(perms1 + perms2))

    def get(self):
        '''
        @rtype tuple (boolean, dict)
        @return (True, ACL record in store) on success;
        (False, empty dict) on failure
        '''
        LOG_PREFIX = '[ACL][read] '
        LOG_SUFFIX = ('object_id: `{}` object_app: `{}` object_storename:'
                      ' `{}`').format(self._object_id, self._object_app,
                                      self._object_storename)

        query_params = self.get_query_params()
        success, content = self.store.query(self.store_name, self.session_key,
                                            self.logger, **query_params)

        rval = ''
        if not success:
            message = 'No ACL found. {}'.format(LOG_SUFFIX)
            self.logger.error('%s %s', LOG_PREFIX, message)
            rval = content
        else:
            try:
                store_record = json.loads(content)
                message = 'Found ACL: {}. {}'.format(store_record, LOG_SUFFIX)
                self.logger.debug('%s %s', LOG_PREFIX, message)
                self._update_with_record(store_record)
                rval = json.dumps(self._make_record())
            except TypeError:
                self.logger.error('%s Failed to convert %s to dict', LOG_PREFIX,
                                  store_record)
                rval = 'Failed to convert {} to dict'.format(store_record)
        return success, rval

    def get_query_params(self):
        '''
        return a dict which can be used to query ACL store
        for ACL object
        @rtype query_params: dict
        @return query_params
        '''
        try:
            return self._store_query_params
        except AttributeError:
            self._store_query_params = {
                ACL.STORE_KEY_OBJ_ID: self._object_id,
                ACL.STORE_KEY_OBJ_APP: self._object_app,
                ACL.STORE_KEY_OBJ_STORE: self._object_storename
            }
            return self._store_query_params

    def get_existing(self):
        '''
        return an existing ACL if it exists; else None

        @rtype dict
        @return existing record from store, for this ACL object. Else None
        '''
        LOG_PREFIX = '[ACL][get_existing] '
        try:
            return self._existing
        except AttributeError:
            if not self._id:
                query_params = self.get_query_params()
                success, existing = self.store.query(self.store_name,
                                                     self.session_key, self.logger, **query_params)
            else:
                success, existing = self.store.read(self.store_name, self._id,
                                                    self.session_key, self.logger)

            # read content only if success
            if success:
                self._kv_initialized = True
                existing = json.loads(existing)
                # we receive empty lists on success. hmm
                if len(existing):
                    self._existing = existing[0]
                    return self._existing
            else:
                # If the ACL was not fetched due to the KV Store not being initialized yet, this is NOT an error.
                if KV_INITIALIZING in existing:
                    self._kv_initialized = False
                else:
                    self.logger.error('%s Unable to fetch existing. %s', LOG_PREFIX, existing)

    def exists(self):
        '''
        Check if an ACL for our object exists in store
        @rtype boolean
        @return True if an ACL for our obj exists; False otherwise
        '''
        existing = self.get_existing()
        return True if existing else False

    def set(self):
        '''
        Persist an ACL record.

        @rtype tuple: boolean, str
        @return (True, persisted acl's id) / (False, error message)
        '''
        LOG_PREFIX = '[ACL][write] '
        rval = ''

        self._set_acl_id(str(uuid1()))
        acl = self._make_record()
        success, data = self.store.create(self.store_name, acl, self.session_key,
                                          self.logger, record_id=self.get_acl_id())
        if success is False:
            self.logger.error(('%s Unable to persist ACL. If this message occurs only once, KV'
                               ' Store may still be initializing. Attempted persist of {0} in store: "{1}".'
                               ' acl_id: "{2}"').format(acl, self.store_name, self._id), LOG_PREFIX)
        else:
            self.logger.info(('%s Successfully persisted ACL: {0} in store: "{1}".'
                              ' Return value: "{2}". acl_id: "{2}"').format(
                acl, self.store_name, rval, self._id), LOG_PREFIX)
            rval = json.loads(data).get('_key')
        return success, rval

    def merge_with_existing(self):
        '''
        merge `record in store` with self. self will contain merged perms
        @return nothing
        '''
        if not self.exists():
            return
        existing = self.get_existing()
        acl = existing.get(ACL.STORE_KEY_OBJ_ACL)
        self._object_read = ACL.merge_perms(self._object_read,
                                            acl.get('read'))
        self._object_write = ACL.merge_perms(self._object_write,
                                             acl.get('write'))
        self._object_delete = ACL.merge_perms(self._object_delete,
                                              acl.get('delete'))
        return

    def update(self, merge=False):
        '''
        Update an existing acl with new perms or create a new one
        if none exists.
        @type merge: boolean
        @param merge: True implies merge with existing;
            False implies replace existing perms

        @rtype Tuple of boolean and str
        @return (True, Content) on successful update;
            (False, Message) if otherwise
        '''
        LOG_PREFIX = '[ACL][update] '
        if not self.exists():
            return self.set()

        if merge is True:
            self.merge_with_existing()

        # no special action is needed if merge is False.
        acl = self._make_record()
        success, content = self.store.single_update(self.store_name, acl,
                                                    self.session_key, self.logger, self.get_acl_id())
        if success is False:
            self.logger.error('%s Failed to update ACL. %s', LOG_PREFIX, content)
            rval = content
        else:
            rval = json.loads(content).get('_key')
        return success, rval

    def delete(self, acl_id=None):
        '''
        Delete an existing acl from store
        @type acl_id: str
        @param acl_id: acl id to delete

        @rtype tuple (boolean, str)
        @return (True, deleted content) is success
            (False, error message) if Failure
        '''
        LOG_PREFIX = '[ACL][delete] '
        query_params = None
        success = False

        if not acl_id:
            query_params = self.get_query_params()
            success, content = self.store.delete(self.store_name, self.session_key, self.logger,
                                                 query_params=query_params)
        else:
            success, content = self.store.delete(self.store_name, self.session_key, self.logger,
                                                 record_id=acl_id)
        if not success:
            self.logger.error(('%s Unable to delete ACL. acl_id: {0}'
                               ' query_params: {1}').format(acl_id, query_params), LOG_PREFIX)
        else:
            self.logger.info(('%s Deleted ACL successfully. acl_id: {0}'
                              ' query_params: {1}').format(acl_id, query_params), LOG_PREFIX)
        return success, content

    def is_kv_initialized(self):
        return self._kv_initialized


class UserAccess(object):
    '''
    Utility Class that talks to splunkd, kvstore and maybe does other stuff...
    '''
    store = UserAccessStore.getInstance(app_name='SA-UserAccess', ns=DEFAULT_OWNER)

    @staticmethod
    def get_app_capability_store_name():
        return CAPABILITIES_STORE

    @staticmethod
    def _get_acl_query_params(object_app, object_type, object_store):
        '''
        Get query params to query UserAccessStore instance for ACLs
        @type object_app: string
        @param object_app: `app` that owns the object(s)

        @type object_type: string
        @param object_type: type of object. Ex: deep dive

        @type object_store: string
        @param object_store: store where object lives. Ex: itsi_pages

        @rtype: dictionary
        @return dictionary of query params
        '''
        query_params = {}
        if object_app:
            query_params[ACL.STORE_KEY_OBJ_APP] = object_app
        if object_type:
            query_params[ACL.STORE_KEY_OBJ_TYPE] = object_type
        if object_store:
            query_params[ACL.STORE_KEY_OBJ_STORE] = object_store
        return query_params

    @staticmethod
    def delete_perms(
            object_id,
            object_app,
            object_type,
            object_storename,
            session_key,
            logger,
            object_owner=DEFAULT_OWNER):
        '''Given details of an object, delete its associated perms.
        @type object_id: str
        @param object_id: id of the object

        @type object_app: str
        @param object_app: app to which object belongs

        @type object_type: str
        @param object_type: object type. ie. deep dive, glass table, etc...

        @type object_storename: str
        @param object_storename: store in app where object resides

        @type session_key: str
        @param session_key: splunkd session key

        @return True on success; False on failure.
        '''
        LOG_PREFIX = '[UserAccess][delete_perms] '
        acl = ACL(object_id, object_app, object_storename, object_type, object_owner, session_key, logger)
        success, content = acl.delete()
        msg_suffix = (' object id: `%s` object app: `%s` object type: `%s` object'
                      ' storename: `%s` object owner `%s`') % (object_id, object_app,
                                                               object_type, object_storename, object_owner)

        # the case where `success` can be False is never hit. That is why that
        # case isnt captured here. This is to do with the user_access_kvstore.py
        # which always returns True with an empty body.
        '''
        if not success:
            message = 'Unable to delete permissions. %s .' % content + msg_suffix
            logger.error('%s %s', LOG_PREFIX, message)
            return False
        '''
        message = 'Permissions deleted. %s .' % content + msg_suffix
        logger.debug(message)
        return True

    @staticmethod
    def get_perms(
            object_id,
            object_app,
            object_type,
            object_storename,
            session_key,
            logger,
            object_owner=DEFAULT_OWNER):
        '''
        Given details of an object, fetch the permissions for this object
        if available.
        @type object_id: str
        @param object_id: id of the object

        @type object_app: str
        @param object_app: app to which object belongs

        @type object_type: str
        @param object_type: object type. ie. deep dive, glass table, etc...

        @type object_storename: str
        @param object_storename: store in app where object resides

        @type session_key: str
        @param session_key: splunkd session key

        @return None on failure; dict on success
        '''
        LOG_PREFIX = '[get_perms] '
        acl = ACL(object_id, object_app, object_storename, object_type, object_owner, session_key, logger)
        existing = acl.get_existing()
        msg_suffix = (' object id: `%s` object app: `%s` object type: `%s` object'
                      ' storename: `%s` object owner `%s`') % (object_id, object_app,
                                                               object_type, object_storename, object_owner)
        if not acl.is_kv_initialized():
            message = 'KV Store not initialized yet, so permissions were not fetched. Try again later.'
            logger.warn('%s %s', LOG_PREFIX, message)
            return None
        if not existing:
            message = 'Unable to get permissions. ' + msg_suffix
            logger.error('%s %s', LOG_PREFIX, message)
            return None
        message = 'Found permissions: {}. '.format(existing) + msg_suffix
        logger.info('%s %s', LOG_PREFIX, message)
        return existing[ACL.STORE_KEY_OBJ_ACL]

    @staticmethod
    def update_perms(
            object_id,
            acl,
            object_app,
            object_type,
            object_storename,
            session_key,
            logger,
            object_owner=DEFAULT_OWNER,
            merge=False,
            role_inheritance=False):
        '''
        @type object_id: str
        @param object_id: id of the concerned object

        @type acl: dict
        @param acl: acl to update the object with

        @type object_app: str
        @param object_app: app that owns the object Ex: ITSI

        @type object_type: str
        @param object_type: type of the concerned object Ex: service

        @type object_storename: str
        @param object_storename: store where the object originally resides

        @type session_key: str
        @param session_key: splunkd session key

        @type logger: logger
        @param logger: caller's logger

        @type object_owner: str
        @param object_owner: owner of the concerned object

        @type merge: boolean
        @param merge: False implies `replace` ACL with provided values
            True implies, `merge` existing values with provided values

        @type role_inheritance: bool
        @param role_inheritance: If true, make inherited roles also have the permission.
            Default is False.

        @rtype tuple (boolean, str)
        @return (True, content) on success; (False, error) on failure
        '''
        LOG_PREFIX = '[UserAccess][update_perms] '
        ACL._validate_acl_blob(acl)
        if role_inheritance:
            roles = UserAccess.fetch_all_imported_roles(session_key, logger)
            if len(roles) > 0:
                ACL._add_inherited_roles(acl, roles)

        LOG_SUFFIX = ('object_id: `{}` acl: `{}` object_app: `{}`'
                      ' object_type: `{}` object_storename: `{}`'
                      ' object_owner: `{}`').format(
            object_id, acl, object_app, object_type,
            object_storename, object_owner)

        logger.debug('%s %s', LOG_PREFIX, LOG_SUFFIX)
        acl = ACL(object_id, object_app, object_storename, object_type,
                  object_owner, session_key, logger, **acl)

        success, content = acl.update(merge)
        if not success:
            logger.error(
                '%s Unable to update ACL. If this message occurs only once, KV Store may still be initializing. %s. %s',
                LOG_PREFIX, content, LOG_SUFFIX)
        else:
            logger.info('%s Successfully updated ACL. %s. %s',
                        LOG_PREFIX, content, LOG_SUFFIX)

        return success, content

    @staticmethod
    def bulk_update_perms(
            object_ids,
            acl,
            object_app,
            object_type,
            object_storename,
            session_key,
            logger,
            object_owner=DEFAULT_OWNER,
            object_shared_by_inclusion=True,
            replace_existing=True,
            role_inheritance=False):
        '''
        given a list of object_ids, update their permissions in our
        internal store

        @type object_ids: list
        @param object_ids: list of object ids

        @type acl: dict
        @param acl: dictionary with keys read/write/delete

        @type object_app: str
        @param object_app: app which owns these object_ids

        @type object_type: str
        @param object_type: type of object i.e. Deep Dive

        @type object_store: str
        @param object_store: where these objects actually reside ie. itsi_pages

        @type session_key: str
        @param session_key: splunkd session key

        @type: logger
        @param logger: caller's logger object

        @type object_owner: str
        @param object_owner: owner of these objects

        @type object_shared_by_inclusion: bool
        @param object_shared_by_inclusion: Are these objects shared by
            inclusion?

        @type replace_existing: bool
        @param replace_existing: Rewrite existing ACL with provided
            if False, we will merge with existing

        @type role_inheritance: bool
        @param role_inheritance: If true, make inherited roles also have the permission.
            Default is False.

        @return tuple (True, list of ACL ids) on success;
            (False, pertinent string) on failure
        '''
        LOG_PREFIX = '[UserAccess][bulk_update_perms] '
        LOG_SUFFIX = ('object_ids: `{}` acl: `{}` object_app: `{}`'
                      ' object_type: `{}` object_storename: `{}`'
                      ' object_owner: `{}`').format(
            object_ids, acl, object_app, object_type,
            object_storename, object_owner)
        if isinstance(acl, string_types):
            try:
                acl = json.loads(acl)
            except Exception as e:
                msg = 'Bad input. Unable to json`ify `{}`'.format(acl)
                logger.exception(e)
                logger.error(msg)
                raise BadRequest(msg)
        ACL._validate_acl_blob(acl)
        if role_inheritance:
            roles = UserAccess.fetch_all_imported_roles(session_key, logger)
            if len(roles) > 0:
                ACL._add_inherited_roles(acl, roles)

        object_ids = list(set(object_ids))
        logger.debug('%s %s', LOG_PREFIX, LOG_SUFFIX)

        # construct ACL records to commit
        acl_records = []
        for object_id in object_ids:
            new_ = ACL(object_id, object_app, object_storename, object_type,
                       object_owner, session_key, logger,
                       acl[ACL.STORE_KEY_OBJ_ACL_READ],
                       acl[ACL.STORE_KEY_OBJ_ACL_WRITE],
                       acl[ACL.STORE_KEY_OBJ_ACL_DELETE],
                       object_shared_by_inclusion)

            acl_records.append(new_._make_record())
        logger.debug('%s ACL Records to commit: %s', LOG_PREFIX, acl_records)

        success, rval = ACL.bulk_update(acl_records, session_key, logger)
        if not success:
            logger.error('%s Failed to update ACL records. Response: %s. %s',
                         LOG_PREFIX, rval, LOG_SUFFIX)
        else:
            logger.info('%s Successfully updated ACL records. Response: %s. %s',
                        LOG_PREFIX, rval, LOG_SUFFIX)
        return success, rval

    @staticmethod
    def get_accessible_object_ids(
            user,
            operation,
            session_key,
            logger,
            object_ids=None,
            object_app=None,
            object_type=None,
            object_store=None):
        '''
        For given user:
        * best performant: from given list of object_ids, return accessible ids
        * worst performant: if no object ids are given, return accessible ids
        if object_ids are given, it implies that the caller is asking us for a
            subset of these object_ids
        if no object_ids are given, we will query ACL store for all objects and
            then construct a list of accessible ids

        @type user: string
        @param user: `user` for whom we are making this request

        @type operation: string
        @param operation: indicates user operation: read/write/delete.

        @type session_key: string
        @param session_key: splunkd session key

        @type logger: logger object
        @param logger: caller's logger

        @type object_ids: list
        @param object_ids: list of strings; each string, an object id

        @type object_app: string
        @param object_app: the app for which this query is being issued.
            If no value is provided, fetch IDs for all apps that have
            stored ACL info for their objects

        @type object_type: string
        @param object_type: Defaults to None; object type to issue query for

        @type object_store: string
        @param object_store: Store name where the object is stored. If no
            value is provided, fetch ids across all stores whose objects
            have ACL info stashed away with us.

        @rtype: list
        @return: list of object ids accessible by this user
        @raise: BadRequest on missing mandatory params
        '''
        LOG_PREFIX = '[UserAccess][get_accessible_object_ids] '
        accessible_ids = []
        if not isinstance(user, string_types) or len(user.strip()) == 0:
            raise BadRequest('`user` must be a valid string of non-zero length.')
        if not isinstance(operation, string_types) or \
                operation.strip() not in ACL.SUPPORTED_OPERATIONS:
            raise BadRequest(('`operation` must be a valid string and '
                              'should be one of {}. Received `{}`').format(
                ACL.SUPPORTED_OPERATIONS, operation))

        logger.debug('%s `user`: %s `operation`: %s', LOG_PREFIX, user, operation)
        logger.debug('%s Fetching roles for "%s"', LOG_PREFIX, user)
        user_roles = UserAccess.fetch_user_roles(user, session_key, logger)
        logger.debug('%s "%s" has the role(s): %s', LOG_PREFIX, user, user_roles)

        UserAccess.store.update_singleton(app_name='SA-UserAccess')
        if object_ids:
            # we have object_ids caller wants a subset of these, issue a bulk read
            object_ids = list(set(object_ids))
            logger.debug('%s Given object_ids: {}'.format(object_ids), LOG_PREFIX)
            success, rval = UserAccess.store.bulk_read(ACL_STORE, object_ids,
                                                       session_key, logger, field_name=ACL.STORE_KEY_OBJ_ID)
        else:
            logger.debug('%s object_app: %s object_type: %s object_store: %s',
                         LOG_PREFIX, object_app, object_type, object_store)
            query_params = UserAccess._get_acl_query_params(
                object_app, object_type, object_store)
            success, rval = UserAccess.store.query(
                ACL_STORE, session_key, logger, **query_params)

        if not success:
            logger.error('%s Unable to query UserAccessStore. %s', LOG_PREFIX, rval)
            return accessible_ids

        acls = json.loads(rval)
        logger.debug('%s Fetched ACLs: {}'.format(acls), LOG_PREFIX)

        # Check for any object_id ACL is missing or not
        # if missing then we are creating new ACL object for that object_id
        objects_ids_need_acl_refetch = []
        for object_id in object_ids:
            if not any(acl[ACL.STORE_KEY_OBJ_ID] == object_id for acl in acls):
                logger.info("%s ACL object_id {} has no occurence in acl store".format(object_id), LOG_PREFIX)
                acl = ACL(object_id, object_app, object_store, object_type, DEFAULT_OWNER, session_key, logger)
                logger.info("%s Creating a new ACL for object_id {}, ".format(object_id), LOG_PREFIX)
                success, rval = acl.set()
                if not success:
                    logger.error('%s Failed to create ACL for object_id {}'.format(object_id), LOG_PREFIX)
                else:
                    logger.info('%s Successfully created ACL for object_id {} with _key {}'.format(object_id, rval),
                                LOG_PREFIX)
                    objects_ids_need_acl_refetch.append(object_id)

        # Fetch ACLs for object_ids for which we have newly created ACLs
        if len(objects_ids_need_acl_refetch) > 0:
            logger.info('%s Given object_ids refetching ACL object: {}'.format(objects_ids_need_acl_refetch),
                        LOG_PREFIX)
            success, rval = UserAccess.store.bulk_read(ACL_STORE, objects_ids_need_acl_refetch,
                                                       session_key, logger, field_name=ACL.STORE_KEY_OBJ_ID)
            if not success:
                logger.error('%s Unable to query UserAccessStore. %s', LOG_PREFIX, rval)
            else:
                acls.extend(json.loads(rval))

        for acl in acls:
            # check if acl for operation contains role of user
            role_in_acl = ACL.roles_in_acl(user_roles,
                                           acl[ACL.STORE_KEY_OBJ_ACL][operation])
            logger.debug(('%s User role(s): %s. operation: `%s`. ACL:  %s role in'
                          ' acl: %s'),
                         LOG_PREFIX, user_roles, operation,
                         acl[ACL.STORE_KEY_OBJ_ACL][operation], role_in_acl)

            # if we are sharing by inclusion, and if user's role
            # is NOT in the list, remove obj
            if ACL.object_shared_by_inclusion(acl):
                logger.debug('%s Object Sharing is by Inclusion', LOG_PREFIX)
                if role_in_acl:
                    logger.debug('%s User role is in ACL', LOG_PREFIX)
                    accessible_ids.append(acl[ACL.STORE_KEY_OBJ_ID])
            else:
                logger.debug('%s Object Sharing is by Exclusion', LOG_PREFIX)
                if not role_in_acl:
                    logger.debug('%s User role is not in ACL', LOG_PREFIX)
                    accessible_ids.append(acl[ACL.STORE_KEY_OBJ_ID])

        logger.debug('%s Accessible object_ids: {}'.format(accessible_ids), LOG_PREFIX)
        return accessible_ids

    @staticmethod
    def are_object_ids_accessible(user, operation, object_ids, session_key, logger):
        '''
        Given a `user`, `desired operation` and `list of object ids`:
        are they accessible by `user`?

        @type user: string
        @param user: `user` for whom we are issuing this query

        @type operation: string
        @param operation: indicates if a user is trying to either read/write/delete.

        @type object_ids: list
        @param object_ids: list of strings; each string, represents an object id
        '''
        LOG_PREFIX = '[UserAccess][are_object_ids_accessible] '
        if not isinstance(user, string_types) or len(user.strip()) == 0:
            raise BadRequest('`user` must be a valid string of non-zero length.')
        if not isinstance(operation, string_types) or \
                operation.strip() not in ACL.SUPPORTED_OPERATIONS:
            raise BadRequest(('`operation` must be a valid string and should be'
                              ' in {}').format(ACL.SUPPORTED_OPERATIONS))

        accessible_ids = UserAccess.get_accessible_object_ids(user, operation,
                                                              session_key, logger, object_ids)
        logger.debug(('%s Given object_ids: {}\nAccessible object_ids:'
                      ' {}').format(object_ids, accessible_ids), LOG_PREFIX)

        if (len(accessible_ids) == len(object_ids)) and \
                intersects(object_ids, accessible_ids):
            logger.debug('%s Given object ids are accessible by `%s` for `%s`',
                         LOG_PREFIX, user, operation)
            return True
        logger.debug('%s Given object ids are not accessible by `%s` for `%s`',
                     LOG_PREFIX, user, operation)
        return False

    @staticmethod
    def register_app_capabilities(app_name, capability_matrix, session_key, logger):
        '''
        This is STEP I of consuming SA-UserAccess
        A consumer of SA-UserAccess is expected to register capabilities
        vis-a-vis its objects as a matrix..

        @type app_name: string
        @param app_name: represents app name
            Ex: itsi/es etc...

        @type capability_matrix: dict
        @param capability_matrix: capabilities viz-a-viz app objects
            Ex:
                {
                    'glass_table': {
                        'read': 'read_itsi_glass_table',
                        'write': 'write_itsi_glass_table',
                        'delete': 'delete_itsi_glass_table'
                        },
                    'deep_dive': {
                        'read': 'read_itsi_deep_dive',
                        'write': 'write_itsi_deep_dive',
                        'delete': 'delete_itsi_deep_dive'
                        },
                    ...
                }

        @type session_key: string
        @param session_key : splunkd session key

        @param type: logger
        @param logger: caller's logger object

        @return True on successful registration, False if otherwise
        '''
        LOG_PREFIX = '[UserAccess.register_capability_matrix] '
        STORE_NAME = CAPABILITIES_STORE
        if not isinstance(app_name, string_types) or not isinstance(capability_matrix, dict):
            message = 'Expecting a non-None string for app_name and a non-None dict for capability_matrix'
            logger.error('%s %s', LOG_PREFIX, message)
            return False

        # first check if app is already registered
        try:
            already_registered = UserAccess.is_app_registered(app_name, session_key, logger)
            if already_registered is True:
                message = 'App "{0}" has already registered its capabilities.'.format(app_name)
                logger.warn('%s %s', LOG_PREFIX, message)
                return True
        except ResourceNotFound as e:
            message = 'app - "{0}" has not registered its capabilities. Will try registering now.'.format(app_name)
            logger.debug('%s %s', LOG_PREFIX, message)

        # app isn't registered. Try registering.
        success, data = UserAccess.store.create(
            store_name=STORE_NAME,
            record=capability_matrix,
            session_key=session_key,
            logger=logger, record_id=app_name)
        if success is True:
            logger.debug('Successfully registered capabilities for app {}. Response: {}'.format(app_name, data))
        else:
            logger.error('Unable to register capabilities for app {}.'.format(app_name))
        return success

    @staticmethod
    def deregister_app_capabilities(app_name, session_key, logger):
        '''
        Utility method that de-registers app capabilities viz-a-viz app objects
        @type app_name: string
        @param app_name: deregister capabilities of an app with this name

        @type session_key: string
        @param session_key splunkd session key

        @type logger: logger
        @param logger: caller's logger object

        @rtype: boolean
        @return True if success; False otherwise
        '''
        LOG_PREFIX = '[UserAccess.deregister_app_capabilities] '
        STORE_NAME = CAPABILITIES_STORE

        if not isinstance(app_name, string_types):
            message = 'Expecting a non-None, string for app_name'
            logger.error('%s %s', LOG_PREFIX, message)
            return False

        success = UserAccess.store.delete(
            store_name=STORE_NAME,
            record_id=app_name,
            session_key=session_key, logger=logger)
        if success is False:
            message = 'Unable to de-register app capabilities for "{0}".'.format(app_name)
            logger.error('%s %s', LOG_PREFIX, message)
        else:
            message = 'Successfully de-registered app capabilities for "{0}".'.format(app_name)
            logger.debug('%s %s', LOG_PREFIX, message)
        return success

    @staticmethod
    def is_app_registered(app_name, session_key, logger):
        '''
        A consumer of SA-UserAccess is expected to register its capabilities viz-a-viz its objects as matrix..
        A helper to check if app has registered its capabilities

        @type app_name: string
        @param app_name: represents app name

        @type session_key: string
        @param session_key: Splunkd session key

        @type logger: logger
        @param logger: caller's logger object

        @rtype: boolean
        @return True if app has registered, False otherwise
        '''
        LOG_PREFIX = '[UserAccess][is_app_registered] '
        app_capabilities = None
        try:
            app_capabilities = UserAccess.get_app_capabilities(app_name, session_key, logger)
        except BadRequest as e:
            logger.error('%s Unable to find capabilities for app "%s"', LOG_PREFIX, app_name)
        return (True if app_capabilities else False)

    @staticmethod
    def get_app_capabilities(app_name, session_key, logger):
        '''
        Get the capabilities of an app that has registered its capabilities with us

        @type app_name: string
        @param app_name: Name of app

        @type session_key: string
        @param session_key: splunkd session key

        @type logger: logger
        @param logger: caller's logger

        @rtype app_capabilities: dictionary
        @return app_capabilities: capabilities of the app

        @raise BadRequest on malformed app_name
        '''
        STORE_NAME = CAPABILITIES_STORE
        LOG_PREFIX = '[UserAccess.get_app_capabilities] '

        if not isinstance(app_name, string_types):
            message = 'Expecting a non-None string for app_name and not of type {0}.'.format(type(app_name))
            logger.error('%s %s', LOG_PREFIX, message)
            raise BadRequest(message)

        success, app_capabilities = UserAccess.store.read(
            store_name=STORE_NAME,
            record_id=app_name,
            session_key=session_key, logger=logger)

        if success is False:
            raise BadRequest('Unable to find app "{}". See internal logs'.format(app_name))
        return app_capabilities

    @staticmethod
    def _fetch_all_roles(session_key, logger, output_mode='json'):
        '''
        Fetch all roles with current session key

        @type session_key: string
        @param session_key: splunkd session key

        @type logger: logger
        @param logger: caller's logger

        @type output_mode: string
        @param output_mode: Splunkd supported output modes. Defaults to json

        @rtype: dict
        @return object: json'ified access details of username
        '''
        LOG_PREFIX = '[UserAccess._fetch_all_roles] '
        uri = '/services/authorization/roles'
        getargs = {'output_mode': output_mode, 'count': 0}
        try:
            response, content = rest.simpleRequest(
                uri,
                method='GET',
                getargs=getargs,
                sessionKey=session_key,
                raiseAllErrors=False)
        except Exception as e:
            logger.error('%s Error while polling splunkd.', LOG_PREFIX)
            logger.exception(e)
            raise

        if response.status != 200:
            message = ('Error while polling Splunkd. Response: "{}".'
                       ' Content: "{}"').format(response, content)
            logger.error('%s %s', LOG_PREFIX, message)
            raise Exception(message)
        else:
            logger.debug('%s Fetched all roles for current session: %s',
                         LOG_PREFIX, content)
            return json.loads(content)

    @staticmethod
    def _fetch_user_access_details(username, session_key, logger, output_mode='json'):
        '''
        Given a username, fetch the user's access control details

        @type username: string
        @param username: concerned username

        @type session_key: string
        @param session_key: splunkd session key

        @type output_mode: string
        @param output_mode: Splunkd supported output modes. Defaults to json

        @rtype: dict
        @return object: json'ified access details of username

        @raise BadRequest: if invalid params
        @raise Exception: if other internal errors
        '''
        LOG_PREFIX = '[UserAccess._fetch_user_access_details] '
        if (not isinstance(username, string_types)) or len(username.strip()) == 0:
            raise BadRequest(('Expecting a valid username which is non-empty,'
                              ' non-None and of type str. Instead got - {0}').format(username))
        if (not isinstance(username, string_types)) or len(session_key.strip()) == 0:
            raise BadRequest(('Expecting a valid session_key which is non-empty,'
                              ' non-None and of type str'))

        uri = '/services/authentication/users/{}'.format(username)
        getargs = {'output_mode': output_mode}
        try:
            response, content = rest.simpleRequest(
                uri,
                method='GET',
                getargs=getargs,
                sessionKey=session_key,
                raiseAllErrors=False)
        except Exception as e:
            logger.error('%s Error while polling splunkd.', LOG_PREFIX)
            logger.exception(e)
            raise

        if response.status != 200:
            message = ('Error while polling Splunkd. Response: "{}".'
                       ' Content: "{}"').format(response, content)
            logger.error('%s %s', LOG_PREFIX, message)
            raise Exception(message)
        else:
            logger.debug('%s Fetched user access details for user "%s". %s',
                         LOG_PREFIX, username, content)
            return json.loads(content)

    @staticmethod
    def fetch_user_capabilities(username, session_key, logger):
        '''
        Given username, fetch the user's capabilities
        @param username: concerned username
        @param type: string

        @param session_key: splunkd session key
        @param type: string

        @return list: of capabilities
        @return type: list

        @raise BadRequest: if invalid input params
        @raise Exception: for other exceptions
        '''
        LOG_PREFIX = '[UserAccess.fetch_user_capabilities] '
        try:
            user_access_details = UserAccess._fetch_user_access_details(username, session_key, logger)
        except BadRequest as e:
            logger.error('%s Bad request: %s', LOG_PREFIX, str(e))
            raise BadRequest(str(e))
        except Exception as e:
            logger.error('%s Encountered an Internal Error.', LOG_PREFIX)
            logger.exception(e)
            raise

        capabilities = user_access_details['entry'][0]['content']['capabilities']
        logger.debug('%s Fetched capabilities for "%s". They are: %s', LOG_PREFIX, username, str(capabilities))
        return capabilities

    @staticmethod
    def fetch_user_roles(username, session_key, logger):
        '''
        Given username, fetch the user's roles

        @type username: string
        @param username: concerned username

        @type session_key: string
        @param session_key: splunkd session key

        @rtype: list
        @return: user roles

        @raise BadRequest: if invalid input param
        @raise Exception: for other errors
        '''
        LOG_PREFIX = '[UserAccess.fetch_user_roles] '
        try:
            user_access_details = UserAccess._fetch_user_access_details(username, session_key, logger)
        except BadRequest as e:
            logger.error('%s Bad request: %s', LOG_PREFIX, str(e))
            raise BadRequest(str(e))
        except Exception as e:
            logger.error('%s Encountered an Internal Error.', LOG_PREFIX)
            logger.exception(e)
            raise

        roles = user_access_details['entry'][0]['content']['roles']
        logger.debug('%s Fetched roles for user - %s. %s', LOG_PREFIX, username, str(roles))
        return user_access_details['entry'][0]['content']['roles']

    @staticmethod
    def fetch_all_imported_roles(session_key, logger):
        '''
        Fetch all roles and their imported roles with given session key

        @type session_key: string
        @param session_key: splunkd session key

        @param logger: logger object
        @param type: logger

        @rtype: dict
        @return object: the roles and their imported roles, the key is the role name,
            the value is a list of its imported roles.
        '''
        LOG_PREFIX = '[UserAccess.fetch_all_imported_roles] '
        try:
            roles_detail = UserAccess._fetch_all_roles(session_key, logger)
        except Exception as e:
            logger.error('%s Encountered an Internal Error.', LOG_PREFIX)
            logger.exception(e)
            raise
        roles = {}
        if 'entry' not in roles_detail:
            logger.warn('Cannot fetch any roles for current session.')
            return roles
        for entry in roles_detail['entry']:
            if 'name' in entry and 'content' in entry and 'imported_roles' in entry['content']:
                roles[entry['name']] = entry['content']['imported_roles']
        return roles

    @staticmethod
    def fetch_all_user_roles(username, session_key, logger):
        '''
        Given username, fetch the user's roles plus the inherited roles

        @type username: string
        @param username: concerned username

        @type session_key: string
        @param session_key: splunkd session key

        @param logger: logger object
        @param type: logger

        @rtype: list
        @return: user roles

        @raise BadRequest: if invalid input param
        @raise Exception: for other errors
        '''
        LOG_PREFIX = '[UserAccess.fetch_all_user_roles] '
        try:
            user_roles = UserAccess.fetch_user_roles(username, session_key, logger)
            all_imported_roles = UserAccess.fetch_all_imported_roles(session_key, logger)
        except BadRequest as e:
            logger.error('%s Bad request: %s', LOG_PREFIX, str(e))
            raise BadRequest(str(e))
        except Exception as e:
            logger.error('%s Encountered an Internal Error.', LOG_PREFIX)
            logger.exception(e)
            raise

        all_roles_for_user = set(user_roles)
        processed_roles = set()

        def append_inherited_roles(role):
            if role in processed_roles:
                # Prevent looping forever from cyclic inheritance
                return
            else:
                processed_roles.add(role)

            # Recursively add roles via inheritance for each roles assigned to user
            inherited_roles = all_imported_roles.get(role)
            if inherited_roles is not None:
                for inherited_role in inherited_roles:
                    all_roles_for_user.add(inherited_role)
                    append_inherited_roles(inherited_role)

        for role in user_roles:
            append_inherited_roles(role)

        return list(all_roles_for_user)

    @staticmethod
    def is_user_capable(username, capability, session_key, logger, owner=None):
        '''
        @param username: The username we are concerned with
        @param type: string

        @param capability: The capability we wish to check for
        @param type: string

        @param session_key: splunkd session key
        @param type: string

        @param logger: logger object
        @param type: logger

        @param owner: The owner of the object we might want to use for reference
        @param type: string

        @return False: if user is not capable, True if otherwise
        '''
        LOG_PREFIX = '[UserAccess.is_user_capable] '

        if isinstance(owner, string_types) and username.strip().lower() == owner.strip().lower():
            message = '{0} "{1}" wants to work on object with self ownership. Incoming owner is "{2}".'.format(
                LOG_PREFIX, username, owner)
            logger.debug(message)
            return True

        message = '{0} Fetching capabilities for {1}. Checking for capability - {2}'.format(LOG_PREFIX, username,
                                                                                            capability)
        logger.debug(message)

        user_capabilities = UserAccess.fetch_user_capabilities(username, session_key, logger)
        assert type(user_capabilities) is list
        message = '{0} Capabilities for "{1}" are "{2}".'.format(LOG_PREFIX, username, json.dumps(user_capabilities))
        logger.debug('%s', message)

        if capability not in user_capabilities:
            message = '{0} "{1}" is not capable of "{2}".'.format(LOG_PREFIX, username, capability)
            logger.debug(message)
            return False
        else:
            logger.debug('%s "%s" is capable of "%s" ', LOG_PREFIX, username, capability)
            return True

    @staticmethod
    def is_user_capable_all_ops(username, object_type, capabilities_names, session_key, logger, owner=None):
        '''
        @param username: The username we are concerned with
        @param type: string

        @param object_type: ITOA object type you are concerned with
        @param type: string

        @param capabilities_names: The capabilities we wish to check for
        @param type: dict

        @param session_key: splunkd session key
        @param type: string

        @param logger: logger object
        @param type: logger

        @param owner: The owner of the object we might want to use for reference
        @param type: string

        @return Object: returns a object with booleans corresponding to read, write, and delete permissions for user
        '''
        LOG_PREFIX = '[UserAccess.is_user_capable_all_ops] '

        if isinstance(owner, string_types) and username.strip().lower() == owner.strip().lower():
            message = '{0} "{1}" wants to work on object with self ownership. Incoming owner is "{2}".'.format(
                LOG_PREFIX, username, owner)
            logger.debug(message)
            return True

        message = '{0} Fetching capabilities for {1}. Checking for object type - {2}'.format(LOG_PREFIX, username,
                                                                                             object_type)
        logger.debug(message)

        user_capabilities = UserAccess.fetch_user_capabilities(username, session_key, logger)
        assert type(user_capabilities) is list
        message = '{0} Capabilities for "{1}" are "{2}".'.format(LOG_PREFIX, username, json.dumps(user_capabilities))
        logger.debug('%s', message)

        capabilities = {}
        for capability in capabilities_names:
            if capabilities_names[capability] not in user_capabilities:
                message = '{0} "{1}" is not capable of "{2}".'.format(LOG_PREFIX, username, capability)
                logger.debug(message)
                capabilities[capability] = False
            else:
                logger.debug('%s "%s" is capable of "%s" ', LOG_PREFIX, username, capability)
                capabilities[capability] = True
        return capabilities

    @staticmethod
    def get_current_username(logger):
        '''
        Get current username
        @param logger: caller's logger object
        @param type: logger object
        '''
        LOG_PREFIX = '[UserAccess.get_current_username] '
        current_user_obj = getCurrentUser()
        current_uname = current_user_obj.get('name', 'unknown') if isinstance(current_user_obj, dict) else 'unknown'
        message = '{0} Current user\'s name - {1}'.format(LOG_PREFIX, current_uname)
        logger.debug(message)
        return current_uname

    @staticmethod
    def get_username(logger, **kwargs):
        '''
        Get the username from kwargs or currentUser if its missing from kwargs
        @param kwargs: key value pair object. expected to contain "user" key

        @rtype: string
        @return username: the requested username.
            if a "user" key is present in kwargs, that or "current user"

        @raise UserAccessError: on invalid username
        '''
        LOG_PREFIX = '[UserAccess.get_username] '
        # query splunkd for current user OR use "user" in input kwargs if that is present
        current_uname = UserAccess.get_current_username(logger)
        username = kwargs.get('user') if (
                isinstance(kwargs, dict) and kwargs.get('user') is not None) else current_uname
        if username.strip().lower() == 'unknown':
            message = 'Expecting a valid username instead of "unknown".'
            logger.error('%s %s', LOG_PREFIX, message)
            raise UserAccessError(status=400, message=message)
        return username

    @staticmethod
    def get_current_owner(kwargs, username, owner, session_key, logger, object_type):
        '''
        Given the kwargs and if object type is glass table or deep dive,
        fetch owner of existing object, or parse owner from payload

        @param kwargs: key value pair object. expected to contain "data" key

        @param username: concerned username
        @param type: string

        @param owner: owner from args
        @param type: string

        @param session_key: splunkd session key
        @param type: string

        @param logger: caller's logger object
        @param type: logger object

        @return owner: owner from kwargs
        @return type: string

        @raise UserAccessError: no _owner in json
        @raise UserAccessError: user trying to access private object of other user
        '''

        LOG_PREFIX = '[UserAccess.get_current_owner] '
        # Return owner from args if no data in kwargs
        # i.e if request method is PUT or POST
        if isinstance(kwargs['data'], dict) and kwargs['data']:
            data = kwargs['data']
            object_id = data.get("_key", None)
            json_owner = data.get('_owner', None)
            acl = data.get('acl', None)
            acl_owner = acl.get('owner', None) if acl else None
            if not json_owner:
                # ACL owner not mandatory, but object owner is.
                message = 'owner fields corrupted or missing in payload. kwargs: {}'.format(kwargs)
                logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=400, message=message)
            message = '{} wants to work on object_id: {} with owner: {}'.format(username, object_id, json_owner)
            logger.info('%s %s', LOG_PREFIX, message)
            if object_id:
                store = UserAccessStore.getInstance(app_name='SA-ITOA', ns=DEFAULT_OWNER)
                success, temp_object = store.read(
                    store_name=UserAccess.get_collection_name(object_type, logger),
                    record_id=object_id,
                    session_key=session_key,
                    logger=logger)
                if success:
                    temp_object = json.loads(temp_object)
                    object_owner = temp_object.get('_owner', 'nobody')
                    object_acl_owner = temp_object['acl']['owner']
                    # Object exists and user wants to change ownership, which is not allowed
                    if (object_owner != json_owner or (acl_owner and acl_owner != object_acl_owner)):
                        message = 'Changing ownership of existing objects is not permitted.'
                        logger.error('%s %s', LOG_PREFIX, message)
                        raise UserAccessError(status=403, message=message)
                    return object_owner
                else:
                    message = 'Object {} could not be retrieved or does not exist'.format(object_id)
                    logger.error('%s %s', LOG_PREFIX, message)
            # Object does not exist, thus object sharing by inclusion is not possible
            if (json_owner != "nobody"
                    and not ((acl_owner and json_owner == username == acl_owner)
                             or (acl_owner == None and json_owner == username))):
                message = 'Payload has inconsistent ownership, please verify owners {}, {} and {}'.format(
                    username, json_owner, acl_owner)
                logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=403, message=message)
            if (json_owner == "nobody" and acl_owner and acl_owner != username):
                message = 'Payload has inconsistent ownership, please verify owners {} and {}'.format(username,
                                                                                                      acl_owner)
                logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=403, message=message)
            return json_owner
        else:
            return owner

    @staticmethod
    def get_collection_name(object_type, logger):
        """
            This method returns the collection name on the basis of object type.
        """
        OBJECT_COLLECTION_MATRIX = {
            'team': 'itsi_team',
            'service': 'itsi_services',
            'base_service_template': 'itsi_base_service_template',
            'entity': 'itsi_services',
            'kpi': 'itsi_services',
            'kpi_base_search': 'itsi_services',
            'kpi_template': 'itsi_services',
            'kpi_threshold_template': 'itsi_services',
            'saved_page': 'itsi_services',
            'deep_dive': 'itsi_pages',
            'glass_table': 'itsi_pages',
            'home_view': 'itsi_service_analyzer',
            'migration': 'itsi_migration',
            'event_management_state': 'itsi_event_management',
            'backup_restore': 'itsi_backup_restore_queue',
            'entity_relationship': 'itsi_entity_relationships',
            'entity_relationship_rule': 'itsi_entity_relationship_rules',
            'entity_management_policies': 'itsi_entity_management_policies',
            'entity_management_rules': 'itsi_entity_management_policies',
            'content_pack': 'itsi_content_pack_authorship'
        }
        return OBJECT_COLLECTION_MATRIX.get(object_type)

    @staticmethod
    def fetch_capability_name(capability_matrix, object_type, operation, logger):
        '''
        Given a supported ITOA object_type, and the desired supported operation, return the capability name
        @param capability_matrix: a dictionary representing capabilities of an app
            Ex: {
                    'glass_table' : {
                        'read':'read_itsi_glass_table'.
                        'write':'write_itsi_glass_table',
                        'delete':'delete_itsi_glass_table'
                        },
                    'deep_dive': {
                        'read':'read_itsi_deep_dive',
                        'write':'write_itsi_deep_dive',
                        'delete':'delete_itsi_deep_dive'
                        },
                    ...
                }
        @param object_type: ITOA object type you are concerned with
        @param type: string

        @param operation: desired operation
        @param type: string

        @param logger: logger object
        @param type: logger

        @return tuple desired_capability, message: desired capability name as in authorize.conf or None if error...
        @return type: string, string
        '''
        LOG_PREFIX = '[UserAccess.fetch_capability_name] '

        if capability_matrix is None or len(capability_matrix) == 0:
            message = 'Expecting capability_matrix to be non-None and non-empty.'
            logger.error('%s %s', LOG_PREFIX, message)
            return None, message

        if object_type is None or operation is None:
            message = 'Expecting non-None object_type and operation.'
            logger.error('%s %s', LOG_PREFIX)
            return None, message

        object_type = object_type.strip().lower()
        operation = operation.strip().lower()

        obj_matrix = capability_matrix.get(object_type)
        if obj_matrix is None:
            message = 'No capabilities defined for "{0}". Check your app\'s authorize.conf.'.format(object_type)
            logger.error('%s %s', LOG_PREFIX)
            return None, message

        capability_name = obj_matrix.get(operation)
        message = 'Object type - {0}, operation - {1}, Capability name is - {2}.'.format(object_type, operation,
                                                                                         capability_name)
        logger.debug('%s %s', LOG_PREFIX, message)
        return capability_name, message

    @staticmethod
    def fetch_capabilities_names_all_ops(capability_matrix, object_type, logger):
        '''
        Given a supported ITOA object_type, return the capabilities names
        @param capability_matrix: a dictionary representing capabilities of an app
            Ex: {
                    'glass_table' : {
                        'read':'read_itsi_glass_table'.
                        'write':'write_itsi_glass_table',
                        'delete':'delete_itsi_glass_table'
                        },
                    'deep_dive': {
                        'read':'read_itsi_deep_dive',
                        'write':'write_itsi_deep_dive',
                        'delete':'delete_itsi_deep_dive'
                        },
                    ...
                }
        @param object_type: ITOA object type you are concerned with
        @param type: string

        @param logger: logger object
        @param type: logger

        @return tuple desired_capabilities, message: desired capability name as in authorize.conf or None if error...
        @return type: dict, string
        '''
        LOG_PREFIX = '[UserAccess.fetch_capabilities_names_all_ops] '

        if capability_matrix is None or len(capability_matrix) == 0:
            message = 'Expecting capability_matrix to be non-None and non-empty'
            logger.error('%s %s', LOG_PREFIX, message)
            return None, message

        if object_type is None:
            message = 'Expecting non-None object_type'
            logger.error('%s %s', LOG_PREFIX)
            return None, message

        object_type = object_type.strip().lower()

        obj_matrix = capability_matrix.get(object_type)
        if obj_matrix is None:
            message = 'No capabilities defined for "{0}". Check your app\'s authorize.conf.'.format(object_type)
            logger.error('%s %s', LOG_PREFIX)
            return None, message

        message = 'Object type - {0}, Capabilities names are - {1}'.format(object_type, obj_matrix)
        logger.debug('%s %s', LOG_PREFIX, message)
        return obj_matrix, message

    @staticmethod
    def handle_missing_acls(object_ids, object_app, object_type, object_store, session_key, logger):
        LOG_PREFIX = '[UserAccess][handle_missing_acls] '
        acl_obj_ids = []
        handle_status = True

        logger.info('%s Handle missing acls start for object_type {}'.format(object_type), LOG_PREFIX)
        object_ids = list(set(object_ids))
        logger.info('%s Given object_ids: {}'.format(object_ids), LOG_PREFIX)
        success, rval = UserAccess.store.bulk_read(ACL_STORE, object_ids,
                                                   session_key, logger, field_name=ACL.STORE_KEY_OBJ_ID)

        if not success:
            logger.error('%s Unable to query UserAccessStore. %s', LOG_PREFIX, rval)
            return False

        acls = json.loads(rval)
        logger.info('%s Fetched ACLs: {}'.format(acls), LOG_PREFIX)

        for acl in acls:
            acl_obj_ids.append(acl[ACL.STORE_KEY_OBJ_ID])

        for object_id in object_ids:
            if acl_obj_ids.count(object_id) == 0:
                logger.info("%s ACL object_id {} has no occurence in acl store".format(object_id), LOG_PREFIX)
                logger.info("%s Creating new ACL for object_id {}".format(object_id), LOG_PREFIX)
                acl = ACL(object_id, object_app, object_store, object_type, DEFAULT_OWNER, session_key, logger)
                success, rval = acl.set()
                if not success:
                    logger.error('%s Failed to create ACL for object_id {}'.format(object_id), LOG_PREFIX)
                    handle_status = False
                else:
                    logger.info('%s Successfully created ACL for object_id {} with _key {}'.format(object_id, rval),
                                LOG_PREFIX)

            elif acl_obj_ids.count(object_id) > 1:
                count = acl_obj_ids.count(object_id)
                logger.info("%s ACL object_id {} has {} occurences in acl store".format(object_id, count), LOG_PREFIX)
                logger.info("%s Deleting all ACLs for object_id {}".format(object_id), LOG_PREFIX)
                for i in range(count):
                    acl = ACL(object_id, object_app, object_store, object_type, DEFAULT_OWNER, session_key, logger)
                    acl_id = acl.get_acl_id()
                    logger.info(
                        "%s Delete acl with obj_id {}, acl_id {} iteration {} start".format(object_id, acl_id, i),
                        LOG_PREFIX)
                    success, rval = acl.delete(acl_id)
                    if not success:
                        logger.error('%s Failed to delete ACL for obj_id {}, acl_id {}'.format(object_id, acl_id),
                                     LOG_PREFIX)
                        handle_status = False
                    else:
                        logger.info('%s Successfully deleted ACL for obj_id {}, acl_id {}'.format(object_id, acl_id),
                                    LOG_PREFIX)
                    logger.info(
                        "%s Delete acl with obj_id {}, acl_id {} iteration {} complete".format(object_id, acl_id, i),
                        LOG_PREFIX)
                acl = ACL(object_id, object_app, object_store, object_type, DEFAULT_OWNER, session_key, logger)
                logger.info("%s Creating a new ACLs for object_id {}, ".format(object_id), LOG_PREFIX)
                success, rval = acl.set()
                if not success:
                    logger.error('%s Failed to create ACL for object_id {}'.format(object_id), LOG_PREFIX)
                    handle_status = False
                else:
                    logger.info('%s Successfully created ACL for object_id {} with _key {}'.format(object_id, rval),
                                LOG_PREFIX)
            else:
                logger.info("%s ACL object_id {} has 1 occurence in acl store".format(object_id), LOG_PREFIX)

        logger.info('%s Handle missing acls finish for object_type {}'.format(object_type), LOG_PREFIX)

        return handle_status


##
## Decorators for consumption by RESTful endpoints
##
class CheckUserAccess(object):
    '''
    Decorator for handling user access
    '''

    def __init__(
            self,
            capability_matrix,
            object_type,
            logger,
    ):
        '''
        @param self: The self param

        @param capability_matrix: dictionary of capabilities key'ed by object_type which is specific to an app
            the object name is app specific i.e. its unknown..
            however, the value is expected to be a dictionary consisting of keys 'read'/'write'/'delete'
            Ex: {
                    'glass_table' : {
                        'read':'read_itsi_glass_table'.
                        'write':'write_itsi_glass_table',
                        'delete':'delete_itsi_glass_table'
                        },
                    'deep_dive': {
                        'read':'read_itsi_deep_dive',
                        'write':'write_itsi_deep_dive',
                        'delete':'delete_itsi_deep_dive'
                        },
                    ...
                }
        @param type: dict

        @param logger: caller's logger object
        @param type: logger
        '''
        self.capability_matrix = capability_matrix
        self.logger = logger
        self.object_type = object_type
        self.supported_ops = ['read', 'write', 'delete']

        self.usage_msg = (
            'Expecting caller of this decorator, potentially your endpoint, to pass the following params:-\n'
            '- valid non-None dict indicating capabilities of various object types of the caller in the following format:\n'
            '   {"<object_type>": {"read": <capability_name>, "write": <capability_name>, "delete": <capability_name>}, ...}\n'
            '   Ex: {"glass_table": {"read": read_itsi_glass_table", "write": "write_itsi_glass_table", "delete": "delete_itsi_glass_table"}, ...}\n'
            '- callback method for fetching username - should take no params & return a string indicating the username to work on\n'
            '- callback method for fetching session_key - should take no params & return a string containing a non-Empty splunkd session key\n'
            '- callback method for fetching operation - should take no params & return a string with one of the following values - "read" or "write" or "delete"\n'
            '- valid logger object')

    def is_function(self, obj):
        '''
        Utility to check if obj is a function
        '''
        return hasattr(obj, '__call__')

    def __call__(self, f):
        '''
        @param self: the self parameter
        @param f: function being decorated. Call f if user has capability
        '''

        def wrapper(decorated_self, *args, **kwargs):
            """
            The decorator invoked wrapper for the decorated function (REST handler)
            This wrapper does the access check on the REST request and throws an exception if access is denied

            @type: object
            @param decorated_self: the self reference to the decorated function instance

            @type: tuple
            *args: args from the decorated function

            @type: dict
            **kwargs: kwargs from the decorated function

            @rtype: variable
            @return: return value from invoke of the decorated function
            @raises UserAccessError on access check failure
            """

            LOG_PREFIX = '[CheckUserAccess.__call__ wrapper()] '
            user_is_capable = False

            username = None
            session_key = None
            operation = None
            object_type = None
            owner = None

            # Get request info from specific implementation of controller if available
            if hasattr(decorated_self, 'get_rest_request_info'):
                try:
                    username, session_key, object_type, operation, owner = decorated_self.get_rest_request_info(args,
                                                                                                                kwargs)

                    object_type = self.object_type if self.object_type is not None else object_type
                except Exception as e:
                    # blanket catch, validated below
                    self.logger.exception(e)
                    pass

            # Get object owner for glass tables or deep dives
            if hasattr(decorated_self, 'get_privatizeable_object_types'):
                if object_type in decorated_self.get_privatizeable_object_types():
                    owner = UserAccess.get_current_owner(kwargs, username, owner, session_key, self.logger, object_type)

            if username is None:
                message = 'Unable to obtain username for the requested operation "{}".'.format(operation)
                self.logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=500, message=message)

            if object_type is None or len(object_type.strip()) == 0:
                message = 'Expecting non-None, non-empty object_type as an argument to your app\'s method' \
                          'being decorated. kwargs - {}'.format(kwargs)
                self.logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=400, message=message)

            if operation is None:
                message = 'Unable to obtain desired operation for the requested.'
                self.logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=500, message=message)
            if operation not in self.supported_ops:
                message = 'Unsupported operation "{0}". Supported operations are - {1}.'.format(operation,
                                                                                                self.supported_ops)
                self.logger.error('', LOG_PREFIX, message)
                raise UserAccessError(status=500, message=message)

            if session_key is None:
                message = 'Unable to obtain session key for the requested operation "{}".'.format(operation)
                self.logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=500, message=message)

            if owner is None:
                message = 'No "owner" in received json. No ownership based checks will be enforced.'
                self.logger.warn('%s %s', LOG_PREFIX, message)
                self.logger.debug('%s Received kwargs %s', LOG_PREFIX, kwargs)

            # fetch capability name
            capability_name, message = UserAccess.fetch_capability_name(self.capability_matrix, object_type, operation,
                                                                        self.logger)
            if capability_name is None:
                self.logger.error('%s Unable to find capability. Error - %s', LOG_PREFIX, message)
                raise UserAccessError(status=400, message=message)

            self.logger.info(
                '%s Access Control Request received. Metadata collected/inferred: username- %s, owner- %s, object_type- %s, operation- %s, fetched capability- %s',
                LOG_PREFIX,
                username,
                owner,
                object_type,
                operation,
                capability_name)

            # check if user is capable
            try:
                user_is_capable = UserAccess.is_user_capable(username, capability_name, session_key, self.logger,
                                                             owner=owner)
            except BadRequest as e:
                message = '{}'.format(e)
                raise UserAccessError(status=400, message=message)
            except Exception as e:
                message = '{}'.format(e)
                raise UserAccessError(status=500, message=message)

            if user_is_capable:
                message = '"{0}" has the capability "{1}".'.format(username, capability_name)
                self.logger.info('%s %s', LOG_PREFIX, message)
                return f(decorated_self, *args, **kwargs)
            else:
                message = '"{0}" does not have the capability "{1}".'.format(username, capability_name)
                self.logger.error('%s %s', LOG_PREFIX, message)
                raise UserAccessError(status=403, message=message)
            return f(decorated_self, *args, **kwargs)

        return wrapper
