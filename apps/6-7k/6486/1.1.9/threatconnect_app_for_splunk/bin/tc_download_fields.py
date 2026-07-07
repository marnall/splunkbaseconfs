#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Download ThreatConnect Owner Information Command"""
# standard library
import os
import sys
from collections import OrderedDict
from typing import Any, Dict

# third-party
# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import Configuration, dispatch


@Configuration()
class FieldsDownloadCommand(BaseGeneratingCommand):
    """Command to download field data from ThreatConnect API.

    Usage:
    | tcfields
    """

    # properties
    _command = 'tcfields'
    _field_data_dict = None
    filename = os.path.basename(__file__)
    ks_owner_data = None
    field_name_tracker = []

    def add_result(self, action, name, type_):
        """Return ordered dict for results."""
        self.logger.info(f'action={action}, name="{name}", type={type_}')
        result_data = OrderedDict()
        result_data['Action'] = action
        result_data['Name'] = name
        result_data['Type'] = type_
        self.results.append(result_data)

    def delete_fields(self):
        """Delete fields that have been removed from ThreatConnect"""
        for key, field_data in self.field_data_dict.items():
            if key not in self.field_name_tracker:
                self.add_result('delete', field_data.get('name'), 'kvs-entry')
                self.tcs.collections.fields.delete_by_id(field_data.get('_key'))

    def generate(self):
        """Implement generate command for downloading fields."""
        # retrieve field data from ThreatConnect
        for _, field_data in self.retrieve_fields().items():
            self.process_field(field_data)

        # delete fields not in ThreatConnect
        self.delete_fields()

        # display the results
        for r in self.results:
            yield r

    @property
    def field_data_dict(self):
        """Return field data dict with id as key and data as value."""
        if self._field_data_dict is None:
            self._field_data_dict = {}
            for field_data in self.tcs.collections.fields.query():
                self._field_data_dict[field_data.name] = field_data
        return self._field_data_dict

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def process_field(self, field_data: Dict[str, Any]):
        """Process the field Data

        Args:
            field_data (dict): Response object from TC API.
        """
        # add current field id to field id tracker
        self.field_name_tracker.append(field_data.get('name'))

        if field_data.get('name') not in self.field_data_dict:
            # id doesn't exist must be a new field
            self.process_field_add(field_data)
            self.add_result('add', field_data.get('name'), 'kvs-entry')
        else:
            action = 'skip'
            data = self.field_data_dict.get(field_data.get('name'))
            if data is not None and (
                data.get('name') != field_data.get('name')
                or data.get('description') != field_data.get('description')
                or data.get('includedByDefault') != field_data.get('includedByDefault')
            ):
                action = 'update'
                self.process_field_update(data, field_data)
            self.add_result(action, field_data.get('name'), 'kvs-entry')

    def process_field_add(self, field_data):
        """Add field data to KV Store

        Args:
            field_data (dict): Response object from TC API.
        """
        data = {
            'description': field_data.get('description'),
            'includedByDefault': field_data.get('includedByDefault', False),
            'name': field_data.get('name'),
        }
        # insert new field and collection _key
        data['_key'] = self.tcs.collections.fields.insert(data).get('_key')

        # add new field to field data dict
        self.field_data_dict[field_data.get('name')] = data

    def process_field_update(self, data, field_data):
        """Update Field data in the KV Store

        Args:
            data (dict): KV Store owner data.
            field_data (dict): Response object from TC API.
        """
        self.tcs.collections.fields.update(
            data.get('_key'), {'_key': data.get('_key'), **field_data}
        )

    def retrieve_fields(self) -> Dict[str, Dict[str, Any]]:
        """Load Owner Data"""
        return self.tcs.request.indicator_fields_data


if __name__ == '__main__':
    try:
        dispatch(FieldsDownloadCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        # standard library
        import traceback

        print(traceback.format_exc(), file=sys.stderr)
