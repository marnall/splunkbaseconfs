# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object

try:
    import http.client as httplib
except ImportError:
    import httplib

from logging_utils import log
from rest_handler.exception import BaseRestException
from rest_handler.session import session
from service_manager.splunkd.conf import ConfManager
from solnlib import user_access

import ite_path_inject  # noqa
import ite_constants
from ite_utils import (get_server_uri, parse_boolean)

logger = log.getLogger()


class IteInternalBadRequestException(BaseRestException):
    def __init__(self, msg):
        super(IteInternalBadRequestException, self).__init__(httplib.BAD_REQUEST, msg)


class IteInternalForbiddenException(BaseRestException):
    def __init__(self, msg):
        super(IteInternalForbiddenException, self).__init__(httplib.FORBIDDEN, msg)


class IteInternalNotFoundException(BaseRestException):
    def __init__(self, msg):
        super(IteInternalNotFoundException, self).__init__(httplib.NOT_FOUND, msg)


class IteInternalInterfaceImpl(object):
    def handle_put_feature_flag(self, request, flag_id):
        if ite_constants.ITE_EDIT_OBJECTS_CAPABILITY not in user_access.get_user_capabilities(
                session['authtoken'], session['user'],
        ):
            raise IteInternalForbiddenException(
                'Feature flag toggling only available to users with the %s capability' %
                ite_constants.ITE_EDIT_OBJECTS_CAPABILITY
            )
        if flag_id not in ite_constants.FEATURE_FLAGS:
            raise IteInternalNotFoundException('Feature flag %s not supported' % flag_id)
        disabled = parse_boolean(request.data.get('disabled', ''))
        if disabled is None:
            raise IteInternalBadRequestException('Body must contain "disabled" field with a Boolean value')

        conf_manager = ConfManager(ite_constants.FEATURE_FLAGS_CONF, get_server_uri(), session['authtoken'],
                                   ite_constants.APP_NAME)

        if conf_manager.get_stanza(flag_id):
            response = conf_manager.update_existing_stanza(flag_id, {'disabled': disabled})
        else:
            response = conf_manager.write_new_stanza(flag_id, {'disabled': disabled})
        return response
