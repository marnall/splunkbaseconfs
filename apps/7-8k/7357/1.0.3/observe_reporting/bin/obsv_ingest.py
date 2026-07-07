#!/usr/bin/env python
import sys
import os
import logging
import time
import json
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from observe_helpers import observe_ingest, get_tenant, get_ingest_token

logger = logging.getLogger('obsv_ingest')

@Configuration()
class StreamingCSC(StreamingCommand):
    """
    The streamingcsc command ships events over http to Observe inc tenant.

    Example:

    ``| makeresults count=5 | eval celsius = random()%100 | obsvhttp``

    """
    def stream(self, records):

        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service
        #    info = service.info //access the Splunk Server info
        logger.debug("OBSERVE Search Metadata Debug Log")
        logger.debug(str(self._metadata))

        session_key= self._metadata.searchinfo.session_key
        obsv_ten = get_tenant(session_key=session_key)
        if obsv_ten == None:
            logger.error("Error fetching observe conf info")
            yield {'_time':time.time(),'_raw':"Error communicating with Splunk conf system"}
        else:
            ten_resp = json.loads(obsv_ten.decode('utf-8'))
            tenant_id = ten_resp['entry'][0]['content']['tenant_id']
            obsv_site = ten_resp['entry'][0]['content']['observe_site']
            obsv_token = get_ingest_token(session_key=session_key,tenant_id=tenant_id)
            tok_resp = json.loads((obsv_token.decode('utf-8')))
            logger.debug(json.dumps(tok_resp))
            tenant_tok = tok_resp['entry'][0]['content']['clear_password']
        logger.debug("Shipping events to Observe")
        # create our session object from Requests
        sess = requests.Session()
        for record in records:
            # observe_ingest(tenant_id=None,obsv_site=None,payload=None, btok=None, extras=None)
            response = observe_ingest(sess,tenant_id,obsv_site,json.dumps(record),tenant_tok)
            logger.debug("OBSERVE Raw Response: {}".format(str(response)))
            if response == None:
                yield {'_time':time.time(),'_raw':"Error communicating with Observe Ingest, see search.log in search inspector"}
                return
            else:
                record["OBSERVE_RESPONSE"] = response
                yield record


dispatch(StreamingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
