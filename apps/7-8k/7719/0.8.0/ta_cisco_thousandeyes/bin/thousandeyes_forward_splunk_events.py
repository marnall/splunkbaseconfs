import sys
import json
import copy

from log_helper import setup_logging

from thousandeyes_utils import get_severity_mapping
from thousandeyes_client import ThousandEyesClient
from thousandeyes_account_manager import ThousandEyesAccountManager
from thousandeyes_itsi_sampling import ITSISampler



ITSI_MANDOTORY_KEYS = ['event_id', 'itsi_group_id', 'itsi_group_title',
                     'itsi_group_severity', 'itsi_group_description', 'orig_time']

def is_itsi_alert(payload, logger):
    '''
    Check if the payload is a valid ITSI alert.
    :param payload: The payload to check.
    :return: True if valid, False otherwise.
    '''
    if not isinstance(payload, dict):
        logger.warning('Payload is not a dictionary')
        return False
    
    for key in ITSI_MANDOTORY_KEYS:
        if key not in payload:
            logger.warning(f'Missing required key: {key}')
            return False
    return True


def map_severity_to_user_configured_label(itsi_group_severity, session_key, logger):
    """
    Map ITSI group severity to user configured severity label.

    :param itsi_group_severity: The ITSI group severity value
    :param session_key: Splunk session key
    :param logger: logger object
    :return: User configured severity label
    """
    try:
        severity_mapping = get_severity_mapping(session_key, logger)

        # Convert severity to lowercase for case-insensitive matching
        itsi_severity_lower = str(itsi_group_severity).lower()

        # Get the mapped user configured label
        user_configured_label = severity_mapping.get(itsi_severity_lower, itsi_group_severity)

        logger.debug(f"Mapped severity '{itsi_group_severity}' to user configured label '{user_configured_label}'")
        return user_configured_label

    except Exception as e:
        logger.error(f"Error mapping severity '{itsi_group_severity}': {e}")
        # Return original severity if mapping fails
        return itsi_group_severity
    

def populate_user_configured_severity_label(body, session_key, logger):
    itsi_group_severity = body.get('itsi_group_severity')
    user_configured_severity_label = map_severity_to_user_configured_label(
        itsi_group_severity, session_key, logger
    )
    body['te_user_configured_severity_label'] = user_configured_severity_label
    logger.debug(f"Added te_user_configured_severity_label: {user_configured_severity_label} for event {body['event_id']} of episode {body['itsi_group_id']} ")


def populate_thousandeyes_test_id(body):
    val = body.get('entity.alias.thousandeyes_test_id', '').strip()
    if val and 'thousandeyes_test_id' not in body:
        body['thousandeyes_test_id'] = val

def handle_event(payload, logger):
    '''
    :param payload:
    :return: 0 - success, 1 - invalid payload, 2 - error while sending alert, 3 - system error
    '''
    result = payload.get('result')

    if not is_itsi_alert(result, logger):
        logger.warning(f'Invalid ITSI alert payload. Ignoring this alert {result}')
        return 1

    conf = payload.get('configuration')
    session_key = payload.get('session_key')
    
    body = copy.deepcopy(result)
    shorten_body = {k: body.get(k) for k in ITSI_MANDOTORY_KEYS + ['thousandeyes_test_id', 'itsi_is_first_event', 'itsi_is_last_event', 'entity.alias.thousandeyes_test_id']}
    logger.debug(f'Handling body (shorten): {shorten_body}')
    
    try:
        populate_thousandeyes_test_id(body)
        body['te_splunk_public_host_url'] = conf['public_host_url']
        populate_user_configured_severity_label(body, session_key, logger)
        shorten_body = {k: body.get(k) for k in ITSI_MANDOTORY_KEYS + ['thousandeyes_test_id', 'itsi_is_last_event', 'itsi_is_first_event', 'te_splunk_public_host_url', 'te_user_configured_severity_label']}
        logger.debug(f'Sampling body (shorten): {shorten_body}')

        sampler = ITSISampler(conf, session_key, logger)
        if sampler.select_and_send(body):
            logger.info(f'Successfully sent alert for event {body["event_id"]} of episode {body["itsi_group_id"]}')
        else:
            logger.info(f'Alert for event {body["event_id"]} of episode {body["itsi_group_id"]} was not selected for sending')
        return 0
    except Exception as e:
        logger.error(f'Error while sending alert to ThousandEyes: {e}')
        return 2


if __name__ == '__main__':
    logger = setup_logging(f'thousandeyes_forward_splunk_events')
    logger.info('Forward Splunk alerts to ThousandEyes')
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        payload = json.loads(sys.stdin.read())
        rc = handle_event(payload, logger)
    else:
        logger.error(f'Error while calling the script! sys.argv: {sys.argv}')
        rc = 3
    logger.info(f'ThousandEyes API call ends, return code: {rc}')
    sys.exit(rc)
