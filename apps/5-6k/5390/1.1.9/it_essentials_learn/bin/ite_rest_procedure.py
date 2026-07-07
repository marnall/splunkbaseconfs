# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_procedure_impl import IteProcedureInterfaceImpl

logger = log.getLogger()


class IteProcedureInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/procedure', methods=['GET', 'POST'])
    def load_or_create_procedures(self, request):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /procedure')
            response = interface_impl.handle_load(request)
            return http.client.OK, response
        elif request.method == 'POST':
            logger.info('POST on /procedure')
            response = interface_impl.handle_create(request)
            return http.client.CREATED, response

    @route('/procedure/{procedure_id}', methods=['GET', 'PUT'])
    def get_or_update_procedure(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /procedure/%s' % procedure_id)
            response = interface_impl.handle_get(request, procedure_id)
            return http.client.OK, response
        elif request.method == 'PUT':
            logger.info('PUT on /procedure/%s' % procedure_id)
            response = interface_impl.handle_update(request, procedure_id)
            return http.client.OK, response

    @route('/procedure/{procedure_id}/deploy', methods=['POST'])
    def toggle_procedure_deploy(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'POST':
            logger.info('POST on /procedure/%s/deploy' % procedure_id)
            response = interface_impl.handle_deploy(procedure_id)
            return http.client.OK, response

    @route('/procedure/{procedure_id}/download', methods=['GET'], is_file_download=True)
    def download_procedure(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /procedure/%s/download' % procedure_id)
            response, headers = interface_impl.handle_download(procedure_id)
            return http.client.OK, response, headers

    @route('/procedure/{procedure_id}/export', methods=['GET'], is_file_download=True)
    def export_by_id(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /procedure/%s/export' % procedure_id)
            response, headers = interface_impl.handle_export_by_id(request, procedure_id)
            return http.client.OK, response, headers

    @route('/procedure/{procedure_id}/favorite', methods=['POST'])
    def favorite_procedure(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'POST':
            logger.info('POST on /procedure/%s/favorite' % procedure_id)
            response = interface_impl.handle_favorite(procedure_id)
            return http.client.OK, response

    @route('/procedure/{procedure_id}/reset', methods=['POST'])
    def reset_procedure(self, request, procedure_id):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'POST':
            logger.info('POST on /procedure/%s/reset' % procedure_id)
            response = interface_impl.handle_reset(procedure_id)
            return http.client.OK, response

    @route('/data_sources', methods=['GET'])
    def load_data_sources(self, request):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /data_sources')
            response = interface_impl.handle_load_data_sources(request)
            return http.client.OK, response

    @route('/export', methods=['GET'], is_file_download=True)
    def bulk_export(self, request):
        interface_impl = IteProcedureInterfaceImpl()
        if request.method == 'GET':
            logger.info('GET on /export')
            response, headers = interface_impl.handle_bulk_export(request)
            return http.client.OK, response, headers
