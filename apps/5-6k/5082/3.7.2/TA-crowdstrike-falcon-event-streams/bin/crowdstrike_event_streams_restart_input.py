import import_declare_test
import json
import os
import requests
import sys
import time
from xml.dom import minidom
import urllib


from splunktaucclib.alert_actions_base import ModularAlertBase

class AlertActionWorkercrowdstrike_event_streams_restart_input(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkercrowdstrike_event_streams_restart_input, self).__init__(ta_name, alert_name)

    def validate_params(self):

        if not self.get_param("base_url"):
            self.log_error('base_url is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("input_name"):
            self.log_error('input_name is a mandatory parameter, but its value is None.')
            return False
        return True

    def process_event(helper, *args, **kwargs):
    
    
        input_name = helper.get_param("input_name")
        helper.log_info("input={}".format(input_name))
    
        helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) + ': Alert action EVENT STREAMS RESTART INPUT started.')
    
        base_url = helper.get_param("base_url")
        helper.log_info("base_url={}".format(base_url))
      
        if base_url.startswith('https://'):
            helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Splunk HTTPS check passed')
        
        else:
            helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Splunk HTTPS check failed - Splunk requires a secure URL')
            helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Exiting alert action')
            return 1
    
        alert_action_username = helper.get_global_setting("alert_action_username")
    
        alert_action_password = helper.get_global_setting("alert_action_password")
    
        url = base_url + "/servicesNS/" + alert_action_username +"/TA-crowdstrike-falcon-event-streams/data/inputs/crowdstrike_event_streams/" + input_name
        
        payload={}
        
        helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Username: '+ alert_action_username + ' Input: ' + input_name + ' Base URL: ' + base_url )
    
    
        def crowdstrike_reset():
            data=urllib.parse.urlencode({'username':alert_action_username, 'password':alert_action_password})
            auth_url = base_url + '/services/auth/login'
    
            try:
                servercontent = requests.request('POST', auth_url, headers={}, data=data, verify=True, timeout=(30, 120))
                session_response = str(servercontent.status_code)
            
            except Exception as e:
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Unable to authenticate to Splunk API.')
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Exception: ' + str(type(e).__name__) + ': ' + str(e))
                return None
            
            if session_response.startswith('20'):
                sessionkey = minidom.parseString(servercontent.text).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue
                helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Successfully acquired Splunk authentication token.')
            else:
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Unable to acquire Splunk authentication token.')
                return None
            
            return sessionkey
            
        def disable_input(session_key):
            disable_url = url + '/disable'
            helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Sending disable request: ' + str(disable_url))

            try:
                headers={'Authorization': 'Splunk %s' % session_key}
                # Note: If Splunk uses self-signed certs, set verify to the CA bundle path
                # e.g., verify=os.path.join(os.environ.get('SPLUNK_HOME', ''), 'etc', 'auth', 'cacert.pem')
                disable_response = requests.request("POST", disable_url, headers=headers, verify=True, timeout=(30, 120))
                helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Disable request response code: ' + str(disable_response.status_code))

            except Exception as e:
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Unable to disable input.')
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Exception: ' + str(type(e).__name__) + ': ' + str(e))
                return

        def enable_input(session_key):
            headers={'Authorization': 'Splunk %s' % session_key}
            enable_url = url + '/enable'
            helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Sending enable request: ' + str(enable_url))

            try:
                enable_response = requests.request("POST", enable_url, headers=headers, verify=True, timeout=(30, 120))
                helper.log_info('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Enable request response code: ' + str(enable_response.status_code))

            except Exception as e:
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Unable to enable input.')
                helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Exception: ' + str(type(e).__name__) + ': ' + str(e))
                return
    
    
        session_key = crowdstrike_reset()
        if session_key is None:
            helper.log_error('CROWDSTRIKE EVENT STREAMS ACTION ' + str(input_name) +': Alert action aborted - authentication failed.')
            return 1
        disable_input(session_key)
        time.sleep(3)
        enable_input(session_key)
if __name__ == "__main__":
    exitcode = AlertActionWorkercrowdstrike_event_streams_restart_input("TA-crowdstrike-falcon-event-streams", "crowdstrike_event_streams_restart_input").run(sys.argv)
    sys.exit(exitcode)
