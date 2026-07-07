import http.server
import socketserver
import json
import sys
import os
import requests
import time

# Configuration
PORT = 8888
# Default to secure.sysdig.com if not provided
UPSTREAM_BASE_URL = os.environ.get("SYSDIG_UPSTREAM_URL", "https://secure.sysdig.com").rstrip('/')
FAIL_COUNT = 3  # Number of 429s to simulate before succeeding

print(f"--- Sysdig Rate Limit Proxy ---")
print(f"Listening on: https://localhost:{PORT}")
print(f"Upstream:     {UPSTREAM_BASE_URL}")
print(f"Behavior:     Returns 429 for the first {FAIL_COUNT} requests, then proxies to Upstream.")

class MockSysdigHandler(http.server.BaseHTTPRequestHandler):
    # Class variable to track requests across instances
    request_count = 0

    def do_proxy(self, method):
        MockSysdigHandler.request_count += 1
        print(f"\n[Proxy] Request #{MockSysdigHandler.request_count} received: {method} {self.path}")

        # 1. Simulate Rate Limit
        if MockSysdigHandler.request_count <= FAIL_COUNT:
            print(f"[Proxy] -> SIMULATING 429 Too Many Requests ({MockSysdigHandler.request_count}/{FAIL_COUNT})")
            self.send_response(429)
            self.send_header('Content-Type', 'application/json')
            
            # Sysdig specific headers (Epoch timestamp)
            # Set reset time to 2 seconds from now
            reset_time = int(time.time() + 2)
            self.send_header('x-ratelimit-limit', '100')
            self.send_header('x-ratelimit-remaining', '0')
            self.send_header('x-ratelimit-reset', str(reset_time))
            
            # We omit standard Retry-After to force sysdig_core.py to use x-ratelimit-reset
            self.end_headers()
            
            error_response = {
                "errors": [
                    {"message": "Simulated Rate limit exceeded", "reason": "Too Many Requests"}
                ]
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
            return

        # 2. Proxy to Real Upstream
        upstream_url = f"{UPSTREAM_BASE_URL}{self.path}"
        print(f"[Proxy] -> Forwarding to: {upstream_url}")

        # Construct headers
        headers = {key: val for key, val in self.headers.items()}
        # Remove Host header so upstream doesn't get confused
        if 'Host' in headers:
            del headers['Host']

        # Get Body if present
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else None

        # Reset request count so the next sequence of requests starts failing again
        MockSysdigHandler.request_count = 0

        try:
            resp = requests.request(
                method=method,
                url=upstream_url,
                headers=headers,
                data=post_body,
                allow_redirects=False, # Let the client handle redirects if needed
                timeout=30
            )

            print(f"[Proxy] <- Upstream responded: {resp.status_code}")

            # Forward Status
            self.send_response(resp.status_code)

            # Forward Headers
            for k, v in resp.headers.items():
                # Skip hop-by-hop headers
                if k.lower() not in ['transfer-encoding', 'content-encoding', 'connection', 'keep-alive']:
                    self.send_header(k, v)
            self.end_headers()

            # Forward Body
            self.wfile.write(resp.content)

        except Exception as e:
            print(f"[Proxy] Error forwarding request: {e}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(b"Bad Gateway: Error communicating with upstream Sysdig")

    def do_GET(self):
        self.do_proxy("GET")

    def do_POST(self):
        self.do_proxy("POST")

    def do_PUT(self):
        self.do_proxy("PUT")
        
    def do_DELETE(self):
        self.do_proxy("DELETE")

if __name__ == "__main__":
    import ssl
    
    # Paths to certs (relative to this script)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    CERT_FILE = os.path.join(BASE_DIR, "server.pem")
    KEY_FILE = os.path.join(BASE_DIR, "server.key")

    socketserver.TCPServer.allow_reuse_address = True
    try:
        print(f"Loading certs from: {BASE_DIR}")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
        
        with socketserver.TCPServer(("", PORT), MockSysdigHandler) as httpd:
            httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
            print(f"HTTPS Server listening on port {PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")