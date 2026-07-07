
# encoding = utf-8

try:
    # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from urlparse import parse_qs

except:
    # Python 3
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs
    unicode = str

import os
from socket import timeout
import sys
import time
import datetime
import json
import ssl
import time
import re
import json
import errno
import collections
from threading import Thread
from cgi import parse_header, parse_multipart

import import_declare_test

from splunklib import modularinput as smi


bin_dir = os.path.basename(__file__)

'''
'''
import import_declare_test

import os.path as op

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi


KEEP_RUNNING = True
def keep_running():
    return KEEP_RUNNING

def wildcard_to_re(wildcard):
    """
    Convert the given wildcard to a regular expression.

    Arguments:
    wildcard -- A string representing a wild-card (like "/some_path/*")
    """

    regex_escaped = re.escape(wildcard)
    return regex_escaped.replace('\*', ".*")

class LogRequestsInSplunkHandler(BaseHTTPRequestHandler):
        
        def handle_request(self):
           
            try:
                query_args = {}
            
                # Get the simple path (without arguments)
                if self.path.find("?") < 0:
                    query = ""
                else:
                    query = self.path[self.path.find("?")+1:]
                    self.server.helper.log_debug("Webhook query: %s" % str(query))
        
                if query is not None and query != "":
                    query_args_from_path = parse_qs(query, keep_blank_values=True)
                    query_args_from_path.update(query_args)
                    query_args = query_args_from_path
            
                # Make the resulting data
                post_body = ""
            
                # Get the content-body
                content_len = int(self.headers.get('content-length', 0))
                
                # If content was provided, then parse it
                if content_len > 0:
                    post_body = json.loads(self.rfile.read(content_len))
                
                '''
                If there is a validationToken parameter in the query string, 
                then this is the request that Office 365 sends to check that this is a valid endpoint.
                Just send the validationToken back.
                '''
                if 'validationToken' in query_args:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain')
                    self.send_header('Connection','close')
                    self.end_headers()
                    self.write_text(query_args['validationToken'][0])
                    global KEEP_RUNNING
                    KEEP_RUNNING = False
                elif content_len > 0:
                    # Send Event to Splunk via event_writer
                    try:
                        self.server.output_results(post_body, self.client_address[0])
                        self.send_response(202)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Connection','close')
                        self.end_headers()
                        self.write_json({"success":True})
                    except Exception as ex:
                        self.server.helper.log_error("Could not write event to Splunk. Content: %s, exception: %s" % (str(post_body), str(ex)))
                    
            except Exception as ex:
                self.server.helper.log_error("Webhook handle_request error: %s" % str(ex))
        
        def write_json(self, json_dict):
            content = json.dumps(json_dict)
    
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            
            self.wfile.write(content)
    
        def write_text(self, content):
    
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            
            self.wfile.write(content)
    
        def do_GET(self):
            self.server.helper.log_debug("Processing GET")
            self.handle_request()
    
        def do_HEAD(self):
            self.server.helper.log_debug("Processing HEAD")
            self.handle_request()
    
        def read_file(self, length):
            return self.rfile.read(length)
            
        def do_POST(self):
            self.server.helper.log_debug("Processing POST")
            self.handle_request()
    
        def convert_list_entries(self, args_list):
            updated_list = []
            modified = False
    
            for entry in args_list:
                if sys.version_info.major >= 3 and isinstance(entry, bytes):
                    updated_list.append(entry.decode('utf-8'))
                    modified = True
                else:
                    updated_list.append(entry)
    
            return updated_list, modified

