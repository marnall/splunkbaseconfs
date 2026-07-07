# encoding = utf-8
from requests.compat import quote_plus
import traceback
import socket

import splunk.admin as admin
from splunk.clilib.cli_common import getMgmtUri
from splunklib import client
from solnlib import conf_manager, utils as sutils
from solnlib.modular_input import checkpointer

from ta_mandiant_threat_intelligence_declare import ta_name


class SplunkSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        ta_name,
        realm=f"__REST_CREDENTIAL__#{ta_name}#configs/conf-{conf_file}",
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)

    return conf_file.get_all()


def build_proxy_config(proxies: dict) -> dict:
    """Proxy config."""
    proxy_type = proxies.get("proxy_type")
    proxy_url = proxies.get("proxy_url")
    proxy_port = proxies.get("proxy_port")
    proxy_user = None
    proxy_pass = None
    if proxies.get("proxy_username") or proxies.get("proxy_password"):
        proxy_user = quote_plus(proxies.get("proxy_username"), safe="")
        proxy_pass = quote_plus(proxies.get("proxy_password"), safe="")

    if not proxy_user:
        proxy_str = f"{proxy_type}://{proxy_url}:{proxy_port}"
    else:
        proxy_str = f"{proxy_type}://{proxy_user}:{proxy_pass}@{proxy_url}:{proxy_port}"

    return {"http": proxy_str, "https": proxy_str}


def resolve_host(hostname):
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


def create_service(sessionkey=None):
    """Create Service to communicate with splunk."""
    mgmt_uri = getMgmtUri()
    hostname = mgmt_uri.split("//")[-1].split(":")[0]  # Extract hostname from URI
    mgmt_port = mgmt_uri.split(":")[-1]

    # Resolve hostname to IPv4 address
    ip_address = resolve_host(hostname)
    if not ip_address:
        raise Exception("Failed to resolve Splunk management URI to an IP address.")

    if not sessionkey:
        sessionkey = SplunkSessionKey().session_key

    service = client.connect(host=ip_address, port=mgmt_port, token=sessionkey, app=ta_name)
    return service


def checkpoint_handler(logger, session_key, meta_configs):
    """
    This function creates as well as handles kv-store checkpoints for each input.

    :param logger: Logger object
    :param session_key: Session key for the particular modular input
    :param meta_configs: input identification meradata
    :return checkpoint_collection: Checkpoint directory
    """
    try:
        dscheme, dhost, dport = sutils.extract_http_scheme_host_port(
            meta_configs["server_uri"]
        )
        checkpoint_collection = checkpointer.KVStoreCheckpointer(
            ta_name.replace("-", "_") + "_checkpointer",
            session_key,
            ta_name,
            scheme=dscheme,
            host=dhost,
            port=dport,
        )
        return checkpoint_collection
    except Exception:
        logger.error("Error in Checkpoint handling: {}".format(traceback.format_exc()))
        return None
