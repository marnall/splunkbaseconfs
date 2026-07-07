import splunk
import requests
import json
from time import sleep
from external_auth import user, password

class ExternalKV(splunk.rest.BaseRestHandler):


    def batches(iterable, batch_size):
        length = len(iterable)
        batch_count = length/batch_size
        for item in range(batch_count):
            yield iterable[item:item+batch_size]

    def batch(iterable, n=1):
        l = len(iterable)
        for ndx in range(0, l, n):
            yield iterable[ndx:min(ndx + n, l)]

    def handle_GET(self):
        sessionKey = self.sessionKey
     
        
        try:
            
            coll = self.request['query']['Collection']
            #coll = "bah_business_unit"
            def update_collection(coll):
                base_collection = "/servicesNS/nobody/OT-Base/storage/collections/data/" + coll 
                json_out = '?output_mode=json'
                uri_filter = "?sort=creation_time:-1&limit=10000"
                
                r = requests.get("https://10.137.128.98:8089" + base_collection + uri_filter, auth=(user, password), verify=False)

                
                if r.text:
                    d = requests.delete("https://127.0.0.1:8089" + base_collection , auth=(user, password), verify=False)
                    json_b = json.loads(r.text)
                    for item in range(0,len(json_b), 100):
                        p = requests.post("https://127.0.0.1:8089" + base_collection + '/batch_save', 
                            data=json.dumps(json_b[item:item+100]), headers={'content-type': 'application/json'}, 
                            auth=(user, password), verify=False)
                    return self.response.write(str(p.status_code))
                    
                return self.response.write(str(r.text))
            
            #Call the update

            update_collection(coll)
            #sleep(3)

           
        except Exception, e:
            self.response.write(e)

    def handle_POST(self):
        sessionKey = self.sessionKey
     
        
        try:
            
            payload = self.request['payload']
            #self.response.write(str(payload))
            user = ''
            password = ''
            coll = ''

            for el in payload.split('&'):
                key, value = el.split('=')
                if 'Username' in key:
                    user = value
                if 'Password' in key:
                    password = value
                if 'Collection' in key:
                    coll = value
            #self.response.write(str(user + password + coll))
            #if user == '' or password == '':
            #    self.response.setStatus(400):
            #    self.response.write('provide your username and password for the development server')

            #coll = "bah_business_unit"
            def update_collection(coll, user, password):
                base_collection = "/servicesNS/nobody/OT-Base/storage/collections/data/" + coll 
                json_out = '?output_mode=json'
                uri_filter = "?sort=creation_time:-1&limit=10000"

                r = requests.get("https://10.137.128.98:8089" + base_collection + uri_filter, auth=(user, password), verify=False)
                if r.text:
                    d = requests.delete("https://127.0.0.1:8089" + base_collection , auth=(user, password), verify=False)
                    json_b = json.loads(r.text)
                    for item in range(0,len(json_b), 100):
                        p = requests.post("https://127.0.0.1:8089" + base_collection + '/batch_save', 
                            data=json.dumps(json_b[item:item+100]), headers={'content-type': 'application/json'}, 
                            auth=(user, password), verify=False)
                    return self.response.write(str(p.status_code))
                    
                return self.response.write(str(r.status_code))
            
            #Call the update

            update_collection(coll, user, password)
            #sleep(3)

           
        except Exception, e:
            self.response.write(e)
