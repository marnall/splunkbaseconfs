# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import ite_path_inject  # noqa

import http.client
import json
from urllib.parse import unquote

import splunk.rest
from rest_handler.exception import BaseRestException
from rest_handler.session import session
from service_manager.splunkd.conf import ConfManager
from solnlib import user_access
from solnlib.utils import retry
from splunklib.binding import HTTPError

import ite_constants


class KVStoreNotReadyException(Exception):
    pass


class IteFeatureFlagRestrictedException(BaseRestException):
    def __init__(self, msg):
        super(IteFeatureFlagRestrictedException, self).__init__(http.client.FORBIDDEN, msg)


# Splunk-related utilities
@retry(retries=10, exceptions=[KVStoreNotReadyException, HTTPError])
def wait_until_kvstore_is_ready(session_key):
    resp, content = splunk.rest.simpleRequest('kvstore/status', method='GET',
                                              sessionKey=session_key,
                                              getargs={'output_mode': 'json'})
    parsed_content = json.loads(content)
    status = parsed_content['entry'][0]['content']['current']['status']
    if status != 'ready':
        raise KVStoreNotReadyException('KVStore is not ready - last checked status: "%s"' % status)


def get_server_uri():
    return splunk.rest.makeSplunkdUri().rstrip('/')


# App-specific utilities
def feature_flag_restricted(flag_id):
    def decorator_unrestricted(func):
        def wrapped_func(*args, **kwargs):
            conf_manager = ConfManager(ite_constants.FEATURE_FLAGS_CONF, get_server_uri(), session['authtoken'],
                                       ite_constants.APP_NAME)
            flag_stanza = conf_manager.get_stanza(flag_id)
            if flag_stanza and not flag_stanza['entry'][0]['content']['disabled']:
                return func(*args, **kwargs)
            raise IteFeatureFlagRestrictedException('Feature flag %s is disabled' % flag_id)

        return wrapped_func

    return decorator_unrestricted


def rbac_restricted(required_capability=None):
    def decorator_unrestricted(func):
        def wrapped_func(*args, **kwargs):
            if required_capability and required_capability in \
                    user_access.get_user_capabilities(session['authtoken'], session['user']):
                return func(*args, **kwargs)
            raise IteFeatureFlagRestrictedException('User %s lacks %s capability' %
                                                    (session['user'], required_capability))

        return wrapped_func

    return decorator_unrestricted


# Generic utilities
def urlencoded_string_to_json(target_str):
    unencoded_str = unquote(target_str)
    try:
        rv = json.loads(unencoded_str)
    except ValueError:
        # String represents a single string value
        rv = [unencoded_str]
    return rv


def parse_boolean(val):
    if val.lower() == 'true' or val == '1':
        return True
    elif val.lower() == 'false' or val == '0':
        return False
    else:
        return None
