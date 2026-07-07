#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import gv_spl_parse

@Configuration()
class ParseCommand(StreamingCommand):
    def stream(self, records):
        argument = self.fieldnames[0]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if argument in record:
                    record["parsed_" + argument] = gv_spl_parse.get_commands( record[argument] ).mv()

            except Exception as e:
                exception_string = str(e)
                record["splparse_failure__"] = exception_string 

            yield record


dispatch(ParseCommand, sys.argv, sys.stdin, sys.stdout, __name__)

