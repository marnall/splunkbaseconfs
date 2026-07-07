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
from splunklib.searchcommands.validators import Fieldname

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
class RPairsCommand(StreamingCommand):
    """
    Class that defines the functionality of the command. It
    extends the StreamingCommand class which means it has to
    override the stream function.

    """

    col = Option(
        doc='''
        **Syntax:** **col=***<fieldname>*
        **Description:** Field that will be used for coloring the points.''',
        require=False,
        validate=Fieldname())

    def stream(self, records):

        # Define the script
        script = '''
            dataset <- lapply(dataset, function(x){
                if(typeof(x) == 'character'){
                    as.factor(x)
                } else {
                    x
                }
            });
        '''

        if self.col:
            script = script + '''
                pairs(dataset, col = dataset$%s);
            ''' % (self.col)
        else:
            script = script + '''
                pairs(dataset);
            '''

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
                "status_code": status,
                "message": message
            }

        else:
            # Use the session to run the pairs command
            status, session, message = r.runRpostscript(script, session)
            if status // 100 != 2:
                yield {
                    "session": session,
                    "status_code": status,
                    "message": message
                }

            else:
                yield {
                    "url": baseurl + '/ocpu/tmp/' + session + '/graphics/1'
                }


dispatch(RPairsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
