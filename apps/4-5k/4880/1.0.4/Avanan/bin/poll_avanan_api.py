from __future__ import print_function
import json
import os
import sys

import requests

from utils import get_access_token, logger

API_ROOT_URL = 'https://splunk-app-production-1.avanan.net'


class Unauthorized(Exception):
    pass


def run(access_token):
    script_dirpath = os.path.dirname(os.path.join(os.getcwd(), __file__))
    last_eventid_filepath = os.path.join(script_dirpath, "last_event.txt")

    # Open file containing the last event ID and get the last record read
    last_eventid = 0
    if os.path.isfile(last_eventid_filepath):
        with open(last_eventid_filepath) as file_:
            last_eventid = int(file_.readline())
    else:
        logger.error('Error: ' + last_eventid_filepath + ' file not found! Starting from zero. \n')

    this_last_eventid = last_eventid
    while True:
        url = '%s/events?last_id=%s' % (API_ROOT_URL, this_last_eventid)
        logger.debug('Sending request to: %s' % url)
        response = requests.get(
            url,
            headers={'Authorization': access_token},
        )
        logger.debug('Response code: %s' % response.status_code)
        if response.status_code in (401, 403):
            raise Unauthorized
        elif response.status_code != 200:
            return
        data = response.json()
        events = data['events']
        logger.debug('Received %s events' % len(events))

        if not events:
            break
        for item in events:
            item['x_domain_name'] = data['domain']
            print(json.dumps(item))
            this_last_eventid = int(item['index_ts'])

    logger.debug('Going to store %s to last_event.txt' % this_last_eventid)
    with open(last_eventid_filepath, 'w') as file_:
        file_.write(str(this_last_eventid))


if __name__ == '__main__':
    session_key = sys.stdin.readline()
    access_token = get_access_token(session_key)
    try:
        run(access_token)
    except Unauthorized:
        access_token = get_access_token(session_key, lookup_local_first=False)
        run(access_token)
