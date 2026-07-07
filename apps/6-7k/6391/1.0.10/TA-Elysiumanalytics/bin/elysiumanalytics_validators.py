import ta_elysiumanalytics_declare  # noqa: F401
import requests
import elysiumanalytics_const as const
import elysiumanalytics_common_utils as utils
from log_manager import setup_logging
import json
from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from urllib.parse import quote
from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
import base64



_LOGGER = setup_logging("elysiumanalytics_validator")


class SessionKeyProvider(ConfigMigrationHandler):
   
    def __init__(self):
       
        self.session_key = self.getSessionKey()


class ValidateElysiumanalyticsInstance(Validator):
    def validate(self, value, data):
        
        splunk_session_key = SessionKeyProvider().session_key
         # Set parameters
        snowflake_instance = data.get("snowflake_instance").strip("/")
      
        snowflake_instance = snowflake_instance+'.snowflakecomputing.com'
       
        snowflake_refresh_token = data.get("snowflake_refresh_token")
        client_id = data.get("client_id")
        client_secret = data.get("client_secret")
        
        encodedData = base64.b64encode(bytes(f"{client_id}:{client_secret}", "ISO-8859-1")).decode("ascii")
        authorize_url = "https://"+snowflake_instance+"/oauth/token-request"
    
        authorize_data = { 
                    "grant_type": "refresh_token", 
                    "refresh_token" : snowflake_refresh_token
                    }
       

        authorize_headers = {'Content-Type': 'application/x-www-form-urlencoded','Accept-Charset':'utf-8','Authorization': 'Basic '+encodedData}
       
       
        try:
            resp = requests.post(authorize_url, headers=authorize_headers,data=authorize_data)
            
            resp.raise_for_status()
            _ = resp.json()
            
            self.put_msg("configuratons validated suceesfully")
            return True
        except Exception as e:
            if resp.status_code == 403:
                msg = "Cannot verify Data lake Instance"
            else:
                
                json_resp = resp.json()
                if "resp" in locals() and resp.status_code == 400 and json_resp['error'] == "invalid_client":
                    msg = " Invalid Client/Secret Credentials. Please enter the valid Credentials."
                elif  "resp" in locals() and resp.status_code == 400 and  json_resp['error'] == 'invalid_grant':
                    msg = "The provided grant or refresh token is invalid."
                else:
                    msg = "Please check the security credentials that you have entered"

            _LOGGER.error(str(e))
            _LOGGER.error(msg)
            self.put_msg(msg)
            return False
