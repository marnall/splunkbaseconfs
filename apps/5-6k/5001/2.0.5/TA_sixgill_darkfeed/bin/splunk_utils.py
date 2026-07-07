import requests
from urllib.parse import urlencode
from xml.dom import minidom
import json


class RequestError(Exception):
    def __init__(self, url, message):
        fail_msg = "Request to url [{}] throws exception. Error [{}]".format(url, message)
        super(RequestError, self).__init__(fail_msg)


class DeleteError(Exception):
    def __init__(self, url, message):
        fail_msg = "Delete request to url [{}] throws exception. Error [{}]".format(url, message)
        super(DeleteError, self).__init__(fail_msg)


class SplunkUtils(object):
    session_key = ""
    base_url = ""
    SUPPORTED_THREAT_TYPE = ["ip_intel", "file_intel", "user_intel", "http_intel",
                             "email_intel", "service_intel", "process_intel",
                             "registry_intel", "certificate_intel"]

    def __init__(self, host, port, username, password, verify):
        self.verify = verify
        self.base_url = "https://{}:{}".format(host, port)
        self.get_session_key(username, password)

    def get_session_key(self, username, password):
        headers = dict()
        headers["Accept"] = "application/html"
        url = "{}/services/auth/login".format(self.base_url)
        try:
            resp = requests.post(url,
                                 headers=headers,
                                 data=urlencode({"username": username, "password": password}),
                                 verify=self.verify)
            if resp.status_code == 200:
                # docs.splunk.com/Documentation/Splunk/7.0.2/RESTTUT/RESTsearches
                self.session_key = minidom.parseString(resp.content).getElementsByTagName("sessionKey")[0].childNodes[
                    0].nodeValue
            else:
                error_msg = "Splunk login failed for user {} with status {}".format(username, resp.status_code)
                raise RequestError(url, error_msg)
        except Exception as e:
            raise e

        return

    def delete_threat_intel_item(self, threat_type, item_key):
        headers = dict()
        headers["Authorization"] = "Splunk {}".format(self.session_key)
        url = "{}/services/data/threat_intel/item/{}/{}".format(self.base_url, threat_type, item_key)

        if threat_type not in self.SUPPORTED_THREAT_TYPE:
            raise RequestError(url, "{} is not supported".format(threat_type))

        ret = {}
        try:
            resp = requests.delete(url, headers=headers, verify=self.verify)

            ret = {"status_code": resp.status_code, "content": resp.json()}

        except Exception as e:
            raise DeleteError(url, "Failed to delete: {}".format(str(e)))

        return ret

    def add_threat_intel_item(self, threat_type, threat_list):
        headers = dict()
        headers["Authorization"] = "Splunk {}".format(self.session_key)
        url = "{}/services/data/threat_intel/item/{}".format(self.base_url, threat_type)

        if threat_type not in self.SUPPORTED_THREAT_TYPE:
            raise RequestError(url, "{} is not supported".format(threat_type))

        item = {"item": json.dumps(threat_list)}

        try:
            resp = requests.post(url,
                                 headers=headers,
                                 data=item,
                                 verify=self.verify)
            try:
                content = resp.json()
            except json.decoder.JSONDecodeError as e:
                content = resp.content
            ret = {"status_code": resp.status_code, "content": content}

        except requests.ConnectionError as e:
            raise RequestError(url, "Connection error. {}".format(str(e)))
        except requests.HTTPError as e:
            raise RequestError(url, "An HTTP error. {}".format(str(e)))
        except requests.URLRequired as e:
            raise RequestError(url, "A valid URL is required.")
        except requests.TooManyRedirects as e:
            raise RequestError(url, "Too many redirects")
        except requests.RequestException as e:
            raise RequestError(url, "Ambiguous exception when handling request. {}".format(str(e)))
        return ret
