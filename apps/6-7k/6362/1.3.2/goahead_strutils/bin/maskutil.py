#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from lib_maskutil import masking

APPNAME = "strutils"
COMMANDNAME = 'maskutil'

@Configuration()
class maskutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to mask ''',require=True,validate=validators.Fieldname())
    additional_input_fields = Option(doc=''' Additional target field names to mask (List "fieldA,fieldB") ''',require=False,validate=validators.List())

    def prepare(self):
        self.configuration.required_fields = [self.input_field]

    def stream(self, events):
        self.logger.debug('maskutil: %s', self)
        output_field = "masked" + "_" + self.input_field
        output_additionals = []
        if self.additional_input_fields is not None:
            if len(self.additional_input_fields) > 0:
                for additional_field in self.additional_input_fields:
                    if additional_field != "":
                        output_additionals.append("masked" + "_" + additional_field)


        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    event[output_field] = masking(event[self.input_field])
                    for a in output_additionals:
                        try:
                            event[a] = masking(event[a.replace("masked_","")])
                        except Exception as e:
                            self.logger.exception("[%s] %s - '%s', '%s'"%(COMMANDNAME,str(e),event[a.replace("masked_","")]))
                            event[a] = "__maskutil_%s_convert_error__"%(event[a.replace("masked_","")])
                except Exception as e:
                    self.logger.exception("[%s] %s - '%s' "%(COMMANDNAME,str(e),event[self.input_field]))
                    event[output_field] = "__maskutil_%s_convert_error__"%(self.input_field)

                yield event

dispatch(maskutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)