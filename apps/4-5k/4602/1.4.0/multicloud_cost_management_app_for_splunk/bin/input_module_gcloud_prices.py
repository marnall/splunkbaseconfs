
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json
import csv
import re
from decimal import *

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    api_key = helper.get_arg('api_key')
    
    splunk_home = os.getenv('SPLUNK_HOME')

    # Request the latest gcloud compute prices
    print('Requesting Google Cloud Prices...')
    response1 = requests.get('https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus?key=' + api_key)
    prices1 = json.loads(json.dumps(response1.json()))
    nextPageToken = prices1['nextPageToken']
    
    response2 = requests.get('https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus?key=' + api_key + '&pageToken=' + nextPageToken)
    prices2 = json.loads(json.dumps(response2.json()))
    nextPageToken = prices2['nextPageToken']
    
    response3 = requests.get('https://cloudbilling.googleapis.com/v1/services/6F81-5844-456A/skus?key=' + api_key + '&pageToken=' + nextPageToken)
    prices3 = json.loads(json.dumps(response3.json()))
    
    print('Prices downloaded.')
    
    # Acquire the list of prices from the JSON
    skus1 = prices1['skus']
    skus2 = prices2['skus']
    skus3 = prices3['skus']
    
    allSkus = [skus1, skus2, skus3]
    
    # List to hold prices
    volumeoutput = [['type', 'region', 'timeunit', 'rate', 'currency']]
    ipoutput = [['type', 'region', 'timeunit', 'rate', 'currency']]
    
    ipPattern = re.compile("^Static Ip Charge in [\w+\s*]*$")
    pdStandardPattern = re.compile("^Storage PD Capacity in [\w+\s*]*$")
    pdSSDPattern = re.compile("^SSD backed PD Capacity in [\w+\s*]*$")
    localSSDPattern = re.compile("^SSD backed Local Storage in [\w+\s*]*$")
    
    for skuList in allSkus:
        for sku in skuList:
            # match IP
            if sku['skuId'] == '66A2-68EA-56BE':
                for region in sku['serviceRegions']:
                    ipoutput.append(['IP', region, 'hourly', Decimal(sku['pricingInfo'][0]['pricingExpression']['tieredRates'][1]['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
            if ipPattern.match(sku['description']):
                for region in sku['serviceRegions']:
                    for tierRate in sku['pricingInfo'][0]['pricingExpression']['tieredRates']:
                        if tierRate['startUsageAmount'] == 1:
                            ipoutput.append(['IP', region, 'hourly', Decimal(tierRate['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
                    
            # match PD Standard
            if sku['skuId'] == 'D973-5D65-BAB2':
                for region in sku['serviceRegions']:
                    volumeoutput.append(['pd-standard', region, 'gibibyte month', Decimal(sku['pricingInfo'][0]['pricingExpression']['tieredRates'][1]['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
            if pdStandardPattern.match(sku['description']):
                for region in sku['serviceRegions']:
                    for tierRate in sku['pricingInfo'][0]['pricingExpression']['tieredRates']:
                        if tierRate['unitPrice']['nanos'] > 0:
                            volumeoutput.append(['pd-standard', region, 'gibibyte month', Decimal(tierRate['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
                    
            # match PD SSD
            if sku['skuId'] == 'B188-61DD-52E4':
                for region in sku['serviceRegions']:
                    volumeoutput.append(['pd-ssd', region, 'gibibyte month', Decimal(sku['pricingInfo'][0]['pricingExpression']['tieredRates'][0]['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
            if pdSSDPattern.match(sku['description']):
                for region in sku['serviceRegions']:
                    for tierRate in sku['pricingInfo'][0]['pricingExpression']['tieredRates']:
                        if tierRate['unitPrice']['nanos'] > 0:
                            volumeoutput.append(['pd-ssd', region, 'gibibyte month', Decimal(tierRate['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
                            
            # match PD Balanced
            if sku['skuId'] == '6AE1-525F-8B80':
                for region in sku['serviceRegions']:
                    volumeoutput.append(['pd-balanced', region, 'gibibyte month', Decimal(sku['pricingInfo'][0]['pricingExpression']['tieredRates'][0]['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
            if pdSSDPattern.match(sku['description']):
                for region in sku['serviceRegions']:
                    for tierRate in sku['pricingInfo'][0]['pricingExpression']['tieredRates']:
                        if tierRate['unitPrice']['nanos'] > 0:
                            volumeoutput.append(['pd-balanced', region, 'gibibyte month', Decimal(tierRate['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
                    
            # match local SSD
            if sku['skuId'] == '62AF-A39E-269B':
                for region in sku['serviceRegions']:
                    volumeoutput.append(['local-ssd', region, 'gibibyte month', Decimal(sku['pricingInfo'][0]['pricingExpression']['tieredRates'][0]['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
            if localSSDPattern.match(sku['description']):
                for region in sku['serviceRegions']:
                    for tierRate in sku['pricingInfo'][0]['pricingExpression']['tieredRates']:
                        if tierRate['unitPrice']['nanos'] > 0:
                            volumeoutput.append(['local-ssd', region, 'gibibyte month', Decimal(tierRate['unitPrice']['nanos']) / Decimal(1000000000), 'USD'])
    
    
    print('Writing volumes csv...')
    gcloud_volume_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'gcloud_volumeprices.csv')
    with open(gcloud_volume_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(volumeoutput)
    csvFile.close()
    print('Finished writing volumes csv.')
    
    print('Writing ip csv...')
    gcloud_ip_price_path = os.path.join(splunk_home, 'etc', 'apps', 'multicloud_cost_management_app_for_splunk', 'lookups', 'gcloud_ipprices.csv')
    with open(gcloud_ip_price_path, 'w') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerows(ipoutput)
    csvFile.close()
    print('Finished writing ip csv.')
