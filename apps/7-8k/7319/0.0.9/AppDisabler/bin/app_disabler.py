import requests
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
import urllib3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument
import splunklib.modularinput as smi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class AppDisabler(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme("App Disabling Input")
        scheme.description = "Set an application to have it disabled when this input runs, if the optional argument app_disabled=False then the app is enabled instead"
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        app_disabled = Argument("app_disabled")
        app_disabled.data_type = Argument.data_type_boolean
        app_disabled.required_on_edit = False
        app_disabled.required_on_create = False
        app_disabled.description = "Should the application be disabled or enabled (default True)"
        scheme.add_argument(app_disabled)

        app_name = Argument("app")
        app_name.data_type = Argument.data_type_string
        app_name.required_on_edit = True
        app_name.required_on_create = True
        app_name.description = "Name of the app where the report exists"
        scheme.add_argument(app_name)

        app_debug = Argument("debug_mode")
        app_debug.data_type = Argument.data_type_boolean
        app_debug.required_on_edit = False
        app_debug.required_on_create = False
        app_debug.description = "Enables debug logging"
        scheme.add_argument(app_debug)

        return scheme

    def stream_events(self, inputs, ew):
        # Create a logger
        logger = logging.getLogger(__name__)

        # Set the log level
        logger.setLevel(logging.INFO)
        #logger.setLevel(logging.DEBUG)
        
        log_file = os.environ['SPLUNK_HOME'] + "/var/log/splunk/app_disabler.log"

        # Create a handler
        handler = RotatingFileHandler(log_file, maxBytes=1048572, backupCount=3)

        # Create a formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(handler)
        
        logger.info("App Disabler attempting to retrieve session key")
        # Define the headers
        headers = {"Authorization": "Splunk " + self.service.token }

        for input_name, input_item in list(inputs.inputs.items()):
            # Set to INFO, we can change to DEBUG if required
            logger.setLevel(logging.INFO)

            # Get fields from the InputDefinition object
            app = input_item["app"]

            if "app_disabled" in input_item:
                app_disabled = input_item["app_disabled"]
            else:
                app_disabled = "True"

            if app_disabled == "True":
                endpoint = "disable"
            else:
                endpoint = "enable"

            if 'app_debug' in input_item:
                if input_item['app_debug'] == "True":
                    logger.setLevel(logging.DEBUG)

            # Define the URLs
            app_url = f"https://localhost:8089/services/apps/local/{app}?f=disabled&output_mode=json"
            app_post = f"https://localhost:8089/services/apps/local/{app}/{endpoint}"

            logger.debug(f"app_disabled={app_disabled} app={app} app_url={app_url} app_post={app_post}")

            logger.info(f"Check app={app} status")

            # Make the GET request
            try:
                logger.debug(f"Attempting to call url={app_url} headers={headers}")
                response = requests.get(app_url, headers=headers, verify=False)
            except requests.exceptions.SSLError:
                logger.error(f"requests.get call to url={app_url} failed due to SSLError, you may need to set verify=False")
                return

            if response.status_code != 200:
                logger.error(f"GET request failed with status_code={response.status_code} text={response.text}")
                return

            # Parse the JSON data
            data = response.json()
            logger.debug(f"Response={data}")

            disabled = data['entry'][0]['content']['disabled']
            logger.debug(f"Disabled value is disabled={disabled}")

            logger.error(f"disabled={disabled} {type(disabled)}")
            if disabled == True and app_disabled == "True":
                logger.info(f"app={app} is already {endpoint}d")
                return
            else:
                # Make the POST request
                try:
                    logger.debug(f"Attempting to call url={app_post} headers={headers}")
                    response = requests.post(app_post, headers=headers, verify=False)
                except:
                    logger.error(f"requests.get call to url={app_url} failed due to SSLError, you may need to set verify=False")
                if response.status_code != 200:
                    logger.error(f"POST request failed with status_code={response.status_code} text={response.text}")
                    return
                logger.debug(f"POST request response status_code={response.status_code} text={response.text}")
                logger.info(f"POST request response status_code={response.status_code}")
                logger.info(f"app={app} is now {endpoint}d")

if __name__ == "__main__":
    exitcode = AppDisabler().run(sys.argv)
    sys.exit(exitcode)
