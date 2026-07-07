# encoding = utf-8

from datetime import datetime, timedelta
import json
import os
import re
import sys
import traceback
python_major_version = sys.version_info.major
if python_major_version == 2:
    from urlparse import urlparse
elif python_major_version == 3:
    from six.moves.urllib.parse import urlparse
    from io import open
from requests.exceptions import HTTPError
from solnlib.splunkenv import get_splunkd_uri
from solnlib.credentials import (CredentialManager, CredentialNotExistException)

import certifi
import defusedxml.ElementTree as ET

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

            
def get_stored_token(helper, client_id):
    """ Decrypt stored token """
    splunkd_info = urlparse(get_splunkd_uri())
    cred_manager = CredentialManager(
        helper.context_meta['session_key'],
        #owner=self._endpoint.user,
        app=helper.get_app_name(),
        realm='realm_oit_jwt',
        scheme=splunkd_info.scheme,
        host=splunkd_info.hostname,
        port=splunkd_info.port
    )
    return cred_manager.get_password(client_id)

def get_and_store_token(helper, parsed_url, client_id, client_secret, ca_chain_file, timeout, use_proxy):
    """ Use client id and secret to get and store token"""
    auth_uri = "{0}://{1}/v2/apis/auth/oauth/token".format(parsed_url.scheme,parsed_url.netloc)
    helper.log_debug("Will use authentication URI: %s" % auth_uri)
    splunkd_info = urlparse(get_splunkd_uri())
    cred_manager = CredentialManager(
        helper.context_meta['session_key'],
        #owner=self._endpoint.user,
        app=helper.get_app_name(),
        realm='realm_oit_jwt',
        scheme=splunkd_info.scheme,
        host=splunkd_info.hostname,
        port=splunkd_info.port
        )

    # Delete anything already stored
    try:
        cred_manager.delete_password(client_id)
    except CredentialNotExistException as err:
        pass

    try:
        payload = "grant_type=client_credentials&client_id=%s&client_secret=%s&scope=*" % (client_id, client_secret)
        helper.log_debug("Get new token with payload: %s" % payload)
        helper.log_debug("Using CA chain file: %s" % ca_chain_file)
        response = helper.send_http_request(auth_uri, 
                                            method="post",
                                            headers={
                                                'accept' : 'application/json',
                                                'Content-Type' : 'application/x-www-form-urlencoded'},
                                            verify=ca_chain_file,
                                            payload=payload,
                                            use_proxy=use_proxy, 
                                            timeout=timeout)
    except Exception as exception:
        msg = 'Failed to authenticate. Error: {}'.format(repr(exception))
        helper.log_critical(msg)
        helper.log_debug(traceback.format_exc())
        sys.exit(msg)
        raise

    try:
        response.raise_for_status()
        token = response.json()["access_token"]
    except Exception as exception:
        msg = 'Failed to authenticate. Server response is not JSON. Error: {}. Response Content: {}'.format(repr(exception),repr(response.content))
        
        helper.log_critical(msg)
        helper.log_debug(traceback.format_exc())
        sys.exit(msg)
        raise

    try:
        cred_manager.set_password(client_id, token)
        helper.log_debug("Stored token for %s" % parsed_url.hostname)
        return token
    except Exception as exception:
        msg = 'Failed to store access token to splunk. Error: {}'.format(repr(exception))
        helper.log_critical(msg)
        helper.log_debug(traceback.format_exc())
        sys.exit(msg)
        raise

def validate_input(helper, definition):
    """ Check correctness of Events Pagination Value.
        Should contain integer value between 2000-50000.
    """
    events_pagination = definition.parameters.get("events_pagination", None)
    try:
        events_pagination = int(events_pagination)
        if events_pagination < 2000 or events_pagination > 50000:
            raise ValueError("Events pagination should be between 2000-50000")
    except Exception as exception:
        raise Exception("Invalid Events Pagination Value: {}".format(repr(exception)))

    """ Validate URL starts with https
    """
    reports_api_url = definition.parameters.get("reports_api_url", None)
    try:
        parsed_url = urlparse(reports_api_url)
        if parsed_url.scheme != "https":
            raise ValueError("HTTPS URL Is Required!")
    except:
        raise ValueError("Invalid Reports URL")

    """ Validate CA Certificate Chain file, if exists 
    """
    if (definition.parameters.get("ca_certificate_chain")):
        ca_certificate_chain = definition.parameters.get("ca_certificate_chain", None)
        ca_chain_file=os.path.join(os.environ['SPLUNK_HOME'], ca_certificate_chain)
    
        try:
            ca_chain_file_r = open(ca_chain_file)
            ca_chain_file_r.close
        except Exception as exception:
            raise ValueError("Error opening " + ca_chain_file + " : {}".format(repr(exception)))

    ###""" FUTURE: Validate KV Store is active
    ###"""

