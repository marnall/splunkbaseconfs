
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import requests
import re

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # subscription_id = definition.parameters.get('subscription_id', None)
    # tenant_id = definition.parameters.get('tenant_id', None)
    pass

def get_access_token(client_id, client_secret, tenant_id):
    endpoint = "https://login.windows.net/%s/oauth2/token" % tenant_id
    payload = {
        'resource': 'https://management.azure.com/',
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    try:
        response = requests.post(endpoint, data=payload).json()
        return response['access_token']
    except Exception, e:
        raise e

def get_start_date(helper, check_point_key):
    
    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)
    
    # If there was a check point date, retun it.
    if (d not in [None,'']):
        helper.log_debug("Getting start date. Checkpoint date found: %s" % d)
        return d
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("start_date")
        if (d not in [None,'']):
            helper.log_debug("Getting start date. Start date in stanza: %s" % d)
            return d
        else:
            # If there was no start date specified, default to 90 day ago
            d = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y-%m-%d')
            helper.log_debug("Getting start date. Calculated start date 90 days in the past: %s" % str(d))
            return d

def get_end_date(helper, query_days, start_date, max_days_ago):
    dt_start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    dt_end = dt_start + datetime.timedelta(days=query_days)
    dt_days_ago = datetime.date.today() - datetime.timedelta(days=max_days_ago)
    helper.log_debug("Getting end date. start: %s, max days: %s, end: %s" % (dt_start.strftime('%Y-%m-%d'), str(max_days_ago), dt_end.strftime('%Y-%m-%d')))
    
    # Adjust the end date if we went too far.
    if dt_end > dt_days_ago:
        d = dt_end
        dt_end = dt_days_ago
        helper.log_debug("Adjusting end date. Old value: %s, new value: %s" % (d.strftime('%Y-%m-%d'), dt_end.strftime('%Y-%m-%d')))
    
    # If the start date is greater than the end date, return None
    if dt_start >= dt_end:
        helper.log_debug("Start date '%s' is greater than or equal to the end date '%s'. Returning 'None'" % (dt_start.strftime('%Y-%m-%d'), dt_end.strftime('%Y-%m-%d')))
        return None
    else:
        helper.log_debug("Returning end date '%s'." % dt_end.strftime('%Y-%m-%d'))
        return dt_end.strftime('%Y-%m-%d')

def stream_values(ew, helper, usage_url, header, billing_periods_returned):
    
    try:
        r = requests.get(usage_url, headers=header)
        r.raise_for_status()
        usage_data = json.loads(r.text)
        
        for value in usage_data["value"]:
            billing_period_id = value["properties"]["billingPeriodId"]
            billing_period_search = re.search('\/subscriptions\/([^\/]+)\/providers\/Microsoft\.Billing\/billingPeriods\/([^\/]+)$', billing_period_id, re.IGNORECASE)
            if billing_period_search:
                billing_period = billing_period_search.group(2)
                billing_periods_returned.add(billing_period)
            event = helper.new_event(data=json.dumps(value), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype())
            ew.write_event(event)
            
        if ('nextLink' in usage_data) and (usage_data['nextLink'] not in [None,'']):
            helper.log_debug("nextLink found: '%s'." % str(usage_data['nextLink']))
            stream_values(ew, helper, usage_data['nextLink'], header, billing_periods_returned)
    except Exception as e:
        message = "HTTP Request error: %s" % str(e)
        helper.log_error(message)
        sys.exit(message)

def collect_billing_period(helper, ew, subscription_id, header, billing_period_name):
    api_version = "2017-04-24-preview"
    sourcetype = "azure:billing:period"
    
    billing_period_url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/%s?api-version=%s" % (subscription_id, billing_period_name, api_version)

    try:
        helper.log_debug("URL used to query billing periods: %s" % str(billing_period_url))
        r = requests.get(billing_period_url, headers=header)
        r.raise_for_status()
        billing_period_data = json.loads(r.text)
        event = helper.new_event(data=json.dumps(billing_period_data), source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=sourcetype)
        ew.write_event(event)
    except Exception as e:
        helper.log_error(str(e))

def collect_events(helper, ew):
    global_client_id = helper.get_global_setting("client_id")
    global_client_secret = helper.get_global_setting("client_secret")
    subscription_id = helper.get_arg("subscription_id")
    tenant_id = helper.get_arg("tenant_id")
    query_days = int(helper.get_arg("query_days"))
    
    billing_check_point_key = "%s_last_date" % helper.get_input_stanza_names()
    billing_period_check_point_key = "%s_last_billing_period_date" % helper.get_input_stanza_names()
    
    api_version = "2018-10-01"
    start_date = get_start_date(helper, billing_check_point_key)
    end_date = get_end_date(helper, query_days, start_date, max_days_ago=2)
    billing_periods_returned = set()
    billing_periods_checkpoint = helper.get_check_point(billing_period_check_point_key)
    
    access_token = get_access_token(global_client_id, global_client_secret, tenant_id)
    
    if(access_token) and (end_date is not None):

        header = {'Authorization':'Bearer ' + access_token}
        usage_url = "https://management.azure.com/subscriptions/%s/providers/Microsoft.Consumption/usageDetails?$orderby=properties/usageEnd&$expand=properties/meterDetails,properties/additionalProperties&$filter=properties/usageStart+ge+'%s'+AND properties/usageEnd+le+'%s'&api-version=%s" % (subscription_id, start_date, end_date, api_version)
        helper.log_debug("Getting events from URL: %s" % usage_url)
        try:
            stream_values(ew, helper, usage_url, header, billing_periods_returned)
            helper.save_check_point(billing_check_point_key, end_date)
            
            helper.log_debug("Billing periods returned from query: %s" % str(billing_periods_returned))
            
            # Get billing period data not already collected
            if len(billing_periods_returned) > 0:
            
                if billing_periods_checkpoint is None:
                    for period in billing_periods_returned:
                        collect_billing_period(helper, ew, subscription_id, header, period)
                        
                    helper.save_check_point(billing_period_check_point_key, repr(billing_periods_returned))
                    helper.log_debug("No billing periods in the check point. Check pointing the billing periods returned from the query: %s" % str(billing_periods_returned))
                else:
                    billing_periods_checkpoint_set = eval(billing_periods_checkpoint)
                    helper.log_debug("Billing periods found in the check pint: %s" % str(billing_periods_checkpoint))
                    
                    billing_periods_delta = billing_periods_returned - billing_periods_checkpoint_set
                    billing_periods_union = billing_periods_returned.union(billing_periods_checkpoint_set)
                    helper.log_debug("Delta between billing periods returned and check point billing periods: %s" % str(billing_periods_delta))
                    
                    for period in billing_periods_delta:
                        collect_billing_period(helper, ew, subscription_id, header, period)
                        
                    helper.save_check_point(billing_period_check_point_key, repr(billing_periods_union))
                    helper.log_debug("Saving the union of billing periods: %s" % str(billing_periods_union))
        except Exception as e:
            helper.log_error(str(e))