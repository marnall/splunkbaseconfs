#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from splunklib.searchcommands import dispatch
from splunklib.searchcommands import StreamingCommand
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import Option
from splunklib.searchcommands.validators import Boolean

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
class RDoCallCommand(StreamingCommand):
    """
    Class that defines the functionality of the command. It
    extends the StreamingCommand class which means it has to
    override the stream function.

    """

    script = Option(
        doc='''
        **Syntax:** **script=***<Rscript>*
        **Description:** Script to execute in R.''',
        require=True)

    getResults = Option(
        doc='''
        **Syntax:** **getResults=***<boolean>*
        **Description:** Boolean, use true to retrieve the R output.''',
        require=False,
        validate=Boolean(),
        default=True)

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

        # Process the response
        if status // 100 != 2:
            yield {
                "session": session,
                "status": status,
                "message": message
            }

        else:
            # Use the session to run the custom script
            status, session, message = r.runRpostscript(self.script, session)
            if status // 100 != 2:
                yield {
                    "session": session,
                    "status": status,
                    "message": message
                }

            else:
                # Fetch the results when required
                if self.getResults:
                    status, results = r.runRgetresults(session)
                    for result in results:
                        yield result

                else:
                    messages = message.splitlines()
                    for (i, v) in enumerate(messages):
                        messages[i] = baseurl + v
                    yield {
                        "session": baseurl + '/ocpu/tmp/' + session,
                        "status": status,
                        "message": messages
                    }

dispatch(RDoCallCommand, sys.argv, sys.stdin, sys.stdout, __name__)
