#!/usr/bin/env python
# encoding = utf-8

#Python Imports
import re
from datetime import datetime
import json
import time

class Post_to_Splunk():

    def post_to_Splunk(device_data, splunk_ckpt, log_label, stanza_checkpoint, time_stamp, helper, ew):

        record_chkpt = False
        seen_aids = set()
        deduplicated = []
        previous_ckpt = splunk_ckpt

        for d in device_data:
            falcon_aid = d['falcon_device']['device_id']
            event_ts = d['ta_data']['Timestamp_value']

            if falcon_aid in seen_aids:
                helper.log_debug(f'{log_label} Duplicate AID removed: {falcon_aid}')
                continue

            seen_aids.add(falcon_aid)

            checkpoint_dt = datetime.strptime(re.sub(r'\.\d+', '', splunk_ckpt), '%Y-%m-%dT%H:%M:%SZ')
            event_dt = datetime.strptime(re.sub(r'\.\d+', '', event_ts), '%Y-%m-%dT%H:%M:%SZ')

            if event_dt > checkpoint_dt:
                helper.log_debug(f'{log_label} New checkpoint detected for AID {falcon_aid} = {event_dt}')
                splunk_ckpt = event_ts
                record_chkpt = True

            deduplicated.append(d)

        device_data = deduplicated

        try:
            helper.log_info(f'{log_label} Preparing to send event data to Splunk for indexing into {helper.get_output_index()}')
            event_data = '\n'.join(json.dumps(line) for line in device_data)
            falcon_device = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
            ew.write_event(falcon_device)
            num_aids = len(seen_aids)
            helper.log_info(f'{log_label} Device processing completed for {num_aids} device IDs, posted to {helper.get_output_index()}')
            helper.log_debug(f'{log_label} Device IDs posted: {seen_aids}')

        except Exception as e:
            helper.log_error(f'{log_label} Error posting data to Splunk: {e}')
            raise RuntimeError(f'Failed to post data to Splunk: {e}') from e

        #Save Checkpoint Data — retry to prevent duplicate ingestion on next run
        if record_chkpt:
            checkpoint_key = time_stamp
            checkpoint = {checkpoint_key: str(splunk_ckpt)}
            checkpoint_saved = False

            for attempt in range(1, 4):
                try:
                    helper.save_check_point(stanza_checkpoint, checkpoint)
                    helper.log_info(f'{log_label} Checkpoint saved: old={previous_ckpt} new={splunk_ckpt}')
                    checkpoint_saved = True
                    break

                except Exception as e:
                    helper.log_error(f'{log_label} Checkpoint save attempt {attempt}/3 failed: {e}')
                    if attempt < 3:
                        time.sleep(2 * attempt)

            if not checkpoint_saved:
                helper.log_error(
                    f'{log_label} CRITICAL - Checkpoint save failed after 3 attempts. '
                    f'Data was written to Splunk but checkpoint was not updated. '
                    f'Next run may produce duplicate data. '
                    f'Checkpoint value that failed to save: {checkpoint}'
                )
                raise RuntimeError(f'Checkpoint save failed - stopping to prevent further duplicate data')
        else:
            helper.log_info(f'{log_label} No new checkpoint detected')

        return splunk_ckpt              