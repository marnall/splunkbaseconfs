# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_use_case_family_impl import IteUseCaseFamilyInterfaceImpl

logger = log.getLogger()


class IteUseCaseFamilyInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/use_case_family', methods=['GET'])
    def load_use_case_families(self, request):
        interface_impl = IteUseCaseFamilyInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case_family')
            response = interface_impl.handle_load(request)
            return http.client.OK, response

    @route('/use_case_family/{use_case_family_id}', methods=['GET'])
    def get_use_case_family(self, request, use_case_family_id):
        interface_impl = IteUseCaseFamilyInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case_family/%s' % use_case_family_id)
            response = interface_impl.handle_get(use_case_family_id)
            return http.client.OK, response
