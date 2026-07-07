try:
    # Python 2
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
    from urlparse import parse_qs

except ImportError:
    # Python 3
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import parse_qs

    unicode = str

import sys
import os
import traceback
import hmac, hashlib
import json
import time
import ssl
import errno
import re

confidential_re = re.compile("(pwd=|(?:^|[. ])(password|secret)(?:[. ]|$))")
def redact_confidential_info(data):
    if "operator" in data.get("payload", {}):
        del data["payload"]["operator"]
    if "operator_id" in data.get("payload", {}):
        del data["payload"]["operator_id"]
    new_dict = {}
    for k,v in data.items():
        if confidential_re.search(k) is None:
            if isinstance(v,str) and confidential_re.search(v) is not None: continue
            new_dict[k] = v
            if isinstance(v, dict):
                new_dict[k] = redact_confidential_info(v)
    return new_dict

class LogRequestsInSplunkHandler(BaseHTTPRequestHandler):

    def handle_request(self):
        try:
            post_body = b""
            content_len = int(self.headers.get('content-length', 0))

            if content_len > 0:
                post_body = self.rfile.read(content_len)

            if self.server.dump_requests:
                self.server.logger.info("(POST body, POST headers): (%s, %s)", post_body, self.headers)

            content_type = self.headers.get('content-type', '')
            if not content_type.startswith('application/json'):
                self.write_response(400, {"success": False, "error": "Unsupported Content-Type"})
                return

            if not post_body:
                self.write_response(400, {"success": False, "error": "Empty request body"})
                return

            try:
                json_body = json.loads(post_body)
            except (json.JSONDecodeError, ValueError):
                self.write_response(400, {"success": False, "error": "Invalid JSON in request body"})
                return

            if json_body.get("event") == "endpoint.url_validation":
                resp = self.handle_validation(json_body)
                self.write_response(200, resp)
            elif self.server.disable_verification or self.is_valid(post_body, self.headers):
                if not self.server.disable_redaction:
                    json_body = redact_confidential_info(json_body)
                self.server.output_results(json_body, self.client_address[0])
                self.write_response(200, {"success": True})
            else:
                self.write_response(403, {"success": False, "error": "Signature mismatch occurred"})
                self.server.logger.error("Signature mismatch occurred. Events most likely coming from unknown source, dropping them.")

        except Exception:
            self.server.logger.error("JWT web hook handle_request error: %s", traceback.format_exc())
            try:
                self.write_response(500, {"success": False, "error": "Internal server error"})
            except Exception:
                self.server.logger.error("Failed to return a 500 response: %s", traceback.format_exc())

    def write_json(self, json_dict):
        content = json.dumps(json_dict)

        if isinstance(content, unicode):
            content = content.encode('utf-8')

        self.wfile.write(content)

    def do_GET(self):
        self.write_response(200, {"success": True})

    def do_HEAD(self):
        self.write_response(405, {"success": False})

    def read_file(self, length):
        return self.rfile.read(length)

    def do_POST(self):
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

    def write_response(self, status_code, json_body):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.write_json(json_body)

    def handle_validation(self, json_body):
        SECRET_TOKEN = self.server.zoom_secret
        data = json_body.get("payload", {}).get("plainToken")

        signature = hmac.new(bytes(SECRET_TOKEN, 'utf-8'), msg=bytes(data, 'utf-8'), digestmod=hashlib.sha256)
        resp = {
            "plainToken": data,
            "encryptedToken": signature.hexdigest()
        }
        return resp

    def is_valid(self, raw_body, headers):
        SECRET_TOKEN = self.server.zoom_secret
        body_str = raw_body.decode('utf-8') if isinstance(raw_body, bytes) else raw_body
        data = "v0:{}:{}".format(headers.get("x-zm-request-timestamp"), body_str)
        signature = hmac.new(bytes(SECRET_TOKEN, 'utf-8'), msg=bytes(data, 'utf-8'), digestmod=hashlib.sha256).hexdigest()
        signature_to_compare = headers.get("x-zm-signature")
        return hmac.compare_digest(signature_to_compare, "v0={}".format(signature))


class WebServer:
    """
    This class implements an instance of a web-server that listens for incoming webhooks.
    """

    MAX_ATTEMPTS_TO_START_SERVER = 5

    def __init__(self, output_results, port, zoom_secret, disable_verification, disable_redaction, dump_requests, cert_file=None, key_file=None, logger=None, cipher_suite=None):

        # Make an instance of the server
        server = None
        attempts = 0

        while server is None and attempts < WebServer.MAX_ATTEMPTS_TO_START_SERVER:
            try:
                server = HTTPServer(('', port), LogRequestsInSplunkHandler)
            except IOError as exception:

                # Log a message noting that port is taken
                if logger is not None:
                    logger.info('The web-server could not yet be started, attempt %i of %i, reason="%s", pid="%r"',
                                attempts, WebServer.MAX_ATTEMPTS_TO_START_SERVER, str(exception), os.getpid())

                    time.sleep(3)

                server = None
                attempts = attempts + 1

        # Stop if the server could not be started
        if server is None:

            # Log that it couldn't be started
            if logger is not None:
                logger.info('The web-server could not be started, pid="%r"', os.getpid())

            # Stop, we weren't successful
            return

        # Save the parameters
        server.output_results = output_results
        server.logger = logger
        server.zoom_secret = zoom_secret
        server.disable_verification = disable_verification
        server.disable_redaction = disable_redaction
        server.dump_requests = dump_requests

        # SSL socket is required on this TA, throw exception if cert file is missing
        if cert_file is not None:
            ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=cert_file, keyfile=key_file, password=None)
            ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Disable TLSv1 and TLSv1.1

            if cipher_suite is not None:
                try:
                    ssl_context.set_ciphers(cipher_suite)
                except Exception:
                    if logger is not None:
                        logger.error("bad cipher suite: {}".format(cipher_suite))

            server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        else:
            raise Exception('Server certificate is missing.')

        # Keep a server instance around
        self.server = server

    def start_serving(self):
        """
        Start the server.
        """

        try:
            self.server.serve_forever()
        except IOError as exception:
            if self.server.logger is not None:
                if exception.errno == errno.EPIPE:
                    # Broken pipe: happens when the input shuts down or when remote peer disconnects
                    pass
                else:
                    self.server.logger.warn("IO error when serving the web-server: %s", str(exception))

    def stop_serving(self):
        """
        Stop the server.
        """

        self.server.shutdown()

        # https://lukemurphey.net/issues/1908
        if hasattr(self.server, 'socket'):
            self.server.socket.close()
