#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import re

# Networking and URL handling imports
from urllib.parse import urlencode
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))

# import Splunk libs
import splunklib.client as client

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


# get the soar account password
def get_soar_password(storage_passwords, soar_id):
    # realm
    credential_realm = (
        "__REST_CREDENTIAL__#splunk_app_soar#configs/conf-ta_splunk_app_soar_account"
    )
    credential_name = f"{credential_realm}:{soar_id}``"

    # extract as raw json
    bearer_token_rawvalue = ""

    for credential in storage_passwords:
        if credential.content.get("realm") == str(
            credential_realm
        ) and credential.name.startswith(credential_name):
            bearer_token_rawvalue = bearer_token_rawvalue + str(
                credential.content.clear_password
            )

    # extract a clean json object
    bearer_token_rawvalue_match = re.search(
        r'\{"password":\s*"(.*)"\}', bearer_token_rawvalue
    )
    if bearer_token_rawvalue_match:
        bearer_token = bearer_token_rawvalue_match.group(1)
    else:
        bearer_token = None

    return bearer_token


# return the list of accounts configured, or None if not any
def trackme_get_soar_accounts(reqinfo):
    # get service
    service = client.connect(
        owner="nobody",
        app="splunk_app_soar",
        port=reqinfo.server_rest_port,
        token=reqinfo.system_authtoken,
        timeout=600,
    )

    # get all accounts
    accounts = []
    conf_file = "ta_splunk_app_soar_account"

    # if there are no account, raise an exception, otherwise what we would do here?
    try:
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_msg = (
            "trackmesplksoar was called but we have no SOAR account configured yet"
        )
        raise Exception(error_msg)

    for stanza in confs:
        for key, value in stanza.content.items():
            if key == "custom_name":
                soar_custom_name = value
                accounts.append(soar_custom_name)

    if accounts:
        return accounts
    else:
        return None


# Get SOAR account credentials, designed to be used for a least privileges approach in a programmatic approach
def trackme_get_soar_account(reqinfo, account):
    # get service
    service = client.connect(
        owner="nobody",
        app="splunk_app_soar",
        port=reqinfo.server_rest_port,
        token=reqinfo.system_authtoken,
        timeout=600,
    )

    # Splunk credentials store
    storage_passwords = service.storage_passwords

    # get all accounts
    accounts = []
    conf_file = "ta_splunk_app_soar_account"

    # if there are no account, raise an exception, otherwise what we would do here?
    try:
        confs = service.confs[str(conf_file)]
    except Exception as e:
        error_msg = (
            "trackmesplksoar was called but we have no SOAR account configured yet"
        )
        raise Exception(error_msg)

    for stanza in confs:
        for key, value in stanza.content.items():
            if key == "custom_name":
                soar_custom_name = value
                accounts.append(soar_custom_name)

    # account configuration
    isfound = False
    soar_id = None
    soar_custom_name = None
    soar_server = None
    soar_username = None

    # get account
    if account in accounts:
        isfound = True

    if isfound:
        for stanza in confs:
            for key, value in stanza.content.items():
                if key == "custom_name":
                    soar_custom_name = value
                if soar_custom_name != account:
                    break
                else:
                    soar_id = stanza.name
                    if key == "server":
                        soar_server = value
                    if key == "username":
                        soar_username = value

    # end of get configuration

    # Stop here if we cannot find the submitted account
    if not isfound:
        error_msg = f'The account="{account}" has not been configured on this instance, cannot proceed!'
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
            }
        )

    # get the bearer token stored encrypted
    soar_password = get_soar_password(storage_passwords, soar_id)

    if not soar_password:
        error_msg = f'The password for the account="{account}" could not be retrieved, cannot proceed!'
        raise Exception(
            {
                "status": "failure",
                "message": error_msg,
                "account": account,
                "server": soar_server,
                "id": soar_id,
            }
        )

    else:
        # render
        return {
            "status": "success",
            "message": "SOAR account is ready",
            "account": account,
            "custom_name": soar_custom_name,
            "server": soar_server,
            "username": soar_username,
            "password": soar_password,
        }
