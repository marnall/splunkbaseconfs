
# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import json

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input,
uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza
    configurations
    """
    # This example accesses the modular input variable
    # checkbox = definition.parameters.get('checkbox', None)
    pass


def get_zones(auth_email, auth_key):

    try:
        response = requests.get(
            url='https://api.cloudflare.com/client/v4/zones/',
            params={
                "match": 'all',
            },
            headers={
                "X-Auth-Email": auth_email,
                "X-Auth-Key": auth_key,
                "Content-Type": "application/json",
            },
        )
        zones = response.content
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
    return zones


def get_waf_events(zone_id, auth_email, auth_key, parameters):

    try:
        response = requests.get(
            url='https://api.cloudflare.com/client/v4/zones/' +
                zone_id + '/logs/received',
            params=parameters,
            headers={
                "X-Auth-Email": auth_email,
                "X-Auth-Key": auth_key,
                "Content-Type": "application/json",
            },
        )
        events = response.text
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
    return events


def collect_events(helper, ew):

    # get global variable configuration
    auth_key = helper.get_global_setting('x_auth_key')
    auth_email = helper.get_global_setting('x_auth_email')
    earliest = helper.get_arg('earliest_event')
    c = helper.get_arg('event_count')

    try:
        c = int(c)
    except:
        c = 0
    timestamps = helper.get_arg('timestamps')

    start_time = datetime.datetime.now() - datetime.timedelta(minutes=int(earliest))
    end_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
    waf_fields = "CacheCacheStatus,CacheResponseBytes,CacheResponseStatus,ClientASN,ClientCountry,ClientDeviceType,ClientIP,ClientIPClass,ClientRequestBytes,ClientRequestHost,ClientRequestMethod,ClientRequestProtocol,ClientRequestReferer,ClientRequestURI,ClientRequestUserAgent,ClientSSLCipher,ClientSSLProtocol,ClientSrcPort,EdgeColoID,EdgeEndTimestamp,EdgePathingOp,EdgePathingSrc,EdgePathingStatus,EdgeResponseBytes,EdgeResponseCompressionRatio,EdgeResponseStatus,EdgeStartTimestamp,OriginIP,OriginResponseBytes,OriginResponseHTTPExpires,OriginResponseHTTPLastModified,OriginResponseStatus,OriginResponseTime,RayID,WAFAction,WAFFlags,WAFMatchedVar,WAFProfile,WAFRuleID,WAFRuleMessage"

    if c >= 1:
        parameters = {
            "timestamps": timestamps,
            "fields": str(waf_fields),
            "start": start_time.strftime("%s"),
            "end": end_time.strftime("%s"),
            "count": c
        }
    else:
         parameters = {
            "timestamps": timestamps,
            "fields": str(waf_fields),
            "start": start_time.strftime("%s"),
            "end": end_time.strftime("%s"),
        }

    response = get_zones(auth_email, auth_key)
    zones = json.loads(response)
    for zone in zones["result"]:
        zone_id = zone["id"]
        zone_name = zone["name"]
        events = get_waf_events(zone_id, auth_email, auth_key, parameters)
        events = events.split('\n')
        for waf_event in events:
            event = helper.new_event(source=zone_name,
                                     index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(),
                                     data=waf_event)
            ew.write_event(event)
