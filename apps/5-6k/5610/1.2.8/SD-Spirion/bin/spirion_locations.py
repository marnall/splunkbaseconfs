#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import requests
import splunklib.client as client
from splunklib.modularinput import *
import sys
import os

requests.packages.urllib3.disable_warnings()

class Spirion_Locations(Script):
    
    MASK           = "--------"
    APP            = __file__.split(os.sep)[-3]
    USERNAME       = None
    REALM = "SpirionEndpoints"
    endpointKind = None
    endpointName = None
    ew = None

    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Spirion Location Data API')
        scheme.description = 'Streams data from Spirion focused on the lower level Location centric view.'
        scheme.use_external_validation = True
        
        # About the secret located in inputs.conf.spec
        secret_argument = Argument('clientSecret')
        secret_argument.data_type = Argument.data_type_string
        secret_argument.description = 'OAuth2 Client Secret is required for retrieving an access token from Identity Authority.'
        secret_argument.required_on_create = True
        scheme.add_argument(secret_argument)
        
        # About the url located in inputs.conf.spec
        url_argument = Argument('url')
        url_argument.data_type = Argument.data_type_string
        url_argument.description = 'URL is necessary to access the Spirion Rest API.'
        url_argument.required_on_create = True
        scheme.add_argument(url_argument)

        # About the IA server url located in inputs.conf.spec
        iaUrl_argument = Argument('iaUrl')
        iaUrl_argument.data_type= Argument.data_type_string
        iaUrl_argument.description = 'Identity Authority URL is necessary for OAuth2 authentication.'
        iaUrl_argument.required_on_create = True
        scheme.add_argument(iaUrl_argument)

        # About the Client ID located in inputs.conf.spec
        clientId_argument = Argument('clientId')
        clientId_argument.data_type = Argument.data_type_string
        clientId_argument.description = 'OAuth2 Client ID is required for retrieving an access token from Identity Authority.'
        clientId_argument.required_on_create =  True
        scheme.add_argument(clientId_argument)

        # About the Scope located in inputs.conf.spec
        scope_argument = Argument('scope')
        scope_argument.data_type = Argument.data_type_string
        scope_argument.description = 'OAuth2 Scope is required for retrieving an access token from Identity Authority.'
        scope_argument.required_on_create = True
        scheme.add_argument(scope_argument)

        
        return scheme

    def get_key(self, key):
        # not using kind because we use realm already
        return "{0}_{1}".format(self.endpointName, key)

    def encrypt_secret(self, key, value, session_key):
        args = {'token': session_key}
        service = client.connect(**args)
        fullKey = self.get_key(key)
        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == fullKey and storage_password.realm == self.REALM:
                    service.storage_passwords.delete(username = storage_password.username, realm = self.REALM)
                    break
            service.storage_passwords.create(value, fullKey, self.REALM)

        except Exception as e:
                raise Exception("An error occurred updating secrets. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e))
    
    def get_secret(self, key, session_key):
        args = {'token':session_key}
        service = client.connect(**args)
        fullKey = self.get_key(key)
        for storage_password in service.storage_passwords:
            if storage_password.username == fullKey and storage_password.realm == self.REALM:
                return storage_password.content.clear_password

    def mask_secrets(self, session_key):
        try:
            args = {'token':session_key}
            service = client.connect(**args)                
            item = service.inputs.__getitem__((self.endpointName, self.endpointKind))
            
            kwargs = {                    
                "clientId": self.MASK,
                "clientSecret": self.MASK,
                "scope": self.MASK
            }
            item.update(**kwargs).refresh()
            
        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))
    
    

    
    def stream_events(self, inputs, ew):
        """The method called to stream events into Splunk. It should do all of its output via
        EventWriter rather than assuming that there is a console attached.
        :param ew: An object with methods to write events and log messages to Splunk.
        """
            
        self.input_name, self.input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata['session_key']
        clientSecret = self.input_items['clientSecret']
        URL = self.input_items['url']
        iaUrl = self.input_items['iaUrl']
        scope = self.input_items['scope']
        clientId = self.input_items['clientId']
        input_name=self.input_name
        endpointKind, endpointName = input_name.split("://")
        self.endpointKind = endpointKind
        self.endpointName = endpointName

        anyUpdated = False
        if clientSecret != self.MASK:
            self.encrypt_secret("clientSecret", clientSecret, session_key) 
            anyUpdated = True
        else:
            clientSecret = self.get_secret("clientSecret", session_key)
        
        if clientId != self.MASK:
            self.encrypt_secret("clientId", clientId, session_key)
            anyUpdated = True
        else:
            clientId = self.get_secret("clientId", session_key)
        if scope != self.MASK:
            self.encrypt_secret("scope", scope, session_key)
            anyUpdated = True
        else:
            scope = self.get_secret("scope", session_key)            

        if anyUpdated:
            self.mask_secrets(session_key)

        # getting the token from identity authority #
        
        ew.log('INFO', 'Getting the token from identity authority')
        url= iaUrl
        body= {
        'grant_type':"client_credentials",
        'scope':scope,
        'client_secret':clientSecret,
        'client_id':clientId,
            }
        header= {
        'Content-Type':"application/x-www-form-urlencoded",
        'Accept':"*/*",
        'Accept-Encoding':"gzip,deflate,br",
         }
        response = requests.request("POST", url, data=body, headers=header, verify= True)
        txt= response.text
        jsonify= json.loads(txt)
        token= jsonify['access_token']
        if response.status_code != 200:
            ew.log('ERROR','token not generated!')

        try:
            #if password != self.MASK:
            #    self.encrypt_password(username, password, session_key)
            #    self.mask_password(session_key, username)
        
            ew.log('INFO', 'Accessing Spirion API for location data')
           
            dir_path = os.path.dirname(os.path.realpath(__file__))
            
            timestamp = json.dumps({'timestamp':None, 'field':[], 'deletedData':False})
            timestampD = json.dumps({'timestamp':None,'field':[], 'deletedData':True})
            
            if not os.path.exists(dir_path + '/spirion_locations'):
                os.makedirs(dir_path +'/spirion_locations')
            
            if not os.path.isfile(dir_path + '/spirion_locations/'+ str(input_name[20:])):
                open(dir_path +'/spirion_locations/'+ str(input_name[20:]),'w').close()
                
            with open(dir_path + '/spirion_locations/'+ str(input_name[20:]),'r') as f:
                line = f.readline().replace('\n', '')
                if not line:
                    line = None
                timestamp = json.dumps({'timestamp':line, 'field':[],'deletedData':False})
                line = f.readline().replace('\n', '')
                if not line:
                    line = None                
                timestampD = json.dumps({'timestamp':line, 'field':[],'deletedData':True})                    

            if (URL.endswith('/')):
                URL = URL[:-1]
            
            # if (URL[0:5]=='http:'):
            #     URL = URL[:4] + 's' + URL[4:]
            
            # if (URL[0:6]!='https:'):
            #     ew.log('ERROR', 'The URL provided has improper format')
            #     return
            
            # Creating a session
            req = requests.Session()
            head = ({'accept': "text/plain",
                    'Authorization': "Bearer %s" %token,
                    'Content-Type': "application/json"})
            ew.log('INFO','Attempting to LogOn to Spirion REST API.')
            #data = json.dumps({'user':username,'password':self.get_password(session_key, username)})
            #dataset=req.post(URL+'/Services/Home/LogOn',data=data, verify=True)
            #if dataset.status_code == 200:
                #ew.log('INFO','Parsing location data for Splunk ingestion.')
                
            #Requesting Rows
            dataset = req.post(URL + '/Data/LoadLocations',data = timestamp, headers = head, verify = True)
            ew.log('INFOEndPointLineNo155', dataset.text)  
            jsonData = json.loads(dataset.text)
            while jsonData['data'] != []:
                timestamp = json.dumps({'timestamp': jsonData['newestTimestamp'], 'deletedData': False})
                for spirion_event in jsonData['data']:
                    event = Event()
                    event.stanza = input_name
                    event.source = input_name
                    event.host = URL + '/Data/LoadLocations'
                    event.data = json.dumps(spirion_event)
                    event.sourcetype = 'spirion_locations'
                    ew.write_event(event)

                dataset = req.post(URL + '/Data/LoadLocations', data = timestamp, headers = head, verify = True)
                ew.log('INFOEndPointLineNo169', dataset.text)   
                jsonData = json.loads(dataset.text)

            # Requesting Deleted Rows
            dataset = req.post(URL + '/Data/LoadLocations',data = timestampD, headers = head, verify = True)
            ew.log('INFOEndPointLineNo174', dataset.text)   
            jsonData = json.loads(dataset.text)
            while jsonData['data'] != []:
                timestampD = json.dumps({'timestamp': jsonData['newestTimestamp'], 'deletedData': True})
                for spirion_event in jsonData['data']:
                    spirion_event['removed_id'] = spirion_event['id']
                    event = Event()
                    event.stanza = input_name
                    event.source = input_name
                    event.host = URL + '/Data/LoadLocations'
                    event.data = json.dumps(spirion_event)
                    event.sourcetype = 'spirion_locations'
                    ew.write_event(event)

                dataset = req.post(URL + '/Data/LoadLocations', data = timestampD, headers = head, verify = True)
                ew.log('INFOEndPointPost', dataset.text) 
                jsonData = json.loads(dataset.text)

                # Saving Timestamps
            with open(dir_path + '/spirion_locations/'+ str(input_name[20:]), 'w') as f:
                time = json.loads(timestamp)
                timeD = json.loads(timestampD)
                f.write(time['timestamp'] + '\n')
                f.write(timeD['timestamp'])

            #dataset = req.post(URL + '/Services/Home/LogOff',verify=True)
            #ew.log('INFO', 'Successfully LogOff from Spirion REST API.')
        except Exception as e:
  
        
            """elif dataset.status_code == 401 or dataset.status_code == 403:
                ew.log('ERROR','The Spirion API username and/password is incorrect or unauthorized for API access. A status code of %s was returned.' %dataset.status_code)
            
            else:
                ew.log('ERROR','A status code of %s was returned. Splunk was unable to retrieve data from the Spirion location API.' %dataset.status_code)"""

            ew.log('ERROR','Splunk was unable to retrieve data from the Spirion API. The following error was encountered when accessing Spirion API Location to obtain data: %s' %e)

if __name__ == "__main__":
    sys.exit(Spirion_Locations().run(sys.argv))