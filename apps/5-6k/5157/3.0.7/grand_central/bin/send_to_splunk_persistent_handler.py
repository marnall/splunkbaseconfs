# standard packages
import splunklib.client as client
import os
import sys
import json
import logging
import uuid


libpath = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [libpath]

# splunkd packages
import splunk.rest as rest
from splunk.persistconn.application import PersistentServerConnectionApplication

# custom packages
from well_architected import WellArchitected
from wa_constants import WA_SERVICE_NAME, WA_ENDPOINT_URL, WA_REGION_NAME
import log_helper

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'persistent_handler.log'])
logging.basicConfig(filename=logfile,level=logging.DEBUG)
debug_logger = log_helper.setup(logging.INFO, 'SendToSplunkPersistentHandler', 'send_to_splunk_persistent_handler.log')

MISSING_PARAM_ERR = 'missing parameter {}'

import splunklib.modularinput as modularinput

class SendToSplunkPersistentHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def flatten_query_params(self, params):
        flattened = {}
        for i, j in params:
            flattened[i] = flattened.get(i) or j
        debug_logger.info('PARAMS: {}'.format(flattened))
        return flattened

    def send(self, index_selection, payload, workload_name, lens_alias, session_key):
        s = client.connect(token=session_key)
        index = s.indexes[index_selection]

        for question in json.loads(payload):
            question['WorkloadName'] = workload_name
            question['LensAlias'] = lens_alias
            index.submit(
                json.dumps(question), 
                sourcetype="aws:wellarchitected:lensreview:improvementsummaries", 
                source="aws:wellarchitected"
            )

    def handle(self, in_string):
        request = json.loads(in_string)
        session_key = request['session']['authtoken']
        post_params = self.flatten_query_params(request['form'])

        try:
            self.send(
                post_params['index'], 
                post_params['payload'], 
                post_params['workloadName'], 
                post_params['lensAlias'], 
                session_key
            )

            return json.dumps({
                'status': 200,
                'payload': { 'message': 'Success' }
            })
        except Exception as e:
            debug_logger.error('Error sending to Splunk: {}'.format(e))
            return json.dumps({
                'status': 500,
                'payload': 'Error: {} - {}'.format(e, post_params)
            })

# borrowing some code from the base EAI handler
pid = os.getpid()
guid = str(uuid.uuid4().hex)

def simple_request_messages_to_str(messages):
    """
    Returns a readable string from a simple request response message

    Arguments
    messages -- The simple request response message to parse
    """
    entries = []
    for message in messages:
        entries.append(message.get('text'))
    return ','.join(entries)


def simple_request_eai(url, action, method, session_key, params=None):
    """
    Returns the payload response from a simpleRequest call

    Arguments
    url -- The REST handler endpoint to use in the simpleRequest
    action -- The readable requested action used in logs
    method -- The REST method to make the request with
    session_key -- The valid session key which will be used in the request
    params -- The parameters sent in the POST body of the simpleRequest
    """
    if not params:
        params = {}
    debug_logger.info(
        'action=http_internal_request state=start method=%s url=%s pid=%s guid=%s' % (method, url, pid, guid))
    try:
        response, content = rest.simpleRequest(
            url,
            getargs=dict(output_mode='json'),
            postargs=params,
            method=method,
            sessionKey=session_key
        )
    except Exception as e:
        debug_logger.error('action=http_internal_request state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise Exception('Unable to %s %s entry. %s' % (action, url, e))
    debug_logger.info('action=http_internal_request state=end pid=%s guid=%s' % (pid, guid))

    try:
        payload = json.loads(content)
    except Exception as e:
        debug_logger.error('action=http_internal_request state=error error="%s"' % e)
        raise Exception('Unable to parse %s response payload.' % url)

    if response.status not in [200, 201]:
        message = simple_request_messages_to_str(response.messages)
        debug_logger.error('action=http_internal_request state=error error="%s"' % message)
        raise Exception(
            'Unable to %s %s entry. %s' % (action, url, message))
    return payload
