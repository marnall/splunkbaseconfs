import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib import six


@Configuration()
class DragosNormalizeIndicatorCommand(StreamingCommand):


    input_fieldname = Option(
        doc='''
        **Syntax:** **input_fieldname=***<fieldname>*
        **Description:** Name of the field holds the indicator that needs to be normalized''',
        require=True, validate=validators.Fieldname())

    output_fieldname = Option(
        doc='''
        **Syntax:** **output_fieldname=***<fieldname>*
        **Description:** Name of the field that will hold the normalized indicator''',
        require=True, validate=validators.Fieldname())

    def stream(self, records):
        self.logger.debug('DragosNormalizeIndicatorCommand: %s', self)  # logs command line
        
        ipv4_regex = re.compile("^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
        ipv6_regex = re.compile("^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]).){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]).){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$", re.IGNORECASE)

        for record in records:
            is_domain = True

            indicator = record[self.input_fieldname]
            if ipv4_regex.match(indicator):
                is_domain = False
            elif ipv6_regex.match(indicator):
                is_domain = False

            if is_domain:
                split_parts = indicator.split(".")
                split_parts.reverse()
                reversed_domain = ".".join(split_parts)
                if reversed_domain[-1] != ".":
                    reversed_domain += "."
                record[self.output_fieldname] = reversed_domain
            else:
                record[self.output_fieldname] = indicator

            yield record

dispatch(DragosNormalizeIndicatorCommand, sys.argv, sys.stdin, sys.stdout, __name__)