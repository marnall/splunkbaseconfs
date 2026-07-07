#!/usr/bin/env python
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from cexc import BaseChunkHandler

class DragosNormalizeIndicator(BaseChunkHandler):

    # defaults
    input_fieldname    = 'indicator'
    output_fieldname   = 'indicator_normalized'

    ipv4_regex = re.compile("^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
    ipv6_regex = re.compile("^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]).){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]).){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$", re.IGNORECASE)


    def _parse_arguments(self, args):
        """
        very simple parser
        """
        # args = [u'john=mc', u'lane', u'wo=tic tic']
        for token in args:
            if not '=' in token:
                # single word: possible but not used/supported by urlparser
                continue

            (k,v) = token.split('=', 1)
            # only consider these arguments
            if k in ["input_fieldname", "output_fieldname"]:
                setattr(self, k, v)


    # metadata is a dict with the parsed JSON metadata payload.
    # data is a list of dicts, where each dict represents a search result.
    def handler(self, metadata, data):
        # The first chunk is a "getinfo" chunk.
        if metadata['action'] == 'getinfo':
            try:
                args = metadata['searchinfo']['args']
            except:
                args = []

            self._parse_arguments(args)
            return {'type': 'streaming', 'required_fields':[ self.input_fieldname, self.output_fieldname ]}

        # Subsequent chunks will have the "execute" action.
        for record in data:
            is_domain = True

            indicator = record[self.input_fieldname]
            if self.ipv4_regex.match(indicator):
                is_domain = False
            elif self.ipv6_regex.match(indicator):
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

        return (
            {'finished': metadata['finished']},
            data
        )

if __name__ == "__main__":
    DragosNormalizeIndicator().run()
