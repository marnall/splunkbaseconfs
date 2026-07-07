""" watchlist.py

Splunk scripted input which downloads and outputs latest Spycloud watchlist hits.

"""
from collections import OrderedDict
import json
import os
import re
import sys

from requests import HTTPError
import api
import common


def main():
    """ Main method """
    session_key = common.get_session_key()
    api_key = common.get_credentials(session_key)

    checkpoint_dir = os.path.join(
        os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'SpyCloud', 'local', 'data'
    )
    checkpoint_path = os.path.join(checkpoint_dir, 'watchlist.checkpoint')
    try:
        with open(checkpoint_path, 'r') as checkpoint_file:
            checkpoint, checkpoint_id = checkpoint_file.read().split('\n')[0:2]
    except IOError:
        checkpoint = '2016-01-01'
        checkpoint_id = ''

    latest = checkpoint
    try:
        for result in api.watchlist(api_key, checkpoint):
            if str(result['document_id']) == checkpoint_id:
                break
            if common.newer_timestamp(latest, result['spycloud_publish_date']):
                latest = re.search(r'(\d+-\d+-\d+)', result['spycloud_publish_date']).groups()[0]
                latest_id = str(result['document_id'])
            # Force timestamp to front of event
            ordered_result = OrderedDict()
            if 'spycloud_publish_date' in result:
                ordered_result['spycloud_publish_date'] = result['spycloud_publish_date']
                del result['spycloud_publish_date']
            for key in result:
                ordered_result[key] = result[key]
            print json.dumps(ordered_result)
    except HTTPError as http_exception:
        if http_exception.response.status_code == 403:
            message = "Failed to authenticate to SpyCloud API. " \
                      "Please make sure you have entered credentials on the app setup page."
        else:
            message = "Received error from SpyCloud API. Error code: %d. %s" % (
                http_exception.response.status_code, http_exception.response.text)
        common.make_error_message(message, session_key, 'watchlist.py')
        sys.exit(0)
    except Exception as other_exception: # pylint: disable=broad-except
        message = "SpyCloud encountered an error: %s" % (str(other_exception))
        common.make_error_message(message, session_key, 'watchlist.py')
        sys.exit(0)

    latest = latest.split('T')[0]
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    if not checkpoint == latest:
        with open(checkpoint_path, 'w') as checkpoint_file:
            checkpoint_file.write(latest + '\n' + latest_id)


if __name__ == "__main__":
    main()
