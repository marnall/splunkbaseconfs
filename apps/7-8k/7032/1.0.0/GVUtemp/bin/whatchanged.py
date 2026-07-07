#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class whatchangedCommand(StreamingCommand):
    #max_length = Option( require=False, default=0, validate=validators.Integer() )
    #multivalue = Option( require=False, default=False, validate=validators.Boolean() )

    def stream(self, records):
        old_field = self.fieldnames[0]
        new_field = self.fieldnames[1]

        #sys.stderr.write( "hello world\n")
        for record in records:
          try:

            exception_string = None

            if not old_field in record:
              raise Exception("No such field:  '" + old_field + "'")
            if not new_field in record:
              raise Exception("No such field:  '" + new_field + "'")

            old_dict = {}
            new_dict = {}

            for line in record[old_field]:
              m = re.search( r"^(\w+):(?s)(.*)$", line )
              if not m:
                raise Exception("Failed to parse line in '" + old_field + "': " + line)
              old_dict[ m.group(1) ] = m.group(2)
            for line in record[new_field]:
              m = re.search( r"^(\w+):(?s)(.*)$", line )
              if not m:
                raise Exception("Failed to parse line in '" + new_field + "': " + line)
              new_dict[ m.group(1) ] = m.group(2)

            # Now compare the two dictionaries
            has_changed = 0
            modified_fields = []
            for key in sorted( set().union( old_dict.keys(), new_dict.keys() ) ):
              if not key in old_dict:
                has_changed = 1
                modified_fields.append( key )
              elif not key in new_dict:
                has_changed = 1
                modified_fields.append( key )
              elif old_dict[ key ] == new_dict[ key ]:
                pass
              else:
                has_changed = 1
                modified_fields.append( key )

            record["has_changed"] = has_changed
            record["modified_fields"] = modified_fields

          except Exception as e:
            exception_string = str(e)
            record["whatchanged_failure__"] = exception_string 

          yield record

dispatch(whatchangedCommand, sys.argv, sys.stdin, sys.stdout, __name__)
