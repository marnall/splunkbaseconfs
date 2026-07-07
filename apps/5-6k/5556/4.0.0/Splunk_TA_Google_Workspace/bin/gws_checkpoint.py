#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import datetime
import logging
import time
import calendar
import sys
from typing import Optional, Tuple, List

import pytz
from solnlib import modular_input, log
from splunklib import client, binding

import gws_utils

LAG_TIME_DAYS = 4  # lag times based on google docs: https://support.google.com/a/answer/7061566?hl=en
DATA_RETENTION_DAYS = 180


def seconds_to_str(seconds: float) -> str:
    """Converts time from seconds to string format.

    Args:
        seconds: time in seconds

    Examples:
        >>> seconds_to_str(1659092824) == "2022-07-29T11:07:04.000Z"
    """
    datetime_from_timestamp = datetime.datetime.fromtimestamp(
        seconds, datetime.timezone.utc
    )
    return (
        datetime_from_timestamp.isoformat("T", "milliseconds").replace("+00:00", "")
        + "Z"
    )


def str_to_seconds(timestamp: str) -> float:
    """Converts datetime in a form of string to a UNIX timestamp value in a
    float format. This function assumes that the timestamp in a form of string
    is in UTC timezone.

    Args:
        timestamp: datetime in string format

    Examples:
        >>> str_to_seconds("2022-07-29T13:07:04Z") == 1659092824.
    """
    timestamp_without_z = timestamp.replace("Z", "")
    d = datetime.datetime.fromisoformat(timestamp_without_z)
    return calendar.timegm(d.utctimetuple())


def get_intervals_for_usage_report(
    logger: logging.Logger,
    start: str,
    end: str,
) -> Optional[List[str]]:
    """
    Creates a list of dates that will be used in API calls to retrieve data.
    :param logger: logger object
    :param start: start date for modinput, checkpoint in most cases
    :param end: string of time now
    :return result: a list of dates for API calls
    """
    start_of_interval = datetime.date.fromisoformat(start[:10])
    end_of_interval = datetime.date.fromisoformat(end[:10])

    end_date_with_lag_time = end_of_interval - datetime.timedelta(days=LAG_TIME_DAYS)

    num_days = (end_date_with_lag_time - start_of_interval).days
    result = []
    if num_days > 0:
        date = start_of_interval
        while date <= end_date_with_lag_time:
            result.append(date.isoformat())
            date = date + datetime.timedelta(days=1)

        return result
    else:
        raise Exception(
            "Could not retrieve data for Usage Report. Reason: No dates in the interval."
        )


def validate_start_date(
    start_date: str,
    now: datetime.datetime,
) -> bool:
    """
    Validates if start date is between 6 months back from now to 4 days back from now,
    because of Google API lag times and retention policy, docs:
    https://support.google.com/a/answer/7061566?hl=en

    :param start_date: start date passed by input
    :param now: datetime object for now_time
    :return bool: True if valid start_date, else false
    """
    start_time = datetime.datetime.fromisoformat(start_date)
    start_time = start_time.astimezone(pytz.timezone("UTC"))
    min_days = now - datetime.timedelta(days=DATA_RETENTION_DAYS)
    max_days = now - datetime.timedelta(days=LAG_TIME_DAYS)

    if min_days < start_time < max_days:
        return True
    else:
        return False


def migrate_activity_report_checkpoint(
    logger: logging.Logger,
    checkpointer: modular_input.KVStoreCheckpointer,
    service: client.Service,
    input_name: str,
):
    checkpoint_from_kvstore = get_activity_report_checkpoint_from_kvstore(
        logger, checkpointer
    )
    if checkpoint_from_kvstore is not None:
        logger.info(
            "Checkpoint already exists in KVStore, no need to do anything else."
        )
        return
    checkpoint_from_file = get_activity_report_checkpoint_from_file(
        logger, service, input_name
    )
    if checkpoint_from_file is None:
        # No legacy file checkpoint exists either — this is a fresh start (e.g. after
        # a failed v3.1.0 migration where the KVStore collection was not created).
        # Proactively seed an initial checkpoint document so that the backing
        # GET .../storage/collections/data/{collection}/checkpoint endpoint always
        # returns a document rather than 404. Without this seed, some versions of the
        # KVStore SDK or transient errors can cause 404 to propagate uncaught and crash
        # the ingestion run.
        logger.info(
            "No checkpoint found in file or KVStore. Seeding an initial KVStore "
            "checkpoint document so that ingestion can proceed cleanly."
        )
        try:
            save_checkpoint_to_kvstore(checkpointer, time.time())
            logger.info("Initial KVStore checkpoint document seeded successfully.")
        except Exception as seed_exc:
            log.log_exception(
                logger,
                seed_exc,
                "Checkpoint Error",
                msg_before=(
                    f"Failed to seed initial KVStore checkpoint for '{input_name}'. "
                    "The checkpoint document will be created during the first "
                    "successful ingestion run instead."
                ),
            )
        return
    logger.info(
        "No checkpoint in KVStore, but exists in file. Updating KVStore to include value from file."
    )
    save_checkpoint_to_kvstore(
        checkpointer,
        checkpoint_from_file,
    )
    logger.info("Deleting existing checkpoint from file.")
    delete_activity_report_checkpoint_from_file(
        logger,
        service,
        input_name,
    )


