# encoding = utf-8
import json
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from client_manager import FncSplunkClientManager
from fnc import FncClientError
from fnc.metastream import FncMetastreamClient
from fnc.metastream.s3_client import MetastreamContext
from fnc.utils import datetime_to_utc_str, str_to_utc_datetime
from global_variables import DATE_FORMAT
from solnlib import utils as sutils
from solnlib.modular_input import checkpointer


def validate_input(helper, definition):
    metadata = definition.metadata.copy()

    dscheme, dhost, dport = sutils.extract_http_scheme_host_port(
        metadata['server_uri']
    )
    helper.ckpt = checkpointer.KVStoreCheckpointer(helper.app + "_checkpointer",
                                                   metadata['session_key'], helper.app,
                                                   scheme=dscheme, host=dhost, port=dport)

    imput_name = metadata['name']
    _clean_checkpoints(helper, imput_name)


def _get_arguments(helper, manager: FncSplunkClientManager):
    logger = manager.get_logger()
    logger.debug("Retrieving arguments for the Events input.")

    # Initializing the FncApiClient
    api_token = helper.get_global_setting("api_token")
    domain = helper.get_global_setting("domain")
    # manager.initialize_api_client(api_token=api_token, domain=domain)

    aws_access_key = helper.get_arg('aws_access_key')
    aws_secret_key = helper.get_arg('aws_secret_key')
    aws_bucket_name = helper.get_arg('aws_bucket_name')
    account_code = helper.get_arg('account_code')
    manager.initialize_metastream_client(
        access_key=aws_access_key,
        secret_key=aws_secret_key,
        bucket=aws_bucket_name,
        account_code=account_code
    )

    # Get checkpoint variable, convert to string
    checkpoint = {}
    last_checkpoint = _get_checkpoint(helper=helper, key='last_checkpoint')
    if last_checkpoint:
        logger.info(f"Last checkpoint was: {last_checkpoint}.")
        checkpoint = json.loads(last_checkpoint)

    history = {}
    last_history = _get_checkpoint(helper=helper, key='last_history')
    if last_history:
        logger.info(f"Last history was: {last_history}.")
        history = json.loads(last_history)

    args = {
        'event_types': helper.get_arg('event_types'),
        'days_to_collect': helper.get_arg('days_to_collect'),
        'checkpoint': checkpoint,
        'history': history
    }
    logger.info('Arguments retrieved.')
    return args


def _get_checkpoint_key(helper, key: str) -> str:
    # Get the checkpoint timestamp key for the received event_type and sensor
    stanza_names = helper.get_input_stanza_names()
    prefix = f'{helper.input_type}_{stanza_names}'
    last_checkpoint_key = f'{prefix}_{key}'
    return last_checkpoint_key


def _clean_checkpoints(helper, input_name):
    helper.log_debug(f"Cleaning checkpoints for input {input_name}.")

    last_checkpoint_key = f'{helper.input_type}_{input_name}_last_checkpoint'
    helper.delete_check_point(last_checkpoint_key)

    last_history_key = f'{helper.input_type}_{input_name}_last_history'
    helper.delete_check_point(last_history_key)


def _get_checkpoint(helper, key: str) -> str:
    last_checkpoint_key = _get_checkpoint_key(helper, key)
    helper.log_debug(f'Retrieving checkpoint with key: {last_checkpoint_key}.')
    last_checkpoint = helper.get_check_point(last_checkpoint_key)
    return last_checkpoint


def _set_checkpoint(helper, key: str, data: str):
    last_checkpoint_key = _get_checkpoint_key(helper, key)

    # Delete the old checkpoints
    helper.delete_check_point(last_checkpoint_key)

    # Save this timestamp as the last checkpoint for interval poll
    helper.save_check_point(last_checkpoint_key, data)


def _send_to_splunk(
    manager: FncSplunkClientManager,
    events: List[dict]
):
    logger = manager.get_logger()
    logger.debug('Creating Splunk events.')

    for event in events:
        # Check counter for last event. If it is, capture the timestamp and
        # set as checkpoint date
        event_timestamp = event['timestamp'].replace("Z", "")
        time_stamp = datetime.strptime(
            event_timestamp, '%Y-%m-%dT%H:%M:%S.%f'
        ).astimezone().replace(tzinfo=timezone.utc)

        manager.create_splunk_event(
            timestamp=time_stamp,
            data=event
        )

    logger.info(f'{len(events)} Splunk events were successfully created.')


def _initialize_checkpoint(event_types: List, timestamp: str):
    checkpoint = {}
    for event_type in event_types:
        checkpoint.update({event_type: timestamp})
    return checkpoint


