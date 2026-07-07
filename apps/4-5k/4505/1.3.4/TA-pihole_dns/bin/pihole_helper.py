
# encoding = utf-8

import os
import sys
import time
import datetime
import json
import pihole_constants as const


def sendit(pihole_host, event_name, helper, params=None):
    """Send Request

    :param pihole_host: Pihole server to query
    :param event_name: Name of event performing the request
    :param helper: Splunk Helper
    :param params: Parameters for request
    :return: response
    """

    account = helper.get_arg('pihole_account')
    api_key = account['api_pass']
    params['auth'] = api_key
    api_port = None
    try:
        account['api_port']
    except:
        event_log = zts_logger(
            msg='API port not defined, Defaulting to port 80',
            action='none',
            event_type=event_name,
            hostname=pihole_host
        )
        helper.log_info(event_log)
    else:
        api_port = account['api_port']

    if api_port:
        dest = f'{pihole_host}:{api_port}'
    else:
        dest = pihole_host

    # Skip run if too close to previous run interval
    if not checkpointer(pihole_host, event_name, helper):
        return False

    headers = {
        'Accept': 'application/json',
        'Content-type': 'application/json'
    }
    url = f'{const.h_proto}://{dest}/{const.api_system}'

    event_log = zts_logger(
        msg=f'started {event_name} collection',
        hostname=pihole_host,
        action='started',
        event_type=event_name,
        url=url
    )
    helper.log_info(event_log)

    try:
        r = helper.send_http_request(
            url, 'get', headers=headers, parameters=params, use_proxy=True, verify=False)
    except Exception as e:
        event_log = zts_logger(
            msg='unable to complete request',
            action="failed",
            event_type=event_name,
            hostname=pihole_host,
            error_msg=e
        )
        helper.log_error(event_log)
        raise SystemExit()

    if r.status_code != 200:
        event_log = zts_logger(
            msg='Request failed',
            action='failed',
            hostname=pihole_host,
            event_type=event_name,
            status_code=r.status_code
        )
        helper.log_error(event_log)
        raise SystemExit(r.status_code)

    event_log = zts_logger(
        msg='Request completed',
        action='success',
        event_type=event_name,
        hostname=pihole_host
    )
    helper.log_info(event_log)
    return r.json()


def checkpointer(pihole_host, event_name, helper, set_checkpoint=False):
    """Checks and returns checkpoint

    :param pihole_host: Host to check for checkpointer
    :param event_name: Name of the event
    :param helper: Splunk Helper
    :param set_checkpoint: Whether to set a new checkpoint
    :return: bool
    """
    # Get Interval
    interval = helper.get_arg('interval')

    # Check for Cron schedule
    try:
        int(interval)
    except ValueError:
        helper.log_info(
            f'msg="Checkpointer not needed, using cron schedule", hostname="{pihole_host}", event_name="{event_name}"')
        return True
    else:
        interval = int(interval)

    # Proceed to checkpointer
    current_time = int(time.time())
    check_time = current_time - interval + 60
    key = f'{pihole_host}_{event_name}'

    if set_checkpoint:
        new_state = int(time.time())
        helper.save_check_point(key, new_state)
        helper.log_info(
            f'msg="Updating Checkpoint", checkpoint="{new_state}", hostname="{pihole_host}", event_name="{event_name}"')
        return True

    if helper.get_check_point(key):
        old_state = int(helper.get_check_point(key))
        helper.log_info(
            f'event_name="{event_name}", msg="Checkpoint found", hostname="{pihole_host}"')
        helper.log_debug(
            f'event_name="{event_name}", msg="Checkpoint information", checkpoint="{old_state}", interval="{interval}", hostname="{pihole_host}"')

        if check_time < old_state:
            helper.log_info(
                f'event_name="{event_name}", msg="Skipping because interval is too close to previous run", '
                f'action="aborted", hostname="{pihole_host}"')
            return False
        else:
            helper.log_info(
                f'event_name="{event_name}", msg="Running scheduled Interval", hostname="{pihole_host}"')

    else:
        helper.log_info(
            f'event_name="{event_name}", msg="Checkpoint file not found", hostname="{pihole_host}"')

    return True


def zts_logger(msg, action, event_type, hostname, **kwargs):
    """ To help with consistent logging format
    :param msg: message for log
    :param action: event outcome (started|success|failure|aborted)
    :param event_type: type of event
    :param hostname: hostname of event
    :param kwargs: any kv pair

    zts_logger(
            msg='message',
            action='success',
            event_type=event_type,
            hostname=hostname
        )
    """
    event_log = f'msg="{msg}", action="{action}", event_type="{event_type}", hostname="{hostname}"'
    for key, value in kwargs.items():
        event_log = event_log + f', {key}="{value}"'

    return event_log