def get_activity_report_checkpoint_from_file(
    logger: logging.Logger, service: client.Service, input_name: str
) -> Optional[float]:
    try:
        if "gws_checkpoints" not in service.confs:
            logger.debug("No gws_checkpoints.conf file found")
            return None
    except client.HTTPError as e:
        # 404 means gws_checkpoints.conf genuinely does not exist — safe to treat
        # as "no legacy file checkpoint" and let the KVStore-based flow continue.
        # For other status codes (5xx, 403, etc.) we cannot tell whether the file
        # exists but was temporarily unreachable, so we re-raise to avoid silently
        # discarding a valid historical checkpoint.
        if e.status == 404:
            logger.debug(
                f"gws_checkpoints.conf not found for {input_name} (HTTP 404). "
                "Treating as no legacy file checkpoint; KVStore checkpointing will continue."
            )
            return None
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=(
                f"Could not read gws_checkpoints.conf for {input_name} because of HTTP "
                f"error code {e.status} '{e.reason}'. The file may be temporarily "
                f"unreachable; re-raising to avoid discarding a valid checkpoint."
            ),
        )
        raise
    conf = service.confs["gws_checkpoints"]
    try:
        stanza = conf[input_name.replace("/", "_")]
        return float(stanza["checkpoint_time"])
    except KeyError as e:
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=f"No stanza found for {input_name} in gws_checkpoints.conf",
        )
        return None
    except client.HTTPError as e:
        # Same rationale as the outer block: only treat 404 as "stanza absent".
        # A 5xx/403 here means the conf file might exist but splunkd is struggling;
        # re-raise rather than silently discarding a potentially valid checkpoint.
        if e.status == 404:
            logger.debug(
                f"Stanza for {input_name} not found in gws_checkpoints.conf (HTTP 404). "
                "Treating as no legacy file checkpoint; KVStore checkpointing will continue."
            )
            return None
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=(
                f"Could not read stanza for {input_name} in gws_checkpoints.conf because "
                f"of HTTP error code {e.status} '{e.reason}'. The stanza may be "
                f"temporarily unreachable; re-raising to avoid discarding a valid checkpoint."
            ),
        )
        raise


def delete_activity_report_checkpoint_from_file(
    logger: logging.Logger, service: client.Service, input_name: str
) -> None:
    try:
        conf = service.confs["gws_checkpoints"]
        conf.delete(input_name.replace("/", "_"))
    except KeyError as e:
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=f"Could not delete checkpoint for {input_name} because of KeyError {e}",
        )
    except client.HTTPError as e:
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=f"Could not delete checkpoint for {input_name} because of HTTP error code {e.status} '{e.reason}'",
        )


def get_activity_report_checkpoint_from_kvstore(
    logger: logging.Logger,
    checkpointer: modular_input.KVStoreCheckpointer,
) -> Optional[str]:
    try:
        checkpoint_dict = checkpointer.get(
            gws_utils.ACTIVITY_REPORT_CHECKPOINT_COLLECTION_KEY
        )
        if checkpoint_dict is None:
            return None
        return checkpoint_dict.get("checkpoint")
    except binding.HTTPError as e:
        log.log_exception(
            logger,
            e,
            "Checkpoint Error",
            msg_before=f"Could not get checkpoint from KVStore because of {e}",
        )
        return None


def get_start_end_times_for_activity_report_from_kvstore(
    logger: logging.Logger,
    lookback_offset: str,
    kvstore_checkpointer: modular_input.KVStoreCheckpointer,
) -> Tuple[str, str]:
    checkpoint = float(int(time.time())) - float(lookback_offset)
    end_time: str = seconds_to_str(checkpoint)
    checkpoint_from_kvstore = get_activity_report_checkpoint_from_kvstore(
        logger, kvstore_checkpointer
    )
    if checkpoint_from_kvstore is None:
        start_time = end_time
        logger.info("No existing checkpoints")
    else:
        # This scenario is possible if the user is changing the lookbackOffset.
        # No checkpoint exists, interval is 5 minutes.
        # First run:
        #   time now - 3 PM
        #   lookback offset is 5 minutes
        #   2:55 PM checkpoint is saved.
        # Second run (user is changing the lookback offset to 1 hour):
        #   time now 3:05 PM
        #   lookback offset is 1 hour
        #   calculated checkpoint - 2:05 PM
        #   checkpoint from KVStore - 2:55 PM
        #   we are defaulting back to start_time = end_time = checkpoint = 2:05 PM
        if float(checkpoint_from_kvstore) > checkpoint:
            start_time = end_time
        else:
            start_time = seconds_to_str(float(checkpoint_from_kvstore))
    logger.info(
        f"Activity report will be queried with startTime: {start_time} UTC and endTime: {end_time} UTC"
    )

    return start_time, end_time