def _collect_metastream_events(
    manager: FncSplunkClientManager,
    context: MetastreamContext,
    event_type: str,
    start_date: datetime,
    end_date: datetime
) -> bool:
    logger = manager.get_logger()
    client: FncMetastreamClient = manager.get_metastream_client()

    total_events: int = 0
    now = datetime.now(tz=timezone.utc)
    now_str = datetime_to_utc_str(now)

    start_date = start_date or context.get_checkpoint(
        event_type=event_type) or now_str
    end_date = end_date or now_str

    if start_date < end_date:
        try:
            for events in client.fetch_events(
                context=context,
                event_type=event_type,
                start_date=start_date,
                end_date=end_date
            ):
                if len(events) > 0:
                    total_events += len(events)
                    _send_to_splunk(manager=manager, events=events)
        except FncClientError as e:
            logger.error(
                f"""Cannot fetch {event_type} events.
                    Error: {e}"""
            )
            return False
        except Exception as e:
            logger.error(
                f"Cannot send {event_type} events to Splunk. Error: {e}"
            )
            logger.error(traceback.format_exc())
            return False

    logger.info(
        f"{total_events} {event_type} events retrieved.")
    return True


def _collect_events_history(
        manager: FncSplunkClientManager,
        context: MetastreamContext,
        event_type: str
) -> bool:
    logger = manager.get_logger()
    client: FncMetastreamClient = manager.get_metastream_client()

    total_count = 0
    # Get the start_date and end_date from the history in the context
    history = context.get_history(event_type=event_type)
    start_date_str = history.get('start_date', None)
    end_date_str = history.get('end_date', None)

    start_date = str_to_utc_datetime(
        datetime_str=start_date_str, format=DATE_FORMAT)
    end_date = str_to_utc_datetime(
        datetime_str=end_date_str, format=DATE_FORMAT)

    if start_date == end_date:
        # If start_date is the same as the end_date then the whole history
        # was already retrieved
        logger.info(
            f'{total_count} events were successfully retrieved.')
    else:
        try:
            # If not, we poll the next piece of size 'interval'
            for events in client.poll_history(
                context=context,
                event_type=event_type
            ):
                if len(events) > 0:
                    _send_to_splunk(manager=manager, events=events)
                    total_count += len(events)
        except FncClientError as e:
            logger.error(
                f"""Cannot fetch {event_type} events history.
                    Error: {e}"""
            )
            return False
        except Exception as e:
            logger.error(
                f"Cannot send {event_type} events to Splunk. Error: {e}"
            )
            logger.error(traceback.format_exc())
            return False

    logger.info(
        f"""{total_count} {event_type} events successfully processed.""")
    return True


def collect_events(helper, ew):
    manager = FncSplunkClientManager(helper, ew)
    logger = manager.get_logger()
    try:
        logger.info('Collecting events.')
        # Get args
        args = _get_arguments(helper, manager=manager)
        client: FncMetastreamClient = manager.get_metastream_client()

        event_types = args['event_types']
        if 'all' in event_types:
            event_types = client.fetch_event_types()

        now = datetime.now(timezone.utc)
        checkpoint: Dict = args.get('checkpoint', '{}')
        history: Dict = args.get('history', '{}')

        h_context: MetastreamContext = None
        context: MetastreamContext = None

        if not checkpoint:
            days_to_collect = args['days_to_collect']
            if days_to_collect:
                try:
                    days = int(days_to_collect)
                except Exception:
                    days = None
                if (days is None or
                        days not in [0, 1, 2, 3, 4, 5, 6, 7]):
                    logger.info(
                        f"The days_to_collect value {days_to_collect} is invalid and will be ignored. Verify it is a number between 0 to 7")
                    days_to_collect = ""
                else:
                    days_to_collect = datetime_to_utc_str(now - timedelta(days=days))

            # Split the poling window in history and
            h_context, context = client.get_splitted_context(
                start_date_str=days_to_collect
            )
            checkpoint = _initialize_checkpoint(
                event_types=event_types,
                timestamp=context.get_checkpoint()
            )
            history = h_context.get_history()
        else:
            context = MetastreamContext()
            h_context = MetastreamContext()
            h_context.update_history(history=history)

        # Polling current events
        for event_type in event_types:
            # Get the start_date and end_date from the history in the context
            # If no end date is passed the default will be:
            # datetime.now(tz=timezone.utc)
            start_date_str = checkpoint.get(event_type)
            start_date = str_to_utc_datetime(
                datetime_str=start_date_str, format=DATE_FORMAT)
            end_date = now

            if start_date < end_date:
                if _collect_metastream_events(
                    manager=manager,
                    context=context,
                    event_type=event_type,
                    start_date=start_date,
                    end_date=end_date
                ):
                    checkpoint.update(
                        {event_type: context.get_checkpoint()})

                    # updete for each type
                    args.update({'checkpoint': checkpoint})

                for event_type in event_types:
                    if _collect_events_history(
                        manager=manager,
                        context=h_context,
                        event_type=event_type
                    ):
                        history = h_context.get_history()
                        args.update({"history": history})

        last_checkpoint = json.dumps(checkpoint)
        logger.debug("Updating last checkpoint checkpoint.")
        _set_checkpoint(helper=helper, key='last_checkpoint',
                        data=last_checkpoint)

        last_history = json.dumps(history)
        logger.debug("Updating last history checkpoint.")
        _set_checkpoint(helper=helper, key='last_history',
                        data=last_history)

        logger.info("Last checkpoint set at {0}".format(
            last_checkpoint))
        logger.info("Last history checkpoint set at {0}".format(
            last_history))

        logger.info("Completed processing Events")
    except Exception as x:
        logger.error(
            f"""Events cannot be retrieved due to: {str(x)}."""
        )
        logger.error(traceback.format_exc())
