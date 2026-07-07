# encoding = utf-8
from datetime import datetime, timezone
from typing import Any, Dict

from client_manager import FncSplunkClientManager
from fnc import FncClientError
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
    _clean_completeness(helper, imput_name)


def _get_arguments(helper, manager: FncSplunkClientManager):
    logger = manager.get_logger()
    logger.debug("Retrieving arguments for the Entity input.")

    # Stringify and remove spaces from entities enter entities into list
    entity_arg = helper.get_arg('entities')
    entities = str(entity_arg).replace(" ", "").split(",")

    # Initializing the FncApiClient
    api_token = helper.get_global_setting("api_token")
    domain = helper.get_global_setting("domain")
    manager.initialize_api_client(api_token=api_token, domain=domain)

    args = {
        'entities': entities,
        'fetch_pdns': helper.get_arg('fetch_pdns'),
        'fetch_dhcp': helper.get_arg('fetch_dhcp'),
        'fetch_vt': helper.get_arg('fetch_vt')
    }

    logger.info('Arguments retrieved for the entity input.')
    return args


def _get_complete_key(helper) -> str:
    # Get the checkpoint timestamp key for the received event_type and sensor
    stanza_names = helper.get_input_stanza_names()
    prefix = f'{helper.input_type}_{stanza_names}'
    last_checkpoint_key = f'{prefix}_completed'
    return last_checkpoint_key


def _clean_completeness(helper, input_name):
    helper.log_debug(f"Cleaning checkpoints for input {input_name}.")

    last_checkpoint_key = f'{helper.input_type}_{input_name}_completed'
    helper.delete_check_point(last_checkpoint_key)


def _is_completed(helper) -> bool:
    completed_key = _get_complete_key(helper)
    helper.log_debug(
        f'Checking if input was already executed. [key: {completed_key}]')
    completed = bool(helper.get_check_point(completed_key))
    helper.log_debug(
        f'Checking if input was already executed. [key: {completed_key}]')
    return completed


def _set_as_completed(helper):
    completed_key = _get_complete_key(helper)

    # Delete the old checkpoints
    helper.delete_check_point(completed_key)

    # Save this timestamp as the last checkpoint for interval poll
    helper.save_check_point(completed_key, 'true')


def _retrieve_entities(manager: FncSplunkClientManager, args: Dict[str, Any]):
    logger = manager.get_logger()
    logger.info("Starting to process Entities.")

    entity_list = args.get('entities', [])

    try:
        # Retrieving entity's information for each entity
        logger.info(f'Searching for {len(entity_list)} entities.')
        for entity in entity_list:
            _retrieve_entity_info(
                manager=manager,
                entity=entity,
                args=args
            )

        logger.info("Entities information were retrieved.")

    except FncClientError as e:
        logger.error(
            "Exception occurred while processing Entities")
        logger.error(e)


def _retrieve_entity_info(
    manager: FncSplunkClientManager,
    entity: str,
    args: Dict[str, Any]
):
    logger = manager.get_logger()
    logger.info(f'Searching information for entity {entity}.')

    fetch_dhcp: bool = args.get('fetch_dhcp', False)
    fetch_pdns: bool = args.get('fetch_pdns', False)
    fetch_vt: bool = args.get('fetch_vt', False)

    if (not entity or (
        not fetch_dhcp and not fetch_pdns and not fetch_vt
    )):
        logger.info("Nothing to retrieve.")

    client = manager.get_api_client()
    entity_info = client.get_entity_information(
        entity=entity,
        fetch_dhcp=fetch_dhcp,
        fetch_pdns=fetch_pdns,
        fetch_vt=fetch_vt
    )
    _send_to_splunk(
        manager=manager,
        fetch_pdns=fetch_pdns,
        fetch_dhcp=fetch_dhcp,
        fetch_vt=fetch_vt,
        entity_info=entity_info
    )

    logger.info(f"Entity {entity}'s information successfully retrieved.")


def _send_to_splunk(
    manager: FncSplunkClientManager,
    fetch_pdns: bool = False,
    fetch_dhcp: bool = False,
    fetch_vt: bool = False,
    entity_info=None
):
    now = datetime.now(tz=timezone.utc)
    logger = manager.get_logger()

    entity = entity_info.get('entity', '')
    if not entity:
        logger.warning(
            "Entity's information cannot be sent to Splunk because the entity is empty.")
        return

    if fetch_pdns:
        _send_event_type(
            manager=manager,
            entity=entity,
            event_type='PDNS',
            entity_info=entity_info,
            timestamp=now
        )

    if fetch_dhcp:
        _send_event_type(
            manager=manager,
            entity=entity,
            event_type='DHCP',
            entity_info=entity_info,
            timestamp=now
        )

    if fetch_vt:
        _send_event_type(
            manager=manager,
            entity=entity,
            event_type='VT',
            entity_info=entity_info,
            timestamp=now
        )

    logger.info(
        f"Entity {entity}'s information was successfully sent to Splunk.")


def _send_event_type(
    manager: FncSplunkClientManager,
    entity,
    event_type,
    entity_info,
    timestamp
):
    logger = manager.get_logger()
    key = event_type.lower()
    info = entity_info.get(key, [])

    logger.info(
        f"Sending the {event_type} information for entity {entity} to Splunk.")
    if len(info) > 0:
        logger.debug(f"Sending {len(info)} events")

    for e in info:
        event: dict = {
            'entity': entity,
            'event_type': event_type,
            'info': e
        }
        manager.create_splunk_event(timestamp=timestamp, data=event)
    if not info:
        logger.info(
            f"There is no {event_type} information for entity {entity}.")


def collect_events(helper, ew):
    manager = FncSplunkClientManager(helper, ew)
    if not _is_completed(helper):
        manager.get_logger().info('Starting to process Entities.')
        # Get args
        args = _get_arguments(helper, manager)
        _retrieve_entities(manager=manager, args=args)
        _set_as_completed(helper)
