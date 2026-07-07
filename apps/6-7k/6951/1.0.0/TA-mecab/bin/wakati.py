#!/usr/bin/env python3

import os,sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import MeCab
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class WakatiCommand(StreamingCommand):

    field = Option(
        doc='',
        require=True,
        validate=validators.Fieldname())

    outfield= Option(
        doc='',
        require=False,
        default='wakati',
        validate=validators.Fieldname())

    def stream(self, records):
        wakati = MeCab.Tagger('-Owakati')
        wakati.parse('')
        for record in records:
            try:
                record[self.outfield] = wakati.parse(record[self.field])
            except KeyError:
                record[self.outfield] = ''

            yield record

dispatch(WakatiCommand, sys.argv, sys.stdin, sys.stdout, __name__)
