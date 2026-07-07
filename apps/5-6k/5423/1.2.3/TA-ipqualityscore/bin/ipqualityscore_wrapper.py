import concurrent.futures
import json
import time
import urllib.parse
import tempfile
import re

import requests

from IPQualityScore.DBReader import DBReader
from constants import IP_REG, IPv6_REG

class CustomResponse:
    def __init__(self, json_data):
        json_data['success'] = True
        json_data['message'] = "Success"
        json_data['from_db_file'] = True

        temp_keys = list(json_data.keys())
        for key in temp_keys:
            if '_IPQSRecord__' in key:
                new_key = key.replace('_IPQSRecord__', '')
                json_data[new_key] = json_data.pop(key)

        self._json = self.remove_non_serializable(json_data)
    
    def json(self):
        return self._json
    
    def remove_non_serializable(self, obj):
        """Remove non-serializable elements from the object."""
        if isinstance(obj, dict):
            return {k: self.remove_non_serializable(v) for k, v in obj.items() if self.is_serializable(v)}
        elif isinstance(obj, list):
            return [self.remove_non_serializable(i) for i in obj if self.is_serializable(i)]
        return obj

    def is_serializable(self, value):
        """Check if value is a serializable."""
        try:
            json.dumps(value)
            return True
        except (TypeError, OverflowError):
            return False

    @property
    def status_code(self):
        return 200

