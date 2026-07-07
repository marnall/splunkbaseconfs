# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object

from logging_utils import log

import ite_path_inject  # noqa
import ite_constants
from ite_models.ite_model_use_case import IteUseCase, IteUseCaseNotFoundException
from ite_models.ite_model_use_case_family import IteUseCaseFamily, IteUseCaseFamilyNotFoundException
from ite_utils import (feature_flag_restricted, rbac_restricted)
from ite_zip_handler import IteZipHandler

logger = log.getLogger()


class IteUseCaseInterfaceImpl(object):
    @rbac_restricted(ite_constants.ITE_EDIT_OBJECTS_CAPABILITY)
    @feature_flag_restricted('edit_mode')
    def handle_create(self, request):
        title = request.data.get('title')
        use_case_family_id = request.data.get('use_case_family_id')

        use_case_family = IteUseCaseFamily.get(use_case_family_id)
        if not use_case_family:
            raise IteUseCaseFamilyNotFoundException(use_case_family_id)

        use_case = IteUseCase.create(title, use_case_family_id)
        response = {
            '_key': use_case.key,
        }
        return response

    def handle_get(self, use_case_id):
        use_case = IteUseCase.get(use_case_id)
        if not use_case:
            raise IteUseCaseNotFoundException(use_case_id)
        response = use_case.to_raw()
        return response

    def handle_load(self, request):
        count = request.query.get('count', 0)
        offset = request.query.get('offset', 0)
        sort_key = request.query.get('sort_key', '')
        sort_dir = request.query.get('sort_dir', 'asc')
        use_cases = IteUseCase.load(
            count=count,
            offset=offset,
            sort_key=sort_key,
            sort_dir=sort_dir,
        )
        response = [use_case.to_raw() for use_case in use_cases]
        return response

    def handle_download(self, use_case_id):
        headers = [
            ['Content-Type', 'application/zip'],
            ['Content-Disposition', 'attachment; filename=%s.zip' % use_case_id],
        ]
        return IteZipHandler.zip_use_case(use_case_id), headers
