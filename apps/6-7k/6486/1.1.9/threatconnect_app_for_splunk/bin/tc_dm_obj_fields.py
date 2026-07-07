#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Datamodel Fields"""
# standard library
import json
import os
import sys

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand  # isort: skip

import splunklib.results as results  # isort: skip
from splunklib.searchcommands import Configuration, dispatch  # isort: skip


@Configuration()
class DatamodelFieldsCommand(BaseGeneratingCommand):
    """Command to generate Datamodel field.

    This command create a KV Store with all Datamodel fields to be used in the
    Datamodel search configuration page to increase the performance of the dropdown.
    The command is run on as a saved search on a schedule.

    Usage:
    | tcdmu
    """

    # properties
    _command = 'tcdmu'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for Collection KV Store Stats."""
        # retrieve datamodel data from Splunk
        self.build_model_data()

        # display the results
        for r in self.results:
            yield r

    @property
    def excluded_base_models(self):
        return {'updates', 'splunk_audit', 'splunk_cim_validation', 'application_state', 'change_analysis'}

    @staticmethod
    def is_base_search(object_data):
        parent_name = object_data.get('parentName', '')
        return parent_name.lower() == 'basesearch'

    def build_model_data(self):
        """Return all Datamodel names.

        structure:
        {
            'Network_Traffic': {
                'All_Traffic': [],
                'Allowed_Traffic': [],
                'Blocked_Traffic': []
            }
        }
        """
        spl = '| datamodel | spath modelName | fields modelName'
        kwargs = {'output_mode': 'json'}
        job = self.service.jobs.oneshot(spl, **kwargs)
        reader = results.JSONResultsReader(job)

        # retrieve results from Splunk
        result_data = {}
        for result in reader:
            model_name = result.get('modelName')
            if model_name.lower() in self.excluded_base_models:
                continue
            data = json.loads(result.get('_raw'))
            result_data.setdefault(model_name, {})
            for object_data in data.get('objects'):
                object_name = object_data.get('objectName')
                parent_name = object_data.get('parentName')
                result_data[model_name].setdefault(object_name, [])

                # add extracted field data
                for field_data in object_data.get('fields', []):
                    self.log.info('extracting fields')
                    # skip fields that don't make sense
                    if field_data.get('fieldName') in ['_time']:
                        continue
                    # skip hidden fields
                    if field_data.get('hidden', False):
                        continue
                    field_name = field_data.get('fieldName')
                    field_name_dm = f'{object_name}.{field_name}'
                    if self.is_base_search(object_data):
                        field_name_dm = f'''{model_name}.{field_name}'''
                        self.log.info(f'field_name_dm: {field_name_dm}')
                        self.log.info(f'field_name: {field_name}')
                    result_data[model_name][object_name].append(field_name)
                    result_data[model_name][object_name].append(field_name_dm)

                # add calculated field data
                for calculation_data in object_data.get('calculations', []):
                    self.log.info('calculating fields')
                    for output_data in calculation_data.get('outputFields'):
                        # skip fields that don't make sense
                        if output_data.get('fieldName') in ['_time']:
                            continue
                        # skip hidden fields
                        if output_data.get('hidden', False):
                            continue
                        field_name_dm = f'''{object_name}.{output_data.get('fieldName')}'''
                        if self.is_base_search(object_data):
                            field_name_dm = f'''{model_name}.{output_data.get('fieldName')}'''
                        result_data[model_name][object_name].append(field_name_dm)
                    self.log.info('exiting calculating fields')

                # add parent extracted/calculated field data
                result_data[model_name][object_name].extend(
                    result_data[model_name].get(parent_name, [])
                )

                if object_name in result_data[model_name][object_name]:
                    result_data[model_name][object_name].remove(object_name)

                self.logger.debug(
                    f'action: process-data-model, model: {model_name}, object: {object_name}, '
                    f'field_count: {len(result_data[model_name][object_name])}'
                )

        # clear previous data
        self.tcs.collections.dm_data.delete()

        # iterate over data to build kv store data and results
        for model_name, model_data in result_data.items():
            for object_name, fields in model_data.items():
                for field_name in fields:
                    data = {
                        'fieldName': field_name,
                        'modelName': model_name,
                        'objectName': object_name,
                    }
                    self.tcs.collections.dm_data.batch_data(data)
                    self.results.append(data)

        # save any remaining data
        self.tcs.collections.dm_data.batch_save()

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    dispatch(DatamodelFieldsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
