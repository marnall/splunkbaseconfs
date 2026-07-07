# encoding = utf-8

import os
import sys
import time
import datetime

import datetime
import json
import splunklib.client
import splunklib.results as results

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
    
    # alerts = definition.parameters.get('alerts', None)
    # dashboard = definition.parameters.get('dashboard', None)
    pass

   



def collect_events(helper, ew):

    class vars:
        opt_alerts = helper.get_arg('alerts')
        opt_dashboard = helper.get_arg('dashboard')
        global_n2ws_api_url = helper.get_global_setting("api_url")
        global_n2ws_api_key = helper.get_global_setting("api_key")
        access_key = helper.get_check_point("access_key")
        refresh_key = helper.get_check_point("refresh_key")
        last_date = helper.get_global_setting("last_date")


    def generate_access_keys():
        response = helper.send_http_request(vars.global_n2ws_api_url + "/token/obtain/external_monitoring/", "POST",
        parameters=None, payload={ "api_key": vars.global_n2ws_api_key },
            headers= {
                 'Content-Type': 'application/json',
                  'Authorization': 'true'
              }, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

        response.raise_for_status()
        jobj = response.json()
        vars.access_key = jobj["access"]
        vars.refresh_key = jobj["refresh"]
        
        helper.save_check_point("access_key", vars.access_key)
        helper.save_check_point("refresh_key", vars.refresh_key)

            
    def refresh_access_key():
        response = helper.send_http_request(vars.global_n2ws_api_url + "/token/refresh/", "POST",
        parameters=None, payload={ "refresh": vars.refresh_key },
            headers= {
                 'Content-Type': 'application/json',
                  'Authorization': 'true'
              }, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)              

        if response.status_code == 200:
            jobj = response.json()
            vars.access_key = jobj["access"]
            helper.save_check_point("access_key", vars.access_key)
            return True
        else:
            helper.log_info("refresh key failed with status code '{}'".format(response.status_code));
            return False

        
        
    def tester_write(text):
        return
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=text)
        ew.write_event(event)
        
    def get_current_dashboard_stats(user, earliest, latest):
        service = splunklib.client.connect(host='localhost', port=8089, token=helper.context_meta['session_key'], owner="nobody")
     
        query = 'search index="'+ helper.get_output_index() + '" source="' + helper.get_input_type() + '" username="' + user + '" earliest="' + earliest + '" latest="' + latest + '" | stats ' + '''
            sum(dashboard_activity.backup_dr_fail_num),
            sum(dashboard_activity.backup_dr_partial_num),
            sum(dashboard_activity.backup_dr_success_num),
            sum(dashboard_activity.backup_fail_num),
            sum(dashboard_activity.backup_partial_num),
            sum(dashboard_activity.backup_s3_fail_num),
            sum(dashboard_activity.backup_s3_partial_num),
            sum(dashboard_activity.backup_s3_success_num),
            sum(dashboard_activity.backup_success_num) | rename sum(dashboard_activity.*) as *'''
        
        #tester_write(query)
        
        helper.log_debug("querying index - {0}".format(query))
        
        oneshotsearch_results = service.jobs.oneshot(query)
    
        reader = results.ResultsReader(oneshotsearch_results)
        
        dashboard_stats=None
        for result in reader:
            dashboard_stats = result
            
        helper.log_debug("query result - {0}".format(dashboard_stats))
        
        #tester_write(json.dumps(dashboard_stats))
        return dashboard_stats
        #return None
        
    def getdashboard_delta(server_activity, agg_activity):
        
        if agg_activity is None:
            return server_activity
            
        import copy
        result=copy.deepcopy(server_activity)
        
        
        for item in result:
            if item in agg_activity:
                result[item] = int(server_activity[item]) - int(agg_activity[item])
        return result
        
    def n2ws_get(api):
        url = vars.global_n2ws_api_url + api
        helper.log_debug("get url '{}'".format(url))

        if vars.access_key is None:
            helper.log_debug("no access key, generating.")
            generate_access_keys()
            helper.log_debug("generated access key '{}', refresh key '{}'".format(vars.access_key, vars.refresh_key))

    
        headers = {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer {}'.format(vars.access_key)
        }

        response = helper.send_http_request(url, "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

        if response.status_code != 200:
            helper.log_debug("get - failure, status code {}".format(response.status_code))

            if response.status_code == 401:
                # try and refresh our token
                helper.log_debug("refreshing token using refresh key '{}'".format(vars.refresh_key))

                refresh_result = refresh_access_key()
                if not refresh_result:
                    helper.log_debug("could not refresh token '{}', re-generating keys".format(vars.access_key))

                    vars.access_key = None
                    vars.refresh_key = None

                    generate_access_keys()

                    

                helper.log_debug('regetting, using new access key {}'.format(vars.access_key))
                headers = {
                  'Content-Type': 'application/json',
                  'Authorization': 'Bearer {}'.format(vars.access_key)
                }

                response = helper.send_http_request(url, "GET", parameters=None, payload=None, headers=headers, cookies=None, verify=False, cert=None, timeout=None, use_proxy=True)

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()



    helper.log_info("fetching dashboard info")
                     
    helper.log_debug("initializing with:\nurl '{}'.\napi key '{}'.\nvars.access_key '{}'.\nvars.refresh_key '{}'"
        .format(vars.global_n2ws_api_url,vars.global_n2ws_api_key,vars.access_key,vars.refresh_key))


    # get alerts
    
    
    cur_start = (datetime.datetime.today()-datetime.timedelta(1)) # get yesterday
    cur_end = datetime.datetime.today() # today
  
    helper.log_debug("getting data for {0}".format(cur_start))
    
    #curr_date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    #last_date = helper.get_check_point("last_date")
    #if last_date is None:
    #    last_date = vars.last_date
    #
    #if last_date is None:
    #    url = "/external_monitoring/dashboard/?end_time_lte={}".format(curr_date)
    #else:
    #    url = "/external_monitoring/dashboard/?end_time_gte={0}&end_time_lte={1}".format(last_date,curr_date)
    
    
    url = "/external_monitoring/dashboard/?start_time_gte={0}&end_time_lte={1}".format(cur_start.strftime("%Y-%m-%dT%H:%M:%S"), cur_end.strftime("%Y-%m-%dT%H:%M:%S"))

    helper.log_debug("getting dashboards using url '{}'".format(url))

    dashboards = n2ws_get(url)
    
    helper.log_info("found {} results".format(len(dashboards)))
    
    for dashboard in dashboards:
        helper.log_debug("dashboard response - {0}".format(json.dumps(dashboard)))
        helper.log_debug("getting dashboard stats for {0}".format(dashboard["username"]))
        
        dashboard_stats = get_current_dashboard_stats(dashboard["username"], cur_start.strftime("%m/%d/%Y:%H:%M:%S"), cur_end.strftime("%m/%d/%Y:%H:%M:%S"))
        
        helper.log_debug("dashboard stats - {0}".format(json.dumps(dashboard_stats)))
        
        dashboard_delta = getdashboard_delta(dashboard["dashboard_activity"], dashboard_stats)
        
        helper.log_debug("delta - {0}".format(json.dumps(dashboard_delta)))
        
        dashboard["dashboard_activity"] = dashboard_delta
        
        helper.log_debug("submitting to source {0}, index {1}, sourcetype {2} - {3}".format(helper.get_input_type(),helper.get_output_index(),helper.get_sourcetype(), json.dumps(dashboard)))
            
        
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=json.dumps(dashboard))
        ew.write_event(event)
    
    #helper.save_check_point("last_date", curr_date)
    
    helper.log_info("success.")