# encoding = utf-8

import ta_netskopeappforsplunk_declare  # noqa: F401
import os
import sys
import time

import logging
import threading
import const
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "common")))
sys.path.insert(0, os.path.abspath(os.path.join(__file__, "..", "modinputs", "iterator")))

import netskope_iterator_collector  # noqa: E402
import utility  # noqa: E402
from netskope_utils import get_conf_file, check_input_config, read_conf_file

logger = logging.getLogger()
hist_type_complete = [0]
HIST_COMPLETED_SLEEP = 24*60*60


def validate_input_params(helper):
    """Provide the validation logic to validate the input stanza configurations."""
    input_name = helper.get_arg("name")
    try:
        int(helper.get_arg("interval"))
    except ValueError:
        logger.error("message=validation | Invalid Interval: input={}".format(input_name))
        return False

    try:
        int(helper.get_arg("retry_count"))
    except ValueError:
        logger.error("message=validation | Invalid Retry Count: input={}".format(input_name))
        return False

    try:
        start_datetime = helper.get_arg("start_datetime")
        if start_datetime is None:
            logger.error("message=validation | Start DateTime not found: input={}".format(input_name))
            return False
        else:
            starttime = utility.DateTimeUtil.iso_to_epoch(start_datetime)
            if starttime > utility.DateTimeUtil.get_current_epoch():
                logger.error("message=validation | Start DateTime should not be in future: input={}".format(input_name))
                return False
    except ValueError:
        logger.error(
            "message=validation | Start DateTime should be "
            "in 'YYYY-MM-DDTHH:MM:SSZ' (UTC) format: input={}".format(input_name)
        )
        return False

    try:
        end_datetime = helper.get_arg("end_datetime")
        if end_datetime is not None:
            endtime = utility.DateTimeUtil.iso_to_epoch(end_datetime)
            if endtime < starttime:
                logger.error("message=validation | End DateTime should not be less then Start DateTime: input={}".format(input_name))
                return False
    except ValueError:
        logger.error(
            "message=validation | End DateTime should be "
            "in 'YYYY-MM-DDTHH:MM:SSZ' (UTC) format: input={}".format(input_name)
        )
        return False

    global_account = helper.get_arg("global_account")
    if not global_account:
        logger.error("message=validation | Account not found: input={}".format(input_name))
        return False

    if not global_account.get("token_v2"):
        logger.error("message=validation | V2 token is not found: input={}".format(input_name))
        return False

    event_type = helper.get_arg("event_type")
    if not event_type:
        logger.error("message=validation | Event types not found: input={}".format(input_name))
        return False
    else:
        for type_ in event_type:
            if type_ not in const.EVENT_TYPE_MAPPING:
                logger.error(
                    "message=validation | Invalid Event type found: invalid_event_type={} valid_event_types= "
                    '["connection", "application", "audit", "infrastructure", "network", "incident", "endpoint"] '
                    "input={}".format(type_, input_name)
                )
                return False
    return True


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def check_existing_CSV_input(helper):
    "Check if CSV input of same type is already configured or not."
    session_key=helper.context_meta["session_key"]
    current_event_types = helper.get_arg("event_type")

    check_input_config(
        session_key=session_key,
        current_input_name=helper.get_arg("name"),
        current_types=current_event_types,
        current_account= helper.get_arg("global_account"),
        stanza_to_search="netskope_events_v2_csv://",
        is_event=True,
        is_csv_input=False
    )


def collect_events(helper, ew):
    """
    This function collects data for selected event types and
    creates n (length of selected event types) no. of threads
    each thread will collect one of the event type's data
    """
    global hist_type_complete
    try:
        script_start_time = time.time()

        # to make sure that error logs always gets printed in log file
        utility.disable_external_lib_logging()

        input_name = helper.get_arg("name")

        is_notification_sent = None
        conf_file_stanzas = read_conf_file(helper.context_meta["session_key"], "inputs")
        for input_stanza in conf_file_stanzas:
            if input_stanza.split("://")[-1] == input_name:
                is_notification_sent = conf_file_stanzas[input_stanza].get("is_notification_sent", None)

        # check if CSV input of same type is already configured or not
        if is_notification_sent is None:
            check_existing_CSV_input(helper)

        logger.debug("message=validate_input_params | Validating input parameters: input={}".format(input_name))
        # validate input params
        validate = validate_input_params(helper)
        if not validate:
            logger.info(
                "message=validation | Execution of script is finished due to error in validation:"
                " input={}".format(input_name)
            )
            return

        logger.info("message=data_collection_start | Script invoked: input={}".format(input_name))

        # initialize the object
        ec = netskope_iterator_collector.EventsCollector(helper, ew)
        workers = []

        lock = threading.Lock()
        for event_type in ec.event_type_mapping:
            netskope_iterator_collector.event_retry_count[event_type] = 0
            t = threading.Thread(target=netskope_iterator_collector.BaseCollector.thread_runner, name="thread-{}".format(event_type), args=(event_type, ec, hist_type_complete, lock, workers))
            t.daemon = True
            t.start()
            workers.append(t)

        # wait till execution of all the thread
        for worker in workers:
            worker.join()
            
        # wait till execution of all the killed threads
        for killed_thread in netskope_iterator_collector.killed_threads:
            killed_thread.join()

        end_datetime = helper.get_arg("end_datetime")
        if end_datetime is not None:
            if hist_type_complete[0] == len(ec.event_type_mapping):
                message = "AppName: '{}' Input: '{}'. Historical data collection has been completed. Please disable this input.".format(
                    'NetSkope Add-on For Splunk',
                    input_name
                )
                logger.warn(message)
                modinput_name = f"{const.MODINPUT_NAME}://{input_name}"
                logger.info("Updating the input %s with is_safe_to_delete=1 parameter.", input_name)
                # Update the input.conf stanza with flag is_safe_to_delete = True.
                try:
                    conf = get_conf_file(helper.context_meta["session_key"], file='inputs', app=const.APP_NAME)
                    conf.update(modinput_name, {const.IS_SAFE_TO_DELETE_FLAG: 1})
                    logger.info("Updated the stanza for input %s successfully.", input_name)
                except Exception as ex:
                    logger.error("Error occurred while updating the input %s with parameter is_safe_to_delete. Error: %s.", input_name, ex)

                time.sleep(HIST_COMPLETED_SLEEP)

        logger.info(
            "message=data_collection_end | Execution of the script is finished: input={} time_taken={} "
            "seconds.".format(input_name, time.time() - script_start_time)
        )

    except Exception as e:
        logger.error(
            "message=unknown_error | Exception occurred while collection of data:"
            ' input={} error="{}" error_trace="{}"'.format(input_name, e, traceback.format_exc())
        )
