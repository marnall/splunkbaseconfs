# encoding = utf-8
import os
import splunk.appserver.mrsparkle.lib.util as util
import os
import sys
import time
import datetime
import csv
import zipfile
import json

import requests

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    url = 'https://s3.amazonaws.com/alexa-static/top-1m.csv.zip'
    filename = os.path.join(os.environ.get('SPLUNK_HOME'),
                            'etc', 'apps', 'TA-skylight-for-splunk',
                            url.split('/')[-1])
    directory_to_extract_to = os.path.join(os.environ.get('SPLUNK_HOME'),
                            'etc', 'apps', 'TA-skylight-for-splunk')
    with open(filename, "wb") as f:
        f.write(requests.get(url).content)
    zip_ref = zipfile.ZipFile(filename, 'r')
    csv_path = zip_ref.extract('top-1m.csv', directory_to_extract_to)
    zip_ref.close()
    with open(csv_path) as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            data = {
                'domain': row[1],
            }
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(data),
                done=True,
                unbroken=True)
            ew.write_event(event)
    os.remove(csv_path)
    os.remove(filename)
