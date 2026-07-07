import import_declare_test
import time
import json
import zscaler
import sys
from datetime import datetime, timedelta
from splunklib import modularinput as smi
import splunklib.client as client
import splunklib.results as results
import zsutils 
import xml.etree.ElementTree as ET


def get_md5_list(logger, session_key: str):
    """
    Retrieves list of pending md5's from the lookup : zscaler-md5-lookup. 
    This list will be looped through to get results from the Zscaler Sandbox API.

    :param logger: logger object
    :param session_key: Splunk session key

    :return: dict of search results on success, None on failure
    """

    logger.info("Retrieving md5 list from zscaler-md5-lookup")
    try:
        args = {'token': session_key}
        service = client.connect(**args)
        kwargs_oneshot = {"earliest_time": "-1h", "latest_time": "now",}
        searchquery_oneshot = "| inputlookup zscaler-md5-lookup.csv | dedup md5"
        oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
        
    except Exception as e:
        logger.error(f"Error getting md5 list from lookup table : {str(e)}")
        return None
    
    # Parse XML and extract MD5 values
    md5_list = []  
    try: 
        oneshotsearch_results_content = oneshotsearch_results.read(size=None).decode("utf-8")
        logger.debug(f"oneshotsearch_results_content: {oneshotsearch_results_content}")

        if not oneshotsearch_results_content:  # Check for empty content (if truly empty)
            logger.warning("Splunk search returned empty result.")
            return []
        
        root = ET.fromstring(oneshotsearch_results_content)        
        for result in root.findall('.//result'):  
            md5_element = result.find('.//field[@k="md5"]/value/text')
            if md5_element is not None:
                md5_value = md5_element.text
                if md5_value == "none":  
                    return []
                md5_list.append(md5_value)
    except ET.ParseError as e: 
        logger.error(f"Error parsing returned md5 search XML: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing results: {e}")
        return None
    
    logger.debug(f"MD5 list retrieved from lookup: {md5_list}")
    return md5_list


class ZSCALER_SANDBOX_EVENTS(smi.Script):
    """Modular Input script to Retrieve Sandbox Events from Zscaler API"""


    def get_app_name(self):
        return "zscaler_sandbox_events"


    def validate_input(helper, definition):
        """
        Input validation is done on the globalConfig.json field definition 
        and is not required here
        """
        pass


    def __init__(self):
        super(ZSCALER_SANDBOX_EVENTS, self).__init__()


    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Collect events from the Zscaler Sandbox API"""

        # Retrieve Splunk session key from input definition metadata
        meta_configs = self._input_definition.metadata
        session_key = meta_configs["session_key"]

        # get input name and input items
        input_name, input_items = zsutils.get_input_name_and_items(inputs)

        # Create logger object 
        logger = zsutils.create_logger(input_name, session_key)
        logger.info("zscaler_sandbox_events -- modular input invoked.")

        cloud = input_items.get("cloud")
        index = input_items.get("index")
        global_account = input_items.get("global_account")
        account_config = zsutils.get_account_config(session_key, global_account, logger)
        username = account_config['username']
        password = account_config['password']
        api_key = account_config['api_key']
        interval = 300
        api_call_time = datetime.now()

        # Get list of MD5's pending detonation from lookup table
        md5List = get_md5_list(logger, session_key)
        logger.debug(f"MD5 list from lookup table: {md5List}")

        if md5List is None:
            logger.error("Failed to get md5 list from lookup table.  Exiting")
            return
        elif len(md5List) == 0:
            logger.info("No MD5's found in lookup table.  Exiting")
            return
        
        # Create Zscaler API object
        z = zscaler.zscaler()

        #Set Proxies, if set in the TA UI
        proxies = zsutils.get_proxy_config(session_key, logger)
        if proxies['proxy_url']:
            logger.debug(f"setting proxy: {json.dumps(proxies)}")
            z.proxies = {
                "http": proxies['proxy_url'] + ":" + proxies['proxy_port'],
                "https": proxies['proxy_url'] + ":" + proxies['proxy_port']
            }

        if not zsutils.zscaler_api_login(z, username, password, api_key, cloud, logger):
            logger.error(f"Failed to login to Zscaler cloud {cloud}")
            return
        else: 
            logger.info(f"Zscaler Login Success to cloud {cloud}")
        
        try:
            counter = 0
            
            for item in md5List:
                
                counter+=1

                # Every two runs, sleep one sec to work around the rate limit of 2 api calls/sec
                logger.debug("Checking per second rate limit is reached")
                if counter % 2 == 0:
                    logger.debug("Sleep 1 sec to refresh api rate limit of 2/sec")
                    time.sleep(1)
                  
                logger.info(f"Checking Zscaler Sandbox for MD5 : {item}")
                quota = z.check_sandbox_quota()
                
                logger.debug(f"Sandbox current quota : {quota}")
               
                while quota['unused'] <= 0: 
                    startTime = quota['startTime']
                    limit_reset_time = startTime + timedelta(days=1)
                    diff = (limit_reset_time - api_call_time).seconds
                    if diff < interval:
                        logger.info(f"waiting {str(diff)} secs to reset quota...\tquota_left [{str(quota['unused'])}] ")
                        time.sleep(diff)
                    else:
                        logger.info("Rate limit won't be reset before the next invocation of this API.  Exiting")
                        return
                    quota = z.check_sandbox_quota()

                report = z.get_sandbox_report(item, "full")

                if ("Please try again later" in report.text):
                    logger.info(f"Sandbox REPORT for MD5 ({item}): {report.text}")
                else:
                    event = smi.Event(data=report.text, index=index, sourcetype="zscalerapi-zia-sandbox")
                    ew.write_event(event)

        finally:
            if z.logout():
                logger.info("Zscaler sandbox session closed successfully")
            else:
                logger.warning("Zscaler logout returned non-200 status, but session cleared locally")


    def get_scheme(self):
        """
        Returns a Splunk Modular Input scheme object for ZScaler Sandbox Events.

        This function defines the configuration schema for a Splunk Modular Input
        that pulls Sandbox events from the ZScaler API.

        Returns:
            smi.Scheme: A Splunk Modular Input scheme object.
        """

        scheme = smi.Scheme("ZScaler Sandbox Events")
        scheme.description = "Modular input to pull Sandbox events from the ZScaler API"

        # Enable external validation for the input
        scheme.use_external_validation = True

        # Enable streaming mode for the input
        scheme.streaming_mode_xml = True

        # Allow multiple instances of this input to run simultaneously
        scheme.use_single_instance = False

        # Add required arguments to the scheme
        scheme.add_argument(smi.Argument(
            'name', 
            title='Name', 
            description='Input Name', 
            required_on_create=True
        ))

        scheme.add_argument(smi.Argument( 
            'cloud', 
            title='cloud', 
            description='Zscaler cloud', 
            required_on_create=True, 
            required_on_edit=True
        ))

        scheme.add_argument(smi.Argument(
            'global_account', 
            title='global_account', 
            description='Global Account', 
            required_on_create=True, 
            required_on_edit=True
        ))

        return scheme


if __name__ == '__main__':
    exit_code = ZSCALER_SANDBOX_EVENTS().run(sys.argv)
    sys.exit(exit_code)

