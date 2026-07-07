import requests as req
import json

class Hyas_api_call:

    def hyas_insight_endpoints_body(ioc_name, ioc_value):
        try:

            payload = json.dumps({
            "applied_filters": {
                ioc_name: ioc_value
            }
            })
            return payload
        
        except Exception as err:
            return err

    def hyas_insight_endpoints(url, api_key, data): 
        try:

            url = url
            
            headers={
                        'Content-type': 'application/json',
                        'X-API-Key': api_key,
                        'User-Agent': 'Splunk Enterprise'
                    }

            payload = data
            post_data = req.post(url = url, data = payload, headers=headers)
            if post_data.status_code == 401:
                data = 401
                return data
            elif post_data.status_code == 404:
                data = 404
                return data
            elif post_data.status_code >= 500:
                data = 500
                return data
            else:   
                data = post_data.json()
                return data
        
        except Exception as err:
            return err