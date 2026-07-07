#!/usr/bin/env python

import sys
import os
import time
import json
from snipeit import SnipeIT, DEFAULT_RESULT_LIMIT

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators

cache = {}

@Configuration()
class SnipeUserSearchCommand(GeneratingCommand):
    search = Option()
    limit = Option(default=DEFAULT_RESULT_LIMIT,
        validate=validators.Integer(1))

    def generate(self):
        server, token = self.__get_credentials()
        snipeit = SnipeIT(server, token)
        query = self.search

        if query in cache:
            results = cache[query]
            for result in results:
                result['_time'] = time.time()
                yield result
        else:
            results = []
            for result in snipeit.userSearch(query, limit=self.limit):
                # Unlikely but we don't want to clobber anything
                if '_time' in result:
                    result['result_time'] = result['_time']

                result['source'] = server
                result['sourcetype'] = 'snipeit_user'
                result['_raw'] = json.dumps(result)
                result['_time'] = time.time()

                results.append(result)
                yield result

            cache[query] = results

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

dispatch(SnipeUserSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
