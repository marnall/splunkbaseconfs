"""
findings.py

Reports findings from Detectify

"""


import time
import os
import json
import sys
import re
from collections import OrderedDict
try:
    import urlparse  # pylint: disable=import-error
except: #pylint: disable=bare-except
    from urllib.parse import urlparse
import calendar
import requests

import common

# Retrieve credentials from credential store
sesh_key = sys.stdin.readline().strip()
session_key = re.sub(r'sessionKey=', "", sesh_key)

dummy, key = common.get_credentials(session_key)
if not dummy or not key:
    MESSAGE = 'No credentials have been found. Please configure TA-detectify first.'
    common.make_error_message(MESSAGE, session_key, 'findings.py')
    sys.exit(0)

# Load checkpoint. If this is the first run, grab all findings
checkpoint_dir = os.path.join(os.environ.get('SPLUNK_HOME'),
                              'etc', 'apps', 'TA-detectify', 'local', 'data')
checkpoint_path = os.path.join(checkpoint_dir, 'findings.checkpoint')
try:
    with open(checkpoint_path, 'r') as f:
        CHECKPOINT = int(f.read().rstrip())
except IOError:
    CHECKPOINT = 1

now = int(calendar.timegm(time.gmtime()))
headers = {'X-Detectify-Key': key, 'Accept-Encoding': 'gzip', 'Accept': 'application/json'}


def is_scan_complete(profile_token):  # pylint: disable=redefined-outer-name
    """ Checks to see if scan has finished """
    resp = requests.get('https://api.detectify.com/rest/v2/scans/%s/'
                        % profile_token, headers=headers)
    resp.raise_for_status()
    return resp.json()['state'] == 'stopped'


# Get scan profiles
response = requests.get('https://api.detectify.com/rest/v2/profiles/', headers=headers,)
response.raise_for_status()
profile_tokens = {}
for profile in response.json():
    # Extract domain name from target endpoint
    domain = urlparse.urlparse(profile['endpoint']).path
    profile_tokens[profile['token']] = domain

UPDATE_CHECKPOINT = False
# Get and print findings for each profile
for profile_token in profile_tokens:
    # Do not proceed if a scan is running
    if not is_scan_complete(profile_token):
        continue
    profile_request = requests.get('https://api.detectify.com/rest/v2/findings/%s/?from=%d' %
                                   (profile_token, CHECKPOINT), headers=headers)
    profile_request.raise_for_status()
    if len(profile_request.json()) > 0:
        UPDATE_CHECKPOINT = True
    for finding in profile_request.json():
        # Place timestamp at beginning of event to make timestamp parsing easier
        output = OrderedDict()
        if 'timestamp' in finding:
            output['timestamp'] = finding['timestamp']
            del finding['timestamp']
        output['domain'] = profile_tokens[profile_token]
        for key in finding:
            output[key] = finding[key]
        print(json.dumps(output))

# Save checkpoint
if UPDATE_CHECKPOINT:
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    with open(checkpoint_path, 'w') as f:
        f.write(str(now))
