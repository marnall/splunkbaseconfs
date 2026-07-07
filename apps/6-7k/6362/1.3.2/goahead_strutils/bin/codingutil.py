#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from chardet import detect as chardet_detect

APPNAME = "strutils"
COMMANDNAME = 'codingutil'

@Configuration()
class codingutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to encode or decode ''',require=True,validate=validators.Fieldname())
    encoding = Option(doc=''' (Optional) Set the coding name to python3 encode() e.g utf-8,sjis,ascii,cp432,cp932''',require=False, default='utf-8')
    decoding = Option(doc=''' (Optional) Set the coding name to python3 decode() e.g utf-8,sjis,ascii,cp432,cp932''',require=False)

    def prepare(self):
        self.configuration.required_fields = [self.input_field]

    def stream(self, events):
        self.logger.debug('codingutil: %s', self)
        if self.decoding is not None:
            decode_field = "decoding" + "_" + self.decoding  + "_" + self.input_field
        else:
            decode_field = "not_given"

        output_field = "codinginfo" + "_" + self.input_field

        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    if decode_field != "not_given":
                        try:
                            event[decode_field] = event[self.input_field].encode(self.encoding).decode(self.decoding)    # decoding to self.decoding
                        except Exception as e:
                            event[decode_field] = str(e)
                    codinginfo = chardet_detect(event[self.input_field].encode(self.encoding))
                    if codinginfo is None: codinginfo = "None"
                    event[output_field] = codinginfo

                except Exception as e:
                    self.logger.exception("[%s] %s - '%s'"%(COMMANDNAME,str(e),event[self.input_field]))
                    event[output_field] = "__codingutil_decode_%s_convert_error__"%(decode_field)

                yield event

dispatch(codingutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)