# encoding = utf-8

#python imports
import json
import datetime
import time

def send_to_splunk(**kwargs):
    helper = kwargs['helper']
    ew = kwargs['ew']
    current_checkpoint = kwargs['current_checkpoint']
    old_checkpoint = current_checkpoint
    response_data = kwargs['response_data']
    log_label = kwargs['log_label']
    stanza_checkpoint = kwargs['stanza_checkpoint']
    meta = kwargs['meta']
    ta_data = kwargs['ta_data']
    remove_meta = kwargs['remove_meta']
    index = helper.get_output_index()

    helper.log_debug(f'{log_label} Preparing to send {len(response_data)} vulnerability events to Splunk')

    # No data to process — return without writing or updating checkpoint
    if not response_data:
        helper.log_info(f'{log_label} No vulnerability data to send to Splunk')
        return 'no_data', 'no checkpoint to save', current_checkpoint

    event_lines = []

    for vulnerability in response_data:
        vulnerability_event = {}
        vulnerability_event['ta_data'] = ta_data
        if not remove_meta:
            vulnerability_event['meta'] = meta

        vulnerability_event['falcon_spotlight'] = vulnerability

        event_lines.append(json.dumps(vulnerability_event))

    # Checkpoint: data is sorted ascending by updated_timestamp, so last item is the latest
    try:
        ts = response_data[-1]['updated_timestamp']
        # Parse timestamp, handling optional fractional seconds
        if '.' in ts:
            current_checkpoint = datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S.%fZ')
        else:
            current_checkpoint = datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')
    except (KeyError, TypeError, ValueError) as e:
        helper.log_error(f'{log_label} Cannot extract updated_timestamp from last record: {type(e).__name__}: {e}')
        raise RuntimeError(f'{log_label} API response missing required field: updated_timestamp') from e
    helper.log_debug(f'{log_label} Checkpoint set from latest record = {current_checkpoint}')

    try:
        #Posts events to Splunk's internal API
        helper.log_info(f'{log_label} Posting data to Splunk to be indexed to index: {index}')
        event_data = '\n'.join(event_lines)
        spotlight_post = helper.new_event(source=helper.get_input_type(), index=index, sourcetype=helper.get_sourcetype(), data=event_data)
        ew.write_event(spotlight_post)
        write_result = 'successful'
        helper.log_debug(f"{log_label} Sent {len(event_lines)} vulnerability events to Splunk for index {index}")
    
    except Exception as e:
        helper.log_error(f'{log_label} Error posting data to Splunk index {index}: {type(e).__name__}: {e}')
        raise RuntimeError(f'{log_label} Error posting data to Splunk index {index}') from e

    #Save Checkpoint Data — retry to prevent duplicate ingestion on next run
    checkpoint_key = 'updated_timestamp'
    checkpoint = {checkpoint_key: current_checkpoint.strftime('%Y-%m-%d %H:%M:%S.%f')}
    checkpoint_saved = False

    for attempt in range(1, 4):
        try:
            helper.save_check_point(stanza_checkpoint, checkpoint)
            helper.log_info(f'{log_label} Checkpoint saved: old={old_checkpoint} new={current_checkpoint}')
            checkpoint_result = f'success: last checkpoint recorded was {checkpoint}'
            checkpoint_saved = True
            break

        except Exception as e:
            if attempt < 3:
                delay = 2 * attempt
                helper.log_warning(f'{log_label} Checkpoint save attempt {attempt}/3 failed: {e} — retrying in {delay}s')
                time.sleep(delay)
            else:
                helper.log_error(f'{log_label} Checkpoint save attempt {attempt}/3 failed: {e}')

    if not checkpoint_saved:
        helper.log_error(f'{log_label} CRITICAL - Checkpoint save failed after 3 attempts. '
                         f'Data was written to Splunk but checkpoint was not updated. '
                         f'Next run may produce duplicate data. '
                         f'Checkpoint value that failed to save: {checkpoint}')
        raise RuntimeError(
            f'{log_label} Checkpoint save failed - stopping to prevent further duplicate data'
        )
    
    return write_result, checkpoint_result, current_checkpoint
    
