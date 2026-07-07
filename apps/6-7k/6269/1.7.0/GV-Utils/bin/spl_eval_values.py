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
class EvalValuesCommand(StreamingCommand):
    def stream(self, records):
        argument = self.fieldnames[0]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if argument in record:
                    record["values_" + argument] = gv_spl_parse.get_potential_values( record[argument] )

            except Exception as e:
                exception_string = str(e)
                record["splevalvalues_failure__"] = exception_string 

            yield record


dispatch(EvalValuesCommand, sys.argv, sys.stdin, sys.stdout, __name__)

