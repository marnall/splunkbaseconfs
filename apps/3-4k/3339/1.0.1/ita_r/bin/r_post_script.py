#!/usr/bin/env python
# coding=utf-8

from __future__ import absolute_import
from __future__ import division, print_function
from __future__ import unicode_literals

from splunklib.searchcommands import dispatch
from splunklib.searchcommands import GeneratingCommand
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import Option

from R import R
from splunk.clilib import cli_common as cli

import sys


@Configuration()
class RPostScriptCommand(GeneratingCommand):
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

    session = Option(
        doc='''
        **Syntax:** **session=***<session id>*
        **Description:** ID of the session that holds the data.''',
        require=True)

    def generate(self):

        # Get global configurations
        cfg = cli.getConfStanza('rsetup', 'R')
        baseurl = cfg.get('baseurl')

        # Create a new R object
        r = R(baseurl)

        # Send the script to R
        status, session, message = r.runRpostscript(self.script, self.session)

        # Return the response
        yield {
            "session": baseurl + "/ocpu/tmp/" + str(session),
            "status_code": status,
            "message": message
        }

dispatch(RPostScriptCommand, sys.argv, sys.stdin, sys.stdout, __name__)
