#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from splunklib.searchcommands import dispatch
from splunklib.searchcommands import StreamingCommand
from splunklib.searchcommands import Configuration

from R import R
from splunk.clilib import cli_common as cli

import sys


def parseDictValues(d):
    """
    Function to convert string values in a dict
    to float or integer values

    Parameters:
        - d: Python dict, containing string values
             that should be converted to float or int

    Return:
        - d: Python dict, parsed dict
    """

    for key, value in d.iteritems():

        # Test for a float
        try:
            d[key] = float(value)
        except ValueError:

            # Test for an int
            try:
                d[key] = int(value)
            except ValueError:
                pass
    return d


@Configuration()
class RPostDataCommand(StreamingCommand):
    """
    Class that defines the functionality of the command. It
    extends the StreamingCommand class which means it has to
    override the stream function.

    """

    def stream(self, records):

        filterFields = ['session', 'status_code', 'message']

        # Get global configurations
        cfg = cli.getConfStanza('rsetup', 'R')
        baseurl = cfg.get('baseurl')

        # Create a new R object
        r = R(baseurl)

        # Clean / parse the data
        recordsDict = []
        for record in records:
            toDict = dict(record)
            for key in filterFields:
                if key in toDict:
                    del toDict[key]
            recordsDict.append(parseDictValues(toDict))

        # Send the data to R
        status, session, message = r.runRpostdata(recordsDict)

        yield {
            "session": session,
            "status_code": status,
            "message": message
        }

dispatch(RPostDataCommand, sys.argv, sys.stdin, sys.stdout, __name__)
