import json
import requests
import time
import datetime

class APIv4:
    RECORDS_PER_PAGE = "50"
    MIN_SLEEP_TIME = 60
    MAX_SLEEP_TIME = 600
    SLEEP_TIME_MINUTES = 5
    MAX_RETRIES = 3

    def __init__(self, api_key, region, proxy, helper):
        self.base_url = "https://{}.api.insight.rapid7.com/vm/v4/integration".format(region)
        self.headers = {
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "User-Agent": "r7:TA-rapid7-insightvm/1.5.0"
        }
        self.helper = helper
        self.proxies = None

        if proxy:
            if proxy.get("proxy_url") and proxy.get("proxy_port"):
                proxy_url = f"{proxy.get('proxy_url')}:{proxy.get('proxy_port')}" if proxy.get('proxy_url').startswith("http") \
                     else f"http://{proxy.get('proxy_url')}:{proxy.get('proxy_port')}"
            
                self.proxies = {"http": proxy_url, "https": proxy_url}
                helper.log_info(f"Proxy configuration: {self.proxies}")
            else:
                helper.log_warning("A proxy misconfiguration has been detected. Ensure both host and port are set")

    def req(self, endpoint, body, current_time=None, comparison_time=None, import_vulns=True, include_same=True, next_link=None):
        if not next_link:
            params = {
                "size": self.RECORDS_PER_PAGE,
                "page": "0",
            }

            if import_vulns:    
                params["comparisonTime"] = comparison_time
                params["currentTime"] = current_time
                if include_same:
                    params["includeSame"] = include_same
            
            url = "{}/{}".format(self.base_url, endpoint)
            self.helper.log_info("Parameters: {}, Body: {}".format(str(params), str(body)))
        else:
            params = {}
            url = next_link
            self.helper.log_info("Url: {}, Body: {}".format(str(url), str(body)))

        try:
            response = requests.post(
                url=url,
                params=params,
                headers=self.headers,
                data=json.dumps(body),
                proxies=self.proxies)
        except requests.exceptions.RequestException as e:
            self.helper.log_error("HTTP Request failed {}".format(e))
            return
        
        self.helper.log_info("Response HTTP Status Code: {}".format(response.status_code))

        return response

    def send_req(self, endpoint, data, process_result_page, current_time=None, comparison_time=None, import_vulns=True, 
            include_same=False):
        count = 1
        num_retries = 0
        total_processed = 0
        success = True
        prev_total_resources = -1
        has_logged_sync_error = False
        next_link = None

        while True:
            response = self.req(endpoint, data, current_time, comparison_time, import_vulns, include_same, next_link)
            
            if response and response.status_code == 401:
                self.helper.log_error("Unauthorized error. Please check to ensure your configuration is using a valid"
                                     " InsightVM API organization key")
                success = False
                break
            elif response and response.status_code == 400 and ( data.get("asset") or data.get("vulnerability") ):
                filter_strings = []
                filter_str = ", "
                if data.get("asset"): filter_strings.append("'asset': '{}'".format(data.get("asset")))
                if data.get("vulnerability"): filter_strings.append("'vulnerability': '{}'".format(data.get("vulnerability")))
                filter_str = filter_str.join(filter_strings)
                self.helper.log_error("The request to the InsightVM API failed due to an improper filter defined. "
                                      "The filter(s) defined currently are {}. Please review the filter(s) and ensure it follows "
                                      "the correct formatting documented on the Rapid7 help pages: "
                                      "https://docs.rapid7.com/insightvm/insightvm-technology-add-on-for-splunk/#insightvm-asset-import".format(filter_str))
                success = False
                break
            elif response is None or response.status_code < 200 or response.status_code > 299:
                if response:
                    self.helper.log_warning("{} API call was unsuccessful, status: {}, reason: {}".format(endpoint, 
                        response.status_code, response.reason))

                retry_available = self.check_request_retries(num_retries, endpoint)
                if retry_available:
                    num_retries += 1
                    continue
                else:
                    success = False
                    break
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                self.helper.log_error("HTTPError in API call: {}".format(e))
                success = False
                break

            r = json.loads(response.content.decode())
            metadata = r.get("metadata")
            links = r.get("links", [])
            next_link = None
            for link in links:
                if link.get("rel") == "next":
                    next_link = link["href"]
                    break
            
            # Results are processed on a per page basis as there might be thousands of pages.
            vuln_dict = process_result_page(r)          
            num_processed = vuln_dict.get("num_processed")

            page_size = metadata.get("size")
            total_resources = metadata.get("totalResources")
            total_pages = metadata.get("totalPages")
            self.helper.log_info("Metadata:\n"
                                 "Page number: {}\n"
                                 "Page size: {}\n"
                                 "Total resources: {}\n"
                                 "Total pages: {}\n"
                                 "Next: {}".format(count, page_size, total_resources, total_pages, next_link))
            self.helper.log_info("Number of items processed: {}".format(num_processed))

            # Log an error if data syncs during an import.
            if prev_total_resources == -1:
                prev_total_resources = total_resources
            elif total_resources != prev_total_resources and not has_logged_sync_error:
                has_logged_sync_error = True
                self.helper.log_error("Detected data syncing during import. This could result in missed import data. " \
                    "Imports should be scheduled to avoid scans and Agent data syncing to platform.")

            count += 1
            total_processed += num_processed
            
            if next_link is None:
                break
            
        self.helper.log_info("Total {} processed: {}".format(endpoint, total_processed))

        return success

    def get_sleep_time(self, num_retries):
        sleep_time = self.MIN_SLEEP_TIME * self.SLEEP_TIME_MINUTES * num_retries

        if sleep_time < self.MIN_SLEEP_TIME:
            return self.MIN_SLEEP_TIME
        elif sleep_time > self.MAX_SLEEP_TIME:
            return self.MAX_SLEEP_TIME
        
        return sleep_time

    def check_request_retries(self, current_retry, endpoint):
        has_retries_available = current_retry < self.MAX_RETRIES

        if not has_retries_available:
            self.helper.log_error("Max retries ({}) reached. Aborting {} API call. ".format(self.MAX_RETRIES, endpoint) + 
                "Please see the help documentation https://docs.rapid7.com/insightvm/insightvm-technology-add-on-for-splunk#faqs")

        else:
            sleep_time = self.get_sleep_time(current_retry)
            current_retry += 1
            self.helper.log_info("Failed request will be reattempted after {} seconds, retry number: {}".format(sleep_time, current_retry))
            time.sleep(sleep_time)

        return has_retries_available
