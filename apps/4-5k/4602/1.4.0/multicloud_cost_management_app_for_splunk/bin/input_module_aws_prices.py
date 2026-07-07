# encoding = utf-8

import os
import sys
import time
import datetime
import csv
import json
import requests

'''

# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    pass


def collect_events(helper, ew):

    splunk_home = os.getenv('SPLUNK_HOME')
    
    # Request prices from s3 bucket
    volume = requests.get('https://apto-aws-prices.s3.eu-west-2.amazonaws.com/volumes.json')
    ip = requests.get('https://apto-aws-prices.s3.eu-west-2.amazonaws.com/ips.json')

    # Acquire the JSON from the response
    volume_prices = json.loads(json.dumps(volume.json()))
    ip_prices = json.loads(json.dumps(ip.json()))

    print('Writing volumes csv...')
    aws_volume_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'aws_volumeprices.csv')
    with open(aws_volume_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(volume_prices)
    csvFile.close()
    print('Finished writing volumes csv.')

    print('Writing ip csv...')
    aws_ip_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'aws_ipprices.csv')
    with open(aws_ip_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(ip_prices)
    csvFile.close()
    print('Finished writing ip csv.')