import requests
import os, sys
import logging, logging.handlers
import json
import splunk
import urllib3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument
import splunklib.modularinput as smi

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_logging():
    logger = logging.getLogger('auto_data_rebalance')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']

    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "auto_data_rebalance.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    #LOGGING_FORMAT = '%(asctime)s %(levelname)-8s %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), maxBytes=1048572, backupCount=3)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

logger = setup_logging()
logger.info("auto_data_rebalance start")

class AutoDataRebalance(smi.Script):
    def get_scheme(self):
        scheme = smi.Scheme("Automatic Data Rebalance")
        scheme.description = "Trigger a data rebalance when the indexer clusters search factor is met"
        scheme.use_external_validation = False 
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False 

        threshold = Argument("threshold")
        threshold.data_type = Argument.data_type_number
        threshold.required_on_edit = False
        threshold.required_on_create = False
        threshold.description = "Threshold (rebalance_threshold) value, defaults to 0.9"
        scheme.add_argument(threshold)

        max_runtime = Argument("max_runtime")
        max_runtime.data_type = Argument.data_type_number
        max_runtime.required_on_edit = False
        max_runtime.required_on_create = False
        max_runtime.description = "Maximum runtime to run the data rebalance, defaults to unlimited"
        scheme.add_argument(max_runtime)

        target_index = Argument("target_index")
        target_index.data_type = Argument.data_type_string
        target_index.required_on_edit = False
        target_index.required_on_create = False
        target_index.description = "Index to rebalance, defaults to all indexes"
        scheme.add_argument(target_index)

        searchable = Argument("searchable")
        searchable.data_type = Argument.data_type_boolean
        searchable.required_on_edit = False
        searchable.required_on_create = False
        searchable.description = "Whether to use searchable mode, defaults to False"
        scheme.add_argument(searchable)

        usage_based = Argument("usage_based")
        usage_based.data_type = Argument.data_type_boolean
        usage_based.required_on_edit = False
        usage_based.required_on_create = False
        usage_based.description = "Whether to use the new usage based data rebalance, defaults to False"
        scheme.add_argument(usage_based)

        debug = Argument("debug")
        debug.data_type = Argument.data_type_boolean
        debug.required_on_edit = False
        debug.required_on_create = False
        debug.description = "Enables debug logging"
        scheme.add_argument(debug)
   
        excess_buckets = Argument("excess_buckets")
        excess_buckets.data_type = Argument.data_type_boolean
        excess_buckets.required_on_edit = False
        excess_buckets.required_on_create = False
        excess_buckets.description = "If set to true this triggers the removal of all excess buckets instead of a data rebalance, defaults to False"
        scheme.add_argument(excess_buckets)

        return scheme

    def is_positive_number(self, value):
        try:
            number = float(value)
            return number > 0
        except ValueError:
            return False

    def stream_events(self, inputs, ew):
        logger.info("Auto Data Rebalance attempting to retrieve session key")
        # Define the headers
        headers = {"Authorization": "Splunk " + self.service.token }

        for input_name, input_item in list(inputs.inputs.items()):
            # Set to INFO, we can change to DEBUG if required
            logger.setLevel(logging.INFO)

            if "threshold" in input_item:
                threshold = input_item["threshold"]
                if not self.is_positive_number(threshold):
                    logger.error("Invalid threshold, needs to be a positive decimal number")
                    break 
            else:
                threshold = "0.9"

            if "max_runtime" in input_item:
                max_runtime = input_item["max_runtime"]
                if not self.is_positive_number(max_runtime):
                    logger.error("Invalid max_runtime, needs to be a positive decimal number (minutes)")
                    break
            else:
                max_runtime = False

            if "target_index" in input_item:
                target_index = input_item["target_index"]
            else:
                target_index = False

            if "searchable" in input_item and input_item["searchable"] in ("1", "True", "true"):
                searchable = True
            else:
                searchable = False

            if "usage_based" in input_item and input_item["usage_based"] in ("1", "True", "true"):
                usage_based = True
            else:
                usage_based = False

            if "excess_buckets" in input_item and input_item["excess_buckets"] in ("1", "True", "true"):
                excess_buckets = True
            else:
                excess_buckets = False

            if "debug" in input_item and input_item["debug"] in ("1", "True", "true"):
                logger.setLevel(logging.DEBUG)

            # Define the URLs
            status_url = "https://localhost:8089/services/cluster/manager/info?f=maintenance_mode&output_mode=json"
            # alternative url /services/cluster/manager/fixup?level=search_factor&output_mode=json could work as well to count fixups instead 
            search_factor_url = "https://localhost:8089/services/cluster/manager/generation/master?output_mode=json&f=search_factor_met"
            server_conf_url = "https://localhost:8089/servicesNS/-/-/configs/conf-server/clustering?output_mode=json"
            server_conf_settings = "https://localhost:8089/servicesNS/nobody/system/configs/conf-server/clustering"
            rebalance_url = "https://localhost:8089/services/cluster/master/control/control/rebalance_buckets?output_mode=json"
            usage_based_url = "https://localhost:8089/services/cluster/master/control/control/rebalance_buckets_usage?output_mode=json"
            excess_buckets_url = "https://localhost:8089/services/cluster/master/control/default/prune_index"
            logger.debug(f"threshold={threshold} max_runtime={max_runtime} target_index={target_index} searchable={searchable}")
            logger.info("Checking maintenance mode and search factor status")

            # Make the GET request
            try:
                logger.debug(f"Attempting to call url={status_url} headers={headers}")
                response = requests.get(status_url, headers=headers, verify=True)
            except requests.exceptions.SSLError:
                logger.error(f"requests.get call to url={status_url} failed due to SSLError, you may need to set verify=False")
                return

            if response.status_code != 200:
                logger.error(f"GET request failed with status_code={response.status_code} text={response.text}")
                return

            # Parse the JSON data
            data = response.json()
            logger.debug(f"Response={data}")

            maintenance_mode = data['entry'][0]['content']['maintenance_mode']
            logger.debug(f"Maintenance mode status is maintenance_mode={maintenance_mode}")

            if maintenance_mode:
                logger.warn("Cluster appears to be in maintenance mode, not attempting a data rebalance")
                break 
            try:
                logger.debug(f"Attempting to call url={search_factor_url} headers={headers}")
                response = requests.get(search_factor_url, headers=headers, verify=True)
            except requests.exceptions.SSLError:
                logger.error(f"requests.get call to url={search_factor_url} failed due to SSLError, you may need to set verify=False")
                return

            if response.status_code != 200:
                logger.error(f"GET request failed with status_code={response.status_code} text={response.text}")
                return

            # Parse the JSON data
            data = response.json()
            logger.debug(f"Response={data}")

            search_factor = data['entry'][0]['content']['search_factor_met']
            logger.debug(f"Search factor is search_factor={search_factor}")

            if search_factor != "1":
                logger.warn("Cluster search factor is not met, not attempting a data rebalance")
                break

            # check if threshold matches our expectations
            try:
                logger.debug(f"Attempting to call url={server_conf_url} headers={headers}")
                response = requests.get(server_conf_url, headers=headers, verify=True)
            except requests.exceptions.SSLError:
                logger.error(f"requests.get call to url={server_conf_url} failed due to SSLError, you may need to set verify=False")
                return

            if response.status_code != 200:
                logger.error(f"GET request failed with status_code={response.status_code} text={response.text}")
                return

            # Parse the JSON data
            data = response.json()
            logger.debug(f"Response={data}")
            if 'rebalance_threshold' in data['entry'][0]['content']:
                current_threshold = data['entry'][0]['content']['rebalance_threshold']
            else:
                current_threshold = False

            if not current_threshold or current_threshold!=threshold:
                logger.info(f"Current rebalance_threshold in server.conf appears to be current_threshold={current_threshold}, setting to threshold={threshold}")
                response = requests.post(server_conf_settings, headers=headers, data={"rebalance_threshold": threshold},verify=True)
                if response.status_code != 200:
                    logger.error(f"POST request failed with status_code={response.status_code} text={response.text}")
                    return

            if excess_buckets:
                logger.debug(f"Attempting to call {excess_buckets_url}")
                # this endpoint takes a POST request with no payload, unless we want to target a particular index
                payload = {}
                if target_index:
                    logger.debug(f"Adding target_index={target_index}")
                    payload['index'] = target_index
 
                response = requests.post(excess_buckets_url, headers=headers, data=payload,verify=True)
                if response.status_code != 200:
                    logger.error(f"POST request failed with status_code={response.status_code} text={response.text}")
                    return

                logger.info("Excess bucket removal triggered")
                # this particular endpoint returns minimal information, continue at this point as we're either running an excess bucket removal or rebalancing
                continue

            if usage_based:
                logger.debug(f"Attempting to call {usage_based_url} action=status")
                response = requests.post(usage_based_url, headers=headers, data={"action": "status"},verify=True)
                if response.status_code != 200:
                    logger.error(f"POST request failed with status_code={response.status_code} text={response.text}")
                    return
                # Parse the JSON data
                data = response.json()
                logger.debug(f"Response={data}")

                content = data['entry'][0]['content']
                stddev_after_usage_rebalance = content['stddev_after_usage_rebalance']
                stddev_before_usage_rebalance = content['stddev_before_usage_rebalance']
                stddev_current = content['stddev_current']

                # this could be a an smiEvent(data=...), ew.write_event(event) if required
                logger.info(f"stddev_after_usage_rebalance={stddev_after_usage_rebalance} stddev_before_usage_rebalance={stddev_before_usage_rebalance} stddev_current={stddev_current}")
                # logic could be used to determine the appropriate standard deviation but for now we'll just run the rebalance
                response = requests.post(usage_based_url, headers=headers, data={"action": "start"},verify=True)
                if response.status_code != 200:
                    logger.error(f"POST request failed with status_code={response.status_code} text={response.text}")
                    return
                data = response.json()
                logger.debug(f"Response={data}")
                description = data['entry'][0]['content']['description']
                logger.info(f"Description returned by usage based rebalance endpoint is desc={description}")
            else:
                logger.debug(f"Attempting to call {rebalance_url} with index={target_index} action=start searchable={searchable}")
                payload = {"action": "start", "searchable": searchable }
                if target_index:
                    logger.debug(f"Adding target_index={target_index}")
                    payload['index'] = target_index
                if max_runtime:
                    logger.debug(f"Adding max_runtime={max_runtime}")
                    payload['max_time_in_min'] = max_runtime
                response = requests.post(rebalance_url, headers=headers, data=payload, verify=True)
                data = response.json()
                logger.debug(f"Response={data}")
                description = data['entry'][0]['content']['description']
                logger.info(f"Description returned by rebalance endpoint is desc={description}")

if __name__ == "__main__":
    exitcode = AutoDataRebalance().run(sys.argv)
    sys.exit(exitcode)
