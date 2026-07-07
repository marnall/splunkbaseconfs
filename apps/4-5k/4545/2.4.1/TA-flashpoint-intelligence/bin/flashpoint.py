import json
import requests
import time
from utils import connect_to_fpi, REQ_TIMEOUT, get_app_version
import splunk.version as v


class FlashPoint(object):
    """Class connect to the Flashpoint-intel api."""

    api_base_url = "https://api.flashpoint.io/"
    __events = []
    unmapped_data = []
    fetched_event_count = 0

    def __init__(self, api_key, proxy_uri, event_type, helper, updated_since=None):
        """Init method.

        :param api_key: Flashpoint API key.
        :param proxy_uri: Proxy uri if proxy is enabled
        :param event_type: Type of events either reports or indicators or cves or mentions
        :param helper: Splunk helper object
        :param updated_since: Start time from which to fetch the events
        """
        self.__request_params = dict()
        self.__json_params = dict()
        self.__api_key = api_key
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'authorization': 'Bearer {}'.format(self.__api_key),
            'X-FP-IntegrationPlatform': 'Splunk',
            'X-FP-IntegrationPlatformVersion': v.__version__,
            'X-FP-IntegrationVersion': get_app_version(helper.context_meta["session_key"])
        }

        if event_type not in ["alerts", "ransomware", "cve", "mentions", "indicators"]:
            self.__request_params = {
                'limit': 500,
                'skip': 0
            }

        if event_type == "reports":
            self.__request_params['embed'] = 'asset'
        elif event_type == "cve":
            self.__request_params['updated_after'] = updated_since + 'Z'
        elif event_type == "compromised_credentials":
            self.__request_params['query'] = '+basetypes:(credential-sighting) +(header_.indexed_at:'
            self.__request_params['sort'] = 'header_.indexed_at:asc'
            self.__request_params['scroll'] = '2m'  # (2 minute): How long scroll session to be kept at server side
        elif event_type == "indicators":
            self.__request_params['last_seen_after'] = updated_since
            self.__request_params['sort'] = 'created_at:asc'
        elif event_type == "alerts":
            self.__request_params['created_after'] = updated_since
            self.__request_params['size'] = 200

        self.event_type = event_type
        self.proxy_uri = proxy_uri
        self.helper = helper
        if updated_since and event_type not in ["alerts", "ransomware", "cve", "mentions", "indicators"]:
            self.__request_params['updated_since'] = updated_since

    def get_request_param(self):
        """Get Request Parameters.

        :return: dict, dictionary containing request parameters
        """
        return self.__request_params

    def set_request_param(self, req_param):
        """Set Request Parameters.

        :param req_param: dict, dictionary of request parameters
        """
        self.__request_params = req_param

    def set_json_param(self, json_param):
        """Set Json Parameters."""
        self.__json_params = json_param

    def delete_scroll_session(self, scroll_id):
        """Delete scroll session in server."""
        url = self.get_event_url(is_scroll=True)
        proxy = {"http": self.proxy_uri, "https": self.proxy_uri}
        payload = {'scroll_id': scroll_id}
        payload = json.dumps(payload)
        response = requests.delete(
            url, headers=self.headers, data=payload, proxies=proxy, verify=True, timeout=REQ_TIMEOUT)
        if response.status_code in [204, 200]:
            return True
        else:
            raise Exception("Status Code: {} Message: {}".format(
                response.status_code, response.text))

    def get_event_url(self, is_scroll=False):
        """Creates events url.

        :return: str
        """
        if self.event_type == "reports":
            return "{}finished-intelligence/v1/reports".format(self.api_base_url)
        elif self.event_type == "indicators":
            return "{}technical-intelligence/v2/indicators".format(self.api_base_url)
        elif self.event_type == "alerts":
            return "{}alert-management/v1/notifications".format(self.api_base_url)
        elif self.event_type in ["ransomware", "mentions"]:
            return "{}sources/v2/communities".format(self.api_base_url)
        elif self.event_type == "cve":
            return "{}vulnerability-intelligence/v1/vulnerabilities/".format(self.api_base_url)
        elif is_scroll:
            return "{}sources/v1/noncommunities/scroll".format(self.api_base_url)
        else:
            return "{}sources/v1/noncommunities/search".format(self.api_base_url)

    def get_events(self, is_scroll=False, communities_call=False):
        """Fetches events from api.

        :return: list
        """
        if communities_call or is_scroll:
            method = "POST"
        else:
            method = "GET"
        self.__events = connect_to_fpi(
            url=self.get_event_url(is_scroll),
            token=self.__api_key,
            proxy_uri=self.proxy_uri,
            helper=self.helper,
            params=self.__request_params,
            json=self.__json_params,
            method=method
        )
        return self.__events

    def get_formatted_events(self):
        """Create formatted Events.

        :return: None
        """
        # Generate events if not available
        if not self.__events:
            self.get_events()

        if self.event_type == "reports":
            return self.get_formatted_reports()
        elif self.event_type == "cve":
            return self.get_formatted_cves()
        elif self.event_type == "mentions":
            return self.get_formatted_mentions()
        elif self.event_type == "compromised_credentials":
            return self.get_formatted_compromised_credentials()
        elif self.event_type == "alerts":
            return self.get_formatted_alerts()
        elif self.event_type == "ransomware":
            return self.get_formatted_ransomware()
        elif self.event_type == "indicators":
            return self.get_formatted_indicators()

    def get_formatted_indicators(self):
        """Function to return indicators in formatted events."""
        events = self.__events.get('items')
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(events or [])))
        return events

    def get_formatted_reports(self):
        """Function to return formatted Reports."""
        events = self.__events.get("data")
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(events or [])))
        return events

    def get_formatted_alerts(self):
        """Function to return formatted Alerts."""
        events = self.__events.get("items")
        next_link = self.__events.get('pagination', {}).get('next', None)
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(events or [])))
        return next_link, events

    def get_formatted_ransomware(self):
        """Function to return formatted Ransomware."""
        scroll_id = self.__events.get('_scroll_id')
        data = []
        hits = self.__events.get("hits", {}).get("hits", [])
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(hits or [])))
        self.fetched_event_count = len(hits or [])
        for res in hits:
            event = res.get("_source", {})
            if not event:
                self.helper.log_info(
                    "Skipping the event for type Ransomware as source field is not present in the event...")
                continue
            item = {}
            item['_source'] = event
            item['_source'].pop('basetypes', None)
            item["_source"].get("_meta", {}).pop("enrichments", None)

            # Check if collect_enrichments is enabled for this input
            collect_enrichments = self.helper.get_arg('collect_enrichments')
            if not collect_enrichments or collect_enrichments == "0":
                item["_source"].pop("enrichments", None)

            data.append(item)

        return scroll_id, data

    def get_formatted_compromised_credentials(self):
        """Function to return formatted Compromized Credentials."""
        data = []
        scroll_id = self.__events.get('_scroll_id')
        hits = self.__events.get("hits", {}).get("hits", [])
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(hits or [])))
        self.fetched_event_count = len(hits or [])
        for res in hits:
            event = res.get("_source", {})
            if not event:
                self.helper.log_info(
                    "Skipping the event for type Compromizd Credentials as source field is not present in the event...")
                continue
            item = {}
            item['_source'] = event
            item['_source'].pop('basetypes', None)
            item['_source'].pop('extraction_id', None)
            item['_source'].pop('extraction_record_id', None)

            data.append(item)
        return scroll_id, data

    def get_formatted_cves(self):
        """Function to return formatted CVEs.

        :return: list (List of formatted CVEs)
        """
        data = []
        hits = self.__events.get("hits").get("hits")
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(hits or [])))
        for res in hits:

            event = res.get("_source", {})
            # Skipping the event if the mitre field is not present in the _source.
            if 'mitre' not in event:
                self.helper.log_info(
                    "Skipping the event for type CVE as mitre field is not present in the event...")
                continue

            item = {"_source": {"mitre": {"body": {}},
                                "nist": {"cvssv2": {}, "updated_at": {}, "products": {}}
                                }}

            item["_source"]['nist']['cvssv2'] = event.get(
                'nist', {}).get("cvssv2")
            item["_source"]['nist']['updated_at'] = event.get(
                'nist', {}).get("updated_at")
            item["_source"]['nist']['products'] = event.get(
                'nist', {}).get("products")

            item["_source"]['fpid'] = event.get("fpid")
            item["_source"]['title'] = event.get("title")
            item["_source"]['mitre']['body']['text/html-sanitized'] = event.get(
                'mitre', {}).get('body', {}).get('text/html-sanitized')
            item["_source"]['mitre']['created_at'] = event.get(
                'mitre', {}).get('created_at')
            item["_source"]['mitre']['updated_at'] = event.get(
                'mitre', {}).get('updated_at')

            data.append(item)
        return data

    def get_formatted_mentions(self):
        """Function to return formatted mentions."""
        scroll_id = self.__events.get('_scroll_id')
        data = []
        titles = []
        hits = self.__events.get("hits", {}).get("hits", [])
        self.helper.log_debug("Fetched {} events: {}".format(self.event_type, len(hits or [])))
        self.fetched_event_count = len(hits or [])
        for res in hits:
            event = res.get("_source", {})
            item = {"_source": {"enrichments": {}, "container": {}, "site": {}}}
            item["_source"]["enrichments"]["cves"] = event.get(
                "enrichments", {}).get("cves")
            item["_source"]["site"]["tags"] = event.get("site", {}).get("tags")
            item["_source"]["site"]["title"] = event.get(
                "site", {}).get("title")
            item["_source"]["site"]["site_type"] = event.get(
                "site", {}).get("site_type")

            item["_source"]["container"]["fpid"] = event.get(
                "container", {}).get("fpid")
            item["_source"]["fpid"] = event.get("fpid")
            item["_source"]["created_at"] = event.get("created_at")
            data.append(item)
            titles += event.get("enrichments", {}).get("cves", [])

        return scroll_id, self.get_cves_for_mentions(data, titles)

    def get_cves_for_mentions(self, formatted_events, titles):
        """Function to get CVEs for mentions.

        :param formatted_events: formatted events for mentions
        :returns: 1 if error occur or returns formatted events for mentions with cve fpid
        """
        titles = list(set(titles))
        self.helper.log_info("length of title is {}".format(len(titles)))
        cve_fpid_data = []
        for i in range(0, len(titles), 100):
            self.helper.log_info(
                "Iterating list from {} to {}".format(i, i + 100))
            cve_titles = "(\"" + titles[i] + "\" OR \"" + \
                ("\" OR \"".join(titles[i + 1: i + 100])) + "\")"
            payload = {"_source_includes": [
                "title"], "query": "+basetypes:vulnerability +title:" + str(cve_titles)}
            payload = json.dumps(payload)
            url = "https://api.flashpoint.io/api/v4/all/search"
            proxy = {"http": self.proxy_uri, "https": self.proxy_uri}
            titles_len = len(titles[i + 1: i + 100]) + 1
            ex = None
            raise_ex = 0
            for _ in range(3):
                raise_ex = 0
                try:
                    cve_response = requests.post(
                        url, headers=self.headers, data=payload, proxies=proxy, verify=True, timeout=REQ_TIMEOUT)
                    cve_data = cve_response.json()
                    response_len = len(cve_data.get("hits").get("hits"))
                    if response_len >= titles_len:
                        cve_fpid_data += cve_data.get("hits").get("hits")
                        break
                    self.helper.log_info(
                        "Couldn't fetch fpids for all the CVEs. Length of the CVE requested was {}, "
                        "while the length of the CVE returned is {}. Retrying in 3 seconds...".format(
                            titles_len, response_len
                        )
                    )
                    time.sleep(3)
                except ValueError as e:
                    ex = e
                    raise_ex = 1
                    self.helper.log_error(
                        "Error in fetching CVEs for Mentions. Retrying in 3 seconds... \n Error:{}".format(str(e)))
                    time.sleep(3)
                except Exception as e:
                    ex = e
                    raise_ex = 1
                    self.helper.log_error(
                        "Error in connecting to Flashpoint API. Retrying in 3 seconds...\nError: {}".format(str(e)))
                    time.sleep(3)
            else:
                if raise_ex:
                    raise Exception(
                        "Error in connecting to Flashpoint API after 3 retries. \nError: {}".format(str(ex)))
                else:
                    self.helper.log_warning(
                        "Number of fpids missed for CVE title is {}".format(titles_len - response_len))
                    cve_fpid_data += cve_data.get("hits").get("hits")

        # loop to create helper dictionary
        helper_dict = {}
        for cve_item in cve_fpid_data:
            helper_dict[cve_item.get("_source").get(
                'title')] = cve_item.get("_id")

        # loop to create formatted event for Mention
        for format_event in formatted_events:
            event_titles = format_event.get("_source", {}).get(
                "enrichments", {}).get("cves", [])
            format_event["_source"]["enrichments"]["cves"] = []
            for title in event_titles:
                cve = {}
                cve['fpid'] = helper_dict.get(title)
                cve['title'] = title
                format_event["_source"]["enrichments"]["cves"].append(cve)

        return formatted_events

    @staticmethod
    def generate_attribute(item):
        """Generate attribute list from event.

        :param item: dict indicator event
        :return: attr_list: list List of attributes
        """
        attr_list = []
        if item['Event'].get('Attribute'):
            attr_list = item['Event'].get('Attribute')
        elif item['Event'].get('Object'):
            for attribute in item['Event'].get('Object'):
                attr_list += attribute['Attribute']
        return attr_list
