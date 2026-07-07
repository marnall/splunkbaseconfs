import requests
import json
# Utility Functions

def form_url(conn, url):
   url = conn.transport+'://' + conn.ip + ':' + conn.port + url
   return url

def form_hdr(conn):
   hdr = dict()
   tmp_ckie = 'auth_cookie='+conn.cookie + ';user='+ conn.user +'; Max-Age=3600; Path=/'
   hdr['Cookie'] = tmp_ckie
   hdr['Content-type'] = 'application/json'
   return hdr

class Connection:
     def __init__(self,params):
         self.transport = params['transport']
         self.port = params['port']
         self.ip = params['ip']
         self.user = params['user']
         self.password = params['password']
         self.cookie = ''
         self.url = self.transport + '://' + self.ip + ':' + self.port
         self.not_init = 1

         if (self.port == '0'):
            return 

         # Step 1 - Login and get the auth cookie
         ret = requests.get(self.url + '/nos/api/login/',auth=(self.user, self.password),verify=False, timeout=20)
         if 'auth_cookie' not in ret.cookies:
            return
         self.cookie=ret.cookies['auth_cookie']

         # Step 2 - Login with valid cookie
         tmp_ckie = 'auth_cookie=' + self.cookie + ';user='+ self.user +'; Max-Age=3600; Path=/'
         self.hdr=dict()
         self.hdr['Cookie']=tmp_ckie

         ret = requests.get(self.url + '/nos/api/login/', headers=self.hdr, auth=(self.user, self.password),verify=False)
         if (ret.status_code != 200):
            ret = requests.get(self.url + '/nos/api/login/', headers=self.hdr, auth=(self.user, self.password),verify=False)
            if (ret.status_code != 200):
               return
         if 'auth_cookie' not in ret.cookies:
            return
         self.cookie=ret.cookies['auth_cookie']
         self.hdr['Cookie'] = 'auth_cookie=' + self.cookie + ';user='+ self.user +'; Max-Age=3600; Path=/'
         self.hdr['Content-Type']='application/json'
         self.not_init = 0

     def get(self, url):
         if (self.not_init == 1):
            return (0, None) 
         ret = requests.get((self.url + url), headers=self.hdr, auth=(self.user, self.password),verify=False)
         if (ret.status_code == 200):
            return (1, ret.json()) 
         return (0, None) 

     def put(self, url, inp):
         if (self.not_init == 1):
            return 0 
         ret = requests.put((self.url + url), data=json.dumps(inp), headers=self.hdr, auth=(self.user, self.password),verify=False)
         if (ret.status_code == 200):
            return 1
         return 0

     def post(self, url, inp):
         if (self.not_init == 1):
            return (0, None) 
         ret = requests.post((self.url + url), data=json.dumps(inp), headers=self.hdr, auth=(self.user, self.password),verify=False)
         if (ret.status_code == 200):
            return (1, ret.json()) 
         return (0, None) 

     def logout(self):
         if (self.not_init == 1):
            return 0 
         ret = requests.get((self.url + '/nos/api/logout/'), headers=self.hdr, auth=(self.user, self.password),verify=False)
         if (ret.status_code == 200):
            return 1
         return 0 
            
