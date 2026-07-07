# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

from builtins import object
try:
    import http.client as httplib
except ImportError:
    import httplib
import json

from logging_utils import log
from rest_handler.exception import BaseRestException

import ite_path_inject  # noqa
import ite_constants
from ite_exporter import IteProcedureExporter
from ite_models.ite_model_procedure import (
    IteProcedure,
    IteProcedureNotFoundException,
)
from ite_models.ite_model_use_case import IteUseCase, IteUseCaseNotFoundException
from ite_data_loader import IteProcedureInitializer
from ite_utils import (feature_flag_restricted, parse_boolean, rbac_restricted, urlencoded_string_to_json)
from ite_zip_handler import IteZipHandler

logger = log.getLogger()


class ProcedureAlreadyExistsException(BaseRestException):
    def __init__(self, msg):
        super(ProcedureAlreadyExistsException, self).__init__(httplib.BAD_REQUEST, msg)


def read_json_from_request_body(rbody, field):
    try:
        data = json.loads(rbody.get(field))
        return data
    except Exception as e:
        raise BaseRestException(httplib.BAD_REQUEST, 'Field "%s" must be valid JSON - Error: %s' % (field, e))


class IteProcedureInterfaceImpl(object):
    @staticmethod
    def format_procedure_response(procedure, username):
        formatted_procedure = procedure.to_raw()
        formatted_procedure['is_favorite'] = procedure.is_favorite
        del formatted_procedure['favorited_by']
        formatted_procedure['is_deployed'] = procedure.is_deployed
        del formatted_procedure['deployed']
        return formatted_procedure

    @rbac_restricted(ite_constants.ITE_EDIT_OBJECTS_CAPABILITY)
    @feature_flag_restricted('edit_mode')
    def handle_create(self, request):
        key = request.data.get('key')
        title = request.data.get('title')
        use_case_id = request.data.get('use_case_id')
        maturity_stage_id = request.data.get('maturity_stage_id')
        content = read_json_from_request_body(request.data, 'content')
        data_sources = read_json_from_request_body(request.data, 'data_sources')

        use_case = IteUseCase.get(use_case_id)
        if not use_case:
            raise IteUseCaseNotFoundException('Use Case %s not found' % use_case_id)

        if key:
            existing_procedure = IteProcedure.get(key)
            if existing_procedure:
                raise ProcedureAlreadyExistsException('Procedure with key %s already exists' % key)

        procedure = IteProcedure.create(
            key=key,
            title=title,
            content=content,
            use_case_id=use_case_id,
            maturity_stage_id=maturity_stage_id,
            data_sources=data_sources,
        )
        response = {
            '_key': procedure.key,
        }
        return response

    def handle_get(self, request, procedure_id):
        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)
        response = IteProcedureInterfaceImpl.format_procedure_response(procedure, request.session['user'])
        return response

    def handle_load(self, request):
        count = request.query.get('count', 0)
        offset = request.query.get('offset', 0)
        sort_key = request.query.get('sort_key', '')
        sort_dir = request.query.get('sort_dir', 'asc')
        use_case = urlencoded_string_to_json(request.query.get('use_case', '%5B%5D'))
        maturity_stage = urlencoded_string_to_json(request.query.get('maturity_stage', '%5B%5D'))
        data_source = urlencoded_string_to_json(request.query.get('data_source', '%5B%5D'))
        use_case_family = urlencoded_string_to_json(request.query.get('use_case_family', '%5B%5D'))
        title_search = request.query.get('title_search', '')
        is_favorite = request.query.get('is_favorite')
        is_deployed = request.query.get('is_deployed')
        # Convert is_favorite parameter to Boolean
        if is_favorite:
            is_favorite = parse_boolean(is_favorite)
        if is_deployed:
            is_deployed = parse_boolean(is_deployed)

        procedures = IteProcedure.find_all_by(
            use_case=use_case,
            maturity_stage=maturity_stage,
            data_source=data_source,
            use_case_family=use_case_family,
            title_search=title_search,
            is_favorite=is_favorite,
            count=count,
            offset=offset,
            sort_key=sort_key,
            sort_dir=sort_dir,
            is_deployed=is_deployed,
        )
        response = [IteProcedureInterfaceImpl.format_procedure_response(procedure, request.session['user']) for
                    procedure in procedures]
        return response

    @rbac_restricted(ite_constants.ITE_EDIT_OBJECTS_CAPABILITY)
    @feature_flag_restricted('edit_mode')
    def handle_update(self, request, procedure_id):
        title = request.data.get('title')
        use_case_id = request.data.get('use_case_id')
        maturity_stage_id = request.data.get('maturity_stage_id')
        content = read_json_from_request_body(request.data, 'content')
        data_sources = read_json_from_request_body(request.data, 'data_sources')

        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)

        procedure.title = title
        procedure.content = content
        procedure.use_case_id = use_case_id
        procedure.maturity_stage_id = maturity_stage_id
        procedure.data_sources = data_sources
        procedure.save()
        response = {
            '_key': procedure.key,
        }
        return response

    @rbac_restricted(ite_constants.ITE_EDIT_OBJECTS_CAPABILITY)
    @feature_flag_restricted('edit_mode')
    def handle_reset(self, procedure_id):
        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)

        ini_cls = IteProcedureInitializer()
        response = ini_cls.reset_destination_with_source(procedure.key)
        if response is None:
            raise IteProcedureNotFoundException(procedure_id, msg='Procedure %s not found in data loader for reset')
        return response

    def handle_favorite(self, procedure_id):
        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)
        procedure.toggle_favorite()
        return {
            '_key': procedure.key,
            'is_favorite': procedure.is_favorite,
        }

    def handle_deploy(self, procedure_id):
        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)
        procedure.toggle_deployed()
        return {
            '_key': procedure.key,
            'is_deployed': procedure.is_deployed,
        }

    def handle_load_data_sources(self, request):
        count = int(request.query.get('count', '0'))
        offset = int(request.query.get('offset', '0'))
        sort_key = request.query.get('sort_key', 'title')
        sort_dir = request.query.get('sort_dir', 'asc')
        return IteProcedure.load_data_sources(count=count, offset=offset, sort_key=sort_key, sort_dir=sort_dir)

    def handle_bulk_export(self, request):
        procedures = self.handle_load(request)
        file_type = request.query.get('filetype', 'docx')
        exporter = IteProcedureExporter(export_type=file_type)
        return exporter.export(procedures)

    def handle_export_by_id(self, request, procedure_id):
        procedure = self.handle_get(request, procedure_id)
        file_type = request.query.get('filetype', 'docx')
        exporter = IteProcedureExporter(export_type=file_type)
        return exporter.export([procedure])

    def handle_download(self, procedure_id):
        headers = [
            ['Content-Type', 'application/zip'],
            ['Content-Disposition', 'attachment; filename=%s.zip' % procedure_id],
        ]
        return IteZipHandler.zip_procedure(procedure_id), headers
