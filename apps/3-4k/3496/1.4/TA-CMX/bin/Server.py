#!/usr/bin/env python


import socket
import sys
import threading
import atexit
import BaseHTTPServer
import SimpleHTTPServer
import ssl
from splunk_http_event_collector import HttpEventCollector
from CMXUtil import *
from splunk.clilib import cli_common as cli

splunk_home = os.environ['SPLUNK_HOME']

logger = get_logger("SERVER")

session_key = sys.stdin.readline().strip()


class HttpEventListner:
    inputargs = {}
    certFile = splunk_home + '/etc/auth/cacert.pem'
    certKey = splunk_home + '/etc/auth/ca.pem'
    testevent = None

    '''
            Read all the configuration from the cmxsetup.conf file.
    '''

    def __init__(self):

        self.inputargs = get_cmx_conf(session_key)
        self.inputargs["SPHOST"] = "127.0.0.1"

        http_ec_key = get_hec_credentials(session_key)

        if not(http_ec_key):
            self.inputargs = cli.getConfStanza('cmxsetup', 'setupentity')
            http_ec_key = self.inputargs["HTTPECKEY"]
            user_name = "hec-token"
            postArgs = {
                "name": user_name,
                "password": http_ec_key,
                "realm": "TA-CMX-HEC"
            }
            r = splunk.rest.simpleRequest("/servicesNS/nobody/TA-CMX/storage/passwords/?output_mode=json",
                                          session_key, postargs = postArgs, method = 'POST')
            if not (200 <= int(r[0]["status"]) <= 300):
                logger.error("Unable to create  password for HEC")
            else:
                logger.info("Stored HEC token to storage/password")

        HttpEventListner.testevent = HttpEventCollector(token = http_ec_key,
                                                        http_event_server = self.inputargs["SPHOST"],
                                                        http_event_port = self.inputargs["HTTPSPEC"],
                                                        http_event_server_ssl = True)



    # Start event payload and add the metadata information

    '''
        This method will start listening on user defined port (HTTPECPORT) for HTTP Events.
        On receiving events, it pulls out data
        and put it in the queue for forwarding to Splunk.
    '''

    def start_listening_for_http(self):

        # Standard socket stuff:

        host = ''  # do we need socket.gethostname() ?
        port = int(self.inputargs["HTTPECPORT"])
        sock = None
        try:

            httpd = BaseHTTPServer.HTTPServer(('', port), SimpleHTTPServer.SimpleHTTPRequestHandler)
            sock = ssl.wrap_socket(httpd.socket, certfile = self.certFile, keyfile = self.certKey,
                                   server_side = True, do_handshake_on_connect = True)

            sock.listen(1)  # don't queue up any requests

        except:
            logger.error("Error in binding to socket", exc_info = True)

        # Loop forever, listening for requ  ests:
        while True:
            try:
                csock, caddr = sock.accept()
                req = csock.recv(65535)  # get the request, 1kB max

                str_data_array = req.splitlines()

                # Start event payload and add the metadata information
                payload = {}
                payload.update({"index": self.inputargs["INDEX"]})
                payload.update({"sourcetype": self.inputargs["SOURCETYPE"]})

                if len(str_data_array) > 1:
                    payload.update({"event": json.loads(str_data_array[len(str_data_array) - 1])})
                    HttpEventListner.testevent.batch_event(payload)

            except Exception:
                logger.error("Error No JSON FOUND", exc_info = True)

                # Look in the first line of the request for a move command
                # A move command should be e.g. 'http://server/move?a=90'
            csock.sendall("""HTTP/1.0 200 OK
        Content-Type: text/html

        <html>
        <head>
        <title>Success</title>
        </head>
        <body>
        Success!
        </body>
        </html>
        """)
            csock.close()

    '''
        This function is used to flush out any remaining events from the queue.

    '''

    def exit_handler(self):
        HttpEventListner.testevent.flush_batch()


if __name__ == '__main__':
    httpeventlistner = HttpEventListner()
    atexit.register(httpeventlistner.exit_handler)
    for x in range(int(httpeventlistner.inputargs["NOOFTHREADS"])):
        t = threading.Thread(target = httpeventlistner.start_listening_for_http())
        t.daemon = True
        t.start()
