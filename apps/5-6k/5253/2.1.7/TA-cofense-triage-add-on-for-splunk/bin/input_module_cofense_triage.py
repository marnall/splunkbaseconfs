# encoding = utf-8

import os
import json
import sys
import time
import traceback

from requests.compat import quote_plus
from datetime import datetime, timedelta
import splunk.rest as rest
from CofenseConnect import CofenseClient, constants
import cofense_triage_custom_exceptions as CE

my_app = __file__.split(os.sep)[-3]


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza
    configurations."""
    pass


def utcformat(dt):
    """Convert datetime object to string in UTC format (
    YYYY-mm-ddTHH:MM:SS.mmmZ)."""
    try:
        iso_str = "{}{}".format(
            datetime.strftime(dt, "%Y-%m-%dT%H:%M:%S.%f")[:-3], "Z")
        return iso_str
    except Exception:
        return None


def timestring_to_datetime(timestr):
    """Utility to convert a timestring in YYYY-MM-DD HH:MM:SS format to a
    datetime object."""
    try:
        dt_object = datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S')
        return dt_object
    except Exception:
        return None


def uncheck_reingest(helper):
    """Method to uncheck re-ingest checkbox using rest call."""
    input_name = helper.get_input_stanza_names()
    input_name = quote_plus('://{}'.format(input_name))
    params = 're_ingest=0'
    try:
        session_key = helper.context_meta['session_key']
        response_status, response_content = rest.simpleRequest(
            '/servicesNS/nobody/{}/configs/conf-inputs/cofense_triage{}?{'
            '}'.format(
                str(my_app), str(input_name), str(params)),
            sessionKey=session_key,
            method='POST',
            raiseAllErrors=True
        )
        helper.log_info(
            'Reingest unchecked for input {}'.format(input_name[9:]))
    except Exception:
        helper.log_error('Failed to uncheck reingest checkbox.')
        raise CE.UnknownError(traceback.format_exc())


def ingest_data_into_splunk(data, host, helper, ew, cofense_client,
                            single_event=False):
    """Method to ingest data into Splunk.

    param data: raw data in list format
    param host: host name
    param helper: helper module object
    param ew: event writer object
    param single_event: determine if event is single event or list of events
    """
    endpoint = helper.get_arg('endpoint')
    sourcetype = 'cofense:triage:{}'.format(endpoint)
    feed_list = ['reports', 'reports_inbox', 'reports_processed',
                 'reports_reconnaissance', 'clusters', 'attachments',
                 'categories']
    if endpoint in ['reports_inbox', 'reports_processed',
                    'reports_reconnaissance']:
        endpoint = endpoint[:7]
    feed_option = helper.get_arg(f"{endpoint}_feed")
    if not single_event:
        for data_object in data:
            try:
                if feed_option:
                    if endpoint in feed_list:
                        id = data_object["id"]
                        feed_dict = relationship_dict(cofense_client, helper,
                                                      id,
                                                      constants.ENDPOINTS[
                                                          endpoint], feed_option)
                        for key, value in feed_dict.items():
                            data_object["relationships"][key] = value
                if helper.get_arg('exclude_field'):
                    if endpoint == 'categories':
                        for field in helper.get_arg('exclude_field'):
                            reports = data_object.get('relationships',
                                                      {}).get('reports', [])
                            if isinstance(reports, list):
                                for report in reports:
                                    report.get('attributes', {}).pop(field, None)
                    else:
                        for field in helper.get_arg('exclude_field'):
                            data_object.get('attributes', {}).pop(field, None)

                event = helper.new_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    host=host,
                    sourcetype=sourcetype,
                    data=json.dumps(data_object)
                )
                ew.write_event(event)
            except Exception:
                helper.log_error(
                    'Failed to write data into Splunk for input: {}'.format(
                        helper.get_input_stanza_names()))
                raise CE.DataIngestionError(traceback.format_exc())
    else:
        try:
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                host=host,
                sourcetype=sourcetype,
                data=json.dumps(data)
            )
            ew.write_event(event)
        except Exception:
            helper.log_error(
                'Failed to write data into Splunk for input: {}'.format(
                    helper.get_input_stanza_names()))
            raise CE.DataIngestionError(traceback.format_exc())


def relationship_dict(cofense_client, helper, id, endpoint, feed_option):
    helper.log_info("in relation function")
    feed_key_dict = {
        'domains': 'domain',
        'urls': 'url',
        'hostnames': 'hostname',
        'reporter': 'email',
        'threat_indicators': 'attributes',
        'comments': 'attributes',
        'attachments': 'attributes',
        'attachment_payload': 'attributes',
        'reports': 'attributes',
        'headers': 'attributes'
    }

    all_feed_dict = {}
    for feed in feed_option:
        feed_list = []
        relation_endpoint = f'{endpoint}/{id}/{feed}'
        if feed not in ["reporter", 'attachment_payload']:
            last_page = pagination = False
            while not last_page:
                response = cofense_client.get_data(relation_endpoint,
                                                   pagination)
                data = response['data']
                for obj in data:
                    if feed in ['threat_indicators', 'comments',
                                'attachments', 'headers', 'reports']:
                        new = {
                            'id': obj.get("id", None),
                            feed_key_dict[feed]: obj.get("attributes", {})
                        }
                    else:
                        new = {
                            "id": obj.get("id", None),
                            feed_key_dict[feed]: obj.get("attributes",
                                                         {}).get(
                                feed_key_dict[feed], "")
                        }
                    feed_list.append(new)
                if 'next' in response["links"]:
                    relation_endpoint = str(response['links']['next'])
                    pagination = True
                else:
                    last_page = True
        else:
            response = cofense_client.get_data(relation_endpoint, False)
            data = response['data']
            if feed == 'reporter':
                new = {
                    'id': data.get('id', None),
                    'reporter_email': data.get('attributes', {}).get('email',
                                                                     {})
                }
            else:
                new = {
                    'id': data.get("id", None),
                    feed_key_dict[feed]: data.get("attributes", {})
                }
            feed_list.append(new)
        all_feed_dict[feed] = feed_list
    return all_feed_dict


def collect_data_with_pagination(
    cofense_client, host_url, helper, ew, start_time=None, end_time=None
):
    """Method to collect data which might be distributed in multiple pages.

    >>> Required Params
    :param cofense_client: cofense client object for assisting API calls
    :param helper: Splunk ModInput helper class
    :param ew: Event Writer for ingesting data into Splunk
    :param host_url: formed URL with endpoint and scheme
    >>> Optional params:
    :param start_time:
    :param end_time:
    """
    helper.log_info("Starting data collection")
    input_name = helper.get_input_stanza_names()
    endpoint = helper.get_arg("endpoint")
    pagination = False
    last_page = False
    first_page = True
    data_count = 0
    # Runtime dedup
    seen_records = set()
    # Load checkpoint
    current_checkpoint = helper.get_check_point(input_name) or {}
    checkpoint_time = current_checkpoint.get("updated_at")
    checkpoint_ids = set(current_checkpoint.get("ids", []))
    helper.log_info(f"Loaded checkpoint time: {start_time}")
    helper.log_debug(f"Checkpoint ids: {len(checkpoint_ids)}")
    re_ingest = helper.get_arg('re_ingest')

    try:
        while not last_page:
            response = cofense_client.get_data(
                endpoint, pagination, start_date=start_time, end_date=end_time
            )

            if not response or not response.get("data"):
                helper.log_info("No data returned from API")
                break
            collected_data = []
            page_latest_time = checkpoint_time
            page_latest_ids = set()

            for record in response["data"]:
                record_id = record["id"]
                record_time = record["attributes"]["updated_at"]
                record_key = (record_id, record_time)
                # Runtime dedup (same id + timestamp)
                if record_key in seen_records:
                    continue
                seen_records.add(record_key)
                # Checkpoint filtering
                if checkpoint_time:
                    if record_time < checkpoint_time:
                        continue
                    if record_time == checkpoint_time and record_id in checkpoint_ids:
                        continue
                collected_data.append(record)
                # Track newest record in this page
                if not page_latest_time or record_time > page_latest_time:
                    page_latest_time = record_time
                    page_latest_ids = {record_id}
                elif record_time == page_latest_time:
                    page_latest_ids.add(record_id)
            # Ingest events
            if collected_data:
                ingest_data_into_splunk(
                    collected_data, host_url, helper, ew, cofense_client
                )
                if first_page and re_ingest:
                    uncheck_reingest(helper)
                data_count += len(collected_data)
                # Update checkpoint AFTER ingestion
                checkpoint_time = page_latest_time
                checkpoint_ids = page_latest_ids
                helper.save_check_point(
                    input_name,
                    {"updated_at": checkpoint_time, "ids": list(checkpoint_ids)},
                )
                helper.log_debug(
                    f"Checkpoint updated → {checkpoint_time} "
                    f"({len(checkpoint_ids)} ids)"
                )
            # Pagination handling
            if response.get("links", {}).get("next"):
                endpoint = str(response["links"]["next"])
                pagination = True
                helper.log_debug("Fetching next page")
            else:
                last_page = True
                helper.log_info("No more pages available")

            first_page = False
    except Exception:
        helper.log_error(
            'Failed to collect data for input {} and endpoint {}'.format(
                input_name, endpoint))
        raise CE.DataCollectionError(input_name, endpoint,
                                     traceback.format_exc())
    finally:
        cofense_client.revoke_token()
        helper.log_debug(
            'Collected {} data objects for input {} and endpoint {}'.format(
                data_count, input_name, endpoint))


def collect_data_without_pagination(
        cofense_client,
        input_name,
        host_url,
        helper,
        ew
):
    """Method to collect data where there is no pagination logic required."""
    endpoint = helper.get_arg('endpoint')
    try:
        response = cofense_client.get_data(endpoint)
        if response['data'] != {}:
            ingest_data_into_splunk(response['data'], host_url, helper, ew,
                                    cofense_client, single_event=True)
    except Exception:
        helper.log_error(
            'Error while collecting data for input {} and endpoint {}'.format(
                input_name, endpoint))
        raise CE.DataCollectionError(input_name, endpoint,
                                     traceback.format_exc())
    finally:
        cofense_client.revoke_token()


def remove_checkpoint(helper):
    """Method to remove checkpoint."""
    input_name = helper.get_input_stanza_names()
    try:
        helper.log_debug(
            'Trying to delete checkpoint for input {}'.format(input_name))
        helper.delete_check_point(input_name)
    except Exception:
        helper.log_error(
            "Couldn't delete checkpoint for Input {}".format(input_name))
        raise CE.UnknownError(traceback.format_exc())


def check_all_data_collected(helper):
    """Method to validate if all data is collected based on checkpoint."""
    input_name = helper.get_input_stanza_names()
    endpoint = helper.get_arg('endpoint')
    current_checkpoint = helper.get_check_point(input_name)
    if current_checkpoint:
        helper.log_debug(
            'Found an existing checkpoint for input {} and endpoint {}'.format(
                input_name, endpoint))
        try:
            if current_checkpoint['all_data_collected']:
                helper.log_info(f'Data already collected for input {input_name} and endpoint {endpoint}')
                sys.exit()
        except KeyError:
            pass


def get_latest_starttime(helper, start_time):
    """Method to set start_time to the latest value."""
    input_name = helper.get_input_stanza_names()
    current_checkpoint = helper.get_check_point(input_name)
    if current_checkpoint and current_checkpoint['updated_at'] >= start_time:
        start_time = current_checkpoint['updated_at']
    return start_time


def collect_events(helper, ew):
    """Splunk default collect event method for core logic of data collection
    and ingestion."""
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))
    account = helper.get_arg('global_account')

    try:
        if not account:
            raise Exception("Invalid global_account for {}".format(input_name))
        endpoint = helper.get_arg('endpoint')
        if not endpoint:
            raise Exception(
                "Invalid endpoint {} for {}".format(endpoint, input_name))
        # Get client credentials for current input
        client_id = account.get("client_id")
        client_secret = account.get("client_secret")
        cofense_triage_host_url = '{}://{}'.format(constants.SCHEMA,
                                                   account.get(
                                                       "host_url").strip('/'))
        # Assuming all validations are in place
        # Data Fetching logic starts here ###
        if endpoint in ['status', 'executive_summary']:
            cofense = CofenseClient.CofenseClient(client_id, client_secret,
                                                  cofense_triage_host_url,
                                                  helper)
            data_collection_start_time = time.time()
            collect_data_without_pagination(
                cofense_client=cofense,
                input_name=input_name,
                host_url=cofense_triage_host_url,
                helper=helper,
                ew=ew
            )
            helper.log_info(
                'Data collected successfully (without pagination) in {} '
                'seconds.'.format(
                    time.time() - data_collection_start_time))
            sys.exit()

        start_time = helper.get_arg('start_time')
        end_time = helper.get_arg('end_time')
        re_ingest = helper.get_arg('re_ingest')
        if re_ingest:  # Remove already existing checkpoint for current Input
            # if user wants to re-ingest data
            remove_checkpoint(helper)
        if start_time:
            start_time = utcformat(
                timestring_to_datetime(helper.get_arg('start_time')))
        else:
            start_time = utcformat(datetime.now() - timedelta(
                days=constants.DEFAULT_START_TIMEDELTA))
        start_time = get_latest_starttime(helper, start_time)
        if end_time:
            end_time = utcformat(
                timestring_to_datetime(helper.get_arg('end_time')))
            check_all_data_collected(helper)
        data_collection_start_time = time.time()
        cofense = CofenseClient.CofenseClient(client_id, client_secret,
                                              cofense_triage_host_url, helper)
        collect_data_with_pagination(
            start_time=start_time,
            end_time=end_time,
            cofense_client=cofense,
            host_url=cofense_triage_host_url,
            helper=helper,
            ew=ew
        )
        helper.log_info(
            'Data collected successfully (with pagination) in {} '
            'seconds.'.format(
                time.time() - data_collection_start_time))

    except Exception:
        helper.log_error(
            'Data Collection failed {}'.format(traceback.format_exc()))
