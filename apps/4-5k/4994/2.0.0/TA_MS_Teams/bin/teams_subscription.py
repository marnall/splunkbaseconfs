
import os
import sys
import time
import datetime
import json

import import_declare_test

from splunklib import modularinput as smi




bin_dir = os.path.basename(__file__)

'''
'''
import import_declare_test

import os
import os.path as op
import sys
import time
import datetime
import json

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
import requests
import ta_azure_utils.auth as azauth
import ta_azure_utils.utils as azutils

# encoding = utf-8


def create_subscription(helper, access_token, webhook_url, graph_base_url):
    url = graph_base_url + "/subscriptions"
    headers = {}
    headers["Authorization"] = "Bearer %s" % access_token
    headers["Content-type"] = "application/json"
    proxies = azutils.get_proxy(helper, "requests")
    
    now = datetime.datetime.utcnow()
    expiration_date = now + datetime.timedelta(days=2)

    try:
        data = {
           "changeType": "created, updated",
           "notificationUrl": webhook_url,
           "resource": "/communications/callRecords",
           "expirationDateTime": expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
       
        r = requests.post(url, headers=headers, json=data, proxies=proxies)
        r.raise_for_status()
        response_json = None
        response_json = json.loads(r.content)
        subscription = response_json
        
    except Exception as e:
        raise e

    return subscription
    
def update_subscription(helper, access_token, subscription_id, graph_base_url):
    url = graph_base_url + "/subscriptions/%s" % subscription_id
    headers = {}
    headers["Authorization"] = "Bearer %s" % access_token
    headers["Content-type"] = "application/json"
    proxies = azutils.get_proxy(helper, "requests")
    
    now = datetime.datetime.utcnow()
    expiration_date = now + datetime.timedelta(days=2)

    try:
        data = {"expirationDateTime": expiration_date.strftime("%Y-%m-%dT%H:%M:%SZ")}
       
        r = requests.patch(url, headers=headers, json=data, proxies=proxies)
        r.raise_for_status()
        response_json = None
        response_json = json.loads(r.content)
        subscription = response_json
        
    except Exception as e:
        raise e

    return subscription

class ModInputteams_subscription(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputteams_subscription, self).__init__("ta_ms_teams", "teams_subscription", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputteams_subscription, self).get_scheme()
        scheme.title = ("Teams Subscription (Deprecated)")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("global_account", title="Global Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("tenant_id", title="Tenant ID",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("environment", title="Environment",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("webhook_url", title="Webhook URL",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("endpoint", title="Endpoint",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_MS_Teams"

    def validate_input(helper, definition):
        # TODO: Validate Webhook URL is HTTPS
        pass
    

    def collect_events(helper, ew):
        global_account = helper.get_arg("global_account")
        client_id = global_account["username"]
        client_secret = global_account["password"]
        tenant_id = helper.get_arg("tenant_id")
        webhook_url = helper.get_arg("webhook_url")
        expiration = helper.get_arg("expiration")
        subscription_id = helper.get_arg("subscription_id")
        endpoint = helper.get_arg("endpoint")
        check_point_key = "m365_subscription_%s" % helper.get_input_stanza_names()
        
        environment = helper.get_arg("environment")
        if(environment == "gov"):
            graph_base_url = "https://graph.microsoft.us/%s" % endpoint
        else:
            graph_base_url = "https://graph.microsoft.com/%s" % endpoint
        
        try:
            access_token = azauth.get_graph_access_token(client_id, client_secret, tenant_id, environment, helper)
            
        except Exception as e:
            helper.log_error("Could not get access token: %s" % str(e))
            return
        
        check_point_data = helper.get_check_point(check_point_key)
        
        if check_point_data in [None,'']:
            
            # Create the subscription
            try:
                subscription = create_subscription(helper, access_token, webhook_url, graph_base_url)
                
                event = helper.new_event(
                        data=json.dumps(subscription),
                        time="%.3f" % time.time(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype())
                ew.write_event(event)
                
                helper.save_check_point(check_point_key, json.dumps(subscription))
                helper.log_debug("Successfully created subscription: %s" % json.dumps(subscription))
                
            except Exception as e:
                helper.log_error("Could not create subscription: %s" % str(e))
                raise e
            
        else:
            # This is an existing subscription, so update it.
            subscription_check_point_json = json.loads(check_point_data)
            subscription_expiration = subscription_check_point_json["expirationDateTime"]
            subscription_id = subscription_check_point_json["id"]
            
            try:
                exp = datetime.datetime.strptime(subscription_expiration, '%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                exp = datetime.datetime.strptime(subscription_expiration, '%Y-%m-%dT%H:%M:%S.%fZ')
            except Exception as e:
                helper.log_error("Could not convert check point expiration date (%s): %s" % (subscription_expiration, str(e)))
            
            # If this subscription is going to expire in less than a day, update it. 
            if exp < datetime.datetime.utcnow()+datetime.timedelta(days=2):
                # Update the subscription
                try:
                    subscription = update_subscription(helper, access_token, subscription_id, graph_base_url)
            
                    event = helper.new_event(
                        data=json.dumps(subscription),
                        time="%.3f" % time.time(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype())
                    ew.write_event(event)
                    
                    helper.save_check_point(check_point_key, json.dumps(subscription))
                    helper.log_debug("Successfully updated subscription: %s" % json.dumps(subscription))
                    
                except Exception as e:
                    helper.log_error("Could not update subscription: %s" % str(e))
                    raise e

    def get_account_fields(self):
        account_fields = []
        account_fields.append("global_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode = ModInputteams_subscription().run(sys.argv)
    sys.exit(exitcode)
