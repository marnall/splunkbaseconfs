from requests.auth import AuthBase
import hmac
import base64
import hashlib
import requests,json
from datetime import datetime

try:
    from urllib.parse import urlparse, urlencode
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urlparse import urlparse
    from urllib import urlencode
    from urllib2 import urlopen, Request, HTTPError


#add your custom auth handler class to this module

class MyEncryptedCredentialsAuthHAndler(AuthBase):
    def __init__(self,**args):
        # setup any auth-related data here
        #self.username = args['username']
        #self.password = args['password']
        pass
        
    def __call__(self, r):
        # modify and return the request
        #r.headers['foouser'] = self.username
        #r.headers['foopass'] = self.password
        return r
  
  
#template
class MyCustomAuth(AuthBase):
    def __init__(self,**args):
        # setup any auth-related data here
        #self.username = args['username']
        #self.password = args['password']
        pass
        
    def __call__(self, r):
        # modify and return the request
        #r.headers['foouser'] = self.username
        #r.headers['foopass'] = self.password
        return r

'''
Example custom handler to authenticate to Genesys Cloud using Client Credentials
https://developer.genesys.cloud/authorization/platform-auth/use-client-credentials

Basic algorithm is :

1) obtain a new access token or refresh an expired access token
2) intercept the outgoing API request (the r object) add this access token as a header
'''
class ExampleGenesysOAuthHandler(AuthBase):

    def __init__(self,**args):

        # set parameters from your REST data inputs configuration for this custom handler
        self.client_id = args['client_id']
        self.client_secret = args['client_secret']
        self.oauth_token_url = args['oauth_token_url']

        # initial default Oauth settings, these will reset each time the REST input is restarted
        self.access_token = None
        self.expires_in = -1
        self.last_refresh_time = datetime.now()

        pass
        
    def __call__(self, r):

        # calculate time delta for token expiry logic
        current_time = datetime.now()
        time_delta = current_time - self.last_refresh_time

        # if access_token is not set or it has expired, get a new one
        if self.access_token is None or time_delta.total_seconds() >= self.expires_in :

            # generate headers and body and send POST request to acquire a new access token
            encodedData = base64.b64encode(bytes(f"{self.client_id}:{self.client_secret}", "ISO-8859-1")).decode("ascii")
            headers = {'Authorization': f"Basic {encodedData}",'Content-Type' : "application/x-www-form-urlencoded"}
            body_data = {"grant_type" : "client_credentials"}

            # HTTP POST request
            token_response = requests.post(self.oauth_token_url,headers=headers,data=body_data,verify=False)
            
            #process the json in the response and save received Oauth settings
            token_json = json.loads(token_response.text)
 
            self.access_token = token_json["access_token"]
            self.expires_in = int(token_json["expires_in"])
            self.last_refresh_time = datetime.now()
        
        # just a check in case no headers have been defined for the outgoing API request
        # the r variable is a handle to the outgoing request object
        if r.headers is None :
            r.headers = {}
            r.headers["Content-Type"] = "application/json"

        # add the access_token as a header to the outgoing API request
        if self.access_token is not None :   
            r.headers["Authorization"] = f"Bearer {self.access_token}"

        return r

  
class MyCustomOpsViewAuth(AuthBase):
     def __init__(self,**args):
         self.username = args['username']
         self.password = args['password']
         self.url = args['url']
         pass
 
     def __call__(self, r):
         
         #issue a PUT request (not a get) to the url from self.url
         payload = {'username': self.username,'password':self.password}
         auth_response = requests.put(self.url,params=payload,verify=false)
         #get the auth token from the auth_response. 
         #I have no idea where this is in your response,look in your documentation ??
         tokenstring = "mytoken"
         headers = {'X-Opsview-Username': self.username,'X-Opsview-Token':tokenstring}
         
         r.headers = headers
         return r
       

class MyUnifyAuth(AuthBase):
     def __init__(self,**args):
         self.username = args['username']
         self.password = args['password']
         self.url = args['url']
         pass
 
     def __call__(self, r):
         login_url = '%s?username=%s&login=login&password=%s' % self.url,self.username,self.password
         login_response = requests.get(login_url)
         cookies = login_response.cookies
         if cookies:
            r.cookies = cookies
         return r
         
    
#cloudstack auth example
class CloudstackAuth(AuthBase):
    def __init__(self,**args):
        # setup any auth-related data here
        self.apikey = args['apikey']
        self.secretkey = args['secretkey']
        pass
        
    def __call__(self, r):
        # modify and return the request
    
        parsed = urllib.parse.urlparse(r.url)
        url = parsed.geturl().split('?',1)[0]
        url_params= urllib.parse.parse_qs(parsed.query)
        
        #normalize the list value
        for param in url_params:
            url_params[param] = url_params[param][0]
        
        url_params['apikey'] = self.apikey
        
        keys = sorted(url_params.keys())

        sig_params = []
        for k in keys:
            sig_params.append(k + '=' + urllib.parse.quote_plus(url_params[k]).replace("+", "%20"))
       
        query = '&'.join(sig_params)

        signature = base64.b64encode(hmac.new(
            self.secretkey,
            msg=query.lower(),
            digestmod=hashlib.sha1
        ).digest())

        
        query += '&signature=' + urllib.parse.quote_plus(signature)

        r.url = url + '?' + query
        
        return r