def save_checkpoint_to_kvstore(
    checkpointer: modular_input.KVStoreCheckpointer, checkpoint_value: float
):
    checkpointer.update(
        gws_utils.ACTIVITY_REPORT_CHECKPOINT_COLLECTION_KEY,
        {"checkpoint": checkpoint_value},
    )


def _to_local_time(time_usec) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(time_usec / 10**6)


def get_query_intervals_for_gmail(
    checkpoint: Optional[int], logger: logging.Logger
) -> Tuple[int, int]:
    """Returns start and end time for gmail job.

    Args:
        checkpoint: Checkpoint value, None if does not exist
        logger: Logger object
    """
    interval = datetime.timedelta(minutes=10)
    interval_in_usec = 600000000
    now = datetime.datetime.now(tz=pytz.utc)
    if not checkpoint:
        start_time = now - datetime.timedelta(minutes=20)
        start_time_usec = int(datetime.datetime.timestamp(start_time) * 10**6)
        end_time = start_time + interval
        end_time_usec = int(datetime.datetime.timestamp(end_time) * 10**6)
        logger.info(
            f"No checkpoint exists "
            f"start time is {start_time_usec} (local time {_to_local_time(start_time_usec)}) "
            f"end time is {end_time_usec} (local time {_to_local_time(end_time_usec)})"
        )
    else:
        start_time_usec = checkpoint
        end_time_usec = (
            int(datetime.datetime.timestamp(now) * 10**6) - interval_in_usec
        )
        logger.info(
            f"Checkpoint exists "
            f"start time is {start_time_usec} (local time {_to_local_time(start_time_usec)}) "
            f"end time is {end_time_usec} (local time {_to_local_time(end_time_usec)})"
        )
    return start_time_usec, end_time_usec


def get_query_intervals_for_alerts(
    checkpoint: Optional[str], delay: int, logger: logging.Logger
) -> Tuple[str, str]:
    """Returns start and end time for Google Alerts API job.

    Args:
        checkpoint: Checkpoint value, None if does not exist
        logger: Logger object
    """
    now = datetime.datetime.now(tz=pytz.utc)
    timedelta_delay = datetime.timedelta(minutes=delay)
    timedelta_interval = datetime.timedelta(minutes=10)
    if not checkpoint:
        start_time = now - timedelta_delay - timedelta_interval
        end_time = now - timedelta_delay
        start_time_in_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time_in_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(
            f"No checkpoint exists "
            f"start time is {start_time_in_str} UTC "
            f"end time is {end_time_in_str} UTC"
        )
    else:
        checkpoint_datetime = datetime.datetime.strptime(
            checkpoint, "%Y-%m-%dT%H:%M:%SZ"
        )
        start_time = checkpoint_datetime
        start_time_in_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_time = now - timedelta_delay
        end_time_in_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info(
            f"Checkpoint exists "
            f"start time is {start_time_in_str} UTC "
            f"end time is {end_time_in_str} UTC"
        )
    return start_time_in_str, end_time_in_str


def get_dates_for_usage_report(
    checkpoint: Optional[int],
    logger: logging.Logger,
    start_date=None,
) -> List[str]:
    """
    Returns dates for usage report input
    :param checkpoint: a checkpoint of modinput if present
    :param logger: a logger object
    :param start_date: start_date of modinput, default None
    :return list: list of dates for modinput API calls
    """
    now = datetime.datetime.now(tz=pytz.utc)
    if not checkpoint:
        if not start_date:
            start_time_default = now - datetime.timedelta(days=30)
            start_time = datetime.datetime.timestamp(start_time_default)
            logger.info(
                f"No checkpoint exists "
                f"start time is {start_time} (local time {datetime.datetime.fromtimestamp(start_time)}) "
            )
        else:
            if validate_start_date(start_date, now):
                start_time = str_to_seconds(start_date)
                logger.info(
                    f"No checkpoint exists "
                    f"start time is {start_time} (local time {datetime.datetime.fromtimestamp(start_time)}) "
                )
            else:
                raise Exception(
                    "Start date cannot be further than 6 months back from now and no closer than 4 days back from now due to data retention and lag times. Exiting..."
                )

    else:
        next_checkpoint = datetime.datetime.fromtimestamp(
            checkpoint
        ) + datetime.timedelta(
            days=1
        )  # Added one day to checkpoint as checkpoint is the day that latest event has been generated, so the next value we want is checkpoint +1
        start_time = str_to_seconds(str(next_checkpoint))
        logger.info(
            f"Checkpoint exists "
            f"start time is {start_time} (local time {datetime.datetime.fromtimestamp(start_time)}) "
        )

    start_time_str = seconds_to_str(start_time)
    return get_intervals_for_usage_report(logger, start_time_str, str(now))
