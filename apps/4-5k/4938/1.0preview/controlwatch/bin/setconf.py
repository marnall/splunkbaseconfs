from __future__ import print_function
import sys,re
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, Boolean
import base64
import json
import time
import collections
import logging
from lib import utils

@Configuration(type='reporting')
class SetConf(GeneratingCommand):
    conf = Option(require=True)
    stanza = Option(require=True)
    variable = Option(require=True)
    value = Option(require=True)

    def prepare(self):
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Initializing command")
        if self.service is None:
            raise Exception('Configuration requires_srinfo in commands.conf must be true')
            return
        self.logger.debug(self.service.confs)

    def generate(self):
        found = utils.setVariable(self.service, self.conf, self.stanza, self.variable, self.value)

        yield {
            "value": found,
            }

        # self.logger.debug("Setting Configuration Variable")
        # title = "{}:{}:{}".format(self.conf, self.stanza, self.variable)
        # return [{
        #     title: utils.setConf(self.service, self.conf, self.stanza, self.variable, self.value)
        #     }]

if __name__ == '__main__':
   dispatch(SetConf, sys.argv, sys.stdin, sys.stdout, __name__)
