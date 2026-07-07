""" Add your custom response handler class to this module.
"""

# Standard library imports
import json
import datetime

# Local imports
import logger_manager as log

# Set up logging
logger = log.setup_logging('trustar_modinput')

endpoint_global = None
sourcetype = None


class TruSTARResponseHandler:
    """ All Responses are handled according to their type in this class.
    """

    def __init__(self):
        pass

    def __call__(self, raw_response_output, data_retrieval_endpoint, url, stanza_name):
        """
        Handle responses in field raw_response_output according to response_type.
        
        :param raw_response_output: API response
        :param data_retrieval_endpoint: REST endpoint from where data was retrieved
        :param url: TruSTAR station URL
        :param stanza_name: provided modular input name
        """

        # Declare global variables for setting source and sourcetype of event
        global endpoint_global
        global sourcetype

        # Assign source to splunk event
        endpoint_wo_protocol = data_retrieval_endpoint.split("https://")[1]
        endpoint_global = stanza_name + "::" + endpoint_wo_protocol

        # Update response if required
        # If data is fetched from "/reports" endpoint
        if data_retrieval_endpoint.find("/reports") != -1:
            # Assign sourcetype of splunk event
            sourcetype = "trustar:reports"
            # Parse event data
            self.parse_json_dict(raw_response_output, url)

        elif data_retrieval_endpoint.find("/enclaves") != -1:
            # Assign sourcetype of splunk event
            sourcetype = "trustar:enclaves"
            # Parse event data
            self.parse_json_dict(raw_response_output, url)

        elif data_retrieval_endpoint.find("/indicators") != -1:
            # Assign sourcetype to the Splunk event
            sourcetype = "trustar:indicators"
            # Parse event data
            self.parse_json_dict(raw_response_output, url)

        else:
            sourcetype = "trustar"
            self.parse_json_dict(raw_response_output, url)

    def parse_json_dict(self, event, url):
        """ To generate event from json in response
        
        :param event: event to dump in splunk
        :param url: TruSTAR station URL
        """

        currenttime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')

        event.update({"instance_url": url, "timestamp": currenttime})
        print_xml_stream(json.dumps(event))


def print_xml_stream(s):
    """ To index event in xml format.
    
    :param s: event string
    """

    # Print event string, its source and sourcetype so as to index it in splunk
    print ("<stream><event unbroken=\"1\"><data>%s</data><source>%s</source><sourcetype>%s</sourcetype><done/></event></stream>" % (
            encode_xml_text(s), str(endpoint_global), str(sourcetype)))


def encode_xml_text(text):
    """ To encode some special chars in xml.
    
    :param text: xml text
    :return: encoded text
    """

    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text
