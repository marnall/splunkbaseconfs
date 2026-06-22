import os
import json
import logging
import requests
import logging.handlers
from splunk.persistconn.application import PersistentServerConnectionApplication
import traceback

def setup_logger(level):
    logger = logging.getLogger("custom_rest")
    logger.propagate = False
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(
            os.environ["SPLUNK_HOME"],
            "var",
            "log",
            "splunk",
            "bitdefender_intelligence_api_screens.log",
        ),
        maxBytes=25000000,
        backupCount=5,
    )
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


logger = setup_logger(logging.INFO)

class data_enrichment(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def parse_form_data(self, form_data):
        parsed = {}
        for [key, value] in form_data:
            parsed[key] = value
        return parsed
    
    def handle(self, in_string):
        in_dict = json.loads(in_string)
        payload = self.parse_form_data(in_dict["form"])
        api_key = payload["api_key"]
        ioc = payload.get("ioc")

        try:
            response = requests.get(
                f"https://reputation.ti.bitdefender.com/reputation?ioc={ioc}",
                headers={'Auth-Token': str(api_key)},
                verify=True)
            response.raise_for_status()
            logger.info(response.url)
            return {"status": 200, "payload": response.text}
        
        except requests.exceptions.HTTPError as error:
            if str(response.status_code).startswith("5"):
                logger.error("Internal Server error recieved from Bitdefender Intelligence API.")
                logger.error(error)
                return {"status": 400, "payload": f"Internal Server error recieved from Bitdefender Intelligence API."}
            else:
                logger.error(f"Status code {response.status_code} recieved from Bitdefender Intelligence API.")
                logger.error(error)
                return {"status": 400, "payload": f"Unauthorized access. Please check your credentials."}
        except requests.exceptions.SSLError as error:
            logger.error("SSL Error.")
            logger.error(error)
            return {"status": 400, "payload": f"SSL Error. {error}."}
        except requests.exceptions.ConnectionError as error:
            logger.error("Connection Error.")
            logger.error(error)
            return {"status": 400, "payload": "Unable to connect to Bitdefender Intelligence API."}
        except requests.exceptions.Timeout as error:
            logger.error("Timeout Error.")
            logger.error(error)
            return {"status": 400, "payload": "Timeout error while connecting to Bitdefender Intelligence API."}
        except requests.exceptions.RequestException as error:
            logger.error("Request Error.")
            logger.error(error)
            return {"status": 400, "payload": "Request error while connecting to Bitdefender Intelligence API."}
        except Exception as error:
            logger.error("Unkown error.")
            logger.error(traceback.format_exc())
            return {"status": 400, "payload": "Unknown error."}
