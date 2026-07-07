import splunk.rest as rest
import logger_manager as log
import os
import json
import requests
import splunk.entity as entity
logger = log.setup_logging('trustar_indicator_whitelist')

class whitelist_indicator(rest.BaseRestHandler):

    def validate_values(self):
        values = self.request.get('payload')
        if isinstance(values, str):
            values = values.strip().split(" ")
            if len(values)==2 and len(values[0])==int(values[1]):
                task = "add"
            elif len(values)==3 and len(values[0])+len(values[1])==int(values[2]):
                task = "remove"
            else:
                logger.error("TruSTAR Error: Invalid payload: " + str(self.request.get('payload')))
                task = "error"
        return values, task
    
    def get_proxy_uri(self, https_proxy, https_proxy_port, https_proxy_username, passwords):
        proxy_address = None
        if https_proxy and https_proxy != "None":
            if https_proxy_username and https_proxy_username != "None":
                protocol = https_proxy.split("://")[0]
                server = https_proxy.split("://")[1]
                proxy_address = protocol + "://" + https_proxy_username + ":" + passwords.get('https_proxy_password','') + "@" + server + ":" + https_proxy_port
            else:
                proxy_address = https_proxy + ":" + https_proxy_port
        return proxy_address
    
    def handle_response_status(self, response, task, indicator_value, values):
        if response.status_code != 200:
            if task=="add":
                logger.error("TruSTAR Error: error while adding indicator " + str(json.dumps(indicator_value)) +" to whitelist")
                logger.error("TruSTAR Error: Response: " + str(response.json()))
            else:
                logger.error("TruSTAR Error: error while removing indicator " + str(values) + " from whitelist")
                logger.error("TruSTAR Error: Response Status Code: " + str(response.status_code))
            return "error"
        else:
            if task=="add":
                logger.info("TruSTAR Info: Successfully added indicator " + str(json.dumps(indicator_value)) + " to whitelist")
                logger.info("TruSTAR Info: Response: " + str(response.json()))
            else:
                logger.info("TruSTAR Info: Successfully removed indicator " + str(values) + " from whitelist")
            return "success"
    
    def get_passwords(self, my_app, mod_input_name):
        try:
            entities = entity.getEntities(['admin', 'passwords'], namespace=my_app, owner='nobody', sessionKey=self.sessionKey, search=my_app)
        except Exception as e:
            logger.error("TruSTAR Error: Unable to decrypted password")
            return {"error": True}
        password_key = [mod_input_name+'_key', mod_input_name+'_secret', mod_input_name+'_https_proxy_password']
        passwords = {}
        for _, value in entities.iteritems():
            if value['username'].partition('`')[0] in password_key and not value.get('clear_password', '`').startswith('`'):
                key = value['username'].split('_')
                if key:
                    passwords[key[len(key)-1]] = value.get('clear_password', '')
        return passwords

    def handle_POST(self):
        values, task = self.validate_values()
        if task == "error":
            return "error"

        try:
            path = "/services/data/inputs/trustar"
            _, content = rest.simpleRequest(path, method='GET', sessionKey=self.sessionKey, getargs={"output_mode": "json"}, raiseAllErrors=True)
        except Exception as exe:
            logger.error("TruSTAR Error: Error while getting content : %s " % str(exe))
            return "error"
        data = json.loads(content)['entry']
        if not data:
            logger.error("TruSTAR Error: Modular input not found")
            return "error"

        trustar_url = str(data[0]['content'].get('trustar_url')).strip().strip('/')
        https_proxy_username = str(data[0]['content'].get('https_proxy_username'))
        https_proxy = str(data[0]['content'].get('https_proxy'))
        https_proxy_port = str(data[0]['content'].get('https_proxy_port'))
        cert_path = str(data[0]['content'].get('cert_path'))
        verify = True
        if cert_path and cert_path.strip() != "" and cert_path != "None":
            verify = cert_path.strip()
        mod_input_name = str(data[0].get('name'))
        my_app = __file__.split(os.sep)[-3]
        passwords = self.get_passwords(my_app, mod_input_name)
        if passwords.get("error"):
            return "error"

        proxy_address = self.get_proxy_uri(https_proxy, https_proxy_port, https_proxy_username, passwords)

        body = {'grant_type': 'client_credentials'}
        url = trustar_url + '/oauth/token'
        proxies = {'http': proxy_address, 'https': proxy_address}
        headers={
            "Client-Type":"API",
            "Client-Version": "1.3",
            "Client-Metatag": "SPLUNK"
        }
        try:
            # Make REST call
            response = requests.post(url=url, data=body, auth=(passwords.get('key'), passwords.get('secret')), verify=verify,
                                        proxies=proxies,headers=headers)
            access_token = None
            if response.status_code == 200:
                access_token = response.json()
            if not access_token:
                logger.error("Authentication Failed ! Please verify URL, API key and Secret Key of TruSTAR to Connect.")
                return "error"
        except Exception, e:
            logger.error("TruSTAR Error: Cannot get access_key for authentication , message %s %s " % (e, e.args))
            return "error"

        headers["Authorization"] = "Bearer " + str(access_token['access_token'])
        url = trustar_url + '/api/1.3/whitelist'
        indicator_value = None
        try:
            # Make REST call
            if task=="add":
                headers['Content-Type']= 'application/json'
                indicator_value = [str(values[0])]
                response = requests.post(url=url, data=json.dumps(indicator_value), headers=headers, proxies=proxies)
            else:
                params = {'indicatorType': str(values[0]), 'value': str(values[1])}
                response = requests.delete(url=url, params=params, headers=headers, proxies=proxies)

            return self.handle_response_status(response, task, indicator_value, values)
        except Exception, e:
            logger.error("TruSTAR Error: Cannot get access_key for authentication , message %s %s " % (e, e.args))
            return "error"