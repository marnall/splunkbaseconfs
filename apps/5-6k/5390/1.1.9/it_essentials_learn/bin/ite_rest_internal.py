# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_internal_impl import IteInternalInterfaceImpl

logger = log.getLogger()


class IteInternalInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/feature_flag/{flag_id}', methods=['PUT'])
    def put_feature_flag(self, request, flag_id):
        interface_impl = IteInternalInterfaceImpl()
        if request.method == 'PUT':
            logger.info('PUT on /feature_flag/%s' % flag_id)
            response = interface_impl.handle_put_feature_flag(request, flag_id)
            return http.client.OK, response
