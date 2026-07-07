"""
common.py

Extracts creds from a custom conf file created by setup.xml

"""

from splunklib.client import connect # pylint: disable=import-error
from settings import APP_ID


def get_credentials(session_key):
    """
    Retrieves credentials from encrypted credential store.
    """
    service = connect(token=session_key, owner='nobody', app=APP_ID)

    # list all credentials
    passwords = service.storage_passwords

    api_key = None
    for credential in passwords:
        if credential.realm == "Farsight":
            api_key = credential.clear_password

    return api_key


def get_client_info(session_key):
    """
    Retrieves client info for swclient and version.
    """
    service = connect(token=session_key, owner='nobody', app=APP_ID)

    stanzas = service.confs["app"].list()
    for stanza in stanzas:
        if stanza.name == "launcher":
            version = stanza["version"]
        elif stanza.name == "ui":
            swclient = stanza["label"]

    return swclient, version
