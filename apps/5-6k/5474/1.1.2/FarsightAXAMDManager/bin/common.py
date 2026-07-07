"""
common.py

Extracts creds from a custom conf file created by setup.xml

"""

from splunklib.client import connect # pylint: disable=import-error


def get_credentials(session_key):
    """
    Retrieves credentials from encrypted credential store.
    """
    service = connect(token=session_key, owner='nobody', app='FarsightAXAMDManager')

    # list all credentials
    passwords = service.storage_passwords

    if "AXAMD_KEY" in passwords:
        api_key = passwords["AXAMD_KEY"].clear_password
    else:
        api_key = None

    return api_key
