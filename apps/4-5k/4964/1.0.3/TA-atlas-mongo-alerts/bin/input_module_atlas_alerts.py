# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import json
import requests
from requests.auth import HTTPDigestAuth

DEFAULT_ONLY_LAST_X_MIN = False
DEFAULT_SINCE_MINUTES_AGO = 150  # Since how long into the past script reads the alerts

# Arguments variable name
API_PUBLIC_KEY = 'apiPublicKey'
API_PRIVATE_KEY = 'apiPrivateKey'
ATLAS_BASE_URL = 'atlasBaseUrl'
EVENT_BATCH_SIZE = 'eventBatchSize'
EVENT_SIZE_LIMIT = 'eventSizeLimit'
SINCE_MINUTES_AGO = 'sinceMinutesAgo'
ONLY_LAST_X_MIN = 'onlyLastXMin'



def validate_input(helper, definition):
    """
    validate input
    :param helper:
    :param definition:
    :return:
    """
    print('inside validate input')
    print('field validation completed')


# splunk method to collect events
def collect_events(helper, event_writer):
    """
    data collection function
    :param helper:
    :param event_writer:
    :return: None
    """

    # read argument variables
    args = dict({
        API_PUBLIC_KEY: helper.get_arg(API_PUBLIC_KEY),
        API_PRIVATE_KEY: helper.get_arg(API_PRIVATE_KEY),
        ATLAS_BASE_URL: helper.get_arg(ATLAS_BASE_URL),
        SINCE_MINUTES_AGO: int(helper.get_arg(SINCE_MINUTES_AGO)) if helper.get_arg(SINCE_MINUTES_AGO) else DEFAULT_SINCE_MINUTES_AGO,
        ONLY_LAST_X_MIN: bool(helper.get_arg(ONLY_LAST_X_MIN)),
        EVENT_BATCH_SIZE: 10000,
        EVENT_SIZE_LIMIT: 10000
    })
    #write_event_to_splunk(helper, event_writer, args)
    download_alerts(args, helper, event_writer)

    #print('end of collect_events')


def write_event_to_splunk(helper, event_writer, payload):
    """
    Write payload to splunk
    :param helper: splunk helper
    :param event_writer: splunk event writer
    :param payload: data to write to splunk
    :return:
    """
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                             sourcetype=helper.get_sourcetype(), data=str(payload))
    event_writer.write_event(event)


def download_alerts(args, helper, event_writer):
    """
    Download Alerts
    :param args:  dict containing private key, public key and api url
    :param helper: splunk helper
    :param event_writer: splunk event writer
    :return: None
    """

    auth = HTTPDigestAuth(args.get(API_PUBLIC_KEY), args.get(API_PRIVATE_KEY))
    api_url = "{}/groups".format(args.get(ATLAS_BASE_URL))

    #write_event_to_splunk(helper, event_writer, payload=api_url)

    group_result = requests.get(api_url, auth=auth).json()

    #write_event_to_splunk(helper, event_writer, payload='Group result count: {}'.format(len(group_result)))

    new_alerts = []
    x_min_ago = datetime.utcnow() - timedelta(minutes=args.get(SINCE_MINUTES_AGO, DEFAULT_SINCE_MINUTES_AGO))

    for result in group_result.get('results', []):
        alerts = download_alerts_for_group(args, result['id'])
        #write_event_to_splunk(helper, event_writer,payload='all alert count: {} for group_id: {}'.format(len(alerts), result['id']))
        _new_alerts = [alert for alert in alerts if
                       not args.get(ONLY_LAST_X_MIN, DEFAULT_ONLY_LAST_X_MIN) or datetime.strptime(alert["created"], '%Y-%m-%dT%H:%M:%SZ') >= x_min_ago]
        new_alerts.extend(_new_alerts)

    #write_event_to_splunk(helper, event_writer, payload='new alert count: {} for group_id: {}'.format(len(new_alerts), result['id']))

    # write_event_to_splunk(helper, event_writer, payload=new_alerts)
    for alert_row in new_alerts:
        write_event_to_splunk(helper, event_writer, payload=json.dumps(alert_row))


def download_alerts_for_group(args, group_id):
    """
    Downloads the alerts for an Atlas group
    :param args: dict containing private key, public key and api url
    :param group_id: A String representing the group id of the Atlas project/group whose logs we are downloading
    :return:
    """

    api_public_key = args.get(API_PUBLIC_KEY)
    api_private_key = args.get(API_PRIVATE_KEY)
    atlas_base_url = args.get(ATLAS_BASE_URL)

    auth = HTTPDigestAuth(api_public_key, api_private_key)
    api_url = "{}/groups/{}/alerts".format(atlas_base_url, group_id)
    group_resp = requests.get(api_url, auth=auth).json()
    # print('group_resp: {}'.format(group_resp))

    if "error" in group_resp:
        error_msg = "Encountered an error while attempting to get alerts for group {}".format(group_id)
        raise Exception(error_msg)

    all_alerts = group_resp["results"]
    return all_alerts