class IPQualityScoreWrapper:
    def __init__(self, api_key, base_url, logger):
        """
        Wrapper for handling multithreaded requests to IPQualityScore API for detecting VPN/Proxy,
        validating emails, URLs, phone numbers, and detecting dark web leaks.

        Methods:
            request_get(): Sends a GET request.
            request_post(): Sends a POST request.
            ip_detection_multithreaded(): Detects proxy/VPN for multiple IPs.
            email_validation_multithreaded(): Validates multiple emails.
            url_checker_multithreaded(): Checks multiple URLs.
            phone_validation_multithreaded(): Validates multiple phone numbers.
            dark_web_leak_multithreaded(): Detects dark web leaks for multiple inputs.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.logger = logger
        self.api_endpoints = {
            "ip_detection": "api/json/ip",
            "email_validation": "api/json/email",
            "url_checker": "api/json/url",
            "phone_validation": "api/json/phone",
            "dark_web_leak": "api/json/leaked",
        }
        self.ipv4_client = None
        self.ipv6_client = None


    def get_ipqs_db_file_contents(self, url):
        """Gets file contents from the specified URL."""

        try:
            response = requests.get(url)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False)

                # Write the content of the response to the temporary file
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                
                # Get the path of the temporary file
                temp_file_path = temp_file.name
                temp_file.close()

                ipqs_ip_client = DBReader(temp_file_path)
                return ipqs_ip_client
            else:
                self.logger.error(f"Error downloading IPQS DB file: Status code {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting IPQS DB file contents: {e}")
            return None


    def _log_request(self, url, start_time):
        """Logs the request with the time taken."""
        end_time = time.time()
        self.logger.info(f"URL: {url}, Time taken: {end_time - start_time:.2f} sec")

    def request_get(self, url):
        """Handles GET requests."""
        start_time = time.time()
        resp = requests.get(url, params={"plugin_source": "splunk"})
        self._log_request(url, start_time)
        return resp

    def request_post(self, url, payload):
        """Handles POST requests."""

        # logic only for ip indicators to check results in db file; if found else fetch results from API.
        if "api/json/ip" in url:
            self.logger.info(f"URL {url} payload: {payload}")
            ip_client = None
            ip = payload.get('ip')
            if re.fullmatch(IP_REG, ip):
                ip_client = self.ipv4_client
            elif re.fullmatch(IPv6_REG, ip):
                ip_client = self.ipv6_client
            ip_in_db_file = False

            try:
                ip_db_object = ip_client.Fetch(ip)
                ip_in_db_file = True
            except Exception as e:
                self.logger.error(f"Error fetching IP from DB file: {e};  fetching from API...")

            if ip_in_db_file:
                return CustomResponse(ip_db_object.__dict__)
            
        start_time = time.time()
        headers = {"Accept": "application/json", "IPQS-KEY": self.api_key}
        resp = requests.post(url, headers=headers, params={"plugin_source": "splunk"}, data=payload)
        self._log_request(url, start_time)
        return resp

    def _execute_requests(self, urls, payloads=None, method="POST"):
        """Handles multithreaded execution of requests."""
        self.logger.info(f"Payloads: {payloads}")
        with concurrent.futures.ThreadPoolExecutor(max_workers=500) as executor:
            if method == "POST":
                res = [
                    executor.submit(self.request_post, url, payloads[i])
                    for i, url in enumerate(urls)
                ]
            else:
                res = [executor.submit(self.request_get, url) for url in urls]
            concurrent.futures.wait(res)
        self.logger.info(f"Total responses received: {str(len(res))}")
        return res

    def _process_results(self, res, identifiers):
        """Processes the results from the API responses."""
        results_dict = {}
        for i, identifier in enumerate(identifiers):
            resp = res[i].result()
            if resp.status_code == 200:
                self.logger.info(
                    f"{identifier}: API Call success, response: {json.dumps(resp.json())}"
                )
                results_dict[identifier] = resp.json()
        return results_dict

    def ip_detection_multithreaded(
        self,
        ips,
        strictness,
        allow_public_access_points,
        fast,
        lighter_penalties,
        mobile,
        user_agent,
        user_language,
        transaction_strictness,
        ipv4_db_file,
        ipv6_db_file
    ):
        """Handles multithreaded IP detection."""
        urls = [self.base_url + self.api_endpoints["ip_detection"] for _ in ips]
        payloads = [
            {
                **({"ip": ip} if ip else {}),
                **({"strictness": strictness} if strictness is not None else {}),
                **(
                    {
                        "allow_public_access_points": str(
                            allow_public_access_points
                        ).lower()
                    }
                    if allow_public_access_points is not None
                    else {}
                ),
                **({"fast": str(fast).lower()} if fast is not None else {}),
                **(
                    {"lighter_penalties": str(lighter_penalties).lower()}
                    if lighter_penalties is not None
                    else {}
                ),
                **({"mobile": str(mobile).lower()} if mobile is not None else {}),
                **(
                    {"transaction_strictness": transaction_strictness}
                    if transaction_strictness is not None
                    else {}
                ),
                **({"user_agent": user_agent} if user_agent else {}),
                **({"user_language": user_language} if user_language else {}),
            }
            for ip in ips
        ]

        if ipv4_db_file:
            self.ipv4_client = self.get_ipqs_db_file_contents(ipv4_db_file)
        if ipv6_db_file:
            self.ipv6_client = self.get_ipqs_db_file_contents(ipv6_db_file)

        res = self._execute_requests(urls, payloads)
        return self._process_results(res, ips)

    def email_validation_multithreaded(
        self,
        emails,
        fast,
        timeout,
        suggest_domain,
        strictness,
        abuse_strictness,
    ):
        """Handles multithreaded email validation."""
        urls = [self.base_url + self.api_endpoints["email_validation"] for _ in emails]
        payloads = [
            {
                **({"email": email} if email else {}),
                **({"fast": str(fast).lower()} if fast is not None else {}),
                **({"timeout": timeout} if timeout is not None else {}),
                **(
                    {"suggest_domain": str(suggest_domain).lower()}
                    if suggest_domain is not None
                    else {}
                ),
                **({"strictness": strictness} if strictness is not None else {}),
                **(
                    {"abuse_strictness": abuse_strictness}
                    if abuse_strictness is not None
                    else {}
                ),
            }
            for email in emails
        ]
        res = self._execute_requests(urls, payloads)
        return self._process_results(res, emails)

    def url_checker_multithreaded(self, links, strictness, fast, timeout):
        """Handles multithreaded URL checking."""
        urls = [self.base_url + self.api_endpoints["url_checker"] for _ in links]
        payloads = [
            {
                **({"url": urllib.parse.quote_plus(link)} if link else {}),
                **({"strictness": strictness} if strictness is not None else {}),
                **({"fast": str(fast).lower()} if fast is not None else {}),
                **({"timeout": timeout} if timeout is not None else {}),
            }
            for link in links
        ]
        res = self._execute_requests(urls, payloads)
        return self._process_results(res, links)

    def phone_validation_multithreaded(
        self,
        phones,
        country,
        strictness,
        enhanced_line_check,
        enhanced_name_check,
    ):
        """Handles multithreaded phone validation."""
        urls = [self.base_url + self.api_endpoints["phone_validation"] for _ in phones]
        payloads = [
            {
                **({"phone": phone} if phone else {}),
                **({"strictness": strictness} if strictness is not None else {}),
                **({"country": [country]} if country is not None else {}),
                **(
                    {"enhanced_line_check": enhanced_line_check}
                    if enhanced_line_check is not None
                    else {}
                ),
                **(
                    {"enhanced_name_check": enhanced_name_check}
                    if enhanced_name_check is not None
                    else {}
                ),
            }
            for phone in phones
        ]

        res = self._execute_requests(urls, payloads)
        return self._process_results(res, phones)

    def dark_web_leak_multithreaded(self, inputs, input_type):
        """Handles multithreaded Dark Web leak detection."""
        urls = [
            f"{self.base_url}{self.api_endpoints['dark_web_leak']}/{input_type}/{self.api_key}/{urllib.parse.quote_plus(obj)}"
            for obj in inputs
        ]
        res = self._execute_requests(urls, method="GET")
        return self._process_results(res, inputs)
