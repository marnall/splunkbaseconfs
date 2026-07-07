# -*- coding: utf-8 -*-
import requests
import json

# Arguments variable name
LIMIT = 'limit'
OLDEST = 'oldest'
AUTHORIZATION = 'slack_audit_log_api_token'

api_url = "https://api.slack.com/audit/v1/logs"


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
        LIMIT: str(helper.get_arg(LIMIT)),
        OLDEST: str(helper.get_arg(OLDEST)),
        AUTHORIZATION: str(helper.get_arg(AUTHORIZATION)),
    })
    #write_event_to_splunk(helper, event_writer, args)

    querystring = {"limit": args.get(LIMIT,'0000'), "oldest": args.get(OLDEST,'0')}

    headers = {
        'Authorization': "Bearer {}".format(args.get(AUTHORIZATION)),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    response = requests.request("GET", api_url, headers=headers, params=querystring)
    response.raise_for_status()
    result = response.json()
    for row in result['entries']:
        write_event_to_splunk(helper, event_writer, payload=json.dumps(row))

    


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

