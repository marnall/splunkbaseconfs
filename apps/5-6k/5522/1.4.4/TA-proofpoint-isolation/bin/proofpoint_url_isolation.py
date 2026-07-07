import import_declare_test
import os
import os.path as op
import sys
import time
import json
from datetime import datetime, timezone, timedelta

bin_dir = os.path.basename(__file__)

import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput as base_mi
import dateutil.parser
import hashlib
import math
import proofpoint_isolation_constants as config


#
# encoding = utf-8
# 
# Proofpoint URL Isolation Handler
#


# Used to log the application version from the manifest.
def get_app_version():
    basepath = os.path.dirname(__file__)
    filepath = os.path.abspath(os.path.join(basepath, '..', 'app.manifest'))
    with open(filepath, 'r') as f:
        manifest = json.load(f)
        return str(manifest['info']['id']['version'])


# Get data chunk for event submission
def make_chunks(data, length):
    for i in range(0, len(data), length):
        yield data[i:i + length]


# Used to migrate from MD5 checkpoint to SHA256 for FIPS compliance
def migrate_checkpoint(helper, input_stanza, sha256_checkpoint_key):
    helper.log_info(f"SHA256 migration check for stanza: {input_stanza}")
    try:
        # Attempt to generate MD5 hash for backward compatibility
        md5_hash = hashlib.md5(input_stanza.encode()).hexdigest()
        md5_checkpoint_key = f"next_start_date_{md5_hash}"
        helper.log_info(f"MD5 Checkpoint Key: {md5_checkpoint_key}")
    except ValueError as e:
        # Handle FIPS mode error for MD5
        helper.log_warning(f"MD5 generation failed likely due to FIPS mode for stanza '{input_stanza}': {e}")
        md5_checkpoint_key = None

    if md5_checkpoint_key:
        checkpoint_value = helper.get_check_point(md5_checkpoint_key)
        if checkpoint_value is not None:
            helper.save_check_point(sha256_checkpoint_key, checkpoint_value)
            helper.log_info(
                f"Migrated checkpoint key from MD5 to SHA256: {md5_checkpoint_key} --> {sha256_checkpoint_key}")
            # Delete the old MD5 checkpoint
            helper.delete_check_point(md5_checkpoint_key)
        else:
            helper.log_info(f"No checkpoint data found for MD5 key: {md5_checkpoint_key}, skipping migration.")
    else:
        helper.log_info(
            f"Skipping migration from MD5 to SHA256 for stanza '{input_stanza}' system is likely in FIPS mode.")


