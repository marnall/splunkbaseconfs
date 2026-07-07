
#!/usr/bin/env python
# encoding = utf-8
import re
import random
import time
from datetime import datetime
from Status_Code_Errors import status_code_errors
from Post_to_Splunk import Post_to_Splunk

RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF = 5
DEVICE_PAGE_LIMIT = 5000
ONLINE_STATE_BATCH_SIZE = 100
DEFAULT_CHECKPOINT = '2000-01-01T00:00:01Z'
SESSION_HASH_BITS = 45

def _command_with_retry(falcon, command, log_label, helper, **kwargs):
    """Execute a FalconPy command with rate-limit retry and token expiry handling.

    Must be called before status_code_errors() — by the time
    status_code_errors sees a 429, retries are already exhausted
    and the error is genuinely fatal.
    """
    for attempt in range(RATE_LIMIT_RETRIES + 1):
        response = falcon.command(command, **kwargs)
        status_code = response.get('status_code', 0) if isinstance(response, dict) else 0

        # Handle token expiry — attempt re-authentication once
        if status_code == 401 and attempt == 0:
            helper.log_warning(f'{log_label} Token expired (401) on {command}, attempting re-authentication')
            try:
                falcon.authenticate()
                if falcon.authenticated():
                    helper.log_info(f'{log_label} Re-authentication successful, retrying {command}')
                    continue
                else:
                    helper.log_error(f'{log_label} Re-authentication failed for {command}')
            except Exception as e:
                helper.log_error(f'{log_label} Re-authentication exception during {command}: {type(e).__name__}: {e}')
            return response

        # Handle rate limiting and server errors
        if status_code == 429 or status_code >= 500:
            if attempt < RATE_LIMIT_RETRIES:
                wait = RATE_LIMIT_BACKOFF * (2 ** attempt) + random.uniform(0, 1)
                helper.log_warning(f'{log_label} Retryable error ({status_code}) on {command}, retrying in {wait:.1f}s (attempt {attempt + 1}/{RATE_LIMIT_RETRIES})')
                time.sleep(wait)
                continue
            else:
                helper.log_error(f'{log_label} {command} failed with {status_code} after {RATE_LIMIT_RETRIES} retries')
                return response

        if attempt > 0:
            helper.log_info(f'{log_label} {command} succeeded after {attempt} retries')

        return response
    return response


def _filter_online_only(falcon, device_response, log_label, helper):
    """Filter device records to only those currently online.

    Extracts device_ids from full records, checks online status in batches
    of ONLINE_STATE_BATCH_SIZE via GetOnlineState_V1, returns only online device records.
    """
    device_map = {d['device_id']: d for d in device_response}
    all_ids = list(device_map.keys())
    online_ids = []

    for i in range(0, len(all_ids), ONLINE_STATE_BATCH_SIZE):
        batch = all_ids[i:i+ONLINE_STATE_BATCH_SIZE]
        try:
            response = _command_with_retry(falcon, 'GetOnlineState_V1', log_label, helper, ids=batch)
        except Exception as e:
            helper.log_error(f'{log_label} Online status API call failed: {e}')
            raise RuntimeError(f'Online status API call failed: {e}') from e

        status_code_errors(response, 'Device Online Status', log_label, helper)

        for entry in response.get('body', {}).get('resources', []):
            state = entry.get('state', '')
            if state == 'online':
                online_ids.append(entry.get('id', ''))

    helper.log_info(f'{log_label} Online filter: {len(online_ids)}/{len(all_ids)} devices online')
    return [device_map[did] for did in online_ids if did in device_map]


