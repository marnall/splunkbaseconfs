# encoding = utf-8
import json
from datetime import datetime, timezone

from client_manager import FncSplunkClientManager
from fnc import FncClientError
from fnc.api import ApiContext, FncApiClient
from global_variables import DETECTIONS_ARGUMENTS, HISTORY_LIMIT
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
    logger.info("Retrieving params for Detections input.")

    # Initializing the FncApiClient
    api_token = helper.get_global_setting("api_token")
    domain = helper.get_global_setting("domain")
    manager.initialize_api_client(api_token=api_token, domain=domain)

    args = {
        'include_signature': helper.get_arg('include_signature'),
        'include_description': helper.get_arg('include_description'),
        'include_events': helper.get_arg('include_events'),
        'include_pdns': helper.get_arg('include_pdns'),
        'include_annotations': helper.get_arg('include_annotations'),

        'start_date': helper.get_arg('start_date'),
        'polling_delay': helper.get_arg('polling_delay'),
        'account_uuid': helper.get_arg('account_uuid'),

        'severity_levels': helper.get_arg('severity_levels'),
        'confidence_levels': helper.get_arg('confidence_levels'),

        'status': helper.get_arg('status'),
        'pull_muted_rules': helper.get_arg('pull_muted_rules'),
        'pull_muted_devices': helper.get_arg('pull_muted_devices'),
        'pull_muted_detections': helper.get_arg('pull_muted_detections'),
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


def split_events(events: dict):
    detections_events = []
    for d_id, d_evts in events.items():
        evts = list(map(
            lambda e: {
                "detection_uuid": d_id,
                'rule_uuid': e.get('rule_uuid', ''),
                **(e.get('event', {}))
            }, d_evts))

        detections_events.extend(evts)

    return detections_events


def _send_to_splunk(
    manager: FncSplunkClientManager,
    detections: list,
    detection_events: dict
):
    logger = manager.get_logger()
    if detections and len(detections) > 0:
        logger.debug("Creating Splunk events.")

        for d in detections:
            created_timestamp = d['created'].replace("Z", "")
            # logger.debug(
            #     f"Adding UTC timezone information to detections created date ({created_timestamp})")
            created = datetime.strptime(
                created_timestamp, '%Y-%m-%dT%H:%M:%S.%f'
            ).replace(tzinfo=timezone.utc)

            # logger.debug(f"Splunk Event's timestamp being set from: {created}")
            manager.create_splunk_event(
                timestamp=created, data=d)

    if detection_events and len(detection_events) > 0:
        events = split_events(
            events=detection_events
        )

        for e in events:
            timestamp = e['timestamp'].replace("Z", "")
            # logger.debug(
            #     f"Adding UTC timezone information to detection's event timestamp ({timestamp})")
            time_stamp_event = datetime.strptime(
                timestamp, "%Y-%m-%dT%H:%M:%S.%f").replace(tzinfo=timezone.utc)

            # logger.debug(
            #     f"Splunk Event's timestamp being set from: {time_stamp_event}")
            manager.create_splunk_event(
                timestamp=time_stamp_event,
                source_type='FortiNDRCloud:Events',
                data=e
            )


def filter_result(
    detections: list,
    events: dict,
    severity: list,
    confidence: list
):
    detections = list(
        filter(
            lambda d: (
                d['rule_severity'] in severity and
                d['rule_confidence'] in confidence
            ), detections))
    detections_ids = list(d['uuid'] for d in detections)
    events = dict(
        filter(lambda item: item[0] in detections_ids, events.items()))

    return detections, events


def collect_events(helper, ew):
    manager = FncSplunkClientManager(helper, ew)

    manager.get_logger().info('Collecting Detections.')
    logger = manager.get_logger()

    # Get args
    args = _get_arguments(helper, manager)
    client: FncApiClient = manager.get_api_client()

    # Get checkpoint variable, convert to string
    last_detection = _get_checkpoint(helper=helper, key='last_checkpoint')
    if last_detection:
        logger.info(f"Last checkpoint was: {last_detection}.")

    history = {}
    last_history = _get_checkpoint(helper=helper, key='last_history')
    if last_history:
        logger.info(f"Last history was: {last_history}.")
        history = json.loads(last_history)

    try:
        params = dict(
            filter(lambda item: item[0] in DETECTIONS_ARGUMENTS, args.items()))

        # We restore the context using the persisted values of the
        # last_detection(checkpoint) and the history if they exist
        # Otherwise, we initialize them by calling the get splitted
        # context method.

        context: ApiContext = None
        h_context: ApiContext = None

        if last_detection:
            logger.info("Restoring the Context")
            context = ApiContext()
            context.update_checkpoint(checkpoint=last_detection)
            h_context = ApiContext()
            h_context.update_history(history=history)
            h_context.set_entity_details_cache(
                context.get_entity_details_cache())
        else:
            logger.info("Initializing the Context")
            h_context, context = client.get_splitted_context(
                params)

        # Pull current detections
        started = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f")
        logger.info("Polling current detections.")
        for response in client.continuous_polling(
            context=context, args=params
        ):
            detections = response.get('detections', [])
            events = events = response.get('events', {})

            detections, events = filter_result(
                detections=detections,
                events=events,
                severity=args['severity_levels'],
                confidence=args['confidence_levels']
            )
            if detections:
                _send_to_splunk(
                    manager=manager,
                    detections=detections,
                    detection_events=events
                )
        context.clear_args()

        # Pull next piece of the history data
        logger.info("Polling historical data.")

        params.update({'limit': HISTORY_LIMIT})
        for response in client.poll_history(
            context=h_context, args=params
        ):
            detections = response.get('detections', [])
            events = response.get('events', {})

            detections, events = filter_result(
                detections=detections,
                events=events,
                severity=args['severity_levels'],
                confidence=args['confidence_levels']
            )
            _send_to_splunk(
                manager=manager,
                detections=detections,
                detection_events=events
            )
        ended = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.%f")

        exec_metrics = context.get_global_metrics()
        exec_metrics.merge(h_context.get_global_metrics())
        logger.debug(exec_metrics.get_metric_report(
            f"Detections Polling Report (execution running between {started} and {ended}):"))

        h_context.clear_args()

        # checkpoint for the first Detection iteration
        checkpoint = context.get_checkpoint()
        history = h_context.get_remaining_history()

        logger.debug("Updating last detection checkpoint.")
        _set_checkpoint(helper=helper, key='last_checkpoint',
                        data=checkpoint)

        last_history = json.dumps(history)
        logger.debug("Updating last history checkpoint.")
        _set_checkpoint(helper=helper, key='last_history',
                        data=last_history)

        logger.info("Last detection checkpoint set at {0}".format(
            checkpoint))
        logger.info("Last history checkpoint set at {0}".format(
            last_history))

        logger.info("Completed processing Detections")
    except FncClientError as e:
        logger.error(
            "Exception occurred while processing Detections")
        logger.error(e)
