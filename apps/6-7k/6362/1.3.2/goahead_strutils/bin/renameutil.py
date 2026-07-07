#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

APPNAME = "strutils"
COMMANDNAME = 'renameutil'

@Configuration()
class renameutilCommand(StreamingCommand):
    field = Option(doc=''' Target field names, single field name, comma separated fields list, wildcard is available''',require=True)
    style = Option(doc=''' Rename style select in "replace" or "upper" or "lower" or "prefix" or "suffix" ''',require=True,validate=validators.Set("replace","upper","lower","prefix","suffix"))
    fixstub = Option(doc=''' (Optional) Set the field str to append or replace''',require=False)
    prestub = Option(doc=''' (Optional) Set the field str replaced''',require=False)

    def prepare(self):
        self.configuration.required_fields = [self.field,self.style]

    def stream(self, events):
        self.logger.debug('renameutil: %s', self)

        if self.style == "replace":
            if self.prestub is None:
                raise Exception("Please set prestub= option for replace style mode")
            elif self.fixstub is None:
                raise Exception("Please set fixstub= option for replace style mode")
            else:
                from lib_renameutil import replace_convert
        elif self.style == "prefix":
            if self.fixstub is None:
                raise Exception("Please set fixstub= option for prefix style mode")  
            else:
                from lib_renameutil import append_prefix          
        elif self.style == "suffix":
            if self.fixstub is None:
                raise Exception("Please set fixstub= option for suffix style mode")           
            else:
                from lib_renameutil import append_suffix   
        elif self.style == "upper":
            from lib_renameutil import to_allupper 
        elif self.style == "lower":
            from lib_renameutil import to_alllower 
        else:
            raise Exception("Unexpected style mode: {}".format(self.style))             

        #   process events and routine with converting
        list_fields = []
        c = 0
        for event in events:
            if c == 0:
                c += 1
                if "*" in self.field:
                    restr = self.field.replace("*","(.*)")
                    for fieldname in event.keys():
                        if re.search(r"%s"%restr, fieldname):
                            list_fields.append(fieldname)

                elif "," in self.field:
                    for fieldname in self.field.split(","):
                        if not fieldname in event:
                            raise Exception("Your event doesn't have the input field of %s"%self.field)
                        list_fields.append(fieldname)

                else:
                    if not self.field in event:
                        raise Exception("Your event doesn't have the input field of %s"%self.field)
                    list_fields.append(self.field)

                self.logger.info("target fields: {}".format(list_fields))

            try:
                if self.style == "replace":
                    event = replace_convert(event,list_fields,self.prestub,self.fixstub) 
                elif self.style == "prefix":
                    event = append_prefix(event,list_fields,self.fixstub) 
                elif self.style == "suffix":
                    event = append_suffix(event,list_fields,self.fixstub) 
                elif self.style == "upper":
                    event = to_allupper(event,list_fields) 
                elif self.style == "lower": 
                    event = to_alllower(event,list_fields)   
                else:
                    raise Exception("Unexpected style mode in event loop: {}".format(self.style)) 

            except Exception as e:
                self.logger.exception("[%s](%s) %s - '%s'"%(COMMANDNAME,self.style,str(e),list_fields))
                raise Exception("Error halt by '{}'! style [{}] for fields: {}".format(str(e),self.style,list_fields))

            yield event

dispatch(renameutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)