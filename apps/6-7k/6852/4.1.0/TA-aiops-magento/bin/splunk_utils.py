from json import dumps
from base64 import b64encode
from datetime import datetime, timedelta


def get_cron_ingestion_start_time(helper, data_input_name, start_time, version):
    checkpoint_key = f'cron_ingestion_{data_input_name}_{start_time}_{version}'

    if helper.get_check_point(checkpoint_key) is None:
        helper.save_check_point(checkpoint_key, start_time)

    return helper.get_check_point(checkpoint_key)


def set_cron_ingestion_next_start_time(helper, data_input_name, start_time, version, next_start_time):
    checkpoint_key = f'cron_ingestion_{data_input_name}_{start_time}_{version}'

    helper.save_check_point(checkpoint_key, next_start_time)


def get_order_ingestion_start_time(helper, data_input_name, start_time, version):
    checkpoint_key = f'order_ingestion_{data_input_name}_{start_time}_{version}'

    if helper.get_check_point(checkpoint_key) is None:
        helper.save_check_point(checkpoint_key, start_time)

    return helper.get_check_point(checkpoint_key)


def set_order_ingestion_next_start_time(helper, data_input_name, start_time, version, next_start_time):
    checkpoint_key = f'order_ingestion_{data_input_name}_{start_time}_{version}'

    helper.save_check_point(checkpoint_key, next_start_time)


def get_order_updates_ingestion_start_time(helper, data_input_name, start_time, version):
    checkpoint_key = f'order_updates_ingestion_{data_input_name}_{start_time}_{version}'

    if helper.get_check_point(checkpoint_key) is None:
        helper.save_check_point(checkpoint_key, start_time)

    return helper.get_check_point(checkpoint_key)


def set_order_updates_ingestion_next_start_time(helper, data_input_name, start_time, version, next_start_time):
    checkpoint_key = f'order_updates_ingestion_{data_input_name}_{start_time}_{version}'

    helper.save_check_point(checkpoint_key, next_start_time)


def get_job_ingestion_ingestion_start_time(helper, data_input_name, start_time, version):
    checkpoint_key = f'job_ingestion_{data_input_name}_{start_time}_{version}'

    if helper.get_check_point(checkpoint_key) is None:
        helper.save_check_point(checkpoint_key, start_time)

    return helper.get_check_point(checkpoint_key)


def set_job_ingestion_next_start_time(helper, data_input_name, start_time, version, next_start_time):
    checkpoint_key = f'job_ingestion_{data_input_name}_{start_time}_{version}'

    helper.save_check_point(checkpoint_key, next_start_time)


def write_to_index(helper, ew, data, hostname, source):
    event = helper.new_event(
        dumps(data),
        host=hostname,
        index=helper.get_output_index(),
        source=source,
    )
    ew.write_event(event)


def get_or_create_log_file_state(helper, log_file, **kwargs):
    # Key consists of two attributes separated by underscore:
    #   1. Server id which serves the log file
    #   2. File path of the log file
    # Format: <server_id>_<log_file_path>
    # Example: i-0eed26bf322ef1bb1_/app/p2f3xbqpgpxow_stg2/var/log/system.log.228.gz
    server_id = kwargs.get("server", "unknown")
    log_file_id = f"{server_id}_{log_file.get('path')}"
    key_b64 = b64encode(
        log_file_id.encode()
    ).decode("utf-8")
    key = f"log_file_{key_b64}"

    if helper.get_check_point(key) is None:
        file_state = {
            "creation_date": log_file.get("creation_time"),
            "bytes_read": int(log_file.get("size"))
        }
        helper.save_check_point(key, file_state)

    return helper.get_check_point(key)


def save_log_file_state(helper, log_file, **kwargs):
    # Key consists of two attributes separated by underscore:
    #   1. Server id which serves the log file
    #   2. File path of the log file
    # Format: <server_id>_<log_file_path>
    # Example: i-0eed26bf322ef1bb1_/app/p2f3xbqpgpxow_stg2/var/log/system.log.228.gz
    server_id = kwargs.get("server", "unknown")
    log_file_id = f"{server_id}_{log_file.get('path')}"
    key_b64 = b64encode(
        log_file_id.encode()
    ).decode("utf-8")
    key = f"log_file_{key_b64}"
    file_state = {
        "creation_date": log_file.get("creation_time"),
        "bytes_read": int(log_file.get("size"))
    }
    helper.save_check_point(key, file_state)

    return None
