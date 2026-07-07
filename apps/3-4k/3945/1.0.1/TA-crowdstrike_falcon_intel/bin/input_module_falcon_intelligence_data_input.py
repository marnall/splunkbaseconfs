# encoding = utf-8
import time
import json
from datetime import datetime
import calendar
import splunk.rest as rest
# from solnlib.modular_input import checkpointer


def validate_input(helper, definition):
    """ Validates the input parameters and provides error to user on UI if the validation fails.

    :param helper: object of BaseModInput class
    :param definition: object containing input parameters
    """

    interval = definition.parameters.get('interval')
    try:
        if int(interval) < 0:
            raise Exception("Interval field should be a positive value.")
    except Exception as e:
        raise

    starting_date = definition.parameters.get('starting_date', None)
    if starting_date and starting_date.lower() != "all":
        datetime.strptime(starting_date, "%Y-%m-%d %H:%M:%S")
    pass


def collect_events(helper, ew):
    """ Collect data by making REST call to Falcon Intelligence platform and index it in Splunk.

    :param helper: object of BaseModInput class
    :param ew: object of EventWriter class
    """

    # Get log level configured by user
    loglevel = helper.get_log_level()
    # Set log level configured by user
    helper.set_log_level(loglevel)
    # Get proxy settings
    proxy_settings = helper.get_proxy()
    proxy = True if proxy_settings else False
    # Get account details configured by user
    opt_falcon_intelligence_account = helper.get_arg('falcon_intelligence_account')
    # Get stanza name of input which has triggered the modular input
    stanza_name = str(helper.get_input_stanza_names())
    # Get starting date for the input configured by user
    starting_date = helper.get_arg('starting_date')
    
    # checkpoint_dir = helper.context_meta.get("checkpoint_dir")
    # ck = checkpointer.FileCheckpointer(checkpoint_dir)
    # state = ck.get(stanza_name)
    # Obtain checkpoint details corresponding to the input that triggered the modular input
    state = helper.get_check_point(stanza_name)

    if state:
        published_date = state.get("published_date")
        marker = state.get("marker")
    else:
        marker = None
        if starting_date and starting_date.lower() != "all":
            published_date_dt_object = datetime.strptime(starting_date, "%Y-%m-%d %H:%M:%S")
            published_date = calendar.timegm(published_date_dt_object.utctimetuple())
        else:
            published_date = 946684800

    # Get session key
    session_key = helper.context_meta['session_key']
    # Make REST call to fetch app details
    try:
        resp, content = rest.simpleRequest("/servicesNS/nobody/system/apps/local/TA-crowdstrike_falcon_intel",
                                       sessionKey=session_key, getargs={"output_mode": "json"}, raiseAllErrors=True)
        # Get app details from the response
        app_info = json.loads(content)['entry'][0]['content']
        # Get version info from app details
        version = app_info.get("version", "x.x.x")
        
    except Exception as ex:
        helper.log_error("CrowdStrike Error: Error while fetching app version. Passing x.x.x as default version %s" %(ex.message))
        version = "x.x.x"
        
    # Prepare request headers
    headers = {"X-CSIX-CUSTID": opt_falcon_intelligence_account.get("username"),
               "X-CSIX-CUSTKEY": opt_falcon_intelligence_account.get("password"), "Content-Type": "application/json",
               "X-INTEGRATION": "splunk_ta_" + version}

    # Prepare request parameters
    parameters = {"gte": published_date, "perPage": 10000, "order": "desc"}
    if marker:
        parameters.update({"marker": marker})
        latest_published_date = published_date
    else:
        latest_published_date = calendar.timegm(time.gmtime())
    while True:
        marker_previous = parameters.get("marker")
        # Make REST call to fetch data from falcon intelligence platform
        try:
            if parameters.get("marker"):
                url = "https://intelapi.crowdstrike.com"+parameters.get("marker")
                response = helper.send_http_request(url,
                                                "get", headers=headers, verify=True,
                                                timeout=120, use_proxy=proxy)
            else:
                response = helper.send_http_request("https://intelapi.crowdstrike.com/indicator/v2/search/published_date",
                                                "get", parameters=parameters, headers=headers, verify=True,
                                                timeout=120, use_proxy=proxy)
        except Exception as e:
            helper.log_error("CrowdStrike Error: Error while fetching data from falcon intelligence platform. %s" %(str(e)))
            break

        if response.status_code != 200:
            error_dict = {"status_code": response.status_code, "response": response.text}
            helper.log_error("CrowdStrike Error: Unexpected response obtained from Falcon platform: %s"
                             % (str(error_dict)))
            break
        
        if not response.json():
            helper.save_check_point(stanza_name, {"published_date": latest_published_date, "marker": None})
            break
        
        header = response.headers
        marker = header.get("Next-Page", None)
        
        for indicator_data in response.json():
            indicator_data.update({"indexed_timestamp": "%d" % time.time()})
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                     sourcetype=helper.get_sourcetype(), data=json.dumps(indicator_data),
                                     time=indicator_data.get("published_date"))
            ew.write_event(event)
        
        if marker_previous==marker:
            helper.save_check_point(stanza_name, {"published_date": latest_published_date, "marker": None})
            break
        
        helper.save_check_point(stanza_name, {"published_date": latest_published_date, "marker": marker})
        parameters.update({"marker": marker})
