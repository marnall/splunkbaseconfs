# encoding = utf-8
import os
import sys
import time
import datetime
import json
bin_dir = os.path.basename(__file__)
import import_declare_test
import os.path as op
import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi 
import dateutil.parser
import re

def get_start_date(helper, check_point_key):
    
    # Try to get a date from the check point first
    d = helper.get_check_point(check_point_key)
    
    # If there was a check point date, retun it.
    if (d not in [None,'']):
        return dateutil.parser.parse(d["max_date"])
    else:
        # No check point date, so look if a start date was specified as an argument
        d = helper.get_arg("start_date_time")
        if (d not in [None,'']):
            return dateutil.parser.parse(d)
        else:
            # If there was no start date specified, default to 5 days ago
            return datetime.datetime.now() - datetime.timedelta(days=5)

def is_https(url):
    if url.startswith("https://"):
        return True
    else:
        return False

def get_messages(helper, microsoft_trace_url, microsoft_office_365_username, microsoft_office_365_password):
    helper.log_debug("_Splunk_ message trace URL: %s" % microsoft_trace_url)
    proxy = helper.get_proxy()
    proxies = {}
    messages = None
    
    if(proxy):
        proxy_url = "%s://%s:%s" % (proxy["proxy_type"], proxy["proxy_url"], proxy["proxy_port"])
        
        if(proxy["proxy_username"] and proxy["proxy_password"]):
            proxy_url = "%s://%s:%s@%s:%s" % (proxy["proxy_type"], proxy["proxy_username"], proxy["proxy_password"], proxy["proxy_url"], proxy["proxy_port"])
            
        proxies = {
                "http" : proxy_url,
                "https" : proxy_url
            }
    
    try:
        r = requests.get(
            microsoft_trace_url,
            proxies = proxies,
            auth=requests.auth.HTTPBasicAuth(microsoft_office_365_username, microsoft_office_365_password),
            headers={'Accept':'application/json'}
        )
        helper.log_debug("_Splunk_ response headers: %s" % r.headers)
        r.raise_for_status()
        messages = json.loads(r.content)

    except Exception as e:
        message = "_Splunk_ HTTP Request error: %s" % str(e)
        helper.log_error(message)
        raise e
        
    return messages

def get_events_continuous(helper, ew):
    global_account = helper.get_arg("office_365_account")
    global_microsoft_office_365_username = global_account["username"]
    global_microsoft_office_365_password = global_account["password"]
    query_window_size = int(helper.get_arg("query_window_size"))
    delay_throttle = int(helper.get_arg("delay_throttle"))
    interval = int(helper.get_arg("interval"))
    check_point_key = "%s_obj_checkpoint" % helper.get_input_stanza_names()
    messages = None
    
    start_date = get_start_date(helper, check_point_key)
    end_date = start_date + datetime.timedelta(minutes=query_window_size)
    helper.log_debug("_Splunk_ Start date: %s, End date: %s" % (start_date, end_date))
    utc_now = datetime.datetime.utcnow()
    
    if end_date > utc_now - datetime.timedelta(minutes=delay_throttle):
        helper.log_debug("_Splunk_ end_date is greater than the specified delay throttle [start_date=%s end_date=%s utc_now=%s] Skipping..." % (start_date, end_date, utc_now))
        return
    
    microsoft_trace_url = "https://reports.office365.com/ecp/reportingwebservice/reporting.svc/MessageTrace?$filter=StartDate eq datetime'%sZ' and EndDate eq datetime'%sZ'" % (start_date.isoformat(), end_date.isoformat())

    message_response = get_messages(helper, microsoft_trace_url, global_microsoft_office_365_username, global_microsoft_office_365_password)
    messages = message_response['value'] or None

    if messages is None:
        # Since no message were retrieved during this poll, move the query window forward by the amount of seconds in the interval.
        max_date = start_date + datetime.timedelta(seconds=interval)
        helper.log_debug("_Splunk_ no messages returned.  Setting max date to %s" % max_date)
        checkpoint_data = {}
        checkpoint_data["max_date"] = str(max_date)
        helper.save_check_point(check_point_key, checkpoint_data)
        return

    max_date = start_date
    helper.log_debug("_Splunk_ max date before getting message: %s" % str(max_date))

    while messages:
        for message in messages:
        
            # According to https://msdn.microsoft.com/en-us/library/office/jj984335.aspx
            # The StartDate and EndDate fields do not provide useful information in the report results...
            # Sometimes popping "StartDate" fails because of unknown issue. So to avoid an unexpected error, Try/Except method is used here.
            try:
                message.pop("StartDate")
                message.pop("EndDate")
            except Exception as e:
                helper.log_error("_Splunk_ Message Pop error: %s" % str(e))

            this_date_received = dateutil.parser.parse(message["Received"])
            max_date = max([max_date, this_date_received])
        
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(), 
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(message))
            ew.write_event(event)

        sys.stdout.flush()
        messages = None

        # Check point the largest date seen during the query
        checkpoint_data = {}
        checkpoint_data["max_date"] = str(max_date)
        helper.log_debug("_Splunk_ max date after getting messages: %s" % str(max_date))
        helper.save_check_point(check_point_key, checkpoint_data)

        nextLink = None
        if ('@odata.nextLink' in message_response):
            nextLink = message_response['@odata.nextLink']

        if ('odata.nextLink' in message_response):
            nextLink = message_response['odata.nextLink']
        
        if nextLink is not None:
            nextLink = get_url(nextLink)
            helper.log_debug("_Splunk_ nextLink URL (@odata.nextLink): %s" % nextLink)

            # This should never happen, but just in case...
            if not is_https(nextLink):
                raise ValueError("nextLink scheme is not HTTPS. nextLink URL: %s" % nextLink)

            message_response = get_messages(helper, nextLink, global_microsoft_office_365_username, global_microsoft_office_365_password)
            messages = message_response['value'] or None
    
