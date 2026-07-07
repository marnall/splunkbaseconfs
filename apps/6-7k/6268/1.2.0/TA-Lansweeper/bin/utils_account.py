"""Utilities related to account page."""
import ta_lansweeper_declare
import json
import requests
import socket
import hashlib
import traceback
import common.account_utils as utils
import common.lansweeper_const as const

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunk_aoblib.rest_migration import ConfigMigrationHandler
from solnlib.splunkenv import get_splunkd_access_info
from splunklib.client import connect
from common.logger_manager import setup_logging
from common.proxy import read_proxies_from_conf


_LOGGER = setup_logging("ta_lansweeper_validators")


class SessionKeyProvider(ConfigMigrationHandler):
    """Provides Splunk session key to custom validator."""

    def __init__(self):
        """Save session key in class instance."""
        self.session_key = self.getSessionKey()


class ValidateAccount(Validator):
    """For Account Validation."""

    def resolve_host(self, hostname):
        """Resolve hostname to IPv4/IPv6 address."""
        try:
            # This returns a list of (family, type, proto, canonname, sockaddr) tuples
            infos = socket.getaddrinfo(hostname, None)

            # Filter for IPv4 and IPv6 addresses
            ipv4_addresses = [info for info in infos if info[0] == socket.AF_INET]
            ipv6_addresses = [info for info in infos if info[0] == socket.AF_INET6]

            # Prefer IPv4, but fallback to IPv6 if necessary
            if ipv4_addresses:
                address = ipv4_addresses[0][4][0]
            elif ipv6_addresses:
                address = ipv6_addresses[0][4][0]
            else:
                return None  # No suitable address found
            return address
        except socket.gaierror:
            return None

    def create_service(self, ta_name, host, port, session_key):
        """Create Service to communicate with splunk."""
        # Resolve hostname to IPv4 address
        ip_address = self.resolve_host(host)
        if not ip_address:
            raise Exception("Failed to resolve host to an IP address.")

        service = connect(host=ip_address, port=port, token=session_key, app=ta_name)
        return service

    def validate(self, value, data):
        """For Validating account credentials and storing tokens in same."""
        try:
            token = data.get("token")

            proxy_settings = read_proxies_from_conf()

            session_key = SessionKeyProvider().session_key
            payload = json.dumps(const.SITE_PAYLOAD)
            request_headers = const.HEADERS
            request_headers['Authorization'] = 'Token {}'.format(token)

            response = requests.post(url=const.GRAPHQL_URL, headers=request_headers,
                                     data=payload, verify=const.VERIFY_SSL,
                                     proxies=proxy_settings, timeout=const.REQUEST_TIMEOUT)

            if response.status_code != 200:
                err_messages = utils.get_error_message(response)
                message = "Error(s) while fetching the sites: {}".format(err_messages)
                self.put_msg("Please enter valid token.")
                _LOGGER.error(message)
                return False
            else:
                try:
                    # Updating collection with site details
                    scheme, host, port = get_splunkd_access_info()
                    service = self.create_service(ta_lansweeper_declare.ta_name, host, port, session_key)
                    if const.COLLECTION_NAME not in service.kvstore:
                        service.kvstore.create(const.COLLECTION_NAME)
                    collection = service.kvstore[const.COLLECTION_NAME]
                    collection.data.delete()
                    sites_list = response.json()["data"]["authorizedSites"]["sites"]
                    for each in sites_list:
                        each["site_id"] = each.pop("id")
                        each["site_name"] = each.pop("name")
                        each["account_name"] = const.ACCOUNT_NAME
                        each["_key"] = hashlib.md5((each["site_id"] + each["account_name"]).encode()).hexdigest()
                        collection.data.insert(json.dumps(each))
                except Exception:
                    exception_msg = "Exception occured while updating the sites. {}".format(traceback.format_exc())
                    self.put_msg("Exception occured while updating the sites. Refer log for details")
                    _LOGGER.error(exception_msg)
                    return False

        except Exception as e:
            exception_msg = "Exception occured while validating: {}".format(e)
            self.put_msg("""Unable to request Lansweeper instance.
                    Please validate the provided credentials and
                    Proxy configurations or check the network connectivity.""")
            _LOGGER.error(exception_msg)
            return False

        _LOGGER.info("Lansweeper account successfully validated.")
        return True
