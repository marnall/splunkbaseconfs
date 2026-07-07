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
import math

@Configuration()
class FlakyCommand(StreamingCommand):
    """ Gets the metrics for flaky test.
    """
    status_list = Option(
        doc='''
        **Syntax:** **status_list=***<status_list_field>*
        **Description:** Name of the field that stores the multivalue of status''',
        require=True, validate=validators.Fieldname())

    intermittency = Option(
        doc='''
        **Syntax:** **intermittency=***<intermittency field>*
        **Description:** Name of the intermittency field''',
        require=True, validate=validators.Fieldname())

    intermittency_count = Option(
        doc='''
        **Syntax:** **intermittency_count=***<intermittency_count field>*
        **Description:** Name of the intermittency_count field''',
        require=False, validate=validators.Fieldname())

    severity = Option(
        doc='''
        **Syntax:** **severity=***<severity field>*
        **Description:** Name of the severity field''',
        require=False, validate=validators.Fieldname())

    def compute_intermittency(self, status_list):
        if not status_list or len(status_list) <= 1:
            return 0;

        gap = 0

        for idx in range(0, len(status_list) - 1):
            if status_list[idx] != status_list[idx+1]:
                gap = gap + 1

        return round(1.0 * gap / (len(status_list) - 1), 2)

    def compute_intermittency_count(self, status_list):
        if not status_list or len(status_list) <= 1:
            return 0;

        gap = 0

        for idx in range(0, len(status_list) - 1):
            if status_list[idx] != status_list[idx+1]:
                gap = gap + 1

        return gap

    def compute_severity(self, status_list, b=1, u=0.5):
        sum = 0
        l = len(status_list)
        for idx, status in enumerate(status_list):
            f = 1 - status if status >= 0 else 0
            sum += f * math.exp(-u * (l - 1 - idx))
        return round(sum * b, 2)

    def stream(self, records):
        self.logger.debug('flaky: %s', self)  # logs command line
        
        for record in records:
            status_list = record[self.status_list] if self.status_list in record else []
            self.logger.debug('status_list: {}'.format(status_list))
            status_list = [int(value) for value in status_list]

            record[self.intermittency] = self.compute_intermittency(status_list)

            if self.intermittency_count is not None:
                record[self.intermittency_count] = self.compute_intermittency_count(status_list)

            if self.severity is not None:
                record[self.severity] = self.compute_severity(status_list)

            yield record

dispatch(FlakyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
