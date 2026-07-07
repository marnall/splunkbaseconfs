"""
common.py

Extracts creds from a custom conf file created by setup.xml

"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import connect # pylint: disable=import-error


def get_credentials(session_key):
    """
    Retrieves credentials from encrypted credential store.
    """
    service = connect(token=session_key, owner='nobody', app='SA-FarsightDNSDB')

    # list all credentials
    passwords = service.storage_passwords

    if "DNSDB_KEY" in passwords:
        api_key = passwords["DNSDB_KEY"].clear_password
    else:
        api_key = None

    return api_key


def get_client_info(session_key):
    """
    Retrieves client info for swclient and version.
    """
    service = connect(token=session_key, owner='nobody', app='SA-FarsightDNSDB')

    stanzas = service.confs["app"].list()
    swclient = "splunk"
    for stanza in stanzas:
        if stanza.name == "launcher":
            version = stanza["version"]
    return swclient, version
