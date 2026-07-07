# -*- coding: utf-8 -*-D
#Copyright (C) 2010-2026 Sideview LLC.  All Rights Reserved.
import base64
import json
import logging
import os
import requests
import sys
import traceback

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

APP = "canary"
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")


if SPLUNK_HOME:
    try:
        import canary_util
    except ImportError:
        sys.path.insert(1,os.path.join(SPLUNK_HOME, "etc", "apps", APP, "bin"))
        import canary_util

    import splunk
    from splunk.persistconn.application import PersistentServerConnectionApplication
else:
    # base class offers zero help with actually handling the request, so when
    # in flask we don't need it.
    class PersistentServerConnectionApplication:
        pass

import canary_util.conf_io
import sideview_canary as sv

logger = sv.setup_logging(logging.DEBUG)



#Note: Elastic does need to be running.
# eg by running this:
# /opt/elk/elasticsearch-7.15.2/bin/elasticsearch -d -p pid


BASE_HEADERS = {'Content-type': 'application/json', 'Accept': 'text/plain'}


ES_CONF_FILENAME = "elastic"
DEFAULT_CONNECTIVITY_STANZA_NAME = "elasticserver"


class ESProxyMisconfiguredError(Exception):
    pass

def get_query_args(params, key="query"):
    """ just processing the inscrutable struct into more useful args"""
    out = {}
    if key not in params:
        return out
    query_array = params[key]
    for pair in query_array:
        out[pair[0]] = pair[1]
    return out

def make_msg(text, level):
    " construct a splunk-results json object for a message and level"
    return {'text' : text, 'type' : level}



