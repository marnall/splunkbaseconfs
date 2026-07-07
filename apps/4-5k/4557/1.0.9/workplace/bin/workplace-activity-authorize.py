import splunk
import requests

class handler(splunk.rest.BaseRestHandler):
    def handle_authorize(self):
        try:
            credentials = {}
            credentials['code'] = self.args.get('code')
            credentials['grant_type'] = 'authorization_code'
            credentials['client_id'] = self.args.get('client_id')
            credentials['client_secret'] = self.args.get('client_secret')
            credentials['redirect_uri'] = self.args.get('redirect_uri')
            oauth2_token_endpoint = self.args.get('oauth2_token_endpoint')

            headers = {'content-type': 'application/x-www-form-urlencoded'}
            token_response = requests.post(oauth2_token_endpoint, data=credentials, headers=headers)
            if (token_response.status_code == 200):
                self.response.setHeader('content-type', 'application/json')
                self.response.write(token_response.text)
            else:                
                self.response.setStatus(400)
        except:
            self.response.setStatus(400)            

    handle_POST = handle_authorize