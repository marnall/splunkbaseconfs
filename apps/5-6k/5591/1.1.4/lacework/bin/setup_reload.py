#!/usr/bin/env python3
# This script is ran by setupReload.sh on a scheduled interval based on inputs.conf 'interval' field.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import requests
import json
from constants import LaceworkAPIConfConstants, StoragePasswordConfConstants
from helpers import getStanzaValue
from splunklib.binding import HTTPError
import splunklib.client as client

LW_API_FILENAME = LaceworkAPIConfConstants.LW_API_FILENAME
LW_API_STANZA = LaceworkAPIConfConstants.LW_API_STANZA
LW_API_FIELD_DOMAIN = LaceworkAPIConfConstants.LW_API_FIELD_DOMAIN
TOKEN_URI = LaceworkAPIConfConstants.LW_API_GEN_ACCESS_TOKEN_URI

SP_API_TOKEN_STANZA = StoragePasswordConfConstants.SP_API_TOKEN_STANZA
SP_CREDENTIAL_REALM = StoragePasswordConfConstants.SP_CREDENTIAL_REALM
SP_CREDENTIAL_KEYID = StoragePasswordConfConstants.SP_CREDENTIAL_KEYID
SP_CREDENTIAL_SECRET = StoragePasswordConfConstants.SP_CREDENTIAL_SECRET

path_prefix = os.path.dirname(__file__)


def get_API_domain(service):
    """Get API domain from lacework-api.conf

    Raises:
        KeyError: Raised when API domain cannot be found from lacework-api.conf

    Returns:
        str: API domain path. E.g. https://exampleDomain.lacework.net
    """
    domain = getStanzaValue(service.confs, LW_API_FILENAME, LW_API_STANZA, LW_API_FIELD_DOMAIN)
    
    json.dumps({"status": 200, "message": "API domain of type: " + str(type(domain)) + "fetched!"})

    return "https://" + str(domain)


def get_session_key():
    """Get session key from reading standard in data sent from splunkd.
    This is enabled through providing a passAuth in inputs.conf.

    Returns:
        str: A session key used for connecting to Splunk service
    """
    sessionKey = sys.stdin.readline().strip()

    if len(sessionKey) == 0:
        print(json.dumps({"status": 400, "message": ("Did not receive a session key from splunkd. " +
                                                     "Please enable passAuth in inputs.conf for this " +
                                                     "script")}))
        exit(2)
    return sessionKey


def gen_API_token(service):
    storage_passwords = service.storage_passwords
    credentials = storage_passwords.list()

    keyId = ""
    secret = ""

    # Get keyID and secret
    for item in credentials:
        if item.realm == SP_CREDENTIAL_REALM:
            if item.username == SP_CREDENTIAL_KEYID:
                keyId = item.clear_password
            if item.username == SP_CREDENTIAL_SECRET:
                secret = item.clear_password

    # Missing one or both of keyID and secret
    if not (keyId and secret):
        print(json.dumps({"status": 403, "message": (
            "Unable To Generate API Token! Key ID and secret needed for such user are not found.")}))
        return

    # Get expiry time. Subtract 1 to expiry_time to make sure api token is always renewed to a different one
    interval = getStanzaValue(service.confs, "inputs", "script://$SPLUNK_HOME/etc/apps/lacework/bin/setupReload.sh", "interval")
    expiry_time = max(int(float(interval)) - 1, 0)

    # Get API token
    payload = {"keyId": keyId, "expiryTime": expiry_time}
    headers = {"X-LW-UAKS": secret,
               "Content-Type": "application/json"}
    try:
        response = requests.post(url=get_API_domain(service
        )+TOKEN_URI, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(json.dumps({"status": response.status_code,
                          "message": "An error occured while generating the API token. A message was received:\n" + response.text}))
        raise e
    API_token = response.json()["data"][0]["token"]

    # Store API token
    # Remove any existing token before creating a new one
    is_token_existed = any(item.realm == SP_API_TOKEN_STANZA and item.username ==
                           SP_API_TOKEN_STANZA for item in credentials)
    if is_token_existed:
        storage_passwords.delete(SP_API_TOKEN_STANZA, SP_API_TOKEN_STANZA)
    storage_passwords.create(
        API_token, SP_API_TOKEN_STANZA, SP_API_TOKEN_STANZA)

    # Reload App to reload passwords.conf after password has been created
    service.apps.__getitem__("lacework").reload()

    print(json.dumps(
        {"status": 200, "message": "API Token Successfully Generated!"}))


def gen_accounts(service):
    # Create a search query for each of the saved searches
    savedsearches_accessor = service.saved_searches
    jobs_accessor = service.jobs
    kwargs_blockingsearch = {"exec_mode": "blocking"} # blocking mode so the job is ran synchronously 

    for search in savedsearches_accessor:
        if (search.content()['request.ui_dispatch_app'] == "lacework"):
            search_query = 'savedsearch ' + '"' + search.name + '"'
            gen_account_job = jobs_accessor.create(search_query, **kwargs_blockingsearch)
            print(json.dumps(
                {"status": 200, "message": search.name + " Successfully Ran!"}))


def run():
    """Main function that fetches and stores an API token based on credentials read
     from passwords.conf using splunk endpoints

    Raises:
        requests.exceptions.HTTPError: Raised when API token cannot be generated successfully
    """
    # Connect to Splunk service
    session_key = get_session_key()
    service = client.Service(
        owner="nobody", app="lacework", sharing="app", token=session_key)

    # Gen API token
    gen_API_token(service)

    # Gen Accounts using search command from saved searches
    gen_accounts(service)


if __name__ == "__main__":
    run()