class ElasticSearchProxyHandler(PersistentServerConnectionApplication):
    """
    An attempt to proxy as much of the Elastic API to actual elastic servers as
    canary & sideview apps need.

    Effectively this is a Work-In-Progress until it it feels done.

    Special features of this endpoint so far:

    query-style parameters are supported (for ALL http actions!) of:

    ?es_connection=<value>

    select an alternate elastic search instance other than the default.  A
    value of 'foo' here loads conection information from elastic.conf from
    [elasticsearch:foo]

    when no such param is passed, the config from [elasticsearch] is used.

    ?json_format=splunk_json

    When passed, if the proxy believes that it is proxying an elastic search
    query, the response is passed in a format similar to splunk's 'json' format.

    If not provided, the json is returned exactly as elasticsearch provides it.

    (The default behavior may be inverted.)
    """

    def __init__(self, command_line, command_arg):
        """oh hai"""
        PersistentServerConnectionApplication.__init__(self)


    def _init_es_conninfo(self, connection_name):
        """Fetches host and port for the target elastic search instance from
           canary/local/elastic.conf"""

        if not connection_name:
            stanza_name = DEFAULT_CONNECTIVITY_STANZA_NAME
        else:
            stanza_name = '%s:%s' % (DEFAULT_CONNECTIVITY_STANZA_NAME, connection_name)
        cio = canary_util.conf_io.ConfIO(APP, ES_CONF_FILENAME)
        conn_stanza = cio.get_stanza(stanza_name)
        host, port = conn_stanza.get('host'), conn_stanza.get('port')

        # port could be zero but currently it is "0" if zero
        if not host or not port:
            errmsg = "ES Proxy not configured correctly in conf host=%s port=%s" %  (host, port)
            logger.error(errmsg)
            raise ESProxyMisconfiguredError(errmsg)

        if port:
            try:
                port_as_int = int(port)
            except ValueError:
                errmsg = "Conf value for Elastic search 'port' not an integer: %s" % port
                logger.error(errmsg)
                raise ESProxyMisconfiguredError from errmsg


        if port_as_int < 0 or port_as_int > 65535:
            errmsg = "Conf value for Elastic search 'port' not a valid port number: %s" % port
            logger.error(errmsg)
            raise ESProxyMisconfiguredError(errmsg)

        protocol = conn_stanza.get('protocol')
        if protocol not in ('http', 'https'):
            errmsg = "Conf value for Elastic search 'protocol' is not http or https: %s" % protocol
            logger.error(errmsg)
            raise ESProxyMisconfiguredError(errmsg)

        apikey =  conn_stanza.get('apikey')
        if apikey:
            try:
                _ = base64.b64decode(apikey)
            except:
                # not echoing value to logs due to security sanity
                errmsg = "Conf value for Elastic search 'apikey' is not valid base64, please correct."
                logger.error(errmsg)
                raise ESProxyMisconfiguredError(errmsg)

        certpath = conn_stanza.get('certpath')
        # While a relative path would "work", it's fragile, and raises
        # questions  about assumptions of path restriction and insane ../..
        # confusion
        if certpath and not os.path.isabs(certpath):
            errmsg = "Conf value for Elastic search 'certpath' is not absolute, please change to an absolute path."
            logger.error(errmsg)
            raise ESProxyMisconfiguredError(errmsg)

        self.es_host, self.es_port = host, port
        self.apikey = apikey
        self.protocol = protocol
        self.certpath = certpath

    def _build_error_response(self, msg, status, formatted_exception=None):
        response_dict = {}
        json_messages = []
        json_messages.append(make_msg(msg, 'ERROR'))
        if formatted_exception:
            json_messages.append(make_msg(formatted_exception, 'INFO'))

        response_body = { 'messages' : json_messages }
        response_dict['status'] = status
        response_dict['payload'] = json.dumps(response_body)
        return response_dict

    def _build_exception_response(self, msg, status, e):
        e_type, e_val, e_tb = sys.exc_info()
        formatted_exception = ''.join(traceback.format_exception(e_type, e_val, e_tb))
        return self._build_error_response(msg, status, formatted_exception)


    def do_esql_search(self, uri, req_body, headers, response_dict, session, json_format):
        """ Perform an elastic search, optionally repackaging the output to
            simulate splunk output"""

        if req_body:
            req_data = json.loads(req_body)
        else:
            req_data = None
        request_headers = dict()
        request_headers.update(headers)
        if self.apikey:
            request_headers['Authorization'] = "ApiKey %s" % (self.apikey,)
        try:

            uri = uri + "?format=json"
            response = session.post(uri, data=json.dumps(req_data), headers=request_headers, verify=False)
        except requests.exceptions.ConnectionError as e:
            response_status = 502 # bad gateway (elastic not available )
            errmsg = "Failed to connect to elasticsearch " + uri

            return self._build_exception_response(errmsg, response_status, e)

        #logger.debug("received %s from elastic", response.status_code)
        #logger.debug(response.text)
        if response.status_code == 200:

            #it is unclear if this is still relevant in ESQL
            query_startpoint = 0
            if req_data:
                query_startpoint = req_data.get('from') # one way to page

        elastic_response = json.loads(response.text)

        # in the async case, for the first responses that only have 'id' and 'is_running'
        # it's of marginal use to convert it to the "splunk style" so for now we just leave it alone
        if json_format == 'splunk_json':
            response_dict["payload"] = sv.convert_elastic_to_splunk_json(elastic_response)
        elif json_format == "splunk_json_cols":
            response_dict["payload"] = sv.convert_elastic_to_splunk_json_cols(elastic_response)

        response_dict["status"] = int(response.status_code)
        return response_dict

    def get_esql_results(self, uri, headers, response_dict, session, json_format='splunk_json'):
        request_headers = {}
        request_headers.update(headers)

        logger.debug("inside get_esql_results")
        if self.apikey:
            request_headers['Authorization'] = "ApiKey %s" % (self.apikey,)

        try:
            uri = uri + "?format=json"
            response = session.get(uri, headers=request_headers, verify=False)
        except requests.exceptions.ConnectionError as e:
            response_status = 502 # bad gateway (elastic not available )
            errmsg = "Failed to connect to elasticsearch " + uri

            return self._build_exception_response(errmsg, response_status, e)

        response_obj = json.loads(response.text)
        #logger.error(json.dumps(response_obj, indent=4))

        if json_format == 'splunk_json':
            output = sv.convert_elastic_to_splunk_json(response_obj)
        elif json_format == "splunk_json_cols":
            output = sv.convert_elastic_to_splunk_json_cols(response_obj)
        else:
            output = "unexpected case"

        response_dict["payload"] = output
        response_dict["status"] = int(response.status_code)
        return response_dict


    def handle(self, in_string):
        """ time to make the donuts """

        params = json.loads(in_string)


        qs_dict = get_query_args(params)

        if "kill" in qs_dict:
            sys.exit()
        response_dict = {
            "headers": {"Content-Type": "application/json"}
        }

        # fetch configuration for connection (or default)
        req_conn = qs_dict.get('es_connection')
        try:
            self._init_es_conninfo(req_conn)
        except ESProxyMisconfiguredError as e:
            response_status = 503 # unavailable
            return self._build_error_response(str(e), response_status)

        try:
            with requests.Session() as sess:

                if self.certpath:
                    sess.verify = certpath

                path_info = params['path_info']
                path_parts = path_info.split('/')

                json_format = qs_dict.get('json_format', "splunk_json")

                # ESQL async API
                if path_info.startswith("_query/async"):


                    req_body = params.get('payload')
                    uri = "%s://%s:%s/%s" % (self.protocol, self.es_host, self.es_port, path_info)

                    if len(path_parts)==2:
                        # the initial POST to start the search
                        if not req_body:
                            return self._build_error_response("No payload", 400, "")

                        logger.info("handling a request to start a new async ES|QL search")
                        req_object = json.loads(req_body)
                        #right now just for simplicity we tell it to never "just return" the results.
                        req_object["wait_for_completion_timeout"] = "0s"
                        req_body = json.dumps(req_object)
                        return self.do_esql_search(uri, req_body, BASE_HEADERS, response_dict, sess, json_format)

                    #otherwise this is passing an ID meaning it's equivalent to a get_results call
                    id=path_parts[2]
                    logger.info("handling a GET request in the async ES|QL API, for id=%s", id)
                    return self.get_esql_results(uri, BASE_HEADERS, response_dict, sess, json_format=qs_dict.get("json_format", "splunk_json"))


                # ESQL but not the async API.
                elif len(path_parts)==1 and path_parts[0] == '_query':

                    logger.info("handling a synchronous ES|QL request")
                    # assume this is a index/documenttype search request
                    req_body = params.get('payload')

                    uri = "%s://%s:%s/%s" % (self.protocol, self.es_host, self.es_port, path_info)
                    response_dict = self.do_esql_search(uri, req_body, BASE_HEADERS, response_dict, sess, json_format)

                    return response_dict

                else :
                    # Versions before April 2024 had various complex things here. But we have switched to
                    # ESQL or bust.
                    raise ValueError("the path submitted did not match any known case.  path=" + path_info)

        except Exception as e:
            response_status = 500 # server error
            errmsg = "ES Proxy encountered an unexpected error"
            return self._build_exception_response(errmsg, response_status, e)
