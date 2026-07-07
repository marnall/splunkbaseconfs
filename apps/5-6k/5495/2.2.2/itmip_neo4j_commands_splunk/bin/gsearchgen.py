import itmip_neo4j_commands_splunk_declare
#import logging
#import os
import sys
#import time
import re

from splunklib.searchcommands import dispatch, Configuration, Option, GeneratingCommand
from itmip_neo4j_commands_splunk_common import neo4jenvironment

@Configuration(type='reporting',distributed=False)
class gsearchgen(GeneratingCommand):
    _query = None
    _debug = False
    _account = None

    @Option(require=True)
    def query(self):
        if re.search('(CREATE|DELETE|MERGE)\s+', self._query, re.I):
            self.write_error("Query is not allowed to contain CREATE or DELETE!")
            exit()
        return self._query

    @query.setter
    def query(self, value):
        self._query = value

    @Option
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        self._debug = value

    @Option
    def account(self):
        return self._account

    @account.setter
    def account(self, value):
        self._account = value


    def generate(self):
        self._debug = bool(self._debug)

        if self._account is None:
            account = "neo4j"
        else:
            account = self.account
        
        try:
            neo4jenv = neo4jenvironment(outerclass=self, account=account, scriptname="gsearchgen", debug=self._debug, statsonly=False)
        except Exception as e:
            self.write_error("Not possible to setup neo4jenvironment: {0}".format(e))
            exit()

        try:  
            outcome = neo4jenv.execute_query(query=self.query, data="")
            if outcome:
                for each in outcome:
                    yield each
        except Exception as e:
            if self._debug: neo4jenv.logger2.debug("The execute query raised the following error: {0}".format(e))
   
        return



if __name__ == "__main__":
    dispatch(gsearchgen, sys.argv, sys.stdin, sys.stdout, __name__)
