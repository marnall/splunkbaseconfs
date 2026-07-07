# Copyright (C) 2005-2026 Splunk Inc. All Rights Reserved.

import ite_path_inject  # noqa

import json
import os
from os.path import dirname
import logging
import sys
import shutil
from collections import OrderedDict
import errno

from ite_models.ite_schema_maturity_stage import IteMaturityStageSchema, IteMaturityStageParameterException
from ite_models.ite_schema_use_case_family import IteUseCaseFamilySchema, IteUseCaseFamilyParameterException
from ite_models.ite_schema_use_case import IteUseCaseSchema, IteUseCaseParameterException
from ite_models.ite_schema_procedure import IteProcedureSchema, IteProcedureParameterException
from ite_models.utils import get_object_primary_key_from_value
from ite_models.ite_validation import IteContentValidationViolationSummary, IteObjectViolationRecord


if __name__ == '__main__':
    # Create logger that logs to STDOUT
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
else:
    # if the module is not the main module (i.e. imported by other ITE routine)
    # set logger to the corresponding ITE logger
    from logging_utils.log import getLogger
    logger = getLogger()


# NOTE: in python3.4 `Enum` is introduced and we should switch to that
# once we don't need to support python2 anymore
class DirectoryType(object):
    USE_CASE_FAMILY = 1
    USE_CASE = 2
    PROCEDURE = 3


