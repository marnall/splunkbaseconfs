""" breach_catalog.py

Splunk scripted input which downloads and outputs latest Spycloud breaches.

"""
from collections import OrderedDict
import json
import os
import sys

from requests import HTTPError
import api
import common


def main():
    """ Main method """
    session_key = common.get_session_key()
    api_key = common.get_credentials(session_key)

    checkpoint_dir = os.path.join(os.environ.get(
        'SPLUNK_HOME'), 'etc', 'apps', 'SpyCloud', 'local', 'data')
    checkpoint_path = os.path.join(checkpoint_dir, 'breach_catalog.checkpoint')
    try:
        with open(checkpoint_path, 'r') as checkpoint_file:
            checkpoint, checkpoint_id = checkpoint_file.read().split('\n')[0:2]
    except IOError:
        checkpoint = '2000-01-01'
        checkpoint_id = ''

    latest = checkpoint
    try:
        for result in api.breach_catalog(api_key, checkpoint):
            if str(result['uuid']) == checkpoint_id:
                break
            if common.newer_timestamp(latest, result['spycloud_publish_date']):
                latest = result['spycloud_publish_date']
                latest_id = str(result['uuid'])
            # Force timestamp to front of event
            ordered_result = OrderedDict()
            if 'breach_date' in result:
                ordered_result['breach_date'] = result['breach_date']
                del result['breach_date']
            for key in result:
                ordered_result[key] = result[key]
            print json.dumps(ordered_result)
    except HTTPError as http_exception:
        if http_exception.response.status_code == 403:
            message = "Failed to authenticate to SpyCloud API. " \
                      "Please make sure you have entered credentials on the app setup page."
        else:
            message = "Received error from SpyCloud API. Error code: %d. %s" \
                      % (http_exception.response.status_code, http_exception.response.text)
        common.make_error_message(message, session_key, 'breach_catalog.py')
        sys.exit(0)
    except Exception as other_exception: # pylint: disable=broad-except
        message = "SpyCloud encountered an error: %s" % (str(other_exception))
        common.make_error_message(message, session_key, 'breach_catalog.py')
        sys.exit(0)

    latest = latest.split('T')[0]
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    if not checkpoint == latest:
        with open(checkpoint_path, 'w') as checkpoint_file:
            checkpoint_file.write(latest + '\n' + latest_id)


if __name__ == "__main__":
    main()
