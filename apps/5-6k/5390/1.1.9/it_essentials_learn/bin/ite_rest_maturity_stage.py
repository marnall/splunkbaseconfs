# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_maturity_stage_impl import IteMaturityStageInterfaceImpl

logger = log.getLogger()


class IteMaturityStageInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/maturity_stage', methods=['GET'])
    def load_maturity_stages(self, request):
        interface_impl = IteMaturityStageInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /maturity_stage')
            response = interface_impl.handle_load(request)
            return http.client.OK, response

    @route('/maturity_stage/{maturity_stage_id}', methods=['GET'])
    def get_maturity_stage(self, request, maturity_stage_id):
        interface_impl = IteMaturityStageInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /maturity_stage/%s' % maturity_stage_id)
            response = interface_impl.handle_get(maturity_stage_id)
            return http.client.OK, response

    @route('/use_case_family_breakdown', methods=['GET'])
    def get_use_case_family_breakdown(self, request):
        interface_impl = IteMaturityStageInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case_family_breakdown')
            response = interface_impl.handle_get_use_case_family_breakdown()
            return http.client.OK, response