class ModInputproofpoint_url_isolation(base_mi.BaseModInput):

    def __init__(self):
        use_single_instance = False
        super(ModInputproofpoint_url_isolation, self).__init__("ta_proofpoint_isolation", "proofpoint_url_isolation",
                                                               use_single_instance)
        self.global_checkbox_fields = None

    def get_scheme(self):
        """overloaded splunklib modularinput method"""
        scheme = super(ModInputproofpoint_url_isolation, self).get_scheme()
        scheme.title = ("Proofpoint URL Isolation")
        scheme.description = (
            "Go to the add-on\'s configuration UI and configure modular inputs under the Inputs menu.")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True

        scheme.add_argument(smi.Argument("name", title="Name",
                                         description="",
                                         required_on_create=True))

        """
        For customized inputs, hard code the arguments here to hide argument detail from users.
        For other input types, arguments should be get from input_module. Defining new input types could be easier.
        """
        scheme.add_argument(smi.Argument("api_key", title="API Key",
                                         description="Proofpoint Isolation API Key",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("page_size", title="Page Size",
                                         description="Number of records processed per request 1 to 10000 (default: 10000)",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("chunk_size", title="Chunk Size",
                                         description="Number of records processed per event 1 to 10000 (default: 10000)",
                                         required_on_create=True,
                                         required_on_edit=False))
        scheme.add_argument(smi.Argument("request_timeout", title="Request Timeout",
                                         description="Number of seconds before the web request timeout occurs (default: 60)",
                                         required_on_create=True,
                                         required_on_edit=False))
        return scheme

    def get_app_name(self):
        return "TA-proofpoint-isolation"

    def validate_input(helper, definition):
        """Implement your own validation logic to validate the input stanza configurations"""
        # This example accesses the modular input variable
        # text = definition.parameters.get('text', None)
        pass

    def collect_events(helper, ew):
        # Current log level
        loglevel = helper.get_log_level()
        helper.log_info("Log Level: {0}".format(loglevel))

        # Get App Name
        app_name = helper.get_app_name()
        helper.log_info("Application Name: {0}".format(app_name))

        # Get the application version
        app_version = get_app_version()
        helper.log_info("Application Version: {0}".format(app_version))

        # Get Input Type
        input_type = helper.get_input_type()
        helper.log_info("Input Type: {0}".format(input_type))

        # User defined input stanza
        input_stanza = str(helper.get_input_stanza_names())
        helper.log_info("Input Stanza: {0}".format(input_stanza))

        # Stanza hash for checkpoint
        stanza_hash = hashlib.sha256(input_stanza.encode()).hexdigest()
        helper.log_debug("Stanza hash: {0}".format(stanza_hash))

        # Checkpoint key for next start date
        checkpoint_key = "next_start_date_{0}".format(stanza_hash)
        helper.log_debug("Checkpoint Key: {0}".format(checkpoint_key))

        # Check if migration is needed. 
        if helper.get_check_point(checkpoint_key) is None:
            migrate_checkpoint(helper, input_stanza, checkpoint_key)

        # Get checkpoint date value
        checkpoint_data = helper.get_check_point(checkpoint_key)
        helper.log_info("Checkpoint Data: {0}".format(checkpoint_data))

        # Get API key
        api_key = helper.get_arg('api_key')
        # Logging of API key even in Debug will fail appinspect
        # helper.log_debug("API Key: {0}".format(api_key))

        # Get Page Size
        page_size = int(helper.get_arg('page_size'))
        helper.log_debug("Page Size: {0}".format(page_size))

        # Get Page Size
        chunk_size = int(helper.get_arg('chunk_size'))
        helper.log_debug("Chunk Size: {0}".format(chunk_size))

        # Current Polling Interval
        polling_interval = int(helper.get_arg('interval'))
        helper.log_debug("Polling interval: {0}".format(polling_interval))

        # Check request timeout
        request_timeout = float(helper.get_arg('request_timeout'))
        helper.log_debug("HTTP Request Timeout: {0}".format(request_timeout))

        helper.log_debug("Base URL: {0}".format(config.PFPT_URL_ISO_ENDPOINT))
        helper.log_debug("HTTP Method: {0}".format(config.PFPT_URL_ISO_METHOD))

        # Will be set to start date by either checkpoint or 30days back
        date_start = None

        # Will be set to current date
        date_end = None

        # If not previously excuted
        if (checkpoint_data is None):
            current_date = datetime.now(timezone.utc)
            date_end = current_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            date_start = (current_date - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
        else:
            date_end = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]
            # Incremental pull from last oldest dataset
            date_start = checkpoint_data

        # Log the current end of the range
        helper.log_info("Start Date: {0}".format(date_start))

        # Log the current end of the range
        helper.log_info("End Date: {0}".format(date_end))

        # Authentication via Header (AppInspect Fix)
        headers = {'Authorization': 'Bearer {}'.format(api_key)}

        parameters = {"from": date_start, "to": date_end, "pageSize": page_size}

        isolation_data = []

        # Current page
        page = 1

        # Assume at least 1 page
        pages = 1

        # Records processed
        records = 0

        # Used store the most recent date in the dataset processed
        most_recent_datetime = None

        # Start assuming we have one page but total pages are calcualted in the loop
        while True:
            response = None
            try:
                response = helper.send_http_request(config.PFPT_URL_ISO_ENDPOINT, config.PFPT_URL_ISO_METHOD,
                                                    parameters,
                                                    payload=None, headers=headers, cookies=None, verify=True, cert=None,
                                                    timeout=request_timeout, use_proxy=True)
            except Exception as e:
                helper.log_error("Call to send_http_request failed: {0}".format(e))
                break

            if (response.status_code == 200):
                helper.log_debug("Proofpoint Isolation API successfully queried")
            elif (response.status_code == 400):
                helper.log_error("Proofpoint Isolation API bad request")
            elif (response.status_code == 403 or response.status_code == 401):
                helper.log_error("Proofpoint Isolation API api key invalid")
            else:
                helper.log_error("Proofpoint Isolation API unknown failure [{}]".format(response.status_code))

            # Raise HTTPError exception if we had a failure
            if response.status_code != 200:
                response.raise_for_status()

            r_json = response.json()

            # Since we need the jobID for subsequent requests add it to the request
            # parameters for the next call to the web service.
            if 'jobId' in r_json:
                parameters['jobId'] = r_json['jobId']
                # Log the current jobID
                helper.log_debug("Job ID: {0}".format(r_json['jobId']))
            else:
                helper.log_error("Job ID is not defined in the JSON response, exiting")
                break

            # Since we need the pageToken for subsequent requests add it to the 
            # request parameters for the next call to the web service.
            if 'pageToken' in r_json:
                parameters['pageToken'] = r_json['pageToken']
                # Log the current pageToken
                helper.log_debug("Page Token: {0}".format(r_json['pageToken']))
            else:
                helper.log_debug("Page Token: None")

            # We will only have data once the status is COMPLETED so we poll until
            # our request state is COMPLETED.
            if 'status' in r_json:
                helper.log_debug("Status: {0}".format(r_json['status']))
                # According to the API we keep polling with the jobId until
                # the the status is completed.
                if r_json['status'].casefold() != "COMPLETED".casefold():
                    helper.log_debug("Polling until status is COMPLETED.")
                    continue
            else:
                helper.log_error("Status is not defined in the JSON response, exiting")
                break

            # Total is not a realiable way to determine the number of record pages to read for
            # we really need to read until status == COMPLETED and pageToken == None
            # could be useful information at some point in the future
            if 'total' in r_json:
                helper.log_debug("Total Records: {0}".format(r_json['total']))
                pages = math.ceil(int(r_json['total']) / int(page_size))
            else:
                helper.log_debug("Total Records: None")

            # Data contains the total number or records for the current query
            if 'data' in r_json:
                helper.log_info("Data Records: {0}".format(len(r_json['data'])))
                if len(r_json['data']) > 0:
                    helper.log_info("Page: {0} of {1}".format(page, pages))
                    for entry in r_json['data']:
                        # Collect all data for the current time range
                        isolation_data.append(entry)
                page += 1
            else:
                helper.log_info("Data Records: None")

            # Terminal case for the while loop
            if r_json['status'].casefold() == "COMPLETED".casefold() and 'pageToken' not in r_json:
                break

        if isolation_data:
            # Sort the isolation data by oldest to newest date
            isolation_data_sorted = sorted(isolation_data, key=lambda x: dateutil.parser.parse(x['date']))
            for chunk in make_chunks(isolation_data_sorted, chunk_size):
                # Get last date for the chunk we are processing
                last_processed_entry_date = dateutil.parser.parse(chunk[-1]['date'])
                # Create the event for the chunk
                event = helper.new_event(json.dumps(chunk), time=None, host=None, index=None, source=None,
                                         sourcetype=None,
                                         done=True, unbroken=True)
                # Write the single event
                try:
                    ew.write_event(event)
                    # Might be good to track the total records processed
                    records += len(chunk)
                    next_start_date = last_processed_entry_date + timedelta(seconds=1)
                    helper.save_check_point(checkpoint_key, next_start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3])
                    helper.log_info(
                        "Updating checkpoint [{0}] with: {1}".format(checkpoint_key, next_start_date.strftime(
                            '%Y-%m-%dT%H:%M:%S.%f')[:-3]))
                except Exception as e:
                    helper.log_error("Call to write_event failed: {0}".format(e))
                    break

        helper.log_info("Total records processed: {0}".format(records))

        # helper.delete_check_point(checkpoint_key)

    def get_account_fields(self):
        account_fields = []
        return account_fields

    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields

    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == "__main__":
    exitcode = ModInputproofpoint_url_isolation().run(sys.argv)
    sys.exit(exitcode)
