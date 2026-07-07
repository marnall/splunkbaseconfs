# otrs connector
import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult
from otrs_consts import *
import urllib2
import json


class OtrsConnector(BaseConnector):
    '''
    OTRS connector
    this module can create, update, get and search ticket
    '''

    def __init__(self):
        super(OtrsConnector, self).__init__()
        return

    def _test_connectivity(self):
        self.save_progress("Querying a single server to check connectivity")
        config = self.get_config()
        self.save_progress("URL: %s" % (config[OTRS_DEVICE_URL]))
        url = self._prepare_url(OTRS_ROUTE_MAPPING_GET_TICKET, ticket_id="1")
        try:
            req = urllib2.Request(url)
            response = urllib2.urlopen(req)
            response.read()
        except Exception as e:
            self.save_progress("Error message : %s" % (e))
            self.append_to_message(OTRS_ERR_CONNECTION)
            return self.set_status_save_progress(phantom.APP_ERROR, OTRS_ERR_CONNECTION)
        return self.set_status_save_progress(phantom.APP_SUCCESS, OTRS_SUCC_CONNECTION)

    def _prepare_url(self, mapping, ticket_id=None):
        config = self.get_config()

        if mapping in config:
            action_route_uri = config[mapping]
        else:
            action_route_uri = OTRS_DEFAULT_ROUTE[mapping]

        if ticket_id is not None:
            base_url = '%s/%s/%s%s?UserLogin=%s&Password=%s&TicketID=%s'
            url_param = (
                config[OTRS_DEVICE_URL], OTRS_REST_ENDPOINT, config[OTRS_SERVICE],
                action_route_uri, config[OTRS_USERNAME], config[OTRS_PASSWORD], ticket_id)
        else:
            base_url = '%s/%s/%s%s?UserLogin=%s&Password=%s'
            url_param = (
                config[OTRS_DEVICE_URL], OTRS_REST_ENDPOINT, config[OTRS_SERVICE],
                action_route_uri, config[OTRS_USERNAME], config[OTRS_PASSWORD])

        url = base_url % url_param
        return url

    def _handle_json_data(self, input_data):
        string_data = ""
        if isinstance(input_data, str):
            try:
                json.loads(input_data)
                string_data = input_data
            except Exception as e:
                return (None, e)
        if isinstance(input_data, dict):
            try:
                string_data = json.dumps(input_data)
            except Exception as e:
                return (None, e)
        if string_data == "":
            return (None, INVALID_INPUT_DATA)
        return (string_data, None)

    def _prepare_json_ticket_data(self, param):
        if not param:
            return None, OTRS_ERR_NO_PARAMETERS
        json_data = {}
        for k, v in param.iteritems():
            if ':' in k and v is not None:
                keys = k.split(':')
                if keys[0] in json_data:
                    json_data[keys[0]][keys[1]] = v
                else:
                    json_data[keys[0]] = { keys[1]: v }
        if json_data:
            if OTRS_ARTICLE_PARAM_KEY in json_data:
                json_data[OTRS_ARTICLE_PARAM_KEY][OTRS_ARTICLE_CONTENTTYPE_PARAM_KEY] = OTRS_ARTICLE_CONTENTTYPE
            return json_data, None
        else:
            return None, OTRS_ERR_NO_PARAMETERS

    def _handle_request(self, url, data=None, rest_type=None):
        if data:
            data, error = self._handle_json_data(data)
            if error:
                return None, error
        try:
            if data:
                req = urllib2.Request(url, data)
                req.add_header('Content-Type', 'application/json')
            else:
                req = urllib2.Request(url)
            if rest_type is not None:
                req.get_method = lambda: rest_type
            response = urllib2.urlopen(req)
            returned_data = response.read()
        except Exception as e:
            return None, e
        json_data = json.loads(returned_data)
        if OTRS_RETURENED_ERROR_KEY in json_data:
            return None, json.dumps(json_data[OTRS_RETURENED_ERROR_KEY])
        return json_data, None

    def _handle_ticket_managemenet(self, param, mapping, rest_type=None):
        # prepare action component
        action_result = ActionResult(dict(param))
        self.add_action_result(action_result)

        # validate json data
        json_data, error = self._prepare_json_ticket_data(dict(param))
        if error:
            action_result.set_status(phantom.APP_ERROR, OTRS_ERR_JSON_TICKET_DATA, error)
            return action_result.get_status()
        # preapare url
        if OTRS_TICKET_ID_PARAM_KEY in param:
            url = self._prepare_url(mapping, ticket_id=param[OTRS_TICKET_ID_PARAM_KEY])
        else:
            url = self._prepare_url(mapping)
        # send request to otrs server
        result, error = self._handle_request(url=url, data=json.dumps(json_data), rest_type=rest_type)
        action_result.add_data(result)
        if error:
            action_result.set_status(phantom.APP_ERROR, OTRS_ERR_REST, error)
        else:
            action_result.set_status(phantom.APP_SUCCESS, OTRS_SUCC_REST)

        return action_result.get_status()

    def _handle_get_ticket(self, param, mapping):
        action_result = ActionResult(param)
        self.add_action_result(action_result)
        url = self._prepare_url(mapping, ticket_id=param[OTRS_TICKET_ID_PARAM_KEY])
        result, error = self._handle_request(url=url)
        if error is not None:
            action_result.set_status(phantom.APP_ERROR, OTRS_ERR_REST, error)
        else:
            action_result.add_data(result['Ticket'][0])
            action_result.set_status(phantom.APP_SUCCESS, OTRS_SUCC_REST)
        return action_result.get_status()

    def _handle_search_ticket(self, param, mapping):
        action_result = ActionResult(param)
        self.add_action_result(action_result)
        url = self._prepare_url(mapping)
        result, error = self._handle_request(url=url, data=param["query"], rest_type=REST_POST)
        if error is not None:
            action_result.set_status(phantom.APP_ERROR, OTRS_ERR_REST, error)
        else:
            action_result.add_data(result)
            action_result.set_status(phantom.APP_SUCCESS, OTRS_SUCC_REST)
        return action_result.get_status()

    def handle_action(self, param):
        result = None
        action = self.get_action_identifier()
        if action == ACTION_ID_TEST_CONNECTIVITY:
            result = self._test_connectivity()
        elif action == ACTION_ID_CREATE_TICKET:
            result = self._handle_ticket_managemenet(param, mapping=OTRS_ROUTE_MAPPING_CREATE_TICKET)
        elif action == ACTION_ID_UPDATE_TICKET:
            result = self._handle_ticket_managemenet(param, mapping=OTRS_ROUTE_MAPPING_UPDATE_TICKET, rest_type=REST_PATCH)
        elif action == ACTION_ID_GET_TICKET:
            result = self._handle_get_ticket(param, OTRS_ROUTE_MAPPING_GET_TICKET)
        elif action == ACTION_ID_SEARCH_TICKET:
            result = self._handle_search_ticket(param, OTRS_ROUTE_MAPPING_SEARCH_TICKET)
        return result


# cancheck code by just executing in console
if __name__ == '__main__':
    import sys
    import pudb
    pudb.set_trace()
    if len(sys.argv) < 2:
        print 'No test json specified as input'
        exit(0)
    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print json.dumps(in_json, indent='    ')
        connector = OtrsConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print ret_val
    exit(0)
