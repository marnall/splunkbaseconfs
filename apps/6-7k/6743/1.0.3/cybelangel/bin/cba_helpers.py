import datetime as dt
import os
import requests as rq
import json
import splunk.entity as entity
import splunklib.client as client 
import sys


class CybelAngel():
    def __init__(self,sessionKey):
        self.client_id = None 
        self.client_secret = None
        self.token = None 
        self.token_time = None 
        self.sessionKey = sessionKey
        self.secrets = None
        self._load_secrets()        # Load Secrets 
        self._load_token_time()     # Load the token time from JSON file
        self.get_cba_credentials()  # Load CBA client ID & Client Secret from storage/passwords 
        self.get_cba_token()        # Get Authorization Token from CBA 


    def _load_secrets(self):
        service = client.connect(host="localhost", app="cybelangel", owner="nobody", token=self.sessionKey, autologin=True)
        self.secrets = service.storage_passwords

    def _load_token_time(self):
        token_file_name = os.path.join(os.environ["SPLUNK_HOME"],'etc','apps','cybelangel','default','data','cba','token_store.json')
        with open(token_file_name, 'r') as f:
            data = json.load(f)
            self.token_time = data["date"]

    def _update_token_time(self):
        token_file_name = os.path.join(os.environ["SPLUNK_HOME"],'etc','apps','cybelangel','default','data','cba','token_store.json')
        self.token_time = str(dt.datetime.utcnow())
        with open(token_file_name,'w') as f:
            data = {
                "date": self.token_time
            }
            f.write(json.dumps(data))

    def get_cba_credentials(self):
        """ Retrieve CBA API credentials from Splunk storage/passwords """
        try:
            for secret in self.secrets:
                secret_content = secret.content
                if secret_content['realm'] == "cybelangel":
                    self.client_id = secret_content['username']
                    self.client_secret = secret_content['clear_password'] 
        except Exception as e:
            raise Exception("Could not get %s credentials from splunk. Error: %s" % ("cybelangel", str(e)))


    def _get_token(self):
        """ Retrieve CBA API credentials from Splunk storage/passwords """
        try:
            for secret in self.secrets:
                secret_content = secret.content
                if secret_content['realm'] == "cba_api_key":
                    self.token = secret_content['clear_password']
        except Exception as e:
            raise Exception("Could not get %s credentials from splunk. Error: %s" % ("cybelangel", str(e)))


    def _update_token(self):
        """ Update the CybelAngel API token in storage/passwords """ 
        try:
            for secret in self.secrets:
                secret_content = secret.content
                if secret_content['realm'] == "cba_api_key":        #Check if the API key exists
                    self.secrets.delete(username="api_key", realm="cba_api_key")
            self.secrets.create(username="api_key",password=self.token, realm="cba_api_key")
            # Load token date 
            self._update_token_time()
        except Exception as e:
            raise Exception("Could not update %s credentials from splunk. Error: %s" % ("cybelangel", str(e)))

    def check_token(self):
        """ Check the time the token was acquired to see if another needs to be requested """
        
        if self.token_time == None:                           #Initial Value needs to be null value on installation
            return True
        timeDiff = (dt.datetime.utcnow(
        ) - dt.datetime.strptime(self.token_time, "%Y-%m-%d %H:%M:%S.%f")).total_seconds()
        if timeDiff >= 3600:
            return True 
        else:
            return False 

    def get_cba_token(self):
        """ Retreive a new token using provided credentials """
        if self.check_token() == True:
            headers = {'content-type': 'application/json'}

            payload = {'client_id': self.client_id,'client_secret': self.client_secret,'audience': "https://platform.cybelangel.com/",'grant_type': "client_credentials"}
            try:
                token = rq.post('https://auth.cybelangel.com/oauth/token', params=headers, data=payload)
                self.token = json.loads(token.text)["access_token"]
                self._update_token()
                self._update_token_time()
            except rq.exceptions.HTTPError as error:
                raise SystemExit(error)
        else:
            self._get_token()

    def request_cba_reports(self):
        """ Retrieve CBA Reports """
        url = "https://platform.cybelangel.com/api/v2/reports"
        headers = {'Content-Type': "application/json",'Authorization': "Bearer " + self.token}
        reqParams = {
            'end-date': dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M"),
            'start-date':"2000-01-02T01:01:01"}      
        try:
            response = rq.request("GET", url, headers=headers, params=reqParams)
            return json.loads(response.text)
        except rq.exceptions.HTTPError as error:
            raise SystemExit(error)

    def request_cba_domains(self):
        """ Retrieve CBA Domains watchlist """
        url = "https://platform.cybelangel.com/api/v1/domains"
        headers = {'Content-Type': "application/json",'Authorization': "Bearer " + self.token}  
        try:
            response = rq.request("GET", url, headers=headers)
            return json.loads(response.text)
        except rq.exceptions.HTTPError as error:
            raise SystemExit(error)

    def request_cba_credentials(self):
        """ Retrieve CBA Credentials watchlist """
        url = "https://platform.cybelangel.com/api/v1/credentials"
        headers = {'Content-Type': "application/json",'Authorization': "Bearer " + self.token}

        reqParams = {
            "sort_by":"last_detection_date"
            }      
        try:
            response = rq.request("GET", url, headers=headers, params=reqParams)
            return json.loads(response.text)
        except rq.exceptions.HTTPError as error:
            raise SystemExit(error)










