#!/usr/bin/env python
# encoding = utf-8

import json


class Post_to_Splunk():

    def post_to_Splunk(**kwargs):

        indicator_data      = kwargs['indicator_data']
        chkpt_type          = kwargs['chkpt_type']
        splunk_ckpt         = kwargs['splunk_ckpt']
        version             = kwargs['version']
        deleted             = kwargs['deleted']
        stanza_name         = kwargs['stanza_name']
        stanza_checkpoint   = kwargs['stanza_checkpoint']
        api_endpoint        = kwargs['api_endpoint']
        log_label           = kwargs['log_label']
        ew                  = kwargs['ew']
        helper              = kwargs['helper']

        # gets the index name from the config
        index = str(helper.get_output_index())

        # creates the TA data section
        ta_data = {'Cloud_environment': api_endpoint, 'Input': stanza_name, 'TA_version': version, 'Include_deleted': deleted}
        updated_indicators = []

        helper.log_info(f'{log_label} Adding TA data to indicators')

        # adds TA data section to each event
        for d in indicator_data:
            updated = d['last_updated'] > d['published_date']
            d['ta_data'] = {**ta_data, 'Updated_indicator': updated}
            updated_indicators.append(d)

            marker = d['_marker']
            if chkpt_type == '_marker':
                if str(splunk_ckpt) > str(marker):
                    chkpt_value = splunk_ckpt
                else:
                    chkpt_value = marker

            elif chkpt_type == 'last_updated':
                chkpt_value = marker
                chkpt_type = '_marker'

        helper.log_debug(f'{log_label} Creating bulk upload package')
        # preps data for bulk upload
        event_data = '\n'.join(json.dumps(line) for line in updated_indicators)
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)

        helper.log_debug(f'{log_label} Attempting to log event into Splunk')
        try:
            ew.write_event(event)
            helper.log_info(f'{log_label} Sent Intel data to Splunk for indexing to index: {index}')
        except BrokenPipeError:
            helper.log_error(f'{log_label} BrokenPipeError writing to Splunk — splunkd closed the event pipe. Events written before this error are indexed; remaining events will be collected on next run.')
            raise RuntimeError(f'BrokenPipeError writing to Splunk')
        except Exception as e:
            helper.log_error(f'{log_label} Unable to send data to Splunk: {type(e).__name__}: {e}')
            raise RuntimeError(f'Unable to send data to Splunk: {e}')

        # Save Checkpoint Data
        helper.log_debug(f'{log_label} Checkpoint value will be: {chkpt_value}')
        try:
            checkpoint_key = 'last_marker'
            checkpoint = {checkpoint_key: str(chkpt_value)}
            helper.log_debug(f'{log_label} Checkpoint value = {checkpoint}')
            helper.save_check_point(stanza_checkpoint, checkpoint)
            helper.log_info(f'{log_label} Checkpoint was recorded as {checkpoint}')

        except Exception as e:
            helper.log_error(f'{log_label} Unable to record checkpoint data: {type(e).__name__}: {e}. Data was written to Splunk but checkpoint was not saved — duplicates may occur on next run.')
            raise RuntimeError(f'Unable to record checkpoint data: {e}')

        helper.log_info(f'{log_label} Intel Indicators processing completed for {len(updated_indicators)} indicators - posted to Splunk Index: {index}')
