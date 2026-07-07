# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object

import ite_path_inject  # noqa
from ite_models.ite_model_maturity_stage import IteMaturityStage, IteMaturityStageNotFoundException
from ite_models.ite_model_procedure import IteProcedure
from ite_models.ite_model_use_case import IteUseCase
from ite_models.ite_model_use_case_family import IteUseCaseFamily
from logging_utils import log

logger = log.getLogger()


class IteMaturityStageInterfaceImpl(object):
    def handle_get(self, maturity_stage_id):
        maturity_stage = IteMaturityStage.get(maturity_stage_id)
        if not maturity_stage:
            raise IteMaturityStageNotFoundException('Maturity Stage %s not found' % maturity_stage_id)
        response = maturity_stage.to_raw()
        return response

    def handle_get_use_case_family_breakdown(self):
        """
        Returns the number of procedures that belong to each maturity stage and use case family combination.

        :return:  dict of dicts
        Ex:
            {
                "diagnostic": {                       // Maturity stage key
                    "cloud_infrastructure": 3,        // Use case family key, number of procedures
                    "storage": 0,
                    "server_and_os": 2,
                    "network": 5,
                    "database": 1,
                    "application": 1
                },
                "descriptive": {
                    "cloud_infrastructure": 0,
                    "storage": 4,
                    "server_and_os": 3,
                    "network": 0,
                    "database": 0,
                    "application": 1
                }
            }
        """
        response = {}
        # Initialize response
        maturity_stages = IteMaturityStage.load(count=0)
        use_case_families = IteUseCaseFamily.load(count=0)
        for maturity_stage in maturity_stages:
            response[maturity_stage.key] = {
                use_case_family.key: 0 for use_case_family in use_case_families
            }

        # Set up dictionary to quickly link use case keys to use case family keys
        use_case_family_lookup = {}
        use_cases = IteUseCase.load(count=0)
        for use_case in use_cases:
            use_case_family_lookup[use_case.key] = use_case.use_case_family_id

        # Generate counts
        procedures = IteProcedure.load(count=0)
        for procedure in procedures:
            use_case_family = use_case_family_lookup[procedure.use_case_id]
            response[procedure.maturity_stage_id][use_case_family] += 1
        return response

    def handle_load(self, request):
        count = request.query.get('count', 0)
        offset = request.query.get('offset', 0)
        sort_key = request.query.get('sort_key', '')
        sort_dir = request.query.get('sort_dir', 'asc')
        maturity_stages = IteMaturityStage.load(
            count=count,
            offset=offset,
            sort_key=sort_key,
            sort_dir=sort_dir,
        )
        response = [maturity_stage.to_raw() for maturity_stage in maturity_stages]
        return response
