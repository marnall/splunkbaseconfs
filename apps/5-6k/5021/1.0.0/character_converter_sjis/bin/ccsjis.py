#!/usr/bin/env python

import os,sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class CCSJISCommand(StreamingCommand):

    def stream(self, records):
        try:
            for record in records:
                for field in self.fieldnames:
                    if field in record:
                        record[field] = record[field].encode('cp932')

                yield record
        except:
            pass

dispatch(CCSJISCommand, sys.argv, sys.stdin, sys.stdout, __name__)

