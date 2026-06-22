import json
from dateutil import parser


def send_to_splunk(event_data, checkpoint, stanza_checkpoint, log_label, ta_data, pagination, alert_count, helper, ew):
    data_index = helper.get_output_index()
    update_checkpoint = False
    chkpt_comp = parser.parse(checkpoint)

    helper.log_debug(f"{log_label} Checkpoint comparison")
    for line in event_data:
        line['ta_data']=ta_data
        update_comp = parser.parse(line['updated_timestamp'])
        helper.log_debug(f"{log_label} Timestamp validation - {chkpt_comp > update_comp}  {chkpt_comp < update_comp}  {chkpt_comp == update_comp}")
        if update_comp > chkpt_comp:
            new_checkpoint = line['updated_timestamp']
            helper.log_debug(f"{log_label} New Checkpoint value identified as {new_checkpoint}")
            update_checkpoint = True
            chkpt_comp = update_comp
        else:
            helper.log_debug(f"{log_label} Timestamp does not need to be updated")

    ts_field = 'updated_timestamp'
    old_checkpoint = {ts_field: str(checkpoint)}

    try:
        helper.log_info(f"{log_label} Preparing to send: {len(event_data)} events to Splunk index: {data_index}")
        events = '\n'.join(json.dumps(line) for line in event_data)
        detection_event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=events)
        ew.write_event(detection_event)
        helper.log_info(f"{log_label} Data for {len(event_data)} events successfully pushed to Splunk index: {data_index}")

    except Exception as e:
        helper.log_error(f"{log_label} Data for {len(event_data)} events could not be pushed to Splunk. Please ensure that the TA and Splunk are properly configured")
        helper.log_error(f"{log_label} {e}")
        raise RuntimeError(f"Failed to write events to Splunk: {e}")

    if update_checkpoint:
        helper.log_debug(f"{log_label} Checkpoint is being updated")
        try:
            rec_checkpoint = {ts_field: str(new_checkpoint)}
            helper.log_debug(f"{log_label} Checkpoint value = {rec_checkpoint}")
            helper.save_check_point(stanza_checkpoint, rec_checkpoint)

        except Exception as e:
            helper.log_error(f"{log_label} Unable to record timestamp checkpoint data")
            helper.log_error(f"{log_label} Error report was - {type(e).__name__}: {e}, attempted value: {rec_checkpoint}")
            helper.log_error(f"{log_label} Checkpoint data is not able to be recorded, please correct the issue and restart the collection")
            raise RuntimeError(f"Failed to save checkpoint: {e}")
    else:
        helper.log_info(f"{log_label} No new checkpoint was detected")

    if not pagination:
        if update_checkpoint:
            helper.log_info(f"{log_label} Final checkpoint advanced from {old_checkpoint} to {rec_checkpoint}")
        else:
            helper.log_info(f"{log_label} Final checkpoint unchanged at {old_checkpoint}")
        helper.log_info(f"{log_label} Final number of detections processed {alert_count}")
        helper.log_info(f"{log_label} TA has completed data collection")
    else:
        helper.log_info(f"{log_label} Number of detections processed so far {alert_count}")
        helper.log_info(f"{log_label} Continuing data collection via pagination")
        return

    return
