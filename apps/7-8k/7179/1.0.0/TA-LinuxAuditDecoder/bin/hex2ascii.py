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


import os
import sys
import binascii

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'TA-LinuxAuditDecoder', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class Hex2AsciiCommand(StreamingCommand):
    """ Convert the Linux Audit log HEX value to ASCII text.

    ##Syntax

    .. code-block::
        hex2ascii src=<field> dst=<field>

    ##Description

    The Linx Audit log are encoded with HEX format. This command will convert the Hex value to ASCII form.
    `out` field is the output field name.

    ##Example

    Convert the HEX value in `text` and return the result in `out`.

    .. code-block::
        | index=linux_audit | search proctitle='*' | table proctitle | hex2ascii src=proctitle dst=new_fieldname

    """
    src = Option(
        doc='''
        **Syntax:** **src=***<fieldname>*
        **Description:** Name of the field that will contains the HEX value''',
        require=True, validate=validators.Fieldname())

    dst = Option(
        doc='''
        **Syntax:** **dst=***<fieldname>*
        **Description:** Name of the field that will hold the ascii result''',
        require=True, validate=validators.Fieldname())

    def is_hex_value(self, s):
        try:
            int(s, 16)
            return True
        except ValueError:
            return False

    def stream(self, records):
        self.logger.debug('Hex2AsciiCommand: %s', self)  # logs command line
        for record in records:
            res=''
            try:
                int(record[self.src], 16)
                for i in binascii.a2b_hex(record[self.src]):
                    c=chr(i)
                    if i == 0: c=' '
                    res=res+c
            except Exception as e:
                res=record[self.src]
                  
            record[self.dst] = res
            yield record

dispatch(Hex2AsciiCommand, sys.argv, sys.stdin, sys.stdout, __name__)
