# standard packages
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
debug_logger = log_helper.setup(logging.INFO, 'ListLensesPersistentHandler', 'list_lenses_persistent_handler.log')

MISSING_PARAM_ERR = 'missing parameter {}'

class ListLensesPersistentHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def flatten_query_params(self, params):
        flattened = {}
        for i, j in params:
            flattened[i] = flattened.get(i) or j
        return flattened

    def handle(self, in_string):
        request = json.loads(in_string)
        session_key = request['session']['authtoken']
        params = self.flatten_query_params(request['query'])

        if 'organization_master_account_link_alternate' not in params:
            payload = {'text': MISSING_PARAM_ERR.format('organization_master_account_link_alternate')}
            return json.dumps({
                'payload': payload,
                'status': 400
            })

        organization_master_account_link_alternate = params['organization_master_account_link_alternate']

        try:
            grand_central_aws_account_eai_response_payload = simple_request_eai(
                organization_master_account_link_alternate,
                'list',
                'GET',
                session_key
            )
        except Exception as e:
            return json.dumps({
                'payload': 'problem calling simple_request_eai: {}'.format(e),
                'status': 500
            })

        aws_access_key = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_access_key']
        aws_secret_key_link_alternate = grand_central_aws_account_eai_response_payload['entry'][0]['content']['aws_secret_key_link_alternate']
        passwords_conf_payload = simple_request_eai(aws_secret_key_link_alternate, 'list', 'GET', session_key)
        aws_secret_key = passwords_conf_payload['entry'][0]['content']['clear_password']

        try:
            wa = WellArchitected(
                {
                    'service_name': WA_SERVICE_NAME,
                    'endpoint_url': WA_ENDPOINT_URL,
                    'region_name': WA_REGION_NAME,
                    'aws_access_key_id': aws_access_key,
                    'aws_secret_access_key': aws_secret_key
                }
            )
        except Exception as e:
            logger.error('Error when instantiating wa: {}'.format(e))
            return json.dumps({
                'payload': 'problem instantiating well_architected instance: {}'.format(e),
                'status': 500
            })

        try:
            lenses = wa.list_lenses({ 'MaxResults': 50 })
        except Exception as e:
            logger.error('Error when listing lenses: {}'.format(e))
            return json.dumps({
                'payload': 'Error when listing lenses:: {}'.format(e),
                'status': 500
            })

        return json.dumps({
            'payload': lenses,
            'status': 200
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
