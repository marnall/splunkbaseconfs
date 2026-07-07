#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, unicode_literals

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
import re


@Configuration()
class MvDiffCommand(StreamingCommand):
    """ Gets the mv diff.
    """
    only1 = Option(
        doc='''
        **Syntax:** **only1=***<only1field>*
        **Description:** Name of the field that stores the multivalue only in multivalue field1''',
        require=False, validate=validators.Fieldname())

    only2 = Option(
        doc='''
        **Syntax:** **only2=***<only2field>*
        **Description:** NName of the field that stores the multivalue only in multivalue field2''',
        require=False, validate=validators.Fieldname())

    common = Option(
        doc='''
        **Syntax:** **common=***<commonfield>*
        **Description:** Name of the field that stores the multivalue in both multivalue fields''',
        require=False, validate=validators.Fieldname())

    mv1 = Option(
        doc='''
        **Syntax:** **mv1=***<mv1field>*
        **Description:** Name of the multivalue field1''',
        require=True, validate=validators.Fieldname())

    mv2 = Option(
        doc='''
        **Syntax:** **mv2=***<mv2field>*
        **Description:** Name of the multivalue field2''',
        require=True, validate=validators.Fieldname())

    METADATA_SEP = '====>'

    def stripped_metadata_dict(self, values, metadata_sep=METADATA_SEP):
        """
        Gets dict with {value without metadata: value}
        """
        result = {}
        for value in values:
            if metadata_sep in value:
                result[value.split(metadata_sep)[1]] = value
            else:
                result[value] = value
        return result

    def stripped_metadata_set(self, values, metadata_sep=METADATA_SEP):
        """
        Gets set with {value without metadata}
        """
        result = set()
        for value in values:
            if metadata_sep in value:
                result.add(value.split(metadata_sep)[1])
            else:
                result.add(value)
        return result

    def filtered_dict_values_by_keys(self, source_dict, keys):
        """
        Filter dict values by the specified keys
        """
        return [source_dict[key] for key in keys]

    def stream(self, records):
        self.logger.debug('MvDiffCommand: %s', self)  # logs command line
        
        for record in records:
            orig_set1 = set(record[self.mv1]) if self.mv1 in record else set()
            orig_set2 = set(record[self.mv2]) if self.mv2 in record else set()
            self.logger.debug('orig_set1: {}'.format(orig_set1))
            self.logger.debug('orig_set2: {}'.format(orig_set2))

            set1 = self.stripped_metadata_set(orig_set1)
            set2 = self.stripped_metadata_set(orig_set2)
            self.logger.debug('set1: {}'.format(set1))
            self.logger.debug('set2: {}'.format(set2))

            if self.common is not None:
                common_values = set1 & set2
                record[self.common] = sorted(
                    self.filtered_dict_values_by_keys(self.stripped_metadata_dict(orig_set1), common_values))
                self.logger.debug('common_values: {}'.format(common_values))

            if self.only1 is not None:
                only1_values = set1 - set2
                record[self.only1] = sorted(
                    self.filtered_dict_values_by_keys(self.stripped_metadata_dict(orig_set1), only1_values))
                self.logger.debug('only1_values: {}'.format(only1_values))

            if self.only2 is not None:
                only2_values = set2 - set1
                record[self.only2] = sorted(
                    self.filtered_dict_values_by_keys(self.stripped_metadata_dict(orig_set2), only2_values))
                self.logger.debug('only2_values: {}'.format(only2_values))

            yield record

dispatch(MvDiffCommand, sys.argv, sys.stdin, sys.stdout, __name__)
