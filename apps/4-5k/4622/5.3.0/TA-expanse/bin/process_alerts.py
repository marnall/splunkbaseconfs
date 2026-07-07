import itertools
import json
import logging

from constants import ALERTS_TIME_FORMAT, ALERT_ID_PATH, CIM_TIME_ADDRESS
from dateutil.parser import parse
from datetime import datetime, timedelta
from deduplication import AlertDeduplicationProcessor
from event_type_to_cim import AlertProcessor
from state_utils import get_prior_alerts_update_state, update_alert_checkpoints
from time_utils import get_splunk_time
from xpanse.client import XpanseClient


def process_alerts(helper, ew, expanse_client: XpanseClient,
                   alert_deduplication_processor: AlertDeduplicationProcessor, start_date, input_name):
    """Writes issues updates to splunk, updates state for later runs

        Args:
            helper (smi.Script): A helper object that controls logging and state
            ew (EventWriter): Splunk object used to write events to Splunk index
            expanse_client: Expanse SDK client
            alert_deduplication_processor: deduplication processor for alerts
            start_date (str): The start date for the API call
            input_name (str): The name of the input

        Returns:
            bool: True if the run completed with no Exceptions, False otherwise
            int: The number of issue updates successfully written to Splunk
            int: The number of issues updates the failed to write to Splunk
        """

    success_ids = []
    failure_ids = []

    checkpoint_timestamp = parse(start_date)

    event_date, retry_ids = get_prior_alerts_update_state(helper, input_name)
    alerts_processed = False
    try:
        for api_alert in alert_deduplication_processor.deduplicate(helper,
                                                                   fetch_alerts(helper,
                                                                                expanse_client,
                                                                                start_date,
                                                                                retry_ids)):
            alert_id = api_alert[ALERT_ID_PATH]
            alerts_processed = True
            try:
                alert = format_alert(helper, api_alert, start_date)
                alert['input_name'] = input_name

                # Below needs to be decimal or we lose precision on the time
                alert_event_time = alert[CIM_TIME_ADDRESS]
                # The time of the event formatted for splunk
                splunk_event_time = get_splunk_time(helper, alert_event_time)
                event_date = parse(alert_event_time).strftime(ALERTS_TIME_FORMAT)

                helper.log_debug('Attempting to write update for input {}, event_data={}'.format(input_name,
                                                                                                 str(alert)))
                update_data = helper.new_event(
                    source=helper.get_input_type(),
                    time=splunk_event_time,
                    index=helper.get_expander_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=json.dumps(alert),
                )
                ew.write_event(update_data)
                helper.log_debug('Update written successfully for input {}, event_data={}'.format(input_name,
                                                                                                  str(alert)))
                success_ids.append(alert_id)
                checkpoint_timestamp = max(checkpoint_timestamp, parse(event_date))
            except ValueError as ve:
                failure_ids.append(alert_id)
                helper.log_error(
                    'Failed to write update for input {} to splunk due to error: {}\nUpdate: {}'.format(input_name,
                                                                                                        ve.args[0],
                                                                                                        api_alert))
            except Exception as e:
                failure_ids.append(alert_id)
                helper.log_error(
                    'Unknown error caused failure writing update to splunk on input {}: {}\n'.format(input_name,
                                                                                                     e.args[0]))
    except Exception as e:
        helper.log_error('There was an error trying to collect issue updates from the API: {}'.format(e.args[0]))
        update_alert_checkpoints(helper, input_name, checkpoint_timestamp.strftime(ALERTS_TIME_FORMAT),
                                 failure_ids or [] + [previous_retry_id for previous_retry_id in retry_ids or [] if
                                                      previous_retry_id not in success_ids or []]
                                 )
        return False, len(success_ids or []), len(failure_ids or [])

    if not alerts_processed:
        helper.log_debug('No updates returned start date={} for input {}. Not updating the '
                         'checkpoint '
                         .format(start_date, input_name))
        return True, len(success_ids), len(failure_ids)

    update_alert_checkpoints(helper, input_name, checkpoint_timestamp.strftime(ALERTS_TIME_FORMAT),
                             failure_ids or [])

    if len(failure_ids or []) == 0:
        helper.log_debug('Updates through datetime={} was marked as fully complete in state for input {}'
                         .format(str(event_date), input_name))
    else:
        helper.log_debug(f"""There were failures through datetime={checkpoint_timestamp}. Adding failures to the
        retry checkpoint""")

    return len(success_ids or []) > 0 and len(failure_ids or []) == 0, len(success_ids or []), len(failure_ids or [])


severity_map = {
    'critical': ['unknown', 'critical'],
    'high': ['unknown', 'critical', 'high'],
    'medium': ['unknown', 'critical', 'high', 'medium'],
    'low': ['unknown', 'critical', 'high', 'medium', 'low', 'unknown']
}


def fetch_alerts(helper, expanse_client: XpanseClient, start_date, retry_ids):
    """
        Set the start / end times for alerts lookback to:
        start time = start_date - 24 hours
        end time = now - 10 minutes
    """
    dt_start_time = int(round((parse(start_date) - timedelta(days=1)).timestamp()) * 1000)
    dt_now_with_lookback = int((datetime.utcnow() - timedelta(minutes=10)).timestamp() * 1000)
    logging.debug(f"Fetching Xpanse alerts from "
                  f"{datetime.fromtimestamp(dt_start_time / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')} to "
                  f"{datetime.fromtimestamp(dt_now_with_lookback / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')}")
    request_data = {'sort': {'field': 'server_creation_time', 'keyword': 'ASC'},
                    'filters': [{'field': 'server_creation_time', 'operator': 'gte',
                                 'value': dt_start_time},
                                {'field': 'server_creation_time', 'operator': 'lte',
                                 'value': dt_now_with_lookback}
                                ]}
    severity = helper.get_arg('alert_severity')
    if severity:
        severity_filter = severity_map.get('high')
        if severity.lower() in severity_map:
            severity_filter = severity_map.get(severity.lower())

        request_data['filters'].append(
            {'field': 'severity', 'operator': 'in', 'value': severity_filter})

    alert_segments = []
    if retry_ids:
        chunk_size = 20
        retry_chunks = [retry_ids[i:i + chunk_size] for i in range(0, len(retry_ids), chunk_size)]
        for chunk in retry_chunks:
            parsed_chunk = [int(id) for id in chunk]
            retry_request_data = {'sort': {'field': 'server_creation_time', 'keyword': 'ASC'},
                                  'filters': [{'field': 'alert_id_list', 'operator': 'in',
                                               'value': parsed_chunk}]}
            alert_segments.append(expanse_client.alerts.list(request_data=retry_request_data).dump())
    alert_segments.append(expanse_client.alerts.list(request_data=request_data).dump())
    return itertools.chain.from_iterable(alert_segments)


def format_alert(helper, data, start_date):
    helper.log_debug(
        'Processing raw alert with id={} into CIM'.format(data[ALERT_ID_PATH]))
    alert_update = AlertProcessor.process(data)
    helper.log_debug(f"""Processed alert with update={alert_update}, createdAfter={start_date}'.""")
    return alert_update
