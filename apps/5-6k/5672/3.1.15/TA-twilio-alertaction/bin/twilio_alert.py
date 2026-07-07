# encoding = utf-8
# Always put this line at the beginning of this file
import import_declare_test
import requests

import os
import sys

from splunktaucclib.alert_actions_base import ModularAlertBase
from ta_twilio_alertaction import modalert_twilio_alert_helper
from solnlib import conf_manager

class AlertActionWorkertwilio_alert(ModularAlertBase):

    def __init__(self, ta_name, alert_name):
        super(AlertActionWorkertwilio_alert, self).__init__(ta_name, alert_name)

    def validate_params(self):
        # to1=self.get_param("To")

        # from1=self.get_param("From")
        session_key=self.session_key

        if not self.get_param("To"):
            self.log_error('To is a mandatory parameter, but its value is None.')
            return False
        if not self.session_key:
            self.log_error('session is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("From"):
            self.log_error('From is a mandatory parameter, but its value is None.')
            return False

        if not self.get_param("Message"):
            self.log_error('Message is a mandatory parameter, but its value is None.')
            return False
        # self.log_error(to1)
        # self.log_error(from1)
        self.log_error(f'Session Key: {self.session_key}')

        return True
    
    # def get_twilio_credentials(self):
    #     self.log_error("start")

    #     session_key=self.session_key
    #     # Fetch account SID and auth token from the configuration file using solnlib's conf_manager
        
    #     # Access the configuration file through the conf_manager
    #     cfm2 = conf_manager.ConfManager(session_key, 'TA-twilio-alertaction', realm=f"__REST_CREDENTIAL__#TA-twilio-alertaction#configs/conf-ta_twilio_alertaction_settings")
    #     account_conf_file2 = cfm2.get_conf('ta_twilio_alertaction_settings')
 

    #     if not account_conf_file2 :
    #         self.log_error("account_conf_file2 not found in configuration.")
    #     else:
    #         self.log_error("account_conf_file2 found in configuration.")


    #     # Check if a stanza exists
    #     # stanza_exists = conf_mgr.stanza_exist('twil')
    #     # self.log_error(f"Stanza exists: {stanza_exists}")

    #         # Get a stanza
    #     # try:
    #     #     stanza = conf_mgr.get_conf('ta_twilio_alertaction_account').get('twil')
    #     #     self.log_error(f"Stanza content: {stanza}")
    #     # except conf_manager.ConfStanzaNotExistException as e:
    #     #     self.log_error(f"Error: {e}")
                    
    #         # Read the configuration values from the stanz section
    #         # account_sid = conf.get("ta_twillio_alertaction_account", "twil", "account_sid")
    #         # auth_token = conf.get("ta_twillio_alertaction", "twil", "token")

    #     #     if not account_sid or not auth_token:
    #     #         self.log_error("Account SID or Auth Token not found in configuration.")
    #     #         return None, None

    #     #     return account_sid, auth_token
    #     # except Exception as e:
    #     #     self.log_error(f"Error retrieving Twilio credentials: {str(e)}")
    #     #     return None, None


    def process_event(self, *args, **kwargs):
        status = 0
        try:
            if not self.validate_params():
                return 3
            # result = kwargs.get("result", {})
            # if "ID" not in result:
            #     raise InvalidResultID("Result must have an ID")
             # Get parameters
            # to = self.get_param("To")
            # from_ = self.get_param("From")
            # message = self.get_param("Message")
            # session_key=self.session_key
            # self.log_error(to)
            # self.log_error(from_)
            # self.log_error(message)

            # account_sid, auth_token = self.get_twilio_credentials()
            
            # if not account_sid or not auth_token:
            #     return 5  # Failed to retrieve credentials

            # # Your Twilio API URL (Replace with the actual endpoint you want to use)
            # url = "https://api.twilio.com/2010-04-01/Accounts/AC9f22404a422fb4d47f03c6bd625e1d1c/Messages.json"

            # # Your Twilio credentials
            # account_sid = "account_sid"
            # auth_token = "auth_token"

            # # Prepare data for the POST request
            # data = {
            #     "To": to,
            #     "From": from_,
            #     "Body": message
            # }

            # # Send POST request to Twilio API
            # response = requests.post(url, data=data, auth=(account_sid, auth_token))
            # self.log_error(f'resp={response}')
            # x=response.status_code
            # self.log_error(f'code={x}')


            # # Check response
            # if response.status_code == 201:  # Successful request
            #     self.log_info("Message sent successfully.")
            # else:
            #     self.log_error("Failed to send message. Status code: {}".format(response.status_code))
            #     return 5

            status = modalert_twilio_alert_helper.process_event(self, *args, **kwargs)
        except (AttributeError, TypeError) as ae:
            self.log_error("Error: {}. Please double check spelling and also verify that a compatible version of Splunk_SA_CIM is installed.".format(str(ae)))#ae.message replaced with str(ae)
            return 4
        except Exception as e:
            msg = "Unexpected error: {}."
            if str(e):
                self.log_error(msg.format(str(e)))#e.message replaced with str(ae)
            else:
                import traceback
                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status

if __name__ == "__main__":
    exitcode = AlertActionWorkertwilio_alert("TA-twilio-alertaction", "twilio_alert").run(sys.argv)
    sys.exit(exitcode)