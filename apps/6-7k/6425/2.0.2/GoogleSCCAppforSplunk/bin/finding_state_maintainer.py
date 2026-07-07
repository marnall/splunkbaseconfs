"""This module contain class and method to remove old data from kvstore."""
import sys
import os
import json
import datetime
import traceback  # noqa # pylint: disable=unused-import

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'GoogleSCCAppforSplunk', 'lib'))

import socket  # noqa: E402
from splunklib.searchcommands import dispatch, EventingCommand, Configuration  # noqa: E402
import splunk.clilib.cli_common  # noqa: E402
import splunk.admin as admin  # noqa: E402
import splunklib.client as client  # noqa: E402

from googlescc_logger_manager import setup_logging  # noqa: E402

APP_NAME = os.path.abspath(__file__).split(os.sep)[-3]


class SplunkSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


@Configuration()
class FindingStateMaintainer(EventingCommand):
    """
    maintainfindingstatelookup - Transforming command.

    Command that queries the kvstore and removes 30mins old records.

    **Syntax**::
    `| maintainfindingstatelookup`
    """

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

    def create_service(self, sessionkey=None):
        """Create Service to communicate with splunk."""
        mgmt_uri = splunk.clilib.cli_common.getMgmtUri()
        hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
        mgmt_port = mgmt_uri.split(":")[-1]

        # Resolve hostname to IPv4 address
        ip_address = self.resolve_host(hostname)
        if not ip_address:
            raise Exception("Failed to resolve Splunk management URI to an IP address.")

        if not sessionkey:
            sessionkey = SplunkSessionKey().session_key

        service = client.connect(host=ip_address, port=mgmt_port, token=sessionkey, app="GoogleSCCAppforSplunk")
        return service


    def transform(self, records):
        """Method to clear kvstore via rest calls."""  # noqa: D401
        try:
            session_key = self._metadata.searchinfo.session_key
            logger = setup_logging("googlescc_findingstate_maintainer", session_key)
            logger.info("Initiating finding state maintenance")
            collection_name = "updated_finding_state_collection"
            service = self.create_service(session_key)
            if collection_name in service.kvstore:
                collection = service.kvstore[collection_name]
                event_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)
                expiry_time = event_time.isoformat() + "Z"
                query = json.dumps({"eventTime": {"$lt": expiry_time}})
                collection.data.delete(query=query)
                logger.debug("Finding state maintenance completed successfully.")
            else:
                logger.error("Collection {} does not exist. Please define one in collections.conf.".format(
                    collection_name))
        except Exception:
            logger.error("An exception occurred during finding state maintenance.\n{}".format(
                traceback.format_exc()))
        yield {}

    def __init__(self):
        """Initialize custom command class."""
        super(FindingStateMaintainer, self).__init__()


dispatch(FindingStateMaintainer, sys.argv, sys.stdin, sys.stdout, __name__)
