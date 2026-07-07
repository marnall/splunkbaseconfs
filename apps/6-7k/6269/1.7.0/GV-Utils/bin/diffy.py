#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

import gv_diff
import gv_spl_diff
import gv_xml_diff
import gv_json_diff

@Configuration()
class DiffyCommand(StreamingCommand):
    is_spl_field = Option(
        require=False, default=None, validate=validators.Fieldname()
    )

    syntax_colouring_field= Option(
        require=False, default=None, validate=validators.Fieldname()
    )

    def stream(self, records):
        key = self.fieldnames[0]
        old = self.fieldnames[1]
        new = self.fieldnames[2]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if (  key in record
                  and old in record
                  and new in record ):
                    is_spl = False
                    is_xml = False
                    is_json = False
                    if (   ( self.is_spl_field           and self.is_spl_field           in record and record[self.is_spl_field] and not record[self.is_spl_field] == "0" )
                       or  ( self.syntax_colouring_field and self.syntax_colouring_field in record and record[self.syntax_colouring_field] and record[self.syntax_colouring_field] == "spl" )
                       ):
                      is_spl = True
                    if self.syntax_colouring_field and self.syntax_colouring_field in record and record[self.syntax_colouring_field] and record[self.syntax_colouring_field] == "xml":
                      is_xml = True
                    if self.syntax_colouring_field and self.syntax_colouring_field in record and record[self.syntax_colouring_field] and record[self.syntax_colouring_field] == "json":
                      is_json = True
                    if is_spl:
                      diff = gv_spl_diff.new_spl_diff( record[old], record[new] )
                      record["diff"] = diff.html( record[key] )
                    elif is_xml:
                      diff = gv_xml_diff.new_xml_diff( record[old], record[new] )
                      record["diff"] = diff.html( record[key] )
                    elif is_json:
                      diff = gv_json_diff.new_json_diff( record[old], record[new] )
                      record["diff"] = diff.html( record[key] )
                    else:
                      diff = gv_diff.new_diff( record[old], record[new] )
                      record["diff"] = diff.html( record[key] )

            except Exception as e:
                exception_string = str(e)
                record["diffy_failure__"] = exception_string 

            yield record

dispatch(DiffyCommand, sys.argv, sys.stdin, sys.stdout, __name__)


