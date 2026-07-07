# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import json
import traceback
import os.path as op
import splunk.rest as rest

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path

from gt_utils.transformer import GTConverter
from splunk.persistconn.application import PersistentServerConnectionApplication
from ITOA.rest_interface_provider_base import SplunkdRestInterfaceBase


def flatten_query_params(params):
    # Query parameters are provided as a list of pairs and can be repeated, e.g.:
    #
    #   "query": [ ["arg1","val1"], ["arg2", "val2"], ["arg1", val2"] ]
    #
    # This function simply accepts only the first parameter and discards duplicates and is not intended to provide an
    # example of advanced argument handling.
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened


class GTTransformer(PersistentServerConnectionApplication, SplunkdRestInterfaceBase):

    def __init__(self, *args, **kwargs):
        PersistentServerConnectionApplication.__init__(self)
        self.sessionKey = None
        self.currentUser = None

    def handle(self, in_string):
        """
        Main method handling all http requests

        Supported requests:
        gt: <glasstable json> - parse raw json GT
        id: <gt_id> - parse GT by id from ITSI kvstore
        refresh: 1 - (debugging) restarts the GTTransformer handler to override persistency.
            it will return a 'JSON reply had no "payload" value', as there's no output, but ignore it

        :param in_string: input string
        :return: output
        """
        try:
            request = json.loads(in_string)
            self.sessionKey = request['session']['authtoken']
            self.currentUser = request['session']['user']
            self.migration_check(self.sessionKey)
            query = dict(request.get('form', []))

            gt = query.get('gt')
            id = query.get('id')
            refresh = query.get('refresh')

            if refresh:
                sys.exit()

            if gt:
                gt = json.loads(gt)
            else:
                if id:
                    response = self.fetch_gt(id)
                    if response['response']['status'] != '200':
                        return {
                            'status': 400,
                            'payload': 'Error fetching glass table.'
                        }
                    gt = json.loads(response['content'])

                else:
                    return {
                        'status': 400,
                        'payload': 'No glass table ID provided.'
                    }

            conv = GTConverter(session_key=self.sessionKey)
            response = conv.parse_glasstable(gt)
            return {
                'status': 200,
                'payload': response
            }
        except Exception:
            tb = traceback.format_exc()
            return {
                'status': 500,
                'payload': 'Error: ' + str(tb)
            }

    def fetch_gt(self, id):
        path = rest.makeSplunkdUri() + 'servicesNS/%s/SA-ITOA/itoa_interface/glass_table/%s' % (self.currentUser, id)
        response, content = rest.simpleRequest(
            path,
            method='GET',
            sessionKey=self.sessionKey,
            raiseAllErrors=False
        )
        return {'response': response, 'content': content}