class ModInputteams_webhook(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputteams_webhook, self).__init__("ta_ms_teams", "teams_webhook", use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputteams_webhook, self).get_scheme()
        scheme.title = ("Teams Webhook (Deprecated)")
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
        scheme.add_argument(smi.Argument("webhook_port", title="Port",
                                         description="Port for the webhook",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("webhook_path", title="Path",
                                         description="A wildcard that the path of requests must match (paths generally begin with a \"/\" and can include a wildcard)",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("cert_file", title="SSL Certificate File",
                                         description="The path to the SSL certificate file (if you want to use encryption); typically uses .DER, .PEM, .CRT, .CER file extensions",
                                         required_on_create=False,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("key_file", title="SSL Certificate Key File",
                                         description="The path to the SSL certificate key file (if the certificate requires a key); typically uses .KEY file extension",
                                         required_on_create=False,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA_MS_Teams"

    def validate_input(helper, definition):
        pass
    
    
    

    def collect_events(helper, ew):
        
        def output_results(payload, clientip):
            event = helper.new_event(
                    data=json.dumps(payload),
                    time="%.3f" % time.time(),
                    host=clientip,
                    index=helper.get_output_index(),
                    source=helper.input_type)
            ew.write_event(event)
    
            # If this is a call record, write it to Splunk
            if (("value" in payload) and ("resourceData" in payload["value"][0]) and ("id" in payload["value"][0]["resourceData"])):
    
                # Save the callRecord ID to a check point dir,
                # so a mod input can index the callRecords
                try:
                    check_point_dir = helper.context_meta["checkpoint_dir"]
                    call_record_id = payload["value"][0]["resourceData"]["id"]
                    call_record_file = os.path.join(check_point_dir, call_record_id)
                    open(call_record_file, "a+")
                        
                except Exception as e:
                    helper.log_error("Could not save check point: %s, Payload: %s" % (str(e), str(payload)))
                    raise e
    
        port = int(helper.get_arg("webhook_port"))
        key_file = helper.get_arg("key_file")
        cert_file = helper.get_arg("cert_file")
        path = helper.get_arg("webhook_path")
        
        # Convert the path to a regular expression
        if path is not None and path != "":
            path_re = wildcard_to_re(path)
        else:
            path_re = None
        
        MAX_ATTEMPTS_TO_START_SERVER = 5
    
        # Make an instance of the server
        server = None
        attempts = 0
    
        while server is None and attempts < MAX_ATTEMPTS_TO_START_SERVER:
            try:
                server = HTTPServer(('', port), LogRequestsInSplunkHandler)
            except IOError as exception:
                helper.log_info('The web-server could not yet be started, attempt %i of %i, reason="%s", pid="%r"' % (attempts, MAX_ATTEMPTS_TO_START_SERVER, str(exception), os.getpid()))
                time.sleep(3)
                server = None
                attempts = attempts + 1
    
        if server is None:
            # Log that it couldn't be started
            helper.log_info('The web-server could not be started, pid="%r"' % os.getpid())
            return
    
        server.path = path
        server.helper = helper
        server.output_results = output_results
        server.KEEP_RUNNING = KEEP_RUNNING
    
        # Setup a SSL socket if necessary
        if cert_file is not None and cert_file != "":
            server.socket = ssl.wrap_socket(server.socket, certfile=cert_file, keyfile=key_file, server_side=True)
    
        # Start the web-server
        helper.log_info("Starting server on port=%r, path=%r, cert_file=%r, key_file=%r, stanza=%s, pid=%r" % (port, path_re, cert_file, key_file, helper.get_input_stanza_names(), os.getpid()))
        try:
            server.timeout = 3600
            server.handle_timeout = lambda: (_ for _ in ()).throw(TimeoutError())
            while keep_running():
                server.handle_request()
        except TimeoutError:
            # The timeout fired, so stop the webserver
            pass
        except IOError as exception:
            if exception.errno == errno.EPIPE:
                # Broken pipe: happens when the input shuts down or when remote peer disconnects
                pass
            else:
                helper.log_error("IO error when serving the web-server: %s" % str(exception))
        except Exception as ex:
            helper.log_error("__Splunk__ Error: %s" % str(ex))
        
        helper.log_info("Successfully Exited server on port=%r, path=%r, cert_file=%r, key_file=%r, stanza=%s, pid=%r" % (port, path_re, cert_file, key_file, helper.get_input_stanza_names(), os.getpid()))

    def get_account_fields(self):
        account_fields = []
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
    exitcode = ModInputteams_webhook().run(sys.argv)
    sys.exit(exitcode)
