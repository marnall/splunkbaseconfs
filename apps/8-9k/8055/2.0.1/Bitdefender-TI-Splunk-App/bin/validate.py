import os
import json
import logging
import time
from datetime import datetime, timedelta
import requests
import logging.handlers
from splunk.persistconn.application import PersistentServerConnectionApplication

def setup_logger(level):
    logger = logging.getLogger('custom_rest')
    logger.propagate = False
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'bitdefender_TI_validate.log'),
        maxBytes=25000000,
        backupCount=5
    )
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.INFO)

class validation(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        try:

            request_data = json.loads(in_string)
            results = {} 
            payload = request_data.get('form', [])
            if payload:
                api_key_value = next((item[1] for item in payload if item[0] == 'api_key'), None)
            
            payload = {}
            headers = {
            'Auth-Token': str(api_key_value)
            }

            def simplify_results(final_results):
                simplified_results = {}
                for feed_category, results in final_results.items():
                    simplified_results[feed_category] = {}
                    for feed_name, result in results.items():
                        if isinstance(result, dict) and "status" in result:
                            simplified_results[feed_category][feed_name] = result["status"]
                        else:
                            simplified_results[feed_category][feed_name] = result 
                return simplified_results

            def check_access(feeds):
                feed_results = {}
                for feed in feeds:
                    url = f"{feed['base_url']}{feed['endpoint']}"
                    response = requests.get(url, headers=headers)

                    if response.status_code == 404:
                        status = "Resource not found. The requested resource could not be found."
                    elif response.status_code == 401:
                        status = "Denied"
                    elif response.status_code == 403:
                        status = "Denied"
                    elif response.status_code == 400:
                        status = "Bad Request. The request could not be understood or was missing required parameters."
                    elif response.status_code == 500:
                        status = "Internal Server Error. An error occurred on the server side."
                    elif response.status_code == 200:
                        status = "Granted"
                    else:
                        status = "Unknown error while connecting to Bitdefender Threat Intelligence"

                    feed_results[feed['feed_name']] = {
                        "status": status,
                        "status_code": response.status_code
                    }

                return feed_results
                
            data_enrichment=[
                {"feed_name": "intelligence_api", "endpoint": "/reputation?ioc=f09c17cbb207c3b8a35773e264688978a367c7974a0e49c1a198b2d5a91624aa","base_url":"https://reputation.ti.bitdefender.com"}
            ]

            bitdefender_feeds=[
                {"feed_name": "web_feed", "endpoint": "/reputation?feed_name=web-feed&last_seconds=60", "base_url": "https://feeds.ti.bitdefender.com"},
                {"feed_name": "ip_feed", "endpoint": "/reputation?feed_name=ip-feed&last_seconds=60", "base_url": "https://feeds.ti.bitdefender.com"},
                {"feed_name": "file_feed", "endpoint": "/reputation?feed_name=file-feed&last_seconds=60", "base_url": "https://feeds.ti.bitdefender.com"}
            ]

            data_enrichment = check_access(data_enrichment)
            bitdefender_feeds_results = check_access(bitdefender_feeds)

            final_results = {
                "Bitdefender_feeds": bitdefender_feeds_results,
                "Data_enrichment": data_enrichment  
            }
            for feed_category, results in final_results.items():
                for feed_name, result in results.items():
                    if result["status"] not in ["Granted", "Denied"]:
                        logger.error(
                            f"Error in {feed_category}: {feed_name} - {result['status']} (Status Code: {result['status_code']})"
                        )
                        return {
                            "payload": result["status"],
                            "status": result["status_code"],
                        }

            simplified_results = simplify_results(final_results)
            
            logger.info(simplified_results)
            return {"payload": simplified_results, "status": 200}
          

       
        except Exception as e:
            logger.error(f"Unexpected Error: {e}", exc_info=True)
            return {
                'payload': {"error": "Unexpected Error", "details": str(e)},
                'status': 500
            }
