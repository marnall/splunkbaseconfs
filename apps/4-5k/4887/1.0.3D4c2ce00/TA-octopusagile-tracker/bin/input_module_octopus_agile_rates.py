
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import dateutil.parser

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
def round_minutes(dt, direction, resolution):
    new_minute = (dt.minute // resolution + (1 if direction == 'up' else 0)) * resolution
    return dt + datetime.timedelta(minutes=new_minute - dt.minute)


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # rate_code = definition.parameters.get('rate_code', None)
    pass

def collect_events(helper, ew):

    checkpoint_key = "start_time"
    start_time = helper.get_check_point(checkpoint_key)
    if not start_time:
        start_time = helper.get_arg('start_date')

    proxy_settings = helper.get_proxy()
    rate_code = helper.get_arg('rate_code')
    helper.log_warning(start_time)
    if '.' not in start_time:
        start_time = start_time + '.0'
    start_dt = datetime.datetime.strptime(start_time,"%Y-%m-%d %H:%M:%S.%f")
    helper.log_info(start_dt)
    now = round_minutes(datetime.datetime.now(),'down',30)
    dt_diff = now - start_dt
    end_dt = start_dt + datetime.timedelta(days=1)
    if end_dt < start_dt:
        helper.log_warning("Not running as start time is later than end time")
        exit(0)
    new_rate_announce_time = datetime.datetime.combine(datetime.date.today(), datetime.time(16, 0))
    if now > new_rate_announce_time:
        midnight_tonight = datetime.datetime.combine(datetime.date.today(), datetime.time(16, 0))
        tomorrow_cutoff = datetime.datetime.combine(datetime.date.today()+datetime.timedelta(days=1), datetime.time(23, 30))
        if start_dt > tomorrow_cutoff:
            helper.log_warning("Start time is after 11pm tomorrow - no info available yet")
#            start_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(23, 0))
#            end_dt = start_dt + datetime.timedelta(days=1)
            exit(2)
        if start_dt >= tomorrow_cutoff:
            helper.log_warning("No point looking for more than the cut off")
            exit(3)
        if start_dt < tomorrow_cutoff:
            helper.log_warning("Getting tomorrows data")
            start_dt = round_minutes(datetime.datetime.now(),'down',30)
            end_dt = start_dt + datetime.timedelta(days=1)

	#Is the checkpoint before 11pm tomorrow?
#        if start_dt < midnight_tonight

#    if (dt_diff>datetime.timedelta(days=1)):
#        end_dt = start_dt + datetime.timedelta(days=1)
#    else:
#        end_dt = now

    if end_dt-start_dt == 0:
        helper.log_warning("Nothing to do!")
        exit(0)
    helper.log_warning(end_dt)
    #response = requests.get("
    url="https://api.octopus.energy/v1/products/{}/electricity-tariffs/E-1R-{}-C/standard-unit-rates/?period_from={}&period_to={}".format(rate_code,rate_code,start_dt, end_dt)
    helper.log_debug(url)
    method = "GET"
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    response.raise_for_status()
    r_json = response.json()
    print(response.content)
    for rate in r_json['results']:
        event = helper.new_event(time=rate['valid_from'], host="localhost", index=helper.get_arg("index"), source="octopus_agile_api", sourcetype=helper.get_sourcetype(), data=json.dumps(rate))
        ew.write_event(event)
    if len(r_json['results'])>0:
        helper.save_check_point(checkpoint_key, str(end_dt))