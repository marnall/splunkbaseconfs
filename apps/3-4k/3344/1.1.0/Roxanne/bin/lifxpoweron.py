#!/usr/bin/env python
import requests
import requests.auth
import os
from pprint import pformat  # here only for aesthetic
import time
import datetime
import splunk.clilib.cli_common
import json
import ast
import signal
import colorsys
import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

#Get Splunk Home
splunk_home = os.path.expandvars("$SPLUNK_HOME")


def power_on_devices(access_token, lightid):
        req = requests.put('https://api.lifx.com/v1/lights/'+str(lightid)+'/state', data={'power' : 'on'}, headers={'Authorization': 'Bearer '+access_token})
        return req
@Configuration(local=True)
class LIFXPowerOnCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """
    lightid = Option(
    doc='''
    **Syntax:** **lightid=***<lightid>*
    **Description:** The ID of the Light you'd like to alter''',
    require=False, validate=validators.Fieldname())

    #output = Option(
    #    doc='''
    #    **Syntax:** **fieldname=***<fieldname>*
    #    **Description:** Amount of Saturation between 0.0 and 1.0''',
    #    require=True, validate=validators.Fieldname())

    #pattern = Option(
    #    doc='''
    #    **Syntax:** **pattern=***<regular-expression>*
    #    **Description:** Regular expression pattern to match''',
    #    require=True, validate=validators.RegularExpression())

    #def stream(self, records):
    #    self.logger.debug('CountMatchesCommand: %s', self)  # logs command line
    #    pattern = self.pattern
    #    for record in records:
    #        count = 0L
    #        for fieldname in self.fieldnames:
    #            matches = pattern.findall(unicode(record[fieldname].decode("utf-8")))
    #            count += len(matches)
    #        record[self.fieldname] = count
    #        yield record


    def stream(self, events):
       # Put your event transformation code here
       for event in events:
            #Read in all Access Tokens from LIFX_tokens.conf
            settings = splunk.clilib.cli_common.readConfFile(splunk_home+"/etc/apps/LIFXAddonforSplunk/local/LIFX_tokens.conf")
            for item in settings.iteritems():
                for key in item[1].iteritems():
                    token = key[1]
                    #Create a new process for each access_token
                    power_on_devices(token,self.lightid)
            yield event

dispatch(LIFXPowerOnCommand, sys.argv, sys.stdin, sys.stdout, __name__)