def migrate_checkpoints(helper, app_name, input_name, checkpoint_dir, reports_to_collect):
    """ Migrate checkpoints from files to KV store """

    if os.path.isdir(checkpoint_dir):
        """ Try migrating checkpoints"""
        helper.log_info("Legacy checkpoints directory exists. Will try migrating to KV store.")

        #Remove *_lock files left by deprecated locking mechanism
        lock_file_name = app_name + "_" + input_name + "_lock"
        lock_file = os.path.join(checkpoint_dir,lock_file_name)
        if os.path.exists(lock_file):
            helper.log_info("[migrate_checkpoints] Removing deprecated lock file for {}".format(input_name))
            os.remove(lock_file)

        for report in reports_to_collect:
            
            checkpoint_name_base = app_name + "_" + input_name + "_" + report
            for checkpoint_name_suffix in ["", ".past_data_hours"]:
                checkpoint_name = checkpoint_name_base + checkpoint_name_suffix
                helper.log_info("[migrate_checkpoints] Attempting checkpoint migration for {}".format(checkpoint_name))
                checkpoint_file = os.path.join(checkpoint_dir, checkpoint_name)

                if os.path.exists(checkpoint_file): 
                    kvstore_cp=helper.get_check_point(checkpoint_name)
                    if not kvstore_cp:
                        """ Checkpoint doesn't exist in KV store. Try migrating """
                        file_size = os.path.getsize(checkpoint_file)
                        helper.log_info("[migrate_checkpoints] Processing legacy checkpoint from file {}, size: {}".format(checkpoint_file,file_size))

                        latest_cp=None

                        if file_size != 0:
                            """ Get latest checkpoint value from file"""
                            with open(checkpoint_file, 'r') as lcp_input_file:
                                lcp_input_file.seek(0)
                                lcp_line = lcp_input_file.readline()
                                latest_cp = lcp_line

                        if latest_cp:
                            """ Save file's latest_cp value as KV store checkpoint"""
                            helper.save_check_point(checkpoint_name, latest_cp)
                            helper.log_info("[migrate_checkpoints] Migrated file checkpoint to KV for {}{}".format(input_name,checkpoint_name_suffix))
                    else:
                        helper.log_info("Checkpoint {} already exists in KV store. No migration necessary".format(checkpoint_name))

                    """ Remove old checkpoint file once done """
                    try: 
                        os.remove(checkpoint_file)
                        helper.log_info("[migrate_checkpoints] Deleted legacy checkpoint file {}".format(checkpoint_file))
                    except Exception as exception:
                        msg = "[migrate_checkpoints] Could not remove checkpoint file {}. Exception: {}".format(checkpoint_file,repr(exception))
                        helper.log_critical(msg)
                        sys.exit(msg)

        """ Try removing legacy chekpoints directory if empty"""
        if not os.listdir(checkpoint_dir):
            try: 
                os.rmdir(checkpoint_dir)
            except Exception as exception:
                msg = "[migrate_checkpoints] Could not remove empty checkpoints directory {}. Exception: {}".format(checkpoint_dir,repr(exception))
                helper.log_critical(msg)
                sys.exit(msg)
        else:
            helper.log_info("[migrate_checkpoints] There are still some files in the checkpoints directory, probably belonging to other inputs")
        
        helper.log_info("Checkpoints migration done")

    else:
        helper.log_info("[migrate_checkpoints] No checkpoints migration necessary")

def get_sourcetype_for_report(report):
    """ Calculate sourcetype based on report name"""

    if report == 'alert_v0':
        sourcetype = 'oit:alerts'
    elif report in ('user_command_activity_v0', 'user_interface_activity_v0'):
        sourcetype = 'oit:useractivity'
    elif report == 'user_file_activity_v0':
        sourcetype = 'oit:fileactivity'
    elif report == 'user_messaging_actions_activity_v0':
        sourcetype = 'oit:emailactivity'
    # added in v3.1.0
    elif report == 'audit_configuration_v0':
        sourcetype = 'oit:audit:configuration'
    elif report == 'audit_logins_v0':
        sourcetype = 'oit:audit:logins'
    elif report == 'audit_saved_sessions_v0':
        sourcetype = 'oit:audit:savedsessions'
    elif report == 'audit_session_playback_v0':
        sourcetype = 'oit:audit:sessionplayback'
    elif report == 'system_events_v0':
        sourcetype = 'oit:systemevents'
    elif report == 'user_dba_activity_v0':
        sourcetype = 'oit:dbaactivity'
    elif report == 'user_session_v0':
        sourcetype = 'oit:usersession'     
    else:
        sourcetype = re.sub('^', 'oit:', re.sub('(_|-)', ':', report))
    return(sourcetype)	


