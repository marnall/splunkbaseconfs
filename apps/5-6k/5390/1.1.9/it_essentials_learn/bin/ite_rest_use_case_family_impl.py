# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object

import ite_path_inject  # noqa
from ite_models.ite_model_use_case_family import IteUseCaseFamily, IteUseCaseFamilyNotFoundException
from logging_utils import log

logger = log.getLogger()


class IteUseCaseFamilyInterfaceImpl(object):
    def handle_get(self, use_case_family_id):
        use_case_family = IteUseCaseFamily.get(use_case_family_id)
        if not use_case_family:
            raise IteUseCaseFamilyNotFoundException(use_case_family_id)
        response = use_case_family.to_raw()
        return response

    def handle_load(self, request):
        count = request.query.get('count', 0)
        offset = request.query.get('offset', 0)
        sort_key = request.query.get('sort_key', '')
        sort_dir = request.query.get('sort_dir', 'asc')
        use_case_families = IteUseCaseFamily.load(
            count=count,
            offset=offset,
            sort_key=sort_key,
            sort_dir=sort_dir,
        )
        response = [use_case_family.to_raw() for use_case_family in use_case_families]
        return response
