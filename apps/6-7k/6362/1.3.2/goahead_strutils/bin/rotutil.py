#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from lib_rotutil import rot_convert

APPNAME = "strutils"
COMMANDNAME = 'rotutil'


@Configuration()
class rotutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to encode or decode ''',require=True,validate=validators.Fieldname())
    num = Option(doc=''' (Optional) Set the number of right rotation from -47 to 47 (ROT47) are available. default: 13 (ROT13)''',require=False, default=13, validate=validators.Integer())
    brute = Option(doc=''' (Optional) Brute rotation until 'num' amount ''',require=False,default="false",validate=validators.Boolean())

    def prepare(self):
        self.configuration.required_fields = [self.input_field]

    def stream(self, events):
        self.logger.debug('rotutil: %s', self)
        if self.brute:
            output_field = "brute_"
        else:
            output_field = ""
        output_field += "rot" + str(self.num) + "_" + self.input_field

        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    if self.brute:
                        event[output_field] = [ "[ROT%s]\t"%n + rot_convert(n,event[self.input_field]) for n in range(0-self.num,self.num+1)]
                    else:
                        event[output_field] = rot_convert(self.num,event[self.input_field])
                except Exception as e:
                    self.logger.exception("[%s] %s - '%s'"%(COMMANDNAME,str(e),event[self.input_field]))
                    event[output_field] = "__rotutil_ROT%s_brute=%s_convert_error__"%(self.num,self.brute)

                yield event

dispatch(rotutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)