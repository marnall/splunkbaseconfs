#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import sys

import urllib.parse

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class UrlEncodeCommand(StreamingCommand):
    def stream(self, records):
        argument = self.fieldnames[0]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if argument in record:
                    record[argument + "_encoded"] = urllib.parse.quote_plus( record[argument] )

            except Exception as e:
                exception_string = str(e)
                record["urlencode_failure__"] = exception_string 

            yield record


dispatch(UrlEncodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
