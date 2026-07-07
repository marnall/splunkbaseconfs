# encoding = utf-8
import os
import sys
import time
import datetime
import requests
import json
import urllib3

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
    # base_url = definition.parameters.get('base_url', None)
    pass


def collect_events(helper, ew):
    current_path = os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", helper.get_app_name(), "bin")
    check_file = os.path.join(current_path, "brandefense.txt")

    opt_api_key = helper.get_arg("api_key")
    opt_base_url = helper.get_arg("base_url")
    opt_initial_data_collection = helper.get_arg("initial_data_collection")
    
    if str(opt_base_url).startswith("http://"):
        # helper.log_error("Insecure Connection is not allowed. Base URL must use HTTPS Protocol for secure connections")
        opt_base_url = opt_base_url.replace("http://", "https://")
        # raise ValueError("Insecure Connection is not allowed. Base URL must use HTTPS Protocol for secure connections")
        # return
    if not ("http://" or "https://") in opt_base_url:
        opt_base_url = "https://" + opt_base_url
    if opt_base_url[-1] == "/":
        opt_base_url = opt_base_url[:-1]
    last_run_date = helper.get_check_point("last_run_date_{}".format(helper.get_input_stanza_names()))
    if not last_run_date:
        last_run_date = 0
    helper.log_debug("Last Successful Run Date: {}".format(last_run_date))

    # checking first time run, if no brandefense exist, means app will work first time
    try:
        f = open(check_file)
        f.close()
        period = "1h"
    except IOError:
        helper.log_debug("First Time Run Date: {}".format(last_run_date))

        period = opt_initial_data_collection
    finally:
        f = open(check_file, "w")
        f.close()

    IOCs = ["hash", "domain", "ip_address", "url"]
    headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {opt_api_key}"
    }
    
    for ioc_type in IOCs:
        iteration_threshold = 10
        page_number = 1
        data_set = []  # Hold raw results from each successful API Request
        try:
            # Loop through the results until last page is reached,
            # i.e. when "next" in results is None.
            # Set continue iteration = False to break
            continue_iteration = True

            while continue_iteration:  # AND count < iteration_threshold
                API_URL = "{}/api/v1/threat-intelligence/iocs".format(opt_base_url)
                parameters = {"ioc_type": ioc_type,
                              "page": page_number,
                              "period": period,
                              "limit": 100, }
                response = helper.send_http_request(API_URL, "GET", parameters=parameters,
                                                    headers=headers, cookies=None, verify=True,
                                                    timeout=None, use_proxy=True)
                response.raise_for_status()
                helper.log_debug("Request parameters: {}".format(str(parameters)))
                # get response status
                res = None
                status_code = response.status_code
                if response.status_code == 200:
                    # Get the response body
                    res = response.json()
                    if res != None:
                        if not res["results"]:
                            continue_iteration = False
                        for item in res["results"]:
                            event = helper.new_event(source=helper.get_input_type(),
                                             index=helper.get_output_index(),
                                             sourcetype=helper.get_sourcetype(),
                                             data=json.dumps(item),
                                             )
                            ew.write_event(event)
                            #data_set.append(item)

                page_number += 1
                #if page_number == 2 :
                #   continue_iteration = False

                #data_set.clear()
        except urllib3.exceptions.TimeoutError:
            helper.log_error("Insecure Connection is not allowed. Base URL must use HTTPS Protocol for secure connections")
            raise ConnectTimeoutError(
                self, 'Connection to %s timed out. (connect timeout=%s)' % (self.host, self.timeout))