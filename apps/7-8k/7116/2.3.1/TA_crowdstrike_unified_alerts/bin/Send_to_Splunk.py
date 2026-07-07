from operator import index

import json
import sys

class Post_to_Splunk():

    def send_to_splunk(event_data, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew):
        data_index=helper.get_output_index()
        update_checkpoint = False

        helper.log_debug(f"{log_label}: Create TA data sections")
        for line in event_data:
            line['ta_data']=ta_data

            if 'updated_timestamp' in line.keys():
                if line['updated_timestamp'] > checkpoint:
                    new_checkpoint = line['updated_timestamp']
                    helper.log_debug(f"{log_label}: New Checkpoint value identified as {new_checkpoint}")
                    update_checkpoint = True
            else:
                helper.log_debug(f"{log_label}: No updated_timestamp field found")
        
        try:
            helper.log_info(f"{log_label}: Preparing to send: {len(event_data)} events to Splunk index: {data_index}")            
            events = '\n'.join(json.dumps(line) for line in event_data)
            die_detections_data = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=events)
            ew.write_event(die_detections_data)
            helper.log_info(f"{log_label}: Data for {len(event_data)} events successfully pushed to Splunk index: {data_index}")

        except Exception as e:
            helper.log_error(f"{log_label}: Data for {len(event_data)} events could not be pushed to Splunk. Please ensure that the TA and Splunk are properly configured")
            helper.log_error(f"{log_label}: {e}")
            sys.exit()
        
        if update_checkpoint:
            helper.log_info(f"{log_label}: Checkpoint is being updated")
            try:
                ts_field='updated_timestamp'
                rec_checkpoint={ts_field:str(new_checkpoint)}
                helper.log_debug(f"{log_label}: Checkpoint value = {rec_checkpoint}")
                helper.save_check_point(stanza_checkpoint, rec_checkpoint)
                helper.log_info(f"{log_label}: Checkpoint was recorded {rec_checkpoint}")
                checkpoint = new_checkpoint

            except Exception as e:
                helper.log_error(f"{log_label}: Unable to record timestamp checkpoint data")
                helper.log_error(f"{log_label}: Error reports was - {e}")
                helper.log_error(f"{log_label}: Checkpoint data is not able to be recorded, please correct the issue and restart the collection - TA is shutting down")
                sys.exit()
        else:
            helper.log_info(f"{log_label}: No new checkpoint was detected")

        return checkpoint