def get_url(path):
    url_base = 'https://reports.office365.com/ecp'
    if '../../' in path:
        path = path.replace('../../', '')
    return url_base + '/' + path

def get_events_once(helper, ew):
    global_account = helper.get_arg("office_365_account")
    global_microsoft_office_365_username = global_account["username"]
    global_microsoft_office_365_password = global_account["password"]
    messages = None
    start_date = dateutil.parser.parse(helper.get_arg("start_date_time"))
    end_date = dateutil.parser.parse(helper.get_arg("end_date_time"))
    
    check_point_key = "%s_once_checkpoint" % helper.get_input_stanza_names()
    checkpoint_date = helper.get_check_point(check_point_key)
    
    if (checkpoint_date not in [None,'']):
        check_start_date = dateutil.parser.parse(checkpoint_date["start_date"])
        check_end_date = dateutil.parser.parse(checkpoint_date["end_date"])
        
        if (check_start_date == start_date) and (check_end_date == end_date):
            helper.log_info("_Splunk_ O365 Reporting Add-on skipped \"input Name = %s \" since events between %s and %s should have been indexed" %(helper.get_input_stanza_names(), start_date, end_date))
            return    

    microsoft_trace_url = "https://reports.office365.com/ecp/reportingwebservice/reporting.svc/MessageTrace?$filter=StartDate eq datetime'%sZ' and EndDate eq datetime'%sZ'" % (start_date.isoformat(), end_date.isoformat())

    message_response = get_messages(helper, microsoft_trace_url, global_microsoft_office_365_username, global_microsoft_office_365_password)
    messages = message_response['value'] or None
    
    while messages:
        for message in messages:
        
            # According to https://msdn.microsoft.com/en-us/library/office/jj984335.aspx
            # The StartDate and EndDate fields do not provide useful information in the report results...
            # Sometimes popping "StartDate" fails because of unknown issue. So to avoid an unexpected error, Try/Except method is used here.
            try:
                message.pop("StartDate")
                message.pop("EndDate")
            except Exception as e:
                helper.log_error("_Splunk_ Message Pop error: %s" % str(e))
        
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(), 
                sourcetype=helper.get_sourcetype(),
                data=json.dumps(message))
            ew.write_event(event)

        sys.stdout.flush()
        messages = None

        nextLink = None
        if ('@odata.nextLink' in message_response):
            nextLink = message_response['@odata.nextLink']

        if ('odata.nextLink' in message_response):
            nextLink = message_response['odata.nextLink']
        
        if nextLink is not None:
            nextLink = get_url(nextLink)
            helper.log_debug("_Splunk_ nextLink URL (@odata.nextLink): %s" % nextLink)

            # This should never happen, but just in case...
            if not is_https(nextLink):
                raise ValueError("nextLink scheme is not HTTPS. nextLink URL: %s" % nextLink)

            message_response = get_messages(helper, nextLink, global_microsoft_office_365_username, global_microsoft_office_365_password)
            messages = message_response['value'] or None
    
    checkpoint_data = {}
    checkpoint_data["start_date"] = str(start_date)
    checkpoint_data["end_date"] = str(end_date)
    helper.save_check_point(check_point_key, checkpoint_data)

