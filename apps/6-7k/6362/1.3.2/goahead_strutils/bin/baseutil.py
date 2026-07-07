#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

APPNAME = "strutils"
COMMANDNAME = 'baseutil'

@Configuration()
class baseutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to encode or decode ''',require=True,validate=validators.Fieldname())
    mode = Option(doc=''' Operation mode of encode or decode ''',require=True,validate=validators.Set('encode','decode'))
    base = Option(doc=''' (Optional) Set the number of base64 or base32 or base16 or base85, default: 64 ''',require=False, default="64", validate=validators.Set("2","8","16","32","64","85"))
    coding = Option(doc=''' (Optional) Set the letter-coding for encode() decode() built in python3, default: utf-8 ''',require=False, default="utf-8")

    def prepare(self):
        self.configuration.required_fields = [self.input_field,self.mode]

    def stream(self, events):
        self.logger.debug('baseutil: %s', self)
        output_field = "base" + self.base + self.mode + "_" + self.input_field

        # import function by base & mode pattern
        if self.base == "2":
            if self.mode == "encode": 
                from lib_baseutil import bin_encode as base_convert
            elif self.mode == "decode":                 
                from lib_baseutil import bin_decode as base_convert
        elif self.base == "8":
            if self.mode == "encode": 
                from lib_baseutil import oct_encode as base_convert
            elif self.mode == "decode":                 
                from lib_baseutil import oct_decode as base_convert
        elif self.base == "16":
            if self.mode == "encode": 
                from base64 import b16encode as base_convert
            elif self.mode == "decode":
                from base64 import b16decode as base_convert
        elif self.base == "32":
            if self.mode == "encode": 
                from base64 import b32encode as base_convert
            elif self.mode == "decode":
                from base64 import b32decode as base_convert
        elif self.base == "64":
            if self.mode == "encode": 
                from base64 import b64encode as base_convert
            elif self.mode == "decode":
                from base64 import b64decode as base_convert
        elif self.base == "85":
            if self.mode == "encode": 
                from base64 import b85encode as base_convert
            elif self.mode == "decode":
                from base64 import b85decode as base_convert
        else:
            raise Exception("Your option 'base%s' is not supported."%self.base)

        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    event[output_field] = base_convert(event[self.input_field].encode(self.coding)).decode(self.coding)
                except Exception as e:
                    self.logger.exception("[%s] %s - '%s'"%(COMMANDNAME,str(e),event[self.input_field]))
                    event[output_field] = "__baseutil_BASE%s_%s_convert_error__"%(self.base,self.mode)

                yield event

dispatch(baseutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)