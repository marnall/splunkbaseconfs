import splunk.entity as entity
import splunk.admin as admin

import risksense_util as util
from splunktaucclib.rest_handler.endpoint.validator import Validator


class GetSessionKey(admin.MConfigHandler):
    """
    Class to get session key
    """

    def __init__(self):
        self.session_key = self.getSessionKey()


class RiskSenseAccount(object):
    def __init__(self, name, platform_url, client_name, token):
        """
        Initialize RiskSenseAccount object
        :param name: Account name
        :param platform_url: Platform URL of risksense
        :param client_name: Client name of which data is to be fetched
        :param token: API token provided by risksense
        """
        self.name = name
        self.platform_url = platform_url.strip("")

        clients = client_name.strip().split(",")
        self.client_names = list(
            set(list(map(lambda x: x.upper().strip(), clients))))
        if "ALL" in self.client_names or "all" in self.client_names:
            self.client_names = ["ALL"]

        # Build a dict consisting of normalized client names to original for validation
        # CLIENT1: Client1
        self.invalid_clients = {}
        for name in clients:
            self.invalid_clients[name.upper().strip()] = name

        self.endpoint = util.CLIENT_ENDPOINT
        self.session = util.requests_retry_session()
        self.proxies = self.create_requests_proxy_dict()

        self.params = dict()

        self.headers = {
            "content-type": "application/json",
            "x-api-key": token.strip("")
        }

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)

    def validate(self):
        """
        Validate the account credentials and return client id corresponding to the Client Name

        :return: Client ID
        """

        page = 0
        events_received = 0
        total_events = None
        client_ids = []
        url = "https://{fqdn}{endpoint}".format(fqdn=self.platform_url, endpoint=self.endpoint)
        while not total_events or events_received < total_events:
            # Iterate until all events are collected
            self.params["page"] = page
            response = self.session.get(url, params=self.params, headers=self.headers, verify=util.VERIFY_SSL,
                                        proxies=self.proxies, timeout=util.REQUESTS_TIMEOUT)
            response.raise_for_status()
            response = response.json()

            if not total_events:
                # Get total elements available in API
                total_events = response["page"]["totalElements"]
            clients = response["_embedded"]["clients"]

            if "ALL" in self.client_names or "all" in self.client_names:
                self.client_names = ["ALL"]
                for client in clients:
                    client_ids.append(str(client["id"]))
                    events_received += 1

            else:
                for client in clients:
                    # Fetch client id if the client name matches
                    name = client["name"].upper().strip()
                    if name in self.client_names:
                        client_ids.append(str(client["id"]))
                        # Delete key from dict when client id found
                        self.invalid_clients.pop(name, None)
                    events_received += 1

            page += 1
        return list(set(client_ids))

    def create_requests_proxy_dict(self):
        """
        Creates proxy dictionary used in requests module

        :return: Proxy dict
        """
        proxies = {}
        proxy_settings, proxy_enabled = self.get_proxy_config()

        # Create Proxy URL
        proxy_uri = util.create_uri(proxy_enabled, proxy_settings)
        if proxy_uri:
            proxies = {
                'http': proxy_uri,
                'https': proxy_uri
            }

        return proxies

    @staticmethod
    def get_proxy_config():
        '''
        Gives information of proxy if proxy is enabled
        :return: dictionary having proxy information
        '''
        # Get proxy configurations
        proxy_configuration = util.read_conf_file(
            GetSessionKey().session_key, util.RISKSENSE_SETTINGS_CONF, stanza="proxy")

        entities = entity.getEntities(['admin', 'passwords'], namespace=util.APP,
                                      owner='nobody', sessionKey=GetSessionKey().session_key, search=util.APP, count=-1)
        return util.get_proxy_settings(proxy_configuration, entities)


class AccountValidator(Validator):
    """This class extends base class of Validator."""

    def validate(self, value, data):
        """We define Custom validation here for verifying credentials when storing account information."""
        try:
            RS_account = RiskSenseAccount(data.get("name"), data.get(
                "platform_url"), data.get("client_name"), data.get("token"))
            client_ids = RS_account.validate()

            # Throw error in below cases:
            # Case 1: Client name consists of "All" but no client id found
            # Case 2: invalid_clients list is not empty

            if RS_account.client_names == ["ALL"] and not client_ids:
                self.put_msg(
                    "No Client ID/s found. Please create atleast one client on RiskSense Platform")
                return False

            elif RS_account.invalid_clients and RS_account.client_names != ["ALL"]:
                original_client_names = ','.join(
                    str(v) for v in RS_account.invalid_clients.values())
                self.put_msg(
                    "Client ID/s not found for the following Client Name/s -> '{}'".format(original_client_names))
                return False

            data["client_id"] = ",".join(client_ids)
        except Exception as e:
            self.put_msg(
                "Please enter valid account information or check proxy settings. Cause -> " + str(e))
            return False
        return True
