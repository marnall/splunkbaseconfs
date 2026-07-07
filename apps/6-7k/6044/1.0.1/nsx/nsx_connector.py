# -----------------------------------------
# Phantom sample App Connector python file
# -----------------------------------------

# Phantom App imports
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

# Usage of the consts file is recommended
from nsx_consts import *
import requests
import json
import xmltodict
from bs4 import BeautifulSoup


class RetVal(tuple):
    def __new__(cls, val1, val2):
        return tuple.__new__(RetVal, (val1, val2))


class NsxConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(NsxConnector, self).__init__()

        self._state = None

    def _process_empty_reponse(self, response, action_result):

        if response.status_code == 200:
            return RetVal(phantom.APP_SUCCESS, {})

        return RetVal(action_result.set_status(phantom.APP_ERROR, "Empty response and no information in the header"), None)

    def _process_html_response(self, response, action_result):

        # An html response, treat it like an error
        status_code = response.status_code

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            error_text = soup.text
            split_lines = error_text.split('\n')
            split_lines = [x.strip() for x in split_lines if x.strip()]
            error_text = '\n'.join(split_lines)
        except:
            error_text = "Cannot parse error details"

        message = "Status Code: {0}. Data from server:\n{1}\n".format(status_code,
                error_text)

        message = message.replace('{', '{{').replace('}', '}}')

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_xml_response(self, r, action_result):

        # Try xmltodict parse
        try:
            resp_json = xmltodict.parse(r.text)

            # convert from Ordereddict to normal dict
            resp_json = json.loads(json.dumps(resp_json))
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to convert response from xml to JSON. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_json_response(self, r, action_result):

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            return RetVal(action_result.set_status(phantom.APP_ERROR, "Unable to parse JSON response. Error: {0}".format(str(e))), None)

        # Please specify the status codes here
        if 200 <= r.status_code < 399:
            return RetVal(phantom.APP_SUCCESS, resp_json)

        # You should process the error returned in the json
        message = "Error from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _process_response(self, r, action_result):

        # store the r_text in debug data, it will get dumped in the logs if the action fails
        if hasattr(action_result, 'add_debug_data'):
            action_result.add_debug_data({'r_status_code': r.status_code})
            action_result.add_debug_data({'r_text': r.text})
            action_result.add_debug_data({'r_headers': r.headers})
        if 'xml' in r.headers.get('Content-Type', ''):
            return self._process_xml_response(r, action_result)

        # Process an HTML resonse, Do this no matter what the api talks.
        # There is a high chance of a PROXY in between phantom and the rest of
        # world, in case of errors, PROXY's return HTML, this function parses
        # the error and adds it to the action_result.
        if 'html' in r.headers.get('Content-Type', ''):
            return self._process_html_response(r, action_result)

        # it's not content-type that is to be parsed, handle an empty response
        if not r.text:
            return self._process_empty_reponse(r, action_result)

        # everything else is actually an error at this point
        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return RetVal(action_result.set_status(phantom.APP_ERROR, message), None)

    def _make_rest_call(self, endpoint, action_result, headers=None, params=None, data=None, method="get"):

        config = self.get_config()

        resp_json = None
        request_func = getattr(requests, method)

        if (not request_func):
            action_result.set_status( phantom.APP_ERROR, "Invalid method: {0}".format(method))

        # Create a URL to connect to
        url = "https://{0}{1}".format(config['nsx_manager'], endpoint)

        try:
            r = request_func(
                            url,
                            auth=(config['username'], config['password']),
                            data=data,
                            headers={'Content-Type': 'application/xml'},
                            verify=config.get('verify_server_cert', False))
        except Exception as e:
            return RetVal(action_result.set_status( phantom.APP_ERROR, "Error Connecting to server. Details: {0}".format(str(e))), resp_json)

        return self._process_response(r, action_result)

    def _handle_test_connectivity(self, param):

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # NOTE: test connectivity does _NOT_ take any parameters
        # i.e. the param dictionary passed to this handler will be empty.
        # Also typically it does not add any data into an action_result either.
        # The status and progress messages are more important.

        """
        # self.save_progress("Connecting to endpoint")
        # make rest call
        ret_val, response = self._make_rest_call('/endpoint', action_result, params=None, headers=None)

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            self.save_progress("Test Connectivity Failed. Error: {0}".format(action_result.get_message()))
            return action_result.get_status()

        # Return success
        # self.save_progress("Test Connectivity Passed")
        # return action_result.set_status(phantom.APP_SUCCESS)
        """

        # For now return Error with a message, in case of success we don't set the message, but use the summary
        self.save_progress("Test Connectivity Failed, action not yet implemented")
        return action_result.set_status(phantom.APP_ERROR, "Action not yet implemented")

    def _handle_block_port(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        ip_to_block = param['ip']
        protocol_to_block = param['protocol']
        port_to_block = param['port']

        data = BLOCK_PORT_XML.format(ip_to_block=ip_to_block, port_to_block=port_to_block, protocol_to_block=protocol_to_block,
                    section_name="Blocked IP {0} PORT {1}".format(ip_to_block, port_to_block))

        # make rest call
        ret_val, response = self._make_rest_call('/api/4.0/firewall/globalroot-0/config/layer3sections', action_result, data=data, method="post")

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "IP-PORT Blocked")

    def _handle_block_ip(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        ip_to_block = param['ip']

        data = BLOCK_IP_XML.format(ip_to_block=ip_to_block,
                    section_name="Blocked IP {0}".format(ip_to_block))

        # make rest call
        ret_val, response = self._make_rest_call('/api/4.0/firewall/globalroot-0/config/layer3sections', action_result, data=data, method="post")

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "IP Blocked")

    def _handle_attach_security_tag(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        tag_name = param['tag']

        data = GET_ATTACH_XML
        # Secury Tag is applied with Internal ID, to get Security Tag ID from name
        ret_val, response = self._make_rest_call('/api/2.0/services/securitytags/tag', action_result, data=data, method="get")

        # Response is dictionary, can access Security Tag Internal ID from that.
        try:
            tags = response['securityTags']['securityTag']
        except:
            return (action_result.set_status(phantom.APP_ERROR, "Tags not found"))
        tag_id = None
        for curr_tag in tags:
            if (curr_tag['name'] == tag_name):
                tag_id = curr_tag['objectId']
                break

        if (tag_id is None):
            return (action_result.set_status(phantom.APP_ERROR, "Matching Tag not found"))

        # tag_id = param['tag']

        vmobjectid = param['vmobjectid']

        data = TAG_TO_ATTACH_XML

        # make rest call
        ret_val, response = self._make_rest_call('/api/2.0/services/securitytags/tag/{0}/vm/{1}'.format(tag_id, vmobjectid), action_result, data=data,
            method="put")

        if (phantom.is_fail(ret_val)):
            # the call to the 3rd party device or service failed, action result should contain all the error details
            # so just return from here
            return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "Security Tag Attached to VM")

    def _handle_create_security_tag(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        tag_to_create = param['tag']

        data = CREATE_SECURITY_TAG_XML.format(tag_to_create=tag_to_create)

        # make rest call
        ret_val, response = self._make_rest_call('/api/2.0/services/securitytags/tag', action_result, data=data, method="post")

        # if (phantom.is_fail(ret_val)):
        # the call to the 3rd party device or service failed, action result should contain all the error details
        # so just return from here
        # return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "NSX Security Tag Created")

    def _handle_create_security_group(self, param):

        # Implement the handler here
        # use self.save_progress(...) to send progress messages back to the platform
        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))

        # Add an action result object to self (BaseConnector) to represent the action for this param
        action_result = self.add_action_result(ActionResult(dict(param)))

        # Access action parameters passed in the 'param' dictionary

        # Required values can be accessed directly
        group_to_create = param['group']

        data = CREATE_SECURITY_GROUP_XML.format(group_to_create=group_to_create)

        # make rest call
        ret_val, response = self._make_rest_call('/api/2.0/services/securitygroup/bulk/globalroot-0', action_result, data=data, method="post")

        # if (phantom.is_fail(ret_val)):
        # the call to the 3rd party device or service failed, action result should contain all the error details
        # so just return from here
        # return action_result.get_status()

        # Now post process the data,  uncomment code as you deem fit

        # Add the response into the data section
        action_result.add_data(response)

        # Return success, no need to set the message, only the status
        # BaseConnector will create a textual message based off of the summary dictionary
        return action_result.set_status(phantom.APP_SUCCESS, "NSX Security Group Created")

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'block_port':
            ret_val = self._handle_block_port(param)

        elif action_id == 'block_ip':
            ret_val = self._handle_block_ip(param)

        elif action_id == 'create_security_tag':
            ret_val = self._handle_create_security_tag(param)

        elif action_id == 'create_security_group':
            ret_val = self._handle_create_security_group(param)

        elif action_id == 'attach_security_tag':
            ret_val = self._handle_attach_security_tag(param)

        return ret_val

    def initialize(self):

        # Load the state in initialize, use it to store data
        # that needs to be accessed across actions
        self._state = self.load_state()

        """
        # get the asset config
        config = self.get_config()

        # Access values in asset config by the name

        # Required values can be accessed directly
        required_config_name = config['required_config_name']

        # Optional values should use the .get() function
        optional_config_name = config.get('optional_config_name')
        """

        return phantom.APP_SUCCESS

    def finalize(self):

        # Save the state, this data is saved accross actions and app upgrades
        self.save_state(self._state)
        return phantom.APP_SUCCESS


if __name__ == '__main__':

    import sys
    import pudb
    pudb.set_trace()

    if (len(sys.argv) < 2):
        print "No test json specified as input"
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = NsxConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(ret_val), indent=4))

    exit(0)