class IteContentFilesAggregator(object):
    """
    IteContentFilesAggregator aggregates content files from a source directory into aggregated files
    in a destination directory. During the aggregation process the source data is transformed into their
    corresponding storage format.
    """

    def __init__(self, source_contents_dir, dest_contents_dir):
        self.source_contents_dir = source_contents_dir
        self.dest_contents_dir = dest_contents_dir
        try:
            os.makedirs(self.dest_contents_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        self.violation_tracker = IteContentValidationViolationSummary(logger=logger)

    def aggregate_to_dest(self):
        """
        aggregate_to_dest aggregates the contents from source and writes the results to destination
        """
        try:
            agg_contents = self.get_aggregated_contents()

            self.write_to_file(list(agg_contents['maturity_stages'].values()), 'maturity_stages.json')
            self.write_to_file(list(agg_contents['use_case_families'].values()), 'use_case_families.json')
            self.write_to_file(list(agg_contents['use_cases'].values()), 'use_cases.json')
            self.write_to_file(list(agg_contents['procedures'].values()), 'procedures.json')

            logger.info('Finished aggregating contents into %s', self.dest_contents_dir)
        except Exception:
            logger.exception('Failed to run content files aggregator')

            self.clean_dest_dir()
            sys.exit(1)

    def get_aggregated_contents(self):
        """
        get_aggregated_contents aggregates contents from the source

        :return: (dict) A dictionary of aggregated contents with key being the content type
        """
        contents = dict(
            maturity_stages=OrderedDict(),
            use_case_families=OrderedDict(),
            use_cases=OrderedDict(),
            procedures=OrderedDict()
        )
        logger.info('Reading contents from %s ...' % self.source_contents_dir)

        mat_stages_schemas = self.derive_maturity_stage_schemas(
            os.path.join(self.source_contents_dir, 'maturity_stages.json')
        )
        for ms in mat_stages_schemas:
            if ms is not None:
                contents['maturity_stages'][ms.key] = ms

        for root, dir_names, file_names in os.walk(self.source_contents_dir, topdown=True, followlinks=False):
            level = self._get_relative_level_to_source(root)

            if level == DirectoryType.USE_CASE_FAMILY:
                fam = self.derive_use_case_family_schema(root)
                if fam is not None:
                    contents['use_case_families'][fam.key] = fam

            elif level == DirectoryType.USE_CASE:
                use_case = self.derive_use_case_schema(root)
                if use_case is not None:
                    contents['use_cases'][use_case.key] = use_case

            elif level == DirectoryType.PROCEDURE:
                procedure = self.derive_procedure_schema(root)
                if procedure is not None:
                    contents['procedures'][procedure.key] = procedure

        self.validate_contents_foreign_key_ref_integrity(contents)
        if not self.violation_tracker.is_empty():
            self.violation_tracker.dump(output_format='junit_xml')
            logger.error('Content validation failed. Refer to the output summary and fix the contents accordingly.')
            sys.exit(1)

        self.convert_contents_to_raw(contents)

        return contents

    def clean_dest_dir(self):
        logger.info('Cleaning destination directory at %s...', self.dest_contents_dir)
        shutil.rmtree(self.dest_contents_dir, ignore_errors=True)

    def derive_maturity_stage_schemas(self, mat_stages_file_path):
        """
        derive_maturity_stage_schemas derives maturity stages data based on the input
        maturity stages files path

        :return: (list) A list of maturity stage schema objects
        """
        schemas = []
        with open(mat_stages_file_path, 'rb') as f:
            stages = json.loads(f.read())
            for s in stages:
                content = dict(**s)
                key = get_object_primary_key_from_value(s['title'])
                del content['title']
                try:
                    stage_obj = IteMaturityStageSchema(
                        key=key,
                        title=s['title'],
                        content=content
                    )
                    schemas.append(stage_obj)
                except IteMaturityStageParameterException as e:
                    self.violation_tracker.add_record(IteMaturityStageSchema.__name__, key, e)
        return schemas

    def derive_use_case_family_schema(self, use_case_fam_dir_path):
        """
        derive_use_case_family_schema derives use case family data based on the input directory
        that represents a use case family

        :return: (IteUseCaseFamilySchema) A use case family schema object
        """
        dir_name = os.path.basename(use_case_fam_dir_path)
        key = get_object_primary_key_from_value(dir_name)
        try:
            fam_obj = IteUseCaseFamilySchema(
                key=key,
                title=dir_name
            )
            return fam_obj
        except IteUseCaseFamilyParameterException as e:
            self.violation_tracker.add_record(IteUseCaseFamilySchema.__name__, key, e)

    def derive_use_case_schema(self, use_case_dir_path):
        """
        derive_use_case_schema derives use case data based on the input directory
        that represents a use case

        :return: (IteUseCaseSchema) A use case schema object
        """
        dir_name = os.path.basename(use_case_dir_path)
        fam_dir_name = os.path.basename(dirname(use_case_dir_path))
        key = get_object_primary_key_from_value(dir_name)
        try:
            use_case_obj = IteUseCaseSchema(
                key=key,
                use_case_family_id=get_object_primary_key_from_value(fam_dir_name),
                title=dir_name
            )
            return use_case_obj
        except IteUseCaseParameterException as e:
            self.violation_tracker.add_record(IteUseCaseSchema.__name__, key, e)

    def derive_procedure_schema(self, procedure_dir_path):
        """
        derive_procedure_schema drives procedure data based on the input directory and its contents
        that represent a procedure.

        :return: (IteProcedureSchema) A procedure schema object
        """
        dir_name = os.path.basename(procedure_dir_path)
        use_case_dir_name = os.path.basename(dirname(procedure_dir_path))
        with open(os.path.join(procedure_dir_path, 'content.json'), 'rb') as f:
            content = json.loads(f.read())

            maturity_stage = content.get('maturity_stage')
            if maturity_stage:
                del content['maturity_stage']

            title = content.get('title')
            if title:
                del content['title']

            key = get_object_primary_key_from_value(dir_name)

            data_sources = []
            ds_path = os.path.join(procedure_dir_path, 'data_sources.json')
            if os.path.exists(ds_path):
                with open(ds_path, 'rb') as f:
                    data_sources = json.loads(f.read())

            try:
                procedure_obj = IteProcedureSchema(
                    key=key,
                    title=title,
                    content=content,
                    data_sources=data_sources,
                    use_case_id=get_object_primary_key_from_value(use_case_dir_name),
                    favorited_by=[],
                    maturity_stage_id=get_object_primary_key_from_value(maturity_stage)
                )
                return procedure_obj
            except IteProcedureParameterException as e:
                self.violation_tracker.add_record(IteProcedureSchema.__name__, key, e)

    def validate_contents_foreign_key_ref_integrity(self, aggregated_contents):
        # we only needed to validate procedures and use cases because other objects
        # in contents don't contain foreign key reference
        self._validate_procedure_foreign_key_ref(aggregated_contents)
        self._validate_use_case_foreign_key_ref(aggregated_contents)

    def _validate_procedure_foreign_key_ref(self, aggregated_contents):
        for procedure in aggregated_contents['procedures'].values():
            if procedure.maturity_stage_id not in aggregated_contents['maturity_stages']:
                self.violation_tracker.add_record(
                    IteProcedureSchema.__name__,
                    procedure.key,
                    IteObjectViolationRecord({'maturity_stage_id': [
                        'Maturity stage referenced with id %s does not exist.' % procedure.maturity_stage_id
                    ]})
                )

            if procedure.use_case_id not in aggregated_contents['use_cases']:
                self.violation_tracker.add_record(
                    IteProcedureSchema.__name__,
                    procedure.key,
                    IteObjectViolationRecord({'use_case_id': [
                        'Use case referenced with id %s does not exist.' % procedure.use_case_id
                    ]})
                )

    def _validate_use_case_foreign_key_ref(self, aggregated_contents):
        for use_case in aggregated_contents['use_cases'].values():
            if use_case.use_case_family_id not in aggregated_contents['use_case_families']:
                self.violation_tracker.add_record(
                    IteUseCaseSchema.__name__,
                    use_case.key,
                    IteObjectViolationRecord({'use_case_family_id': [
                        'Use case family referenced with id %s does not exist.' % use_case.use_case_family_id
                    ]})
                )

    def convert_contents_to_raw(self, aggregated_contents):
        for obj_type in aggregated_contents.keys():
            for key, schema in aggregated_contents[obj_type].items():
                aggregated_contents[obj_type][key] = schema.to_raw()

    def _get_relative_level_to_source(self, path):
        """
        _get_relative_level_to_source gets the relative depth of the input path to the source directory.
        This function can be used to determine content type based on its directory's depth.

        :param path: (str) A file path
        """
        rel_path = os.path.relpath(path, start=self.source_contents_dir)
        level = len([c for c in rel_path.split(os.path.sep) if c != '' and c != '.'])
        return level

    def write_to_file(self, data, filename):
        """
        write_to_file writes the input data into a file specified by the input filename in the
        destination directory.

        :param data: (list) A list of objects to save
        :param filename: (str) file name
        """
        filepath = os.path.join(self.dest_contents_dir, filename)
        logger.info('Aggregating data into %s - objects count: %d' % (filepath, len(data)))

        with open(filepath, 'wb') as f:
            data = json.dumps(data).encode('utf-8')
            f.write(data)


if __name__ == '__main__':
    app_dir = dirname(dirname(__file__))
    src_contents_dir = os.path.join(dirname(app_dir), 'use_case_lib')
    dest_contents_dir = os.path.join(app_dir, 'contents', 'default')
    agg = IteContentFilesAggregator(
        src_contents_dir,
        dest_contents_dir
    )
    agg.aggregate_to_dest()
