#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import gv_evalify

@Configuration()
class EvalifyCommand(StreamingCommand):
    def stream(self, records):
        argument = self.fieldnames[0]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if argument in record:
                    record["eval_" + argument] = gv_evalify.new_evalify( record[argument], 0 ).__str__()

            except Exception as e:
                exception_string = str(e)
                record["evalify_failure__"] = exception_string 

            yield record


dispatch(EvalifyCommand, sys.argv, sys.stdin, sys.stdout, __name__)

