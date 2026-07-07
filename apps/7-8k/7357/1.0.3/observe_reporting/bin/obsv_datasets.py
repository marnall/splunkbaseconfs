#!/usr/bin/env python
import sys
import os
import logging
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
from splunklib.searchcommands import \
    dispatch, GeneratingCommand, Configuration, Option, validators
from observe_helpers import observe_query_datasets, get_tenant, get_token

logger = logging.getLogger('obsv_query')

@Configuration()
class GeneratingCSC(GeneratingCommand):
    """
    The generatingcommand returns data from Observe in up to 50k chunks

    Example:

    ``| obsvds``

    Returns a list of datasets and their IDs
    """

    def generate(self):

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info

        

        logger.error("OBSERVE Dataset Search Metadata Debug Log")
        logger.error(str(self._metadata))

        session_key= self._metadata.searchinfo.session_key
        earliest_time = self._metadata.searchinfo.earliest_time
        latest_time = self._metadata.searchinfo.latest_time
        obsv_ten = get_tenant(session_key=session_key)
        if obsv_ten == None:
            logger.error("Error fetching observe conf info")
            yield {'_time':time.time(),'_raw':"Error communicating with Splunk conf system"}
        else:
            ten_resp = json.loads(obsv_ten.decode('utf-8'))
            tenant_id = ten_resp['entry'][0]['content']['tenant_id']
            obsv_site = ten_resp['entry'][0]['content']['observe_site']
            obsv_token = get_token(session_key=session_key,tenant_id=tenant_id)
            tok_resp = json.loads((obsv_token.decode('utf-8')))
            logger.debug(json.dumps(tok_resp))
            tenant_tok = tok_resp['entry'][0]['content']['clear_password']
        logger.debug("Generating events from Observe")
        response = observe_query_datasets(tenant_id,obsv_site,tenant_tok)
        logger.debug("OBSERVE Raw Response: {}".format(str(response)))
        if response == None:
            yield {'_time':time.time(),'_raw':"Error communicating with Observe, see search.log in search inspector"}
            return 
        if type(response) is str:
            yield {'_time':time.time(),'_raw':response}
        else:
                json_obj = json.loads(response.text)
                for dataset in json_obj['data']:
                    yield {'_time': time.time(), 'sourcetype':'observe_api','source':'observe_dataset_api', '_raw': dataset}


dispatch(GeneratingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
