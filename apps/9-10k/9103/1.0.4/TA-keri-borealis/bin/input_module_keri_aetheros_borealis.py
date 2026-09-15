
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import urllib.parse

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

class BorealisClient:
    def __init__(self, helper, ew, base_url: str, client_id: str, client_secret: str, tenant_name: str, site_name: str, last_timestamp: str = None):
        self.helper = helper
        self.ew = ew
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_name = tenant_name
        self.site_name = site_name
        self.last_timestamp = last_timestamp
        #self.session = requests.Session()

        self.auth_token = None
        self.tenant_key = None
        self.site_id = None

    def connect_token(self) -> str:
        """POST /connect/token -- client_credentials grant, no auth."""
        url = f"{self.base_url}/connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "client_secret": self.client_secret,
            "client_id": self.client_id,
            "grant_type": "client_credentials",
        }
        self.helper.log_debug("Obtaining access token...")
        #resp = self.session.post(url, headers=headers, data=data)
        resp = self.helper.send_http_request(url, method="POST", parameters=None, 
            payload=urllib.parse.urlencode(data), headers=headers, cookies=None, 
            verify=True, cert=None, timeout=None, use_proxy=True)
        if not resp.ok:
            self.helper.log_error(resp.text)
            #self.helper.log_error("Request.body=" + str(resp.request.body))
            #self.helper.log_error("Request.headers=" + str(resp.request.headers))
        resp.raise_for_status()
        self.auth_token = resp.json()["access_token"]
        self.helper.log_debug("Access token = " + self.auth_token)
        return self.auth_token

    def get_tenant_key(self) -> str:
        """GET /api/master/tenants/my/list -- bearer auth."""
        url = f"{self.base_url}/api/master/tenants/my/list"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
        }
        self.helper.log_debug("Retrieving Tenant Key...")
        resp = self.helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
        resp.raise_for_status()
        # Loop through returned tenants, looking for a match
        for tenant in resp.json()["items"]:
            if tenant["displayName"] == self.tenant_name:
                self.tenant_key = tenant["key"]
                self.helper.log_debug("Tenant Key = " + self.tenant_key)
        return self.tenant_key # None if not found!

    def get_site_id(self) -> str:
        """GET /api/sites/list -- bearer auth + TenantKey header."""
        url = f"{self.base_url}/api/sites/list"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "TenantKey": self.tenant_key,
        }
        self.helper.log_debug("Getting Site ID...")
        resp = self.helper.send_http_request(url, method="GET", parameters=None, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
        resp.raise_for_status()
        # Loop through sites, looking for a match
        for site in resp.json()["items"]:
            if site["displayName"] == self.site_name:
                self.site_id = site["id"]
                self.helper.log_debug("Site ID = " + self.site_id)
        return self.site_id

    def get_live_events(self, page_size: int = 1000) -> dict:
        """GET /api/live-events?siteId=...&pageSize=... -- bearer auth + TenantKey header."""
        url = f"{self.base_url}/api/live-events"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "TenantKey": self.tenant_key,
        }
        params = {"siteId": self.site_id, "pageSize": page_size}
        self.helper.log_debug("Getting live events....")
        resp = self.helper.send_http_request(url, method="GET", parameters=params, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
        resp.raise_for_status()
        return resp.json()

    def get_reports_live_events(self, page_size: int = 1000, timeout: int = 30) -> dict:
        """GET /api/reports/live-events?siteId=...&pageSize=... -- bearer auth + TenantKey header."""
        url = f"{self.base_url}/api/reports/live-events"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
            "TenantKey": self.tenant_key,
        }
        params = {
            "siteId": self.site_id, 
            "pageSize": page_size,
            "page": 1,
            "timeStamp_CloudServerFrom": self.last_timestamp, 
            "timeStamp_CloudServerTo": ((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=5)).isoformat() if self.last_timestamp else None), # If last_timestamp is None, don't pass CloudServerTo, either
            "sortBy": "timeStamp_CloudServer",
            "sortOrder": 0
            }
        # print(params)
        count = 0
        self.helper.log_info("Retrieving live events between " + (params["timeStamp_CloudServerFrom"] or "None") + " and " + (params["timeStamp_CloudServerTo"] or "None") + " ...")
        while True:
            resp = self.helper.send_http_request(url, method="GET", parameters=params, payload=None,
                                        headers=headers, cookies=None, verify=True, cert=None,
                                        timeout=timeout, use_proxy=True)
            resp.raise_for_status()
            j = resp.json()
            # print(j)
            # Print out each event as a separate line
            for item in j["items"]:
                #print(json.dumps(item))
                event = self.helper.new_event(json.dumps(item), time=item["timeStamp_GMT"], host=None, index=self.helper.get_output_index(), source=self.helper.get_input_type(), sourcetype=self.helper.get_sourcetype(), done=True, unbroken=True)
                self.ew.write_event(event)
                self.last_timestamp = item["timeStamp_CloudServer"] # Update last_timestamp to the latest event
                self.helper.save_check_point("last_timestamp", self.last_timestamp) # Set checkpoint
                count += 1
            self.helper.log_debug(f"Retrieved {count} events.")
            if j["page"] >= j["pageCount"]: # pageCount will return 0 if no items, so we need to allow for that
                break
            params["page"] += 1 # Set up to get next page

        return count

    def run_full_flow(self, page_size: int = 1000, timeout: int = 30) -> int:
        """Runs the full chain: token -> tenant key -> site id -> live events."""
        self.connect_token()
        self.get_tenant_key()
        self.get_site_id()
        #return self.get_live_events(page_size=page_size)
        return self.get_reports_live_events(page_size=page_size, timeout=timeout)




