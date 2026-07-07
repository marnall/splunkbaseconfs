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
from splunklib.searchcommands.validators import Set

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
class RCorrplotCommand(StreamingCommand):
    """
    Class that defines the functionality of the command. It
    extends the StreamingCommand class which means it has to
    override the stream function.

    """

    method = Option(
        doc='''
        **Syntax:** **method=***<method>*
        **Description:** Method to use for the corrplot visualization.''',
        require=False,
        validate=Set('circle',
                     'square',
                     'ellipse',
                     'number',
                     'pie',
                     'shade',
                     'color'),
        default='color')

    order = Option(
        doc='''
        **Syntax:** **order=***<ordering method>*
        **Description:** Method to use for the ordering of the clusters.''',
        require=False,
        validate=Set('original', 'AOE', 'FPC', 'hclust', 'alphabet'),
        default='original')

    bg = Option(
        doc='''
        **Syntax:** **bg=***<background color>*
        **Description:** Color to use for the background of the graph.''',
        require=False,
        default='white')

    title = Option(
        doc='''
        **Syntax:** **title=***<title>*
        **Description:** Title of the graph''',
        require=False,
        default='')

    def stream(self, records):

        # Define the script
        script = '''
            library(corrplot);
            numeric_columns <- sapply(dataset, is.numeric);
            dataset <- dataset[ , numeric_columns];
        '''

        script = script + '''
            c <- cor(dataset);
            corrplot(c, method = '%s', bg = '%s', title = '%s', order = '%s');
        ''' % (self.method, self.bg, self.title, self.order)

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


dispatch(RCorrplotCommand, sys.argv, sys.stdin, sys.stdout, __name__)
