#!/usr/bin/env python
import json
import requests

DEFAULT_RESULT_LIMIT=500

class SnipeIT:
    def __init__(self, server, token):
        if not server.startswith('https://'):
            # raise Exception(f'Configured server url must be https: {server}')
            raise Exception('Configured server url must be https: %s' % server)

        self.server = server
        self.token = token


    def assetSearch(self, asset_name, limit=DEFAULT_RESULT_LIMIT):
        uri = '/api/v1/hardware'
        params = {'search': asset_name, 'limit': limit}
        # yield from self.__make_paginated_get_request(uri, params=params)
        for result in self.__make_paginated_get_request(uri, params=params):
            yield result
        
    def userSearch(self, user, limit=DEFAULT_RESULT_LIMIT):
        uri = '/api/v1/users'
        params = {'search': user, 'limit': limit}
        # yield from self.__make_paginated_get_request(uri, params=params)
        for result in self.__make_paginated_get_request(uri, params=params):
            yield result

    def __make_paginated_get_request(self, uri, params):
        # Get first page
        requested_limit = params['limit']
        params['limit'] = DEFAULT_RESULT_LIMIT
        response = self.__make_get_request(uri, params)
        collected = len(response['rows'])
        remaining = response['total'] - collected

        for result in response['rows']:
            yield result

        # Get remaining pages
        while (remaining and collected < requested_limit):
            remaining = requested_limit - collected
            limit = (DEFAULT_RESULT_LIMIT if DEFAULT_RESULT_LIMIT <=
                remaining else remaining)

            params['limit'] = limit
            params['offset'] = collected
            response = self.__make_get_request(uri, params)
            for result in response['rows']:
                yield result

            collected += len(response['rows'])
            remaining = response['total'] - collected
        
    def __make_get_request(self, uri, params=None):
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.token
        }

        response = requests.get(self.server + uri,
            params=params,
            headers=headers)
        data = json.loads(response.content)
        return data
