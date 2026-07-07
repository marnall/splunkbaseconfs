#!/usr/bin/env python

import sys
import time
import urllib2
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class HitListCommand(GeneratingCommand):
    data= Option(require=True)

    def generate(self):
        t = time.time();
        lines = self.data.split('?');
        for line in lines:
            parts = line.split(':');
            if (len(parts) != 5):
                continue
            yield {
                '_time': t,
                'date': parts[0],
                "seq": parts[1],
                "zip": parts[2],
                "salt": parts[3],
                "plainsize": parts[4],
                '_raw': line.replace(":", " ")
            }

dispatch(HitListCommand, sys.argv, sys.stdin, sys.stdout, __name__)
