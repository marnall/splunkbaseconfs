import import_declare_test


import gzip
import csv
import json
import sys
import json
from future.moves.urllib.parse import urlencode
from future.moves.urllib.request import urlopen, Request
from future.moves.urllib.error import HTTPError, URLError
from splunk.util import unicode

def log_event(helper, event, source, sourcetype, host, index):
    if event is None:
        helper.log_error("ERROR No event provided")
        return False
    query = [('source', source), ('sourcetype', sourcetype), ('index', index)]
    if host:
        query.append(('host', host))
    url = '%s/services/receivers/simple?%s' % (helper.settings['server_uri'], urlencode(query))
    try:
        encoded_body = unicode(event).encode('utf-8')
        req = Request(url, encoded_body, {'Authorization': 'Splunk %s' % helper.settings['session_key']})
        res = urlopen(req)
        if 200 <= res.code < 300:
            helper.log_debug("receiver endpoint responded with HTTP status=%d" % res.code)
            return True
        else:
            helper.log_error("receiver endpoint responded with HTTP status=%d" % res.code)
            return False
    except HTTPError as e:
        helper.log_error("Error sending receiver request: %s" % e)
    except URLError as e:
        helper.log_error("Error sending receiver request: %s" % e)
    except Exception as e:
        helper.log_error("Error %s" % e)
    return False

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase

class AlertActionWorkerget_paloalto_dlp_report(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkerget_paloalto_dlp_report, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("account"):
            self.log_error('account is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("report_id_field"):
            self.log_error('report_id_field is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("source"):
            self.log_error('source is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("sourcetype"):
            self.log_error('sourcetype is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("host"):
            self.log_error('host is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("index"):
            self.log_error('index is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(helper, *args, **kwargs):
        """
        # IMPORTANT
        # Do not remove the anchor macro:start and macro:end lines.
        # These lines are used to generate sample code. If they are
        # removed, the sample code will not be updated when configurations
        # are updated.
    
        [sample_code_macro:start]
    
        # The following example sends rest requests to some endpoint
        # response is a response object in python requests library
        response = helper.send_http_request("http://www.splunk.com", "GET", parameters=None,
                                            payload=None, headers=None, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
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
    
    
        # The following example gets and sets the log level
        helper.set_log_level(helper.log_level)
    
        # The following example gets account information
        user_account = helper.get_user_credential("<account_name>")
    
        # The following example gets the alert action parameters and prints them to the log
        account = helper.get_param("account")
        helper.log_info("account={}".format(account))
    
        report_id_field = helper.get_param("report_id_field")
        helper.log_info("report_id_field={}".format(report_id_field))
    
        source = helper.get_param("source")
        helper.log_info("source={}".format(source))
    
        sourcetype = helper.get_param("sourcetype")
        helper.log_info("sourcetype={}".format(sourcetype))
    
        host = helper.get_param("host")
        helper.log_info("host={}".format(host))
    
        index = helper.get_param("index")
        helper.log_info("index={}".format(index))
    
    
        # The following example adds two sample events ("hello", "world")
        # and writes them to Splunk
        # NOTE: Call helper.writeevents() only once after all events
        # have been added
        helper.addevent("hello", sourcetype="sample_sourcetype")
        helper.addevent("world", sourcetype="sample_sourcetype")
        helper.writeevents(index="summary", host="localhost", source="localhost")
    
        # The following example gets the events that trigger the alert
        events = helper.get_events()
        for event in events:
            helper.log_info("event={}".format(event))
    
        # helper.settings is a dict that includes environment configuration
        # Example usage: helper.settings["server_uri"]
        helper.log_info("server_uri={}".format(helper.settings["server_uri"]))
        [sample_code_macro:end]
        """
    
        helper.log_info("Alert action get_paloalto_dlp_report started.")
        
        # The following example gets and sets the log level
        helper.set_log_level(helper.log_level)
        
        account_name = helper.get_param("account")
        helper.log_info("account_name={}".format(account_name))
    
        # The following example gets account information
        user_account = helper.get_user_credential_by_account_id(account_name)
    
        # The following example gets account information
        #user_account = helper.get_user_credential("<account_name>")
    
        # The following example gets the setup parameters and prints them to the log
        username  = user_account.get("username")
        helper.log_debug("selected username={}".format(username))
        apiToken = user_account.get("password")
        helper.log_debug("apiToken={}".format(apiToken[-4:].rjust(len(apiToken),"*")))
        
        report_id_field = helper.get_param("report_id_field")
        helper.log_info("report_id_field={}".format(report_id_field))
    
        source = helper.get_param("source")
        helper.log_info("source={}".format(source))
    
        sourcetype = helper.get_param("sourcetype")
        helper.log_info("sourcetype={}".format(sourcetype))
    
        host = helper.get_param("host")
        helper.log_info("host={}".format(host))
    
        index = helper.get_param("index")
        helper.log_info("index={}".format(index))
        
        results_file = helper.settings["results_file"]
        
        # Get reportId from results_file above
        
        headers = {
             'Authorization': 'Basic '+apiToken,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        payload = 'grant_type=client_credentials'
        
        url = 'https://auth.apps.paloaltonetworks.com/auth/v1/oauth2/access_token'
        
        response = helper.send_http_request(url, "POST", parameters=None,
                                            payload=payload, headers=headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
                                            
        r_status = response.status_code
        if response.ok:
            helper.log_debug("response={}".format(response.json()))
            access_token = response.json()['access_token']
        # move below block under if     
        data_url = 'https://api.dlp.paloaltonetworks.com/v1/public/report/'
        query_params = "?fetchSnippet=true"
        
        data_headers = { 'Authorization': "Bearer "+access_token,
                        'Content-Type': 'application/json'
                }
    
        #The below produces orderedDict event=OrderedDict([('sourcetype', 'tapaloaltodlp:log'), ('c', '28'), ('__mv_sourcetype', ''), ('__mv_c', ''), ('rid', '21')])
        #events = helper.get_events()
        #for event in events:
        #    helper.log_info("event={}".format(event))
    
        
        
        with gzip.open(results_file, 'rt') as fh:
            for num,result in enumerate(csv.DictReader(fh)):
                report_id = result[report_id_field]
                helper.log_debug("report_id={}".format(report_id))
                
                data_url_final = data_url+report_id+query_params
                helper.log_debug("data_url_final={}".format(data_url_final))
                data_response = helper.send_http_request(data_url_final, "GET", parameters=None,
                                            payload=None, headers=data_headers, cookies=None, verify=True, cert=None, timeout=None, use_proxy=True)
                
                if data_response.ok:
                    helper.log_debug("event={}".format(data_response.json()))
                    event_final = json.dumps(data_response.json())
                    helper.log_debug("event={}".format(event_final))
                    success = log_event(
                    helper,
                    event=event_final,
                    source=source,
                    sourcetype=sourcetype,
                    host=host,
                    index=index
                    )
                    if success:
                        helper.log_info("collected report for report_id={}".format(report_id))
                    else:
                        helper.log_error("exiting")
                        sys.exit(2)
                
                
    
        return 0
if __name__ == "__main__":
    exitcode = AlertActionWorkerget_paloalto_dlp_report("TA-paloalto-dlp", "get_paloalto_dlp_report").run(sys.argv)
    sys.exit(exitcode)
