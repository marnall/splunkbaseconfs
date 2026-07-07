
import ta_spycloud_declare
import splunk.auth
import splunk.rest
import sys

import json
import os
import logging
import datetime
import common
import splunklib.client as client
from consts import APP_NAME 

DEFAULT_INTERVALS = {
    "spycloud_breach_catalog/SpyCloud_Breach_Catalog": "0 * * * *",
    "spycloud_watchlist_identifiers/SpyCloud_Watchlist_Identifiers": "10 * * * *",
    "spycloud_watchlist/SpyCloud_Watchlist": "5 * * * *",
    "spycloud_compass/SpyCloud_Compass": "20 1 * * *",
}

def main():
    session_key = common.get_session_key()

    disable_input(session_key, "identifiers.py")
    disable_input(session_key, "watchlist.py")
    disable_input(session_key, "breach_catalog.py")

    try:
        api_key = common.get_credentials(session_key)
        update_api_key(session_key, api_key)

        identifiers_index = get_index(session_key, "identifiers.py")
        watchlist_index = get_index(session_key, "watchlist.py")
        breach_catalog_index = get_index(session_key, "breach_catalog.py")
        compass_index = watchlist_index

        set_index(session_key, "spycloud_watchlist_identifiers/SpyCloud_Watchlist_Identifiers", identifiers_index)
        set_index(session_key, "spycloud_watchlist/SpyCloud_Watchlist", watchlist_index)
        set_index(session_key, "spycloud_breach_catalog/SpyCloud_Breach_Catalog", breach_catalog_index)
        set_index(session_key, "spycloud_compass/SpyCloud_Compass", compass_index)

        for modular_input, interval_value in DEFAULT_INTERVALS.items():
            set_interval(session_key, modular_input, interval_value)

        breach_catalog_checkpoint = get_checkpoint(session_key, "breach_catalog_v2.checkpoint")
        compass_checkpoint = get_checkpoint(session_key, "compass_v2.checkpoint")
        watchlist_checkpoint = get_checkpoint(session_key, "watchlist_v2.checkpoint")
    
        set_checkpoint(session_key, "breach_catalog_v2_checkpoint", breach_catalog_checkpoint)
        set_checkpoint(session_key, "compass_v2_checkpoint", compass_checkpoint)
        set_checkpoint(session_key, "watchlist_v2_checkpoint", watchlist_checkpoint)

    except Exception as other_exception:
        make_error_message(str(other_exception), session_key)

    disable_input(session_key, "spycloud_upgrade.py")

def get_checkpoint(session_key, checkpoint_file):
    try:
        # No legacy checkpoint file means this should behave as a true first run.
        checkpoint = {"last_run": None, "documents": {}}

        checkpoint_dir = os.path.join(
            os.environ.get("SPLUNK_HOME"), "etc", "apps", "TA-SpyCloud", "local", "data"
        )

        if not os.path.exists(checkpoint_dir):
            return checkpoint
        else:
            checkpoint_path = os.path.join(checkpoint_dir, checkpoint_file)

            try:
                with open(checkpoint_path, "r") as checkpoint_file:
                    checkpoint = json.load(checkpoint_file)
            except Exception as e:
                checkpoint = {"last_run": None, "documents": {}}

        return checkpoint
    
    except Exception as e:
        make_error_message("spycloud_upgrade.py " + str(checkpoint) + " -- " + str(e), session_key)

def set_checkpoint(session_key, kvstore_name, checkpoint):
    service = client.connect(token=session_key, app=APP_NAME, owner='nobody')
    kvstore = service.kvstore[kvstore_name]

    try:
        kvstore.data.update('checkpoint', json.dumps({"value": json.dumps(checkpoint)}))
    except client.HTTPError as e:
        if e.status == 404:
            # If not found, insert a new checkpoint
            try:
                kvstore.data.insert({'_key': 'checkpoint', "value": json.dumps(checkpoint)})
            except Exception as insert_error:
                make_error_message(session_key, "Failed to insert new checkpoint: " + str(insert_error))
        else:
            make_error_message(session_key, "Failed to update checkpoint in KV Store: " + str(e))
    except Exception as general_error:
        make_error_message(session_key, "An unexpected error occurred while updating checkpoint: " + str(general_error))


def update_api_key(session_key, api_key):
    try:
        if api_key is not None and len(api_key) > 0: 

            inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/configs/conf-ta_spycloud_settings/additional_parameters"

            splunk.rest.simpleRequest(
                inputs_path,
                method="POST",
                sessionKey=session_key,
                postargs={"spycloud_key": api_key}
            )

    except Exception as other_exception:
         make_error_message(str(other_exception), session_key)

def get_index(session_key, input_file):
    try:
        index_request_path = "/servicesNS/nobody/" + str(APP_NAME) + "/configs/conf-inputs/script%3A%252F%252F%24SPLUNK_HOME%252Fetc%252Fapps%252F" + str(APP_NAME) + "%252Fbin%252F" + input_file

        index_response, index_content = splunk.rest.simpleRequest(
            index_request_path,
            method="GET",
            sessionKey=session_key,
            getargs={"output_mode": "json"}
        )

        index_content_json = json.loads(index_content)
        index = str(index_content_json["entry"][0]["content"]["index"])
        
        if index_response.status not in [200, 201]:
            logging.error('ScriptedInput test.py')

    except Exception as other_exception:
        make_error_message(str(other_exception), session_key)
        index=None

    return index

def set_index(session_key, modular_input, index):
    try:
        if index is not None and len(index) > 0: 

            inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)

            splunk.rest.simpleRequest(
                inputs_path + "/disable",
                method="POST",
                sessionKey=session_key,
            )

            index_update_response, index_update_content = splunk.rest.simpleRequest(
                inputs_path,
                method="POST",
                sessionKey=session_key,
                postargs={"index": index}
            )

            splunk.rest.simpleRequest(
                inputs_path + "/enable",
                method="POST",
                sessionKey=session_key,
            )
                
    except Exception as other_exception:
         make_error_message(str(other_exception), session_key)


def set_interval(session_key, modular_input, interval_value):
    try:
        if interval_value is not None and len(interval_value) > 0:
            inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)
            splunk.rest.simpleRequest(
                inputs_path,
                method="POST",
                sessionKey=session_key,
                postargs={"interval": interval_value},
            )
    except Exception as other_exception:
        make_error_message(str(other_exception), session_key)

def disable_input(session_key, input_file):
    try:
        input_path = "/servicesNS/nobody/" + str(APP_NAME) + "/configs/conf-inputs/script%3A%252F%252F%24SPLUNK_HOME%252Fetc%252Fapps%252F" + str(APP_NAME) + "%252Fbin%252F" + input_file

        splunk.rest.simpleRequest(
            input_path + "/disable",
            method="POST",
            sessionKey=session_key,
        )

    except Exception as other_exception:
        make_error_message(str(other_exception), session_key)

def make_error_message(message, session_key):
    """ Generates Splunk error message """
    filename = "Spycloud upgrade.py"
    logging.error(str(filename) +  str(message))
    splunk.rest.simpleRequest(
        '/services/messages/new',
        postargs={'name': APP_NAME, 'value': '{} - {}'.format(filename, message),  # pylint: disable=consider-using-f-string
                  'severity': 'error'}, method='POST', sessionKey=session_key
    )

if __name__ == "__main__":
    main()
