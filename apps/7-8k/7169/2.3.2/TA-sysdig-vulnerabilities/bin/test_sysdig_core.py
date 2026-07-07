import json
import os
import requests
import sysdig_core

def new_event(fulltag, data):
    print("NEW EVENT")
    print(fulltag)
    print(json.dumps(data, indent=2))
    print("----------------------")


class MockRestHelper:
    def __init__(self):
        self.http_session = requests.Session()

    def _init_request_session(self, proxy_uri=None):
        pass

class Helper:
    def __init__(self):
        self.rest_helper = MockRestHelper()

    def _get_proxy_uri(self):
        return None

    def get_proxy(self):
        print("GETTING PROXY")
        return {}

    def get_app_name(self):
        return "TA-sysdig-vulnerabilities"

    def log_debug(self, msg):
        print("DEBUG:" + msg)

    def log_info(self, msg):
        print("INFO: " + msg)

    def log_warning(self, msg):
        print("WARNING: " + msg)

    def log_error(self, msg):
        print("ERROR: " + msg)

    def send_http_request(self, url, method, headers, verify, timeout, use_proxy, payload=None):
        """
        Replacement for the Splunk helper send_http_request method.
        This function makes real network calls using the requests library.

        Args:
            url (str): The URL to send the HTTP request to.
            method (str): The HTTP method (e.g., "GET", "POST", etc.).
            headers (dict): HTTP headers to include in the request.
            verify (bool): Whether to verify the SSL certificate.
            timeout (tuple): A tuple (connect_timeout, read_timeout).
            use_proxy (bool): This parameter is included for compatibility; proxy support is not implemented.

        Returns:
            requests.Response: The response object returned by the requests library.
        """
        # Ignoring proxy support for now. If needed, add logic to set up proxies.
        proxies = None

        try:
            response = self.rest_helper.http_session.request(
                method=method,
                url=url,
                headers=headers,
                verify=verify,
                timeout=timeout,
                proxies=proxies,
                data=payload
            )
            return response
        except requests.exceptions.RequestException as e:
            # Log or handle exceptions as required
            print("HTTP request failed:", e)
            raise

if __name__ == "__main__":
    sdc_url = os.getenv("SYSDIG_URL")
    token = os.getenv("SYSDIG_TOKEN")
    nvd_api_key = os.getenv("NVD_API_KEY")
    helper = Helper()
    sysdig_core.configure_retries(helper)
    sysdig_core.fetch_vulnerabilities(sdc_url, token, nvd_api_key, ['vuln_description', 'nvd_data', 'package_data'], max_images=100, new_event=new_event, helper=helper)