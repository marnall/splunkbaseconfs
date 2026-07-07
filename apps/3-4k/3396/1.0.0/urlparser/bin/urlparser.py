#!/usr/bin/env python
import sys
import json

from liburlparser import URLParser
from cexc import BaseChunkHandler

class URLParserCommand(BaseChunkHandler):

    # defaults
    field    = 'url'
    listname = 'mozilla'
    mode     = 'extended'

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
		# urlparser only consider those 3 arguments.
		if k in ["field", "listname", "mode"]:
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
		return {'type': 'streaming', 'required_fields':[ self.field ]}

        # Subsequent chunks will have the "execute" action.
	urlparser = URLParser()
	urlparser.loadTLDList( self.listname )
	urlparser.setParsingMode( self.mode )
   
	for record in data:
		url = record[ self.field ]
		res = urlparser.parse(url)
		record.update(res.to_json())

        return (
            {'finished': metadata['finished']},
            data
        )

if __name__ == "__main__":
    URLParserCommand().run()
