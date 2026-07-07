import base64
import sys
import json
import requests
import splunk
import crowdstrike_app_utils as utils


_LOGGER = utils.get_logger('crowdstrike_upload_ioc')

class UploadIOC(splunk.rest.BaseRestHandler):
       
    
    def handle_POST(self):
        session_key = self.sessionKey
        error_message = None
        try:
            request_data = self.request['form']
            
            try:
                #to handle '' value of expiration days
                expiration_days = int(request_data.get("expiration_days")) if request_data.get("expiration_days") else 30
                request_data.update({"expiration_days": expiration_days})
            except:
                error_message = 'Invalid value for "Expiration Days" encountered'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
    
            if not request_data.get('type'):
                error_message = 'IOC Type is required.'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
            
            if not request_data.get('value'):
                error_message = 'IOC Value is required.'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
            
            error_message = utils.validate_ioc_value(request_data.get('type'), request_data.get('value'))
            
            if error_message:
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
                
    
            if len(request_data.get('description')) > 200:
                error_message = 'Indicator description should not exceed beyond 200 characters'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
    
            if len(request_data.get('source')) > 200:
                error_message = 'Indicator source value should not exceed beyond 200 characters'
                _LOGGER.exception(error_message)
                raise RuntimeError(error_message)
            
            self.request['form']['policy'] = 'detect'
            self.request['form']['share_level'] = 'red'
            
            username, password = utils.get_credentials(session_key)
            proxies = utils.get_proxy_info(session_key)
            
            if username and password:    
                endpoint = "https://falconapi.crowdstrike.com/indicators/entities/iocs/v1"
                base64string = base64.b64encode('%s:%s' % (username, password))
                headers = {"Authorization": "Basic " + base64string, "Content-Type": "application/json"}
                data = [dict(self.request['form'])]
                ioc_response = requests.post(endpoint, headers=headers, data=json.dumps(data), proxies=proxies)
                if ioc_response.status_code != 200:
                    raise Exception, "Upload ioc request get failed error code: %s message: %s" %(str(ioc_response.status_code), str(ioc_response.reason))
                    
                response = utils.return_object(ioc_response.status_code, "OK", None)
            else:
                raise Exception, "No credentials found for Query Type. Please configure by going to 'Configuration' page of Add-On"
        except Exception, e:
            if not e:
                error_message = "Error occurred while uploading Indicator to Falcon. Please try again later or contact Splunk Administrator."
            _LOGGER.exception(e)
            response = utils.return_object(None, "Error", str(e))

        self.response.setHeader('content-type', 'application/json')
        self.response.write(response)

    #handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST