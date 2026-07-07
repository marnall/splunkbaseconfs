import json

class Post_to_Splunk():

    def send_to_splunk(event_data, checkpoint, stanza_checkpoint, log_label, ta_data, helper, ew):
        data_index=helper.get_output_index()
        update_checkpoint = False
        new_checkpoint = checkpoint

        helper.log_debug(f"{log_label} Create TA data sections")
        ts_field = ta_data['Timestamp_Field']
        for line in event_data:
            event_ta_data = dict(ta_data)
            event_ta_data['Timestamp_value'] = line[ts_field]
            line['ta_data'] = event_ta_data
            if line[ts_field] > new_checkpoint:
                new_checkpoint = line[ts_field]
                update_checkpoint = True

        try:
            helper.log_info(f"{log_label} Preparing to send: {len(event_data)} FileVantage events to Splunk index: {data_index}")
            events = '\n'.join(json.dumps(line) for line in event_data)
            filevantage_data = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=events)
            ew.write_event(filevantage_data)
            helper.log_info(f"{log_label} Data for {len(event_data)} events from FileVantage successfully pushed to Splunk index: {data_index}")

        except Exception as e:
            helper.log_error(f"{log_label} Data for {len(event_data)} FileVantage events could not be pushed to Splunk. Please ensure that the TA and Splunk are properly configured")
            helper.log_error(f"{log_label} {e}")
            raise SystemExit()

        if update_checkpoint:
            helper.log_info(f"{log_label} Checkpoint is being updated")
            try:
                rec_checkpoint={ts_field:str(new_checkpoint)}
                helper.save_check_point(stanza_checkpoint, rec_checkpoint)
                helper.log_info(f"{log_label} Checkpoint updated: {checkpoint} -> {new_checkpoint}")
                checkpoint = new_checkpoint

            except Exception as e:
                helper.log_error(f"{log_label} Unable to save checkpoint after successful data push ({type(e).__name__}: {e})")
                helper.log_error(f"{log_label} WARNING: Events already sent to Splunk may be duplicated on next collection run. Resolve checkpoint storage issue before restarting. TA is shutting down.")
                raise SystemExit()
        else:
            helper.log_info(f"{log_label} No new checkpoint was detected")

        return checkpoint