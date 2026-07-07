#!/usr/bin/env python

import sys

from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

import pickle

@Configuration()
class FixDecodeCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """


    def stream(self, records):
        self.logger.debug('FixDecodeCommand: %s', self)  # logs command line
        pkl_file = open('./fixtags.pkl', 'rb')
        fixdict = pickle.load(pkl_file)
        pkl_file.close()
        for record in records:
            for k, v in record.items():
                if fixdict.has_key(k):
                    record[fixdict[k]] = record[k]
            yield record

dispatch(FixDecodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
