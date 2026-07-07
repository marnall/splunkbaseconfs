#!/usr/bin/env python

import sys
import time
import urllib2
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class HitNumCommand(GeneratingCommand):
    number = Option(require=True, validate=validators.Integer())

    def generate(self):
        t = time.time();
        yield {
            'count': str(number)
        }

dispatch(HitNumCommand, sys.argv, sys.stdin, sys.stdout, __name__)
