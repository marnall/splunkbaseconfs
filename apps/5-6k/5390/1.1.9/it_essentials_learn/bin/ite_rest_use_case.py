# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_use_case_impl import IteUseCaseInterfaceImpl

logger = log.getLogger()


class IteUseCaseInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/use_case', methods=['GET', 'POST'])
    def load_or_create_use_cases(self, request):
        interface_impl = IteUseCaseInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case')
            response = interface_impl.handle_load(request)
            return http.client.OK, response
        elif request.method == 'POST':
            logger.info('POST on /use_case')
            response = interface_impl.handle_create(request)
            return http.client.CREATED, response

    @route('/use_case/{use_case_id}', methods=['GET'])
    def get_use_case(self, request, use_case_id):
        interface_impl = IteUseCaseInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case/%s' % use_case_id)
            response = interface_impl.handle_get(use_case_id)
            return http.client.OK, response

    @route('/use_case/{use_case_id}/download', methods=['GET'], is_file_download=True)
    def download_use_case(self, request, use_case_id):
        interface_impl = IteUseCaseInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /use_case/%s/download' % use_case_id)
            response, headers = interface_impl.handle_download(use_case_id)
            return http.client.OK, response, headers