class ModInputms_o365_message_trace(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputms_o365_message_trace, self).__init__("ta_ms_o365_reporting", "ms_o365_message_trace", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputms_o365_message_trace, self).get_scheme()
        scheme.title = ("Microsoft Office 365 Message Trace")
        scheme.description = ("Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("input_mode", title=" Input Mode",
                                         description="Selecting \"Index Once\" ignores \"Query window size\" and \"Delay throttle\". Additionally, \"Start date/time\" and \"End date/time\" are required for \"Index Once\".",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("office_365_account", title="Office 365 Account",
                                         description="",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("query_window_size", title="Query window size (minutes)",
                                         description="Specify how many minute\'s worth of data to query each interval. See the README.md file for more information.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("delay_throttle", title="Delay throttle (minutes)",
                                         description="Microsoft may delay trace events up to 24 hours. Specify how close to \"now\" a query may run (smaller values may introduce data loss for large volumes). See the README.md file for more information.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("start_date_time", title="Start date/time",
                                         description="Date/time to start collecting message traces.  If no date/time is given, the input will start 7 days in the past.",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("end_date_time", title="End date/time",
                                         description="Only specify an end date/time if using the \"Index Once\" option.",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-MS_O365_Reporting"

    def validate_input(helper, definition):
        input_mode = definition.parameters.get('input_mode')
        interval = definition.parameters.get('interval')
        query_window_size = definition.parameters.get('query_window_size')
        delay_throttle = definition.parameters.get('delay_throttle')
        start_date_time = definition.parameters.get('start_date_time')
        end_date_time = definition.parameters.get('end_date_time')
        start = None # Local instance of start date
        end = None # Local instance of end date
        
        # Start date checks
        if start_date_time is not None:
            try:
                start = dateutil.parser.parse(start_date_time)
            except Exception as e:
                error_message = "Invalid date format specified for 'Start date/time'"
                helper.log_error(error_message)
                raise ValueError(error_message)
                
            # Make sure the date entered is less than 30 days in the past.
            # Otherwise, the reporting API will throw an error
            if start < datetime.datetime.now() - datetime.timedelta(days=29):
                raise ValueError("'Start Date' cannot be more than 30 days in the past.")
        
        # Index Once checks
        if input_mode == "index_once":
            
            # Make sure start date and end date were specified
            if (start_date_time is None or end_date_time is None):
                error_message = "'Start date/time' and 'End date/time' are required for an 'Index Once' input."
                helper.log_error(error_message)
                raise ValueError(error_message)
                
            # Make sure the interval is correct
            if (interval != "-1"):
                error_message = "Interval must be '-1' for an 'Index Once' input."
                helper.log_error(error_message)
                raise ValueError(error_message)
            
            # Make sure the end date is a correct format
            if end_date_time is not None:
                try:
                    end = dateutil.parser.parse(end_date_time)
                except Exception as ed:
                    error_message = "Invalid date format specified for 'End date/time'"
                    helper.log_error(error_message)
                    raise ValueError(error_message)
                    
            # Make sure the end date is after the start date
            if  start > end:
                raise ValueError("The 'Start date/time' cannot be larger than the 'End date/time'.")
            
        else:
            # Continuously Monitor checks
            if (query_window_size is None or int(query_window_size) < 1):
                raise ValueError("'Query Window Size' is required and should be at least 1 minute.")
            if (delay_throttle is None or int(delay_throttle) < 1):
                raise ValueError("'Delay throttle' is required and should be at least 1 minute.")
    

    def collect_events(helper, ew):
    
        input_mode = helper.get_arg("input_mode")
        
        if (input_mode == "index_once"):
            get_events_once(helper, ew)
        else:
            get_events_continuous(helper, ew)

    def get_account_fields(self):
        account_fields = []
        account_fields.append("office_365_account")
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields

if __name__ == "__main__":
    exitcode = ModInputms_o365_message_trace().run(sys.argv)
    sys.exit(exitcode)