def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # base_url = definition.parameters.get('base_url', None)
    # credentials = definition.parameters.get('credentials', None)
    # page_size = definition.parameters.get('page_size', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_base_url = helper.get_arg('base_url')
    opt_credentials = helper.get_arg('credentials')
    opt_page_size = helper.get_arg('page_size')
    # In single instance mode, to get arguments of a particular input, use
    opt_base_url = helper.get_arg('base_url', stanza_name)
    opt_credentials = helper.get_arg('credentials', stanza_name)
    opt_page_size = helper.get_arg('page_size', stanza_name)

    # get input type
    helper.get_input_type()

    # The following examples get input stanzas.
    # get all detailed input stanzas
    helper.get_input_stanza()
    # get specific input stanza with stanza name
    helper.get_input_stanza(stanza_name)
    # get all stanza names
    helper.get_input_stanza_names()

    # The following examples get options from setup page configuration.
    # get the loglevel from the setup page
    loglevel = helper.get_log_level()
    # get proxy setting configuration
    proxy_settings = helper.get_proxy()
    # get account credentials as dictionary
    account = helper.get_user_credential_by_username("username")
    account = helper.get_user_credential_by_id("account id")
    # get global variable configuration
    global_userdefined_global_var = helper.get_global_setting("userdefined_global_var")

    # The following examples show usage of logging related helper functions.
    # write to the log for this modular input using configured global log level or INFO as default
    helper.log("log message")
    # write to the log using specified log level
    helper.log_debug("log message")
    helper.log_info("log message")
    helper.log_warning("log message")
    helper.log_error("log message")
    helper.log_critical("log message")
    # set the log level for this modular input
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(log_level)

    # The following examples send rest requests to some endpoint.
    response = helper.send_http_request(url, method, parameters=None, payload=None,
                                        headers=None, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)
    # get the response headers
    r_headers = response.headers
    # get the response body as text
    r_text = response.text
    # get response body as json. If the body text is not a json string, raise a ValueError
    r_json = response.json()
    # get response cookies
    r_cookies = response.cookies
    # get redirect history
    historical_responses = response.history
    # get response status code
    r_status = response.status_code
    # check the response status, if the status is not sucessful, raise requests.HTTPError
    response.raise_for_status()

    # The following examples show usage of check pointing related helper functions.
    # save checkpoint
    helper.save_check_point(key, state)
    # delete checkpoint
    helper.delete_check_point(key)
    # get checkpoint
    state = helper.get_check_point(key)

    # To create a splunk event
    helper.new_event(data, time=None, host=None, index=None, source=None, sourcetype=None, done=True, unbroken=True)
    """

    '''
    # The following example writes a random number as an event. (Multi Instance Mode)
    # Use this code template by default.
    import random
    data = str(random.randint(0,100))
    event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)
    ew.write_event(event)
    '''

    '''
    # The following example writes a random number as an event for each input config. (Single Instance Mode)
    # For advanced users, if you want to create single instance mod input, please use this code template.
    # Also, you need to uncomment use_single_instance_mode() above.
    import random
    input_type = helper.get_input_type()
    for stanza_name in helper.get_input_stanza_names():
        data = str(random.randint(0,100))
        event = helper.new_event(source=input_type, index=helper.get_output_index(stanza_name), sourcetype=helper.get_sourcetype(stanza_name), data=data)
        ew.write_event(event)
    '''
    
    #helper.set_log_level('debug')
    # To reset checkpoint: curl -k -u <username>:<password> -X DELETE https://<host>:8089/servicesNS/nobody/TA-keri-borealis/storage/collections/data/TA_keri_borealis_checkpointer
    
    opt_base_url = helper.get_arg('base_url')
    opt_credentials = helper.get_arg('credentials')
    opt_tenant_name = helper.get_arg('tenant_name')
    opt_site_name = helper.get_arg('site_name')
    opt_page_size = helper.get_arg('page_size')
    opt_timeout = int(helper.get_arg('timeout'))
    opt_start = helper.get_arg('timestamp_start')
    last_timestamp = helper.get_check_point('last_timestamp') or opt_start # use checkpoint if exists
    
    client = BorealisClient(helper, ew, opt_base_url, opt_credentials["username"], opt_credentials["password"], opt_tenant_name, opt_site_name, last_timestamp)
    count = client.run_full_flow(page_size=opt_page_size, timeout=opt_timeout)
    helper.log_info(f"Retrieved {count} events.")
    
