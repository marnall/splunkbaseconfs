#!/usr/bin/env python
#Dominique Vocat

import sys
import os
import subprocess
from subprocess import run, PIPE
import itertools
import re
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

def toSearchlog(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

@Configuration() #local=True
class jq(StreamingCommand):
    """
    Handle parameter passing, lazy way 'round is show user how to pass which combination via searchbnf.conf
    """
    input = Option(require=False, default="_raw")
    #jq_command = Option(require=True, default="jqcommand")
    jq_command = Option(require=False ) #, default="inline_args")
    filter = Option(require=False ) #, default="inline_args")
    output = Option(require=False, default="json")
    debug =  Option(require=False, default="false")

    def stream(self, records):
        for record in records:
            try:
                
                #toSearchlog(  "jq command: " + self.jq_command)
                #"""
                #record[self.output] = "bla "

                #from subprocess import run, PIPE
                if self.jq_command is None:
                    tmp = self.filter
                    toSearchlog( "jq syntax we pass from rawargs: " + str(tmp) )
                else:
                    tmp = record[self.jq_command]
                    toSearchlog( "jq syntax we pass from input value: " + tmp)

                #toSearchlog( "jq syntax we pass: " + tmp)
                #"""

                p = run(['jq', tmp ], stdout=PIPE, input=record[self.input], encoding='ascii') # record[self.jq_command]
                
                record[self.output] = str(p.stdout)
                if self.debug=="true":
                    record["returncode"] = str(p.returncode)
                    record["stderr"] = str(p.stderr)

            except Exception as e:
                import traceback
                stack =  traceback.format_exc()
                toSearchlog(stack)
            
            yield record

    def __init__(self):
        super(jq, self).__init__()
        self.records = None

dispatch(jq, sys.argv, sys.stdin, sys.stdout, __name__)
