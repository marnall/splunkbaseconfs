#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

APPNAME = "strutils"
COMMANDNAME = 'randomutil'

@Configuration()
class randomutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to encode or decode ''',require=True,validate=validators.Fieldname())
    mode = Option(doc=''' Operation mode of shannon or nostril or texttrans ''',require=True,validate=validators.Set('shannon','nostril','texttrans'))
    th = Option(doc=''' (Optional) Set the threshold numeric value of mode shannon and texttrans(0.00 ~ 0.99) default: shannon:3.5, texttrans:0.05 ''',require=False, default="3.5")

    def prepare(self):
        self.configuration.required_fields = [self.input_field,self.mode]

    def stream(self, events):
        self.logger.debug('randomutil: %s', self)
        if self.th is not None:
            try:
                self.th = float(self.th)
                if self.mode == "shannon": 
                    judge = ">th" + str(self.th) + "_" 
                elif self.mode == "texttrans":
                    if self.th == 3.5: 
                        self.th = 0.05
                    judge = "<th" + str(self.th) + "_" 
                else:
                    judge = ""
                output_field = "is_random" +  "_" + self.mode + "_" + judge + self.input_field
            except Exception as e:
                raise Exception("[%s] %s is not an number value. int or float is available."%(str(e),self.th))
        else:
            raise Exception("Unintended Error: threshold option 'th' is None.")

        if self.mode == "shannon":
            from lib_randomutil import shannon_entropy as bool_random
        elif self.mode == "nostril":
            from lib_randomutil import nostril_boolean as bool_random
        elif self.mode == "texttrans":
            from lib_randomutil import texttrans_entropy as bool_random
        else:
            raise Exception("Your option '%s' is not supported."%self.mode)            

        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    event[output_field] = bool_random(event[self.input_field],self.th,self.logger)
                except Exception as e:
                    self.logger.exception("[%s] %s - '%s'"%(COMMANDNAME,str(e),event[self.input_field]))
                    event[output_field] = "__randomutil_%s_th=%s_calc_error__"%(self.mode,self.th)

                yield event

dispatch(randomutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)