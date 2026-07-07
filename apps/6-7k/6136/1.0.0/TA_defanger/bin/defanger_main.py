#!/usr/bin/env python3

from __future__ import absolute_import, division, print_function, unicode_literals

import os, sys

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'searchcommands_app', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from url_ip_defanger import defanger,refanger




@Configuration()
class defanger_main(StreamingCommand):
    """
    String convert to pps

     | defang input_field=<string> (mode=(append|replace))?  (action=(defanger|fanger))?

    """
    input_field = Option(
        doc='''
                **Syntax:** **input_field=***<field>*
                **Description:** Name of the field that you want defanged''',
        name='input_field', require=True, validate=validators.Fieldname())
    mode = Option(name='mode', require=False, default="append")
    action = Option(name='action', require=False, default="defanger")
    suppress_error = Option(name='suppress_error', require=False, default=False, validate=validators.Boolean())

    def stream(self, records):
        self.logger.debug('CountMatchesCommand: %s', self)  # logs command line
        for record in records:
            mode = self.mode
            input_field = self.input_field
            action = self.action
            defang_field = record[input_field]
            if mode == "append":
                if action == "fanger":
                    dest_field = "fanged_value"
                else:
                    dest_field = "defanged_value"
            elif mode == "replace":
                dest_field = input_field
            if action == "defanger":
                try:
                    defang_field_value = defanger(defang_field)
                    record[dest_field] = defang_field_value
                except ValueError as e:
                    print(e)
            if action == "fanger":
                try:
                    fanger_field_value = refanger(defang_field)
                    record[dest_field] = fanger_field_value
                except ValueError as e:
                    print(e)
            yield record


dispatch(defanger_main, sys.argv, sys.stdin, sys.stdout, __name__)