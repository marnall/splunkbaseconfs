import json
import CrowdStrike_Constants as const

def send_to_splunk(search_name, report, log_label, data_index, data_format, helper, ew):
    total = len(report)
    batch_size = const.splunk_batch_size
    try:
        helper.log_info(f'{log_label} Preparing to send: {data_format.upper()} Data for {total} events from report {search_name} to Splunk index: {data_index}')
        for i in range(0, total, batch_size):
            batch = report[i:i + batch_size]
            if data_format == 'csv' and '@timestamp' in batch[0]:
                event_data = '\n'.join(
                    json.dumps({'@timestamp': line['@timestamp'], **{k: v for k, v in line.items() if k != '@timestamp'}})
                    for line in batch
                )
            else:
                event_data = '\n'.join(json.dumps(line) for line in batch)
            scheduled_search_data = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=event_data)
            ew.write_event(scheduled_search_data)
            if total > batch_size:
                helper.log_debug(f'{log_label} Batch {i // batch_size + 1}: wrote {len(batch)} events ({i + len(batch)}/{total})')
        helper.log_info(f'{log_label} {data_format.upper()} Data for {total} events from report {search_name} successfully pushed to Splunk index: {data_index}')
        return True

    except BrokenPipeError:
        helper.log_error(f'{log_label} BrokenPipeError writing to Splunk — splunkd closed the event pipe. This typically means Splunk restarted, the input was disabled, or the write exceeded splunkd buffer limits. Events written before this error are indexed; remaining events will be collected on next run.')
        return False
    except Exception as e:
        helper.log_error(f'{log_label} {data_format.upper()} Data for {total} events from report {search_name} could not be pushed to Splunk. Please ensure that the TA and Splunk are properly configured. The TA will now shutdown to prevent data collection issues.')
        helper.log_error(f'{log_label} {type(e).__name__}: {e}')
        return False
