#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

APPNAME = "strutils"
COMMANDNAME = 'escapeutil'

@Configuration()
class escapeutilCommand(StreamingCommand):
    input_field = Option(doc=''' Target field name to encode or decode ''',require=True,validate=validators.Fieldname())
    escape = Option(doc=''' (Optional) Set escape mode converting from readable to escape str''',require=False, validate=validators.Set("unicode-escape","xmlcharref","urlpercent"))
    unescape = Option(doc=''' (Optional) Set unescape mode converting from escape str to readable''',require=False, validate=validators.Set("unicode-escape","xmlcharref","urlpercent"))

    def prepare(self):
        self.configuration.required_fields = [self.input_field]

    def stream(self, events):
        self.logger.debug('escapeutil: %s', self)
        if self.unescape is not None and self.escape is not None:
            raise Exception("Cannot set both options escape= and unescape=. Select the one.") 
        elif self.unescape is not None:
            result_field = "unescape" + "_" + self.unescape  + "_" + self.input_field
        elif self.escape is not None:
            result_field = "escape" + "_" + self.escape  + "_" + self.input_field
        else:
            result_field = "not_given"

        if self.escape == "xmlcharref" or self.unescape == "xmlcharref":
            from html import unescape as xml_unescape
        elif self.escape == "urlpercent" or self.unescape == "urlpercent":
            import urllib.parse as percent

        #   process events and routine with converting
        for event in events:
            if not self.input_field in event:
                raise Exception("Your event doesn't have the input field of %s"%self.input_field)
            else:
                try:
                    if result_field != "not_given":
                        if self.escape == "unicode-escape":
                            event[result_field] = event[self.input_field].encode("ascii", "backslashreplace").decode() # escape encoding
                        elif self.unescape == "unicode-escape":
                            event[result_field] = event[self.input_field].encode().decode(self.unescape)     # unescape decoding
                        elif self.escape == "xmlcharref":
                            event[result_field] = event[self.input_field].encode("ascii", "xmlcharrefreplace").decode() # escape encoding
                        elif self.unescape == "xmlcharref":
                            event[result_field] = xml_unescape(event[self.input_field])                      # unescape decoding
                        elif self.escape == "urlpercent":
                            event[result_field] = percent.quote(event[self.input_field])                     # escape encoding
                        elif self.unescape == "urlpercent":
                            event[result_field] = percent.unquote(event[self.input_field])                  # unescape decoding

                except Exception as e:
                    self.logger.exception("[%s] %s - '%s'"%(COMMANDNAME,str(e),event[self.input_field]))
                    event[result_field] = "__escapeutil_%s_convert_error__"%(result_field)

                yield event

dispatch(escapeutilCommand, sys.argv, sys.stdin, sys.stdout, __name__)