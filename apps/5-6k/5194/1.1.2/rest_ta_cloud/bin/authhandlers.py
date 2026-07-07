from requests.auth import AuthBase
import hmac
import base64
import hashlib

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