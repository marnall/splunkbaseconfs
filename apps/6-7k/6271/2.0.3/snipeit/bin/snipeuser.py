#!/usr/bin/env python

import sys
import os
from snipeit import SnipeIT, DEFAULT_RESULT_LIMIT

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

cache = {}

@Configuration()
class SnipeUserCommand(StreamingCommand):
    search = Option()
    infield = Option()
    outfield = Option(default='users')
    limit = Option(default=DEFAULT_RESULT_LIMIT,
        validate=validators.Integer(1))

    def stream(self, events):
        server, token = self.__get_credentials()
        snipeit = SnipeIT(server, token)

        if not self.search and not self.infield:
            raise AttributeError('snipeuser: infield or search must be set')

        if self.search and self.infield:
            raise AttributeError('snipeuser: infield and search cannot both be set')
       
        query = self.search if self.search else None

        for event in events:
            results = [None]
            if not query and self.infield in event:
                query = event[self.infield]

            if query:
                if query in cache:
                    results = cache[query]
                else:
                    results = list(snipeit.userSearch(query, limit=self.limit))
                    cache[query] = results

            event[self.outfield] = results
            yield event

    def __get_credentials(self):
        storage_passwords = list(self.service.storage_passwords)
        passwd = None
        for p in storage_passwords:
            if p.access.app == 'snipeit':
                passwd = p
                break
        
        if not passwd:
            raise Exception('snipeasset: SnipeIT credentials are not configured. Please setup SnipeIT app')

        server = passwd.content.get('username')
        token = passwd.content.get('clear_password')

        return server, token

dispatch(SnipeUserCommand, sys.argv, sys.stdin, sys.stdout, __name__)
