
# encoding = utf-8

import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # account = definition.parameters.get('account', None)
    pass

def collect_events(helper, ew):
    import json
    import logging

    # Helper function to ingest JSON from nested dicts
    def print_dict(d):
        new = {}
        for k, v in d.items():
            if isinstance(v, dict):
                v = print_dict(v)
            else:
                if isinstance(v, list):
                    new_list = []
                    for sub in v:
                        if isinstance(sub, dict):
                            new_list.append(print_dict(sub))
                        else:
                            new_list.append(sub)
                    v = new_list

            if not isinstance(v, dict) and not isinstance(v, list):
                v = str(v)

            new[str(k)] = v
        return new

    # Set logging Level to ERROR to avoid ingesting everything from fints library. We don't need other information
    logging.basicConfig(level=logging.ERROR)

    # Add lib path from app root folder to environment
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))

    # Import FinTS and Splunk SDK libaries
    from fints.client import FinTS3PinTanClient, NeedTANResponse
    from fints.utils import minimal_interactive_cli_bootstrap

    from splunk.clilib import cli_common as cli
    import splunklib.client as client

    # Get Account defined in inputs.conf
    opt_account = helper.get_arg('account')

    # Get Account Data defined in fints_accounts.conf
    cfg = cli.getConfStanza('fints_accounts',opt_account)

    opt_blz = cfg['blz']  if "blz" in cfg else None
    opt_user = cfg['user'] if "user" in cfg else None
    opt_pin = cfg['pin'] if "pin" in cfg else None
    opt_endpoint = cfg['endpoint'] if "endpoint" in cfg else None
    opt_iban = cfg['iban'] if "iban" in cfg else None

    # Get clear password from storage password in passwords.conf
    service = client.connect(token=helper.context_meta['session_key'], app=helper.get_app_name(), owner="nobody")
    storage_passwords = service.storage_passwords

    credentials = [k for k in storage_passwords if k.content.get('realm')=='TA-fints' and k.content.get('username')==opt_account][0]

    client_args = (opt_blz, opt_user, credentials.content.get('clear_password'), opt_endpoint)

    # Initialize connection and get sepa accounts (if multi accounts are available)
    try:
        f = FinTS3PinTanClient(*client_args)
        minimal_interactive_cli_bootstrap(f)

        accounts = f.get_sepa_accounts()
    except Exception as e:
        helper.log_error("FinTS Logging - Status:ERROR, Account:" + str(opt_account) + ", BLZ:" + str(opt_blz) + ", User:" + str(opt_user) + ", Endpoint:" + str(opt_endpoint) + ", IBAN:" + str(opt_iban) + ", Message:" + str(e))
        return

    # Select first iban if not given
    if len(accounts) == 1:
        account = accounts[0]
    else:
        if opt_iban is not None:
            for i, mm in enumerate(accounts):
                if mm.iban == opt_iban:
                    account = accounts[i]
                    break
        else:
            account = accounts[0]

    # Finally get target data
    with f:
        try:
            res = f.get_information()
            while isinstance(res, NeedTANResponse):
                raise Exception

            res['Account'] = opt_account
            res['BLZ'] = opt_blz
            res['User'] = opt_user
            res['Endpoint'] = opt_endpoint
            res['IBAN'] = opt_iban

            # Get JSON structure to ingest
            data = json.dumps(print_dict(res))

            # Create event structure
            event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=data)

            # Write event
            ew.write_event(event)

            helper.log_error("FinTS Logging - Status:OK, Account:" + str(opt_account) + ", BLZ:" + str(opt_blz) + ", User:" + str(opt_user) + ", Endpoint:" + str(opt_endpoint) + ", IBAN:" + str(opt_iban))

        except Exception as e:
            helper.log_error("FinTS Logging - Status:ERROR, Account:" + str(opt_account) + ", BLZ:" + str(opt_blz) + ", User:" + str(opt_user) + ", Endpoint:" + str(opt_endpoint) + ", IBAN:" + str(opt_iban) + ", Message:" + str(e))

