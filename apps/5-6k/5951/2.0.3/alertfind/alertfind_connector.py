# File: alertfind_connector.py
# Copyright (c) 2016-2021 Splunk Inc.
#
# SPLUNK CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Splunk Inc. is PROHIBITED.

import sys

# Phantom App imports
import phantom.app as phantom
import requests
import simplejson as json
import xmltodict
from defusedxml import ElementTree
from defusedxml.common import EntitiesForbidden
from lxml import etree
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

# Imports local to this App
from alertfind_consts import *


# Define the App Class
class AlertFindConnector(BaseConnector):

    ACTION_ID_TEST_CONNECTIVITY = "test_connectivity"
    ACTION_ID_SEND_NOTIFICATION = "send_notification"
    ACTION_ID_CANCEL_NOTIFICATION = "cancel_notification"
    ACTION_ID_NOTIFICATION_STATUS = "notification_status"
    ACTION_ID_RECIPIENT_STATUS = "recipient_status"

    def __init__(self):

        # Call the BaseConnectors init first
        super(AlertFindConnector, self).__init__()

        self._base_url = None
        self._xml_root = None
        self._headers = None

    def initialize(self):

        config_url = self.get_config()['url']

        if (not config_url.endswith('/')):
            config_url += '/'

        self._base_url = config_url + 'soap-api/notification?WSDL'

        self._headers = {'SOAPAction': 'a', 'Content-Type': 'application/xml'}

        self._xml_root = self._create_xml_root()

        return phantom.APP_SUCCESS

    def finalize(self):

        return phantom.APP_SUCCESS

    def _create_xml_root(self):

        root_namespaces = ALERTFIND_XML_NAMESPACES

        if (self.get_action_identifier() == self.ACTION_ID_SEND_NOTIFICATION):
            root_namespaces['soapenc'] = "http://schemas.xmlsoap.org/soap/encoding/"

        root = etree.Element('{%s}Envelope' % ALERTFIND_XML_NAMESPACES['soapenv'], nsmap=root_namespaces)
        body = etree.Element('{%s}Body' % ALERTFIND_XML_NAMESPACES['soapenv'])
        root.append(body)

        action = etree.Element('action')
        action.attrib['{%s}encodingStyle' % ALERTFIND_XML_NAMESPACES['soapenv']] = "http://schemas.xmlsoap.org/soap/encoding/"
        body.append(action)

        config = self.get_config()

        self._add_xml_node('String_1', 'xsd:string', action, text=config.get('username'))
        self._add_xml_node('String_2', 'xsd:string', action, text=config.get('password'))

        return root

    def _make_soap_call(self, action_result, fail_on_bad_arg=True):

        try:
            response = requests.post(self._base_url,  # nosemgrep
                    data=ElementTree.tostring(self._xml_root),
                    headers=self._headers)
        except Exception as e:
            return (action_result.set_status(phantom.APP_ERROR, ALERTFIND_ERR_SERVER_CONNECTION, e), None)

        try:
            resp_xml = ElementTree.fromstring(response.content)
        except EntitiesForbidden as e:
            return action_result.set_status(phantom.APP_ERROR, "Failed to parse XML: {}".format(e))

        try:

            resp_json = json.loads(json.dumps(xmltodict.parse(ElementTree.tostring(resp_xml[0]))))

            action_result.add_data(resp_json)

            if (response.status_code != 200):

                if (response.status_code == 500):

                    error = resp_json.get(
                        'soapenv:Body', {}).get('soapenv:Fault', {}).get('faultstring', '')  # pylint: disable=E1101

                    if ('PermissionDeniedException' in error):
                        return action_result.set_status(phantom.APP_ERROR, "Authentication with the AlertFind server failed")

                    if ((not fail_on_bad_arg) and ('InvalidArgumentException' in error)):
                        return action_result.set_status(phantom.APP_SUCCESS, "Test connectivity passed")

                    if (error):
                        return action_result.set_status(
                            phantom.APP_ERROR, "Call to AlertFind server failed with: {}".format(error))

                return action_result.set_status(phantom.APP_ERROR, "Call to AlertFind failed, please see data for error details")

        except Exception as e:
            return action_result.set_status(phantom.APP_ERROR, 'Could not parse XML response from AlertFind server', e)

        return action_result.set_status(phantom.APP_SUCCESS, "Call to AlertFind succeeded")

    def _add_xml_node(self, name, node_type, parent, text=None, namespace={}, array_type=None, array_length=None):

        node = etree.Element(name, nsmap=namespace)

        node.attrib['{%s}type' % ALERTFIND_XML_NAMESPACES['xsi']] = node_type

        if (text is not None):
            node.text = str(text)

        if (array_type and array_length):
            node.attrib['{%s}arrayType' % ALERTFIND_XML_NAMESPACES['soapenc']] = "aler:{0}[{1}]".format(array_type, array_length)

        parent.append(node)

        return node

    def _test_connectivity(self, param):

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_node = self._xml_root[0][0]

        action_node.tag = '{%s}queryNotificationStatus' % ALERTFIND_XML_NAMESPACES['aler']

        self._add_xml_node('long_3', 'xsd:long', action_node, text='-1')

        self.save_progress("Checking credentials with AlertFind server")

        if (not self._make_soap_call(action_result, fail_on_bad_arg=False)):
            return phantom.APP_ERROR

        self.save_progress("Test connectivity passed")

        return phantom.APP_SUCCESS

    def _send_notification(self, param):

        self.debug_print("param", param)

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_node = self._xml_root[0][0]

        action_node.tag = '{%s}sendNotification' % ALERTFIND_XML_NAMESPACES['aler']

        namespace = {"aler": "http://messageone.com/af/types/AlertFindNotificationService"}

        self._add_xml_node('String_3', 'xsd:String', action_node, text=param.get('team'))

        notification_node = self._add_xml_node('Notfication_4', 'aler:Notification', action_node, namespace=namespace)

        self._add_xml_node('body', 'xsd:string', notification_node, text=param.get('notification_body'))
        self._add_xml_node('subject', 'xsd:string', notification_node, text=param.get('notification_subject'))
        self._add_xml_node('stopOnResponses', 'xsd:boolean', notification_node, text=param.get('stop_on_response_limit'))
        self._add_xml_node('authenticationRequired', 'xsd:boolean', notification_node, text=param.get('authenticate'))

        responses = param.get('response_descriptions').split(',')

        responses_node = self._add_xml_node(
                'responses',
                'aler:ArrayOfResponse',
                notification_node,
                array_type='Response',
                array_length=len(responses))

        for response in responses:

            item_node = self._add_xml_node('item', 'aler:Response', responses_node)

            abbreviation = response

            if (len(abbreviation) > 20):
                abbreviation = abbreviation[:20]

            self._add_xml_node('abbreviation', 'xsd:string', item_node, text=abbreviation)
            self._add_xml_node('description', 'xsd:string', item_node, text=response)
            self._add_xml_node('maxRecipients', 'xsd:int', item_node, text=param.get('max_response_recipients', 0))

        recipients = param.get('recipient_ids').split(',')

        recipients_node = self._add_xml_node(
                'arrayOfRecipient_5',
                'aler:arrayOfRecipient',
                action_node,
                array_type='Recipient',
                namespace=namespace,
                array_length=len(recipients))

        for recipient in recipients:

            item_node = self._add_xml_node('item', 'aler:Recipient', recipients_node)

            self._add_xml_node('id', 'xsd:string', item_node, text=recipient.strip())
            self._add_xml_node('type', 'xsd:string', item_node, text=param.get('recipient_type'))
            self._add_xml_node('delayAfter', 'xsd:long', item_node, text=param.get('recipient_delay', 0))

        self._add_xml_node('long_6', 'xsd:long', action_node, text=param.get('delay', 0))

        if (not self._make_soap_call(action_result)):
            return phantom.APP_ERROR

        resp_body = action_result.get_data()[0].get('soapenv:Body', {})

        if (resp_body.get('multiRef')):
            notification_id = resp_body.get('multiRef').get('#text')

        else:
            notification_id = resp_body.get('ns1:sendNotificationResponse', {}).get('result', {}).get('#text')

        action_result.set_summary({'notification_id': notification_id})

    def _cancel_notification(self, param):

        self.debug_print("param", param)

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_node = self._xml_root[0][0]

        action_node.tag = '{%s}cancelNotification' % ALERTFIND_XML_NAMESPACES['aler']

        self._add_xml_node('long_3', 'xsd:long', action_node, text=param.get('notification'))

        return self._make_soap_call(action_result)

    def _notification_status(self, param):

        self.debug_print("param", param)

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_node = self._xml_root[0][0]

        action_node.tag = '{%s}queryNotificationStatus' % ALERTFIND_XML_NAMESPACES['aler']

        self._add_xml_node('long_3', 'xsd:long', action_node, text=param.get('notification'))

        return self._make_soap_call(action_result)

    def _recipient_status(self, param):

        self.debug_print("param", param)

        action_result = self.add_action_result(ActionResult(dict(param)))

        action_node = self._xml_root[0][0]

        action_node.tag = '{%s}queryRecipientStatus' % ALERTFIND_XML_NAMESPACES['aler']

        self._add_xml_node('long_3', 'xsd:long', action_node, text=param.get('notification'))

        return self._make_soap_call(action_result)

    def handle_action(self, param):

        ret_val = None

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if (action_id == self.ACTION_ID_TEST_CONNECTIVITY):
            ret_val = self._test_connectivity(param)
        if (action_id == self.ACTION_ID_SEND_NOTIFICATION):
            ret_val = self._send_notification(param)
        if (action_id == self.ACTION_ID_CANCEL_NOTIFICATION):
            ret_val = self._cancel_notification(param)
        if (action_id == self.ACTION_ID_NOTIFICATION_STATUS):
            ret_val = self._notification_status(param)
        if (action_id == self.ACTION_ID_RECIPIENT_STATUS):
            ret_val = self._recipient_status(param)

        return ret_val


