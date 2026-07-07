#!/usr/bin/env python

import sys
import json
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from log4shell_regexes import *

@Configuration()
class Log4ShellRegexCommand(StreamingCommand):
    """ 

    ##Syntax


    ##Description


    ##Example


    """
    test = Option(
        doc='''
        **Syntax:** **test=***<default|thorough>*
        **Description:** ''',
        require=False)

    def stream(self, events):

        if not self.test:
            self.test = "default"

        if not self.test in ["default", "thorough"]:
            raise Exception("Invalid test type")

        if len(self.fieldnames) != 1:
            raise Exception("Only one field name must be provided")

        t = lambda s: [k for k in test(s)]
        tt = lambda s: [(k, list(v.keys())) for k, v in test_thorough(s).items()]

        for event in events:

            event['log4shellregex'] = []

            if not isinstance(event[self.fieldnames[0]], (list, tuple)):
                event[self.fieldnames[0]] = [event[self.fieldnames[0]]]

            for field_value in event[self.fieldnames[0]]:
                if self.test == "default":
                    event['log4shellregex'] += t(field_value)
                else:
                    event['log4shellregex'] += tt(field_value)
            yield event

dispatch(Log4ShellRegexCommand, sys.argv, sys.stdin, sys.stdout, __name__)