def collect_events(helper, ew):
    """ Poll reports and index events in Splunk """
    helper.log_info("Start processing configuration")
    """ Get inputs from user """
    app_name = helper.get_app_name()
    input_name = helper.get_input_stanza_names()
    reports_api_url = helper.get_arg('reports_api_url')
    parsed_url = urlparse(reports_api_url)
    observeit_api_host = parsed_url.hostname
    http_method = "GET"
    proxy_settings = helper.get_proxy()
    reports_to_collect = helper.get_arg('reports_to_collect')
    client_id = helper.get_arg('client_id')
    client_secret = helper.get_arg('client_secret')
    ##ssl_verification = helper.get_arg('ssl_verification')
    ssl_verification = True
    events_pagination = helper.get_arg('events_pagination')
    past_data_hours = helper.get_arg('past_data_hours')
    api_token = helper.get_arg('authorization_token')
    checkpoint_dir = os.path.join(os.environ['SPLUNK_DB'],'modinputs','observeit_api')
    timeout_conf = 360
    timeout = int(timeout_conf)


    if helper.get_arg("ca_certificate_chain"):
        ca_certificate_chain = helper.get_arg("ca_certificate_chain")
        ca_chain_file=os.path.join(os.environ['SPLUNK_HOME'], ca_certificate_chain)
        helper.log_debug("[config] CA chain file is: %s" % ca_chain_file)
    else:
        ca_chain_file=ssl_verification
        helper.log_info("[config] Using default CA certificate chain: {certifi.where()}")

    """ Set Proxy flag according to user choice """
    use_proxy = bool(proxy_settings)

    subtract_hours = timedelta(hours=int(past_data_hours))
    initial_cp = datetime.utcnow() - subtract_hours
    initial_cp = initial_cp.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    helper.log_debug("End processing configuration")
    
    """ Get a token """
    try:
        api_token = None
        try:
            api_token = get_stored_token(helper, client_id)
        except CredentialNotExistException as err:
            pass
        except Exception as exception1:
            helper.log_warning("Error getting token from secure storage. Requesting a new one. Exception: {}".format(repr(exception1)))
        if not api_token:
            api_token = get_and_store_token(helper, parsed_url, client_id, client_secret, ca_chain_file, timeout, use_proxy)
    except Exception as exception2:
        msg = "Report collection terminated due to authentication failure: {}".format(repr(str(exception2)))
        helper.log_error(msg)
        sys.exit(msg)

    helper.log_debug("Start collecting loop")
    migrate_checkpoints(helper, app_name, input_name, checkpoint_dir, reports_to_collect)

    """ Iterate over all selected reports """
    for report in reports_to_collect:
        checkpoint_name = app_name + "_" + input_name + "_" + report
        checkpoint_name_pdh = checkpoint_name + ".past_data_hours"
        
        """ Set custom sourcetype per collected report """
        custom_sourcetype = get_sourcetype_for_report(report)

        """ Delete Checkpoint  if the past data hours value has changed
            Write new past data hours value to checkpoint_name_pdh
        """
        new_past_data_hours = False

        previous_past_data_hours = helper.get_check_point(checkpoint_name_pdh)
        helper.log_debug("Past Data Hours OLD {} NEW {}".format(previous_past_data_hours, past_data_hours))

        if previous_past_data_hours and previous_past_data_hours != past_data_hours:
            new_past_data_hours = True
            if helper.get_check_point(checkpoint_name):
                helper.log_warning("Past data hours value changed from {} to {}. Checkpoint removed!".format(previous_past_data_hours, past_data_hours))
                helper.delete_check_point(checkpoint_name)

        if not previous_past_data_hours:
            new_past_data_hours = True

        if new_past_data_hours:
            helper.save_check_point(checkpoint_name_pdh, past_data_hours)

        """ Retrieve the latest saved checkpoint value for report being collected
            Log exception for failure and stop script execution.
        """
        try:
            latest_cp=helper.get_check_point(checkpoint_name)
            if not latest_cp:
                """ Initialize checkpoint if not defined. """
                latest_cp = str(initial_cp)
                helper.save_check_point(checkpoint_name, latest_cp)
            helper.log_debug("Starting event collection for report '{}' with checkpoint value: {}".format(report,latest_cp))
        except Exception as exception:
            msg = "Couldn't get checkpoint {} from KV store. Exception: {}".format(checkpoint_name,repr(exception))
            helper.log_critical(msg)
            sys.exit(msg)

        helper.log_debug("Start collecting events")
        """ Set URL per collected report  """
        url = reports_api_url + "/" + report + "/stream"

        """ Try collecting data from the API host. Log exception if failed."""
        try:
            try:
                helper.log_debug("Attempting to get events from URL: {}?since={}&limit={}".format(url,latest_cp,events_pagination))
                response = helper.send_http_request(url, method=http_method,
                                                    headers={
                                                        'Authorization': 'Bearer ' + api_token,
                                                        'accept' : 'application/json'
                                                    },
                                                    verify=ca_chain_file,
                                                    parameters={
                                                        'since': latest_cp,
                                                        'limit': events_pagination
                                                    },
                                                    use_proxy=use_proxy, timeout=timeout)
                response.raise_for_status()
            except HTTPError as e:
                # If 401, get a new token and retry.
                if e.response.status_code == 401:
                    api_token = get_and_store_token(helper, parsed_url, client_id, client_secret, ca_chain_file, timeout, use_proxy)
                    helper.log_debug("Reauthenticated and attempting to get events from URL: {}?since={}&limit={}".format(url,latest_cp,events_pagination))
                    response = helper.send_http_request(url, 
                                                        method=http_method, 
                                                        headers={
                                                            'Authorization': 'Bearer ' + api_token, 
                                                            'accept' : 'application/json'}, 
                                                        verify=ca_chain_file, 
                                                        parameters={
                                                            'since': latest_cp, 
                                                            'limit': events_pagination}, 
                                                        use_proxy=use_proxy, 
                                                        timeout=timeout)
                    response.raise_for_status()
                else:
                    # Some other error besides an expired token, just re-raise exception
                    raise
        except Exception as exception:
            msg = 'Failed to download data from {}. Error: {}.'.format(observeit_api_host, repr(exception))
            helper.log_critical(msg)
            helper.log_debug(traceback.format_exc())
            sys.exit(msg)

        helper.log_debug("End collecting events")

        helper.log_debug("Start processing events")
        """ Iterate on json_data list, then iterate on events from json_data list.
            Log exception for failure.
        """
        try:
            current_cp = None
            counter = 0
            try:
                response_data=json.loads(response.text)['data']
            except ValueError:
                msg = "Failure parsing response for report {} - Server response is not JSON. Response Content: \n{}".format(report,response.text)
                helper.log_critical(msg)
                sys.exit(msg)
                
            for entry in response_data:
                """ risingValue field of the event used for checkpoint time field
                    Since we receive JSON already sorted by risingValue field,
                    there is no need to calculate the max. time checkpoint.
                    Latest event always will be a last event.
                """
                current_cp = entry['risingValue']
                """ Dump each event into JSON """
                entry = json.dumps(entry, sort_keys=True)
                """ Write events to index with provided API Host as host and sourcetype customized per collected report """
                event = helper.new_event(source=helper.get_input_type(),
                                         index=helper.get_output_index(),
                                         sourcetype=custom_sourcetype,
                                         host=observeit_api_host,
                                         data=entry)
                ew.write_event(event)
                counter += 1
        except Exception as exception:
            msg = "Failure: {}. Report: {}.".format(repr(exception),report)
            helper.log_critical(msg)
            sys.exit(msg)

        helper.log_debug("Received {} events for report '{}'".format(counter,report))
        helper.log_debug("End processing events")

        """ Write the latest checkpoint value to the file """
        if current_cp is not None:
            helper.log_debug("Writing latest seen checkpoint value for report '{}' is: {}".format(report,current_cp))
            helper.save_check_point(checkpoint_name, current_cp)
            
    helper.log_debug("End collecting loop")
