#!/usr/bin/env python
#Dominique Vocat

from __future__ import absolute_import, division, print_function, unicode_literals
import random
import csv
import os,sys
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import yaml

def toSearchlog(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

@Configuration()
class yaml_command(StreamingCommand):
    """
    Handle parameter passing, lazy way 'round is show user how to pass which combination via searchbnf.conf
    """
    input = Option(require=False, default="_raw")
    output = Option(require=False, default="json")
    output_format = Option(require=False, default="json")

    def stream(self, records):
        for record in records:
            try:
                if self.output_format=="json":
                    record[self.output] = json.dumps(yaml.load(record[self.input]))
                else:
                    record[self.output] = yaml.dump(json.loads(record[self.input]))    
            except Exception as e:
                import traceback
                stack =  traceback.format_exc()
                toSearchlog(stack)
            
            yield record


    def __init__(self):
        super(yaml_command, self).__init__()
        self.records = None

dispatch(yaml_command, sys.argv, sys.stdin, sys.stdout, __name__)