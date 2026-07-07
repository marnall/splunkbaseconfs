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

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, \
    Option, validators
import sys


@Configuration()
class MvLatestPairCommand(StreamingCommand):
    """ Get the lastest pair in multivalue.

    ##Syntax

    .. code-block::
        mvlatestpair keyfield=<keyfield>  valuefield=<valuefield>

    ##Description

    keyfield: the key field for the pair.
    valuefield: the value field for the pair

    """

    keyfield = Option(
        doc='''
        **Syntax:** **keyfield=***<keyfield>*
        **Description:** The key field for the pair''',
        require=True, validate=validators.Fieldname())

    valuefield = Option(
        doc='''
            **Syntax:** **valuefield=***<valuefield>*
            **Description:** The value field for the pair''',
        require=True, validate=validators.Fieldname())


    def stream(self, records):

        for record in records:
            keys = record[self.keyfield]
            values = record[self.valuefield]

            if isinstance(values, list):
                record[self.valuefield] = list()
                for idx in range(len(values)):
                    if idx<len(values)-1:
                        if keys[idx] != keys[idx+1]:
                            record[self.valuefield].append(values[idx])
                    else:
                        record[self.valuefield].append(values[idx])

            yield record


dispatch(MvLatestPairCommand, sys.argv, sys.stdin, sys.stdout, __name__)
