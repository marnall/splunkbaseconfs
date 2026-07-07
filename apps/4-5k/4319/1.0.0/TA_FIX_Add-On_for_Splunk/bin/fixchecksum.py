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
import sys
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class FixChecksumCommand(StreamingCommand):
    """ Calculates the FIX checksum to compare with the one sent with the message.

    ##Syntax

    .. code-block::
        fixchecksum output=<output_field> <fix_message_field>

    ##Description

    A command to calculate the FIX checksum for fields containing `FIX messages` to look for errors.  This can be used to compare the sent checksum in the `10`, or `CheckSum`, tag to the one calculated by the command.

    ##Example

    Calculate the FIX message checksum in the `FIX message` and store the result in the `CalculatedChecksum` field.

    .. code-block::
        | inputlookup fixmessages | fixchecksum output=<output_field> <fix_message_field>

    """
    output = Option(
        doc='''
        **Syntax:** **output=***<output_field>*
        **Description:** Name of the field that will hold the FIX message''',
        require=True, validate=validators.Fieldname())

    def stream(self, records):
        fieldnames = self.fieldnames
        self.logger.debug('FixChecksumCommand: %s', self)  # logs command line
        for record in records:
            i = "%03d" % (sum((ord(c)) for c in record[fieldnames[0]][:-7]) % 256)
            record[self.output] = i
            yield record


dispatch(FixChecksumCommand, sys.argv, sys.stdin, sys.stdout, __name__)

