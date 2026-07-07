import base64
import io
import json
from os import path
from zipfile import ZipFile

from ite_models.ite_model_procedure import (IteProcedure, IteProcedureNotFoundException)
from ite_models.ite_model_use_case import (IteUseCase, IteUseCaseNotFoundException)
from ite_models.ite_model_use_case_family import (IteUseCaseFamily, IteUseCaseFamilyNotFoundException)


class IteZipHandler:
    @staticmethod
    def write_procedure_contents_to_zip(procedure_raw, zip_file_obj, procedure_path):
        """
        Write procedure contents to a specific directory in the source file format.

        :param procedure_raw: (dict) Raw representation of a procedure
        :param zip_file_obj: (ZipFile) Zip file object
        :param procedure_path: (str) Path for procedure contents to go into within zip_file_obj
        """
        def write_json_to_zip(json_obj, zip_file_obj, filename):
            procedure_buffer = io.BytesIO()
            procedure_bytes = bytes(json.dumps(json_obj, indent=4), encoding='ascii')
            procedure_buffer.write(procedure_bytes)
            zip_file_obj.writestr(filename, procedure_buffer.getvalue())

        # Shaping procedure content
        content = {
            'title': procedure_raw['title'],
        }
        for k, v in procedure_raw['content'].items():
            content[k] = v
        content['maturity_stage'] = procedure_raw['maturity_stage_id']

        write_json_to_zip(content, zip_file_obj, path.join(procedure_path, 'content.json'))
        write_json_to_zip(procedure_raw['data_sources'], zip_file_obj, path.join(procedure_path, 'data_sources.json'))

    @staticmethod
    def zip_procedure(procedure_id):
        """
        Return a zipped file containing the specified procedure.

        :param procedure_id: (str) Procedure ID
        :return: Base64 encoded binary data (zip file)
        """
        procedure = IteProcedure.get(procedure_id)
        if not procedure:
            raise IteProcedureNotFoundException(procedure_id)
        use_case = IteUseCase.get(procedure.use_case_id)
        if not use_case:
            raise IteUseCaseNotFoundException(procedure.use_case_id)
        use_case_family = IteUseCaseFamily.get(use_case.use_case_family_id)
        if not use_case_family:
            raise IteUseCaseFamilyNotFoundException(use_case.use_case_family_id)
        procedure_raw = procedure.to_raw()

        procedure_buffer = io.BytesIO()
        procedure_path = path.join(use_case_family.title, use_case.title, procedure.title)
        with ZipFile(procedure_buffer, 'w') as zip_file:
            IteZipHandler.write_procedure_contents_to_zip(procedure_raw, zip_file, procedure_path)
        return base64.b64encode(procedure_buffer.getvalue()).decode('ascii')

    @staticmethod
    def zip_use_case(use_case_id):
        """
        Return a zipped file containing the specified use case and any procedures contained within.

        :param use_case_id: (str) Use case ID
        :return: Base64 encoded binary data (zip file)
        """
        use_case = IteUseCase.get(use_case_id)
        if not use_case:
            raise IteUseCaseNotFoundException(use_case_id)
        use_case_family = IteUseCaseFamily.get(use_case.use_case_family_id)
        if not use_case_family:
            raise IteUseCaseFamilyNotFoundException(use_case.use_case_family_id)

        use_case_buffer = io.BytesIO()
        use_case_path = path.join(use_case_family.title, use_case.title, '')
        with ZipFile(use_case_buffer, 'w') as zip_file:
            # Write use case folder (necessary if no procedures in use case)
            zip_file.writestr(use_case_path, '')
            for procedure in IteProcedure.find_all_by(use_case=[use_case_id]):
                procedure_raw = procedure.to_raw()
                IteZipHandler.write_procedure_contents_to_zip(
                    procedure_raw, zip_file, path.join(use_case_path, procedure_raw['title']),
                )
        return base64.b64encode(use_case_buffer.getvalue()).decode('ascii')