def main():
    import argparse

    import pudb

    pudb.set_trace()

    argparser = argparse.ArgumentParser()

    argparser.add_argument('input_test_json', help='Input Test JSON file')
    argparser.add_argument('-u', '--username', help='username', required=False)
    argparser.add_argument('-p', '--password', help='password', required=False)
    argparser.add_argument('-v', '--verify', action='store_true', help='verify', required=False, default=False)

    args = argparser.parse_args()
    session_id = None

    username = args.username
    password = args.password
    verify = args.verify

    if username is not None and password is None:

        # User specified a username but not a password, so ask
        import getpass
        password = getpass.getpass("Password: ")

    if username and password:
        try:
            login_url = AlertFindConnector._get_phantom_base_url() + '/login'

            print("Accessing the Login page")
            r = requests.get(login_url, verify=verify, timeout=60)
            csrftoken = r.cookies['csrftoken']

            data = dict()
            data['username'] = username
            data['password'] = password
            data['csrfmiddlewaretoken'] = csrftoken

            headers = dict()
            headers['Cookie'] = 'csrftoken=' + csrftoken
            headers['Referer'] = login_url

            print("Logging into Platform to get the session id")
            r2 = requests.post(login_url, data=data, verify=verify, headers=headers, timeout=60)
            session_id = r2.cookies['sessionid']
        except Exception as e:
            print("Unable to get session id from the platform. Error: {}".format(str(e)))
            sys.exit()

    with open(args.input_test_json) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = AlertFindConnector()
        connector.print_progress_message = True

        if session_id is not None:
            in_json['user_session_token'] = session_id
            connector._set_csrf_info(csrftoken, headers['Referer'])

        ret_val = connector._handle_action(json.dumps(in_json), None)
        print(json.dumps(json.loads(ret_val), indent=4))

    sys.exit()


if __name__ == '__main__':
    main()
