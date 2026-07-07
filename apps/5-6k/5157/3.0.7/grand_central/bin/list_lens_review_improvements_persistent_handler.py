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
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

# custom packages
from well_architected import WellArchitected
from wa_constants import WA_SERVICE_NAME, WA_ENDPOINT_URL, WA_REGION_NAME

# logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'list_lens_review_improvements_persistent_handler.log'])
# logging.basicConfig(filename=logfile,level=logging.DEBUG)

MISSING_PARAM_ERR = 'missing parameter(s) {}'
EXTRA_PARAM_ERR = 'unexpected parameter(s) {}'
EXPECTED_PARAMS = {
    'organization_master_account_link_alternate',
    'workload_id',
    'lens_alias'
}

def setup_logger(name):
    """sets up a logger for logging to
        $SPLUNK_HOME/var/log/splunk/{name}.log

    Args:
        name (str): name of the file to log to.

    Returns:
        [Logger]: logger object
    """
    logger = logging.getLogger(name)
    file_name = '{}.log'.format(name)
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    file_handler = logging.handlers.RotatingFileHandler(
                    make_splunkhome_path(['var', 'log', 'splunk', file_name]),
                                        maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logging = setup_logger('list_lens_review_improvements_persistent_handler')

class ListLensReviewImprovementsPersistentHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def flatten_query_params(self, params):
        flattened = {}
        for i, j in params:
            flattened[i] = flattened.get(i) or j
        return flattened
        # return {k.encode('ascii').decode('ascii'): v.encode('ascii').decode('ascii') for k, v in flattened.items()}

    def handle(self, in_string):

        request = json.loads(in_string)
        session_key = request['session']['authtoken']
        params = self.flatten_query_params(request['query'])

        try:
            param_keys = set(params.keys())
            if EXPECTED_PARAMS != param_keys:
                if EXPECTED_PARAMS - param_keys != {}:
                    err_params = EXPECTED_PARAMS - param_keys
                    payload = {'text': MISSING_PARAM_ERR.format(str(err_params))}
                    logging.error(MISSING_PARAM_ERR.format(str(err_params)))
                else:
                    err_params = param_keys - EXPECTED_PARAMS
                    payload = {'text': EXTRA_PARAM_ERR.format(str(err_params))}
                    logging.error(MISSING_PARAM_ERR.format(str(err_params)))
                return json.dumps({
                    'payload': payload,
                    'status': 400
                })
        except Exception as e:
            return json.dumps({
                'payload': 'here: {}'.format(e),
                'status': 500
            })

        organization_master_account_link_alternate = params['organization_master_account_link_alternate']
        workload_id = params['workload_id']
        lens_alias = params['lens_alias']

        try:
            grand_central_aws_account_eai_response_payload = simple_request_eai(
                organization_master_account_link_alternate,
                'list',
                'GET',
                session_key
            )
        except Exception as e:
            return json.dumps({
                'payload': 'problem making simple_request: {}'.format(e),
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
            logging.error('Error instantiating wa: {}'.format(e))
            return json.dumps({
                'payload': str(e),
                'status': 500
            })

        try:
            lens_review_improvements = wa.list_lens_review_improvements({
                'WorkloadId': workload_id,
                'LensAlias': lens_alias
            })
        except Exception as e:
            logging.error('Error when listing lens review improvements: {}'.format(e))
            return json.dumps({
                'payload': {'error': str(e)},
                'status': 500
            })
        return json.dumps({
            'payload': lens_review_improvements,
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
    logging.info(
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
        logging.error('action=http_internal_request state=error error="%s" pid=%s guid=%s' % (e, pid, guid))
        raise Exception('Unable to %s %s entry. %s' % (action, url, e))
    logging.info('action=http_internal_request state=end pid=%s guid=%s' % (pid, guid))

    try:
        payload = json.loads(content)
    except Exception as e:
        logging.error('action=http_internal_request state=error error="%s"' % e)
        raise Exception('Unable to parse %s response payload.' % url)

    if response.status not in [200, 201]:
        message = simple_request_messages_to_str(response.messages)
        logging.error('action=http_internal_request state=error error="%s"' % message)
        raise Exception(
            'Unable to %s %s entry. %s' % (action, url, message))
    return payload