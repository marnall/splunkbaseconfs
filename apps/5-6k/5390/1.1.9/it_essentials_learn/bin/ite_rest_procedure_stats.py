# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'it_essentials_learn', 'bin']))  # noqa
import ite_path_inject  # noqa

import http.client

from logging_utils import log
from rest_handler.rest_interface_splunkd import route

import ite_rest_interface_splunkd
from ite_rest_procedure_stats_impl import IteProcedureStatsInterfaceImpl

logger = log.getLogger()


class IteProcedureStatsInterface(ite_rest_interface_splunkd.IteRestInterfaceSplunkd):
    @route('/tracking', methods=['POST'])
    def report_procedure_statistic(self, request):
        interface_impl = IteProcedureStatsInterfaceImpl()
        logger.info('POST on /tracking')
        response = interface_impl.handle_tracking(request)
        return http.client.CREATED, response

    @route('/data/{procedure_id}', methods=['GET'])
    def get_procedure_statistic(self, request, procedure_id):
        interface_impl = IteProcedureStatsInterfaceImpl()
        logger.info('GET on /data/%s' % procedure_id)
        response = interface_impl.handle_get(request, procedure_id)
        return http.client.OK, response
