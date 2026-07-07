#!/usr/bin/env python3
import os,sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import MeCab
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class MorphCommand(StreamingCommand):

    field = Option(
        doc='',
        require=True,
        validate=validators.Fieldname())

    outfield= Option(
        doc='',
        require=False,
        default='morph',
        validate=validators.Fieldname())

    def stream(self, records):
        tagger = MeCab.Tagger()
        tagger.parse('')
        for record in records:
            items = []
            try:
                node = tagger.parseToNode(record[self.field])
                while node:
                    features = []
                    if len(node.surface) != 0:
                        item = node.surface
                        for item in node.feature.split(','):
                            if item != '*':
                                features.append(item)
                            else:
                                break
                        items.append(node.surface + '\t' + '-'.join(features) + ',' + ','.join(node.feature.split(',')[4:9]))
                    else:
                        items.append('')
                    node = node.next
                record[self.outfield] = items
            except KeyError:
                record[self.outfield] = items

            yield record

dispatch(MorphCommand, sys.argv, sys.stdin, sys.stdout, __name__)