class Get_CS_Devices():

    def get_CS_devices(falcon, stanza_checkpoint, platform, online_only, version,
                       stanza_name, time_stamp, api_endpoint, ew, log_label, helper):
        """Collect CrowdStrike device records via CombinedDevicesByFilter with pagination.

        Retrieves device inventory from the CrowdStrike API using FQL filters for
        timestamp, platform, and optional online-only filtering. Manages checkpoint
        state for incremental collection and delivers events to Splunk via Post_to_Splunk.
        """

        device_limit = DEVICE_PAGE_LIMIT
        device_counter = 0
        start_date = helper.get_arg('start_date')

        #look for optional filter selections
        if platform == 'all':
            filter_by_os = False
        else:
            filter_by_os = True

        if start_date:
            filter_by_start = True
            start_date = start_date + 'T00:00:01Z'
        else:
            filter_by_start = False

        #look for and retrieve any checkpoint timestamp for the input
        try:
            checkpoint_timestamp = helper.get_check_point(stanza_checkpoint)
            if checkpoint_timestamp is None:
                helper.log_info(f'{log_label} No checkpoint data was found for the {time_stamp} timestamp type for this input.')
                checkpoint_found = False
            else:
                checkpoint = checkpoint_timestamp[time_stamp]
                if checkpoint and str(checkpoint) != 'None':
                    helper.log_info(f'{log_label} Checkpoint data retrieved for {time_stamp}: {checkpoint}')
                    checkpoint_found = True
                else:
                    helper.log_info(f'{log_label} Checkpoint exists but {time_stamp} value is empty or None')
                    checkpoint_found = False

        except (KeyError, TypeError) as e:
            helper.log_error(f'{log_label} Checkpoint data exists but could not be parsed: {checkpoint_timestamp}')
            helper.log_error(f'{log_label} Checkpoint parse error: {e}')
            raise RuntimeError(
                f'{log_label} Corrupted checkpoint data — manual intervention required to prevent duplicate ingestion'
            ) from e

        filter_by_online = online_only

        helper.log_debug(f'{log_label} Filtering Logic Settings - Filter by OS = {filter_by_os} |  Filter by start date = {filter_by_start} |  Filter by Online Only = {filter_by_online}')

        #if a checkpoint is found any customer startdate will not be used
        if checkpoint_found == True:
            splunk_ckpt = checkpoint

        elif filter_by_start == True:
            splunk_ckpt = start_date

        #if neither a custom startdate or checkpoint is found, this is the default
        else:
            splunk_ckpt = DEFAULT_CHECKPOINT

        #API query arguments
        time_filter = f"{time_stamp}:>'{splunk_ckpt}'"
        sort_val = f"{time_stamp}.asc"
        bkup_ckpt = splunk_ckpt

        #query filter expansion for OS filter selection
        if filter_by_os == True:
            fql_filter = f"{time_filter}+platform_name:'{platform}'"
        else:
            fql_filter = time_filter

        session_hash = random.getrandbits(SESSION_HASH_BITS)

        #paginated loop using CombinedDevicesByFilter — returns full device records directly
        next_token = None
        pagination_needed = True

        while pagination_needed:

            params = {
                'limit': device_limit,
                'sort': sort_val,
                'filter': fql_filter
            }
            if next_token:
                params['offset'] = next_token

            helper.log_debug(f'{log_label} CombinedDevicesByFilter request: filter={fql_filter}, limit={device_limit}, sort={sort_val}, offset={next_token}')

            try:
                response = _command_with_retry(
                    falcon, 'CombinedDevicesByFilter', log_label, helper,
                    parameters=params
                )
            except Exception as e:
                helper.log_error(f'{log_label} Device combined API call failed: {e}')
                raise RuntimeError(f'Device combined API call failed: {e}') from e

            status_code_errors(response, 'Device Combined', log_label, helper)

            body = response.get('body', {})
            meta = body.get('meta', {})
            pagination = meta.get('pagination', {})
            total_count = pagination.get('total', 0)
            next_token = pagination.get('next')
            api_data = meta
            device_response = body.get('resources', [])

            helper.log_debug(f'{log_label} CombinedDevicesByFilter response: status={response.get("status_code", "N/A")}, total={total_count}, next_token={next_token}, resources={len(device_response) if device_response else 0}')

            #determine if there were no devices returned from the query
            if not device_response:
                if device_counter == 0:
                    helper.log_info(f'{log_label} No devices identified for collection')
                    return
                break

            batch_size = len(device_response)
            device_counter += batch_size

            if device_counter == batch_size:
                helper.log_info(f'{log_label} The amount of devices that have been identified = {total_count}')

            helper.log_info(f'{log_label} Retrieved {batch_size} devices ({device_counter}/{total_count})')

            #if the online only option is selected, filter to online devices
            if online_only == True:
                device_response = _filter_online_only(falcon, device_response, log_label, helper)
                if not device_response:
                    helper.log_debug(f'{log_label} There were no device IDs identified as online in this batch')
                    #don't advance checkpoint — no data written for this batch
                    if device_counter >= total_count or not next_token:
                        pagination_needed = False
                    continue

            #build event structures
            device_data = []
            for device in device_response:
                ts_value = device.get(time_stamp)
                if not ts_value:
                    helper.log_warning(f'{log_label} Device {device.get("device_id", "unknown")} missing {time_stamp}, skipping')
                    continue
                device_event = {}
                device_event['metadata']                   = api_data
                device_event['falcon_device']              = device
                device_event['ta_data']                    = {'Cloud_environment':api_endpoint, 'Input':stanza_name, 'TA_version': str(version), 'Online_only': online_only, 'Session_hash': session_hash, 'Timestamp_field':str(time_stamp), 'Timestamp_value':str(ts_value)}

                device_data.append(device_event)

            #sort data by timestamp to help streamline checkpoint recording
            device_data = sorted(device_data, reverse=False, key=lambda r: datetime.strptime(re.sub(r'\.\d+', '', r['ta_data']['Timestamp_value']), '%Y-%m-%dT%H:%M:%SZ'))

            #send data to be processed into the forwarder
            splunk_ckpt = Post_to_Splunk.post_to_Splunk(device_data, splunk_ckpt, log_label, stanza_checkpoint, time_stamp, helper, ew)

            #handle an empty return from the on-line only check
            if splunk_ckpt is None:
                splunk_ckpt = bkup_ckpt

            device_data_total = len(device_data)
            if online_only == True:
                helper.log_info(f'{log_label} Successfully collected device details for {device_data_total} device IDs reported as On-Line')
            else:
                helper.log_info(f'{log_label} Successfully collected device details for {device_data_total} device IDs reported')

            #determine if pagination is complete
            if device_counter >= total_count or not next_token:
                pagination_needed = False
            else:
                helper.log_info(f'{log_label} Continuing pagination calls - {device_counter}/{total_count} devices collected')

        helper.log_info(f'{log_label} Collection completed successfully')
        return
