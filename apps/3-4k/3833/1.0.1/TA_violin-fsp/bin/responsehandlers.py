"""add your custom response handler class to this module."""
import json
import datetime
import logger_manager as log

# set up logging
logger = log.setup_logging('violin_fsp')

node_global = None
endpoint_global = None


class ViolinResponseHandler:
    """All Responses are handled according to their type in this class."""

    def __init__(self):
        pass

    def __call__(self, raw_response_output, response_type, node, endpoint, original_endpoint):
        """
        Handle responses in field raw_response_output according to response_type.
        
        :param raw_response_output: response in simple text
        :param response_type: type of response from API call
        :param node: host for concerto API call
        :param endpoint: endpoint for concerto API call
        :param original_endpoint: endpoint without replacing token
        :return: none
        """

        global node_global
        global endpoint_global

        node_global = node
        endpoint_global = original_endpoint.split(node)[1].strip()

        if response_type == "json":
            output = json.loads(raw_response_output)
            output_data = output.get("data", {})
            successkey = output.get("success")

            if (endpoint.find("/concerto/logicalresource/timemark/") != -1) and successkey:
                if "members" in output_data.keys():
                    extra_perms = {"timemark_type": "Group", "timemark_id": endpoint.split("/")[-1]}
                    self.parse_json_dict(node, output_data, extra_perms)
                else:
                    extra_perms = {"timemark_type": "LUN", "timemark_id": endpoint.split("/")[-1]}
                    self.parse_json_list(node, "timemarks", output_data["timemarks"], extra_perms)

            elif ((endpoint.find("/concerto/physicalresource/storagepool/") != -1) or (
                endpoint.find("/concerto/client/sanclient/") != -1)
                    or (endpoint.find("/concerto/server/triggerstatus") != -1 or (
                        endpoint.find("/concerto/server/callhome") != -1) or
                            (endpoint.find("/concerto/physicalresource/physicaladapter/") != -1))) and successkey:
                self.parse_json_dict(node, output_data)

            else:
                self.handle_response(node, output, successkey)

    def handle_response(self, node, vm_response, successkey):
        """
        To handle response 
        
        :param node: host for concerto API call
        :param vm_response: response in json format
        :param successkey: value of "success" field in response
        :return: none
        """
        if vm_response.get("xml"):
            try:
                vm_xml_response_data = vm_response["xml"]
                self.parse_xml_data(node, vm_xml_response_data)
            except Exception as e:
                logger.error("Violin FSP Error: unable to parse xml data %s , %s" % (vm_response, e))

        elif successkey:
                try:
                    vm_response_data = vm_response["data"]
                    for key in vm_response_data.keys():
                        if isinstance(vm_response_data[key], list) and vm_response_data[key]:
                            self.parse_json_list(node, key, vm_response_data[key])
                            break
                    else:
                        self.parse_json_dict(node, vm_response_data)
                except Exception:
                    self.parse_json_dict(node, vm_response)

        else:
            self.parse_json_dict(node, vm_response)

    def parse_json_dict(self, node, vm_response, extra_perms=None):
        """
        To generate event from json in response
        
        :param node: host for concerto API call
        :param vm_response: response in json format
        :param extra_perms: extra parameters to set in event
        :return: none
        """
        currenttime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')
        vm_response_event = {"data": vm_response, "timestamp": currenttime, "node": node}

        if extra_perms:
            vm_response_event.update(extra_perms)

        print_xml_stream(json.dumps(vm_response_event))

    def parse_json_list(self, node, key, vm_response, extra_perms=None):
        """
        To generate events from list of json in response
        
        :param node: host for concerto API call
        :param key: key in response which contained list of items
        :param vm_response: list of items
        :param extra_perms: extra parameters to set in event
        :return: none
        """
        currenttime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')
        for data in vm_response:
            vm_response_event = {key: data, "timestamp": currenttime, "node": node}

            if extra_perms:
                vm_response_event.update(extra_perms)

            print_xml_stream(json.dumps(vm_response_event))

    def parse_xml_data(self, node, vm_response_data):
        """
        To generate event from xml data in response
        
        :param node: host for concerto API call
        :param vm_response_data: xml data
        :return: none
        """
        vm_response_data = vm_response_data.replace("\n", "")
        currenttime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S%z')
        vm_response_event = {"data": vm_response_data, "timestamp": currenttime, "node": node}
        print_xml_stream(json.dumps(vm_response_event))


def print_xml_stream(s):
    """
    To index event in xml format
    
    :param s: event string
    :return: none
    """
    print "<stream><event unbroken=\"1\"><data>%s</data><source>%s</source><done/></event></stream>" % (
            encode_xml_text(s), "violin://" + str(node_global) + "::" + str(endpoint_global))


def encode_xml_text(text):
    """
    To encode some special chars in xml
    
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
