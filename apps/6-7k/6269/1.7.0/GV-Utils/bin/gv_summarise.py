#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import, division, print_function, unicode_literals
import os
import re
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()

class SummariseCommand(StreamingCommand):
    max_length    = Option( require=False, default=0, validate=validators.Integer() )
    multivalue    = Option( require=False, default=False, validate=validators.Boolean() )
    exclude_empty = Option( require=False, default=False, validate=validators.Boolean() )
    json          = Option( require=False, default=False, validate=validators.Boolean() )
    add_prefix    = Option( require=False, default="" )
    remove_prefix = Option( require=False, default="" )

    def stream(self, records):
        argument = self.fieldnames[0]

        #sys.stderr.write( "hello world\n")
        for record in records:
            try:
                exception_string = None

                if self.multivalue and self.json:
                    record["summary"] = "ERROR: Options 'multivalue' and 'json' can't both be true"
                elif argument in record:
                    entries = {} if self.json else []
                    for x in record[argument]:
                        if x in record:
                            separator = "\n" if self.json else "\n" + ( " " * ( len(x) + 2 ) ) 
                            if isinstance( record[x], list ):
                                text_value = separator.join( record[x] )
                            else:
                                text_value = record[x]
                                text_value = re.sub( r'\n', separator, text_value )
                        else:
                            text_value = ""
                        if text_value=="" and self.exclude_empty:
                            continue
                        if self.max_length and len(text_value)>self.max_length:
                            text_value = text_value[0:self.max_length] + "...TRUNCATED FROM " + str(len(text_value)) + " CHARACTERS"
                            # TODO if isinstance( record[x], list ):

                        fieldname = self.add_prefix + re.sub( r'^' + self.remove_prefix, "", x )

                        if self.json:
                            entries[ fieldname ] = text_value
                        else:
                            entries.append( fieldname + ": " + text_value )
                    if self.multivalue:
                        record["summary"] = entries
                    elif self.json:
                        record["summary"] = json.dumps( entries, indent=2 )
                    else:
                        record["summary"] = "\n".join( entries )

            except Exception as e:
                exception_string = str(e)
                record["summarise_failure__"] = exception_string 

            yield record

dispatch(SummariseCommand, sys.argv, sys.stdin, sys.stdout, __name__)


