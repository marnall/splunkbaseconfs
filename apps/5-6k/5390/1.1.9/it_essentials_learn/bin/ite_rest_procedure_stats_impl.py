# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object

from ite_models.ite_model_procedure import IteProcedure, IteProcedureNotFoundException
from ite_models.ite_model_procedure_stats import IteProcedureStats
from ite_models.ite_schema_procedure_stats import VALID_ACTIONS


class IteProcedureStatsInterfaceImpl(object):

    def handle_tracking(self, request):
        procedure_id = request.data.get('procedure')
        action = request.data.get('action')

        if not IteProcedure.get(procedure_id):
            raise IteProcedureNotFoundException(procedure_id)

        procedure_stat = IteProcedureStats.track(procedure_id, action)
        response = {
            '_key': procedure_stat.key,
        }
        return response

    def handle_get(self, request, procedure_id):
        response = {v: False for v in VALID_ACTIONS}

        procedure_stat = IteProcedureStats.get(procedure_id)
        if procedure_stat:
            response.update({action: True for action in procedure_stat.stats})

        return response
