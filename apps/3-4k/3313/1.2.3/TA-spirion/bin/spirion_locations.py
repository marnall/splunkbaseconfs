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

    def get_scheme(self):
        """ Defining a scheme in plaintext which will provide Splunkd data about the modular input."""
        # About the Modular Input
        scheme = Scheme('Spirion Location Data API')
        scheme.description = 'Streams data from Spirion focused on the lower level Location centric view.'
        scheme.use_external_validation = True
        
        # About the user located in inputs.conf.spec
        username_argument = Argument('username')
        username_argument.data_type = Argument.data_type_string
        username_argument.description = 'Username is necessary to authenticate with the Spirion Rest API.'
        username_argument.required_on_create = True
        scheme.add_argument(username_argument)
        
        # About the password located in inputs.conf.spec
        password_argument = Argument('password')
        password_argument.data_type = Argument.data_type_string
        password_argument.description = 'Password is necessary to authenticate with the Spirion Rest API.'
        password_argument.required_on_create = True
        scheme.add_argument(password_argument)
        
        # About the url located in inputs.conf.spec
        url_argument = Argument('url')
        url_argument.data_type = Argument.data_type_string
        url_argument.description = 'URL is necessary to access the Spirion Rest API.'
        url_argument.required_on_create = True
        scheme.add_argument(url_argument)
        
        return scheme
    
    def encrypt_password(self, username, password, session_key):
        args = {'token':session_key}
        service = client.connect(**args)
        
        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
                    break

            service.storage_passwords.create(password, username)

        except Exception as e:
            raise Exception, "An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: %s" % str(e)

    def mask_password(self, session_key, username):
        try:
            args = {'token':session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))
            
            kwargs = {
                "username": username,
                "password": self.MASK
            }
            item.update(**kwargs).refresh()
            
        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, username):
        args = {'token':session_key}
        service = client.connect(**args)
  
        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password

    def stream_events(self, inputs, ew):
        """The method called to stream events into Splunk. It should do all of its output via
        EventWriter rather than assuming that there is a console attached.
        :param ew: An object with methods to write events and log messages to Splunk.
        """
            
        self.input_name, self.input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata['session_key']
        username = self.input_items['username']
        password   = self.input_items['password']
        URL = self.input_items['url']
        self.USERNAME = username
        input_name=self.input_name

        try:
            if password != self.MASK:
                self.encrypt_password(username, password, session_key)
                self.mask_password(session_key, username)
        
            ew.log('INFO', 'Accessing Spirion API for location data')
           
            dir_path = os.path.dirname(os.path.realpath(__file__))
            
            timestamp = json.dumps({'timestamp':'','deletedData':False})
            timestampD = json.dumps({'timestamp':'','deletedData':True})
            
            if not os.path.exists(dir_path+'/spirion_locations'):
                os.makedirs(dir_path+'/spirion_locations')
            
            if not os.path.isfile(dir_path+'/spirion_locations/'+str(input_name[20:])):
                open(dir_path+'/spirion_locations/'+str(input_name[20:]),'w').close()
                
            with open(dir_path+'/spirion_locations/'+str(input_name[20:]),'r') as f:
                timestamp = json.dumps({'timestamp':f.readline().replace('\n', ''),'deletedData':False})                
                timestampD = json.dumps({'timestamp':f.readline().replace('\n', ''),'deletedData':True})                    

            if (URL.endswith('/')):
                URL = URL[:-1]
            
            # if (URL[0:5]=='http:'):
            #     URL = URL[:4] + 's' + URL[4:]
            
            # if (URL[0:6]!='https:'):
            #     ew.log('ERROR', 'The URL provided has improper format')
            #     return
            
            # Creating a session
            req = requests.Session()
            req.headers.update({'Content-Type': 'application/json; charset=utf-8', 'Accept': 'application/json, text/plain, */*; charset=utf-8', 'Accept-Encoding': 'gzip, deflate'})
            ew.log('INFO','Attempting to LogOn to Spirion REST API.')
            data = json.dumps({'user':username,'password':self.get_password(session_key, username)})
            dataset=req.post(URL+'/Services/Home/LogOn',data=data, verify=True)
            if dataset.status_code == 200:
                ew.log('INFO','Parsing location data for Splunk ingestion.')
                
                #Requesting Rows
                dataset=req.post(URL+'/Services/Data/LoadLocations',data=timestamp,verify=True)
                jsonData = json.loads(dataset.content[5:])
                while (jsonData['data']!=[]):
                    timestamp=json.dumps({'timestamp':jsonData['newestTimestamp'],'deletedData':False})
                    for spirion_event in jsonData['data']:
                        event = Event()
                        event.stanza = input_name
                        event.source = input_name
                        event.host = URL + '/Services/Data/LoadLocations'
                        event.data = json.dumps(spirion_event)
                        event.sourcetype = 'spirion_locations'
                        ew.write_event(event)
                        
                    dataset=req.post(URL+'/Services/Data/LoadLocations',data=timestamp,verify=True)
                    jsonData = json.loads(dataset.content[5:])
                
                #Requesting Deleted Rows    
                dataset=req.post(URL+'/Services/Data/LoadLocations',data=timestampD,verify=True)
                jsonData = json.loads(dataset.content[5:])
                while (jsonData['data']!=[]):
                    timestampD=json.dumps({'timestamp':jsonData['newestTimestamp'],'deletedData':True})
                    for spirion_event in jsonData['data']:
                        spirion_event['removed_id']=spirion_event['id']
                        
                        event = Event()
                        event.stanza = input_name
                        event.source = input_name
                        event.host = URL + '/Services/Data/LoadLocations'
                        event.data = json.dumps(spirion_event)
                        event.sourcetype = 'spirion_locations'
                        ew.write_event(event)
                        
                    dataset=req.post(URL+'/Services/Data/LoadLocations',data=timestampD,verify=True)
                    jsonData = json.loads(dataset.content[5:])
                
                #Saving Timestamps
                with open(dir_path+'/spirion_locations/'+str(input_name[20:]),'w') as f:
                    time = json.loads(timestamp)
                    timeD = json.loads(timestampD)
                    f.write(time['timestamp']+'\n')
                    f.write(timeD['timestamp'])
                    
                dataset=req.post(URL+'/Services/Home/LogOff', verify=True)
                ew.log('INFO','Successfully LogOff from Spirion REST API.')     
        
            elif dataset.status_code == 401 or dataset.status_code == 403:
                ew.log('ERROR','The Spirion API username and/password is incorrect or unauthorized for API access. A status code of %s was returned.' %dataset.status_code)
            
            else:
                ew.log('ERROR','A status code of %s was returned. Splunk was unable to retrieve data from the Spirion location API.' %dataset.status_code)

        except Exception as e:
            ew.log('ERROR','Splunk was unable to retrieve data from the Spirion API. The following error was encountered when accessing Spirion API Location to obtain data: %s' %e)

if __name__ == "__main__":
    sys.exit(Spirion_Locations().run(sys.argv))