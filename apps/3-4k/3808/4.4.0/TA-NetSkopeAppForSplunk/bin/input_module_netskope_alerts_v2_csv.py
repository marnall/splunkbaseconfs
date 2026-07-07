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

import netskope_iterator_collector_csv  # noqa: E402
import utility  # noqa: E402
from netskope_utils import check_input_config, read_conf_file

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

    global_account = helper.get_arg("global_account")
    if not global_account:
        logger.error("message=validation | Account not found: input={}".format(input_name))
        return False

    if not global_account.get("token_v2"):
        logger.error("message=validation | V2 token is not found: input={}".format(input_name))
        return False

    alert_type = helper.get_arg("alert_type")

    if not alert_type:
        logger.error("message=validation | Alert Types not found: input={}".format(input_name))
        return False
    else:
        for type_ in alert_type:
            if type_ not in const.ALERT_TYPES:
                logger.error(
                    "message=validation | Invalid Alert Type found: invalid_alert_type={} valid_alert_types= {} input={}".format(
                        type_, const.ALERT_TYPES, input_name
                    )
                )
                return False

    return True


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def check_existing_input(helper):
    "Check if input of same type is already configured or not."
    session_key=helper.context_meta["session_key"]
    current_alert_types = helper.get_arg("alert_type")

    
    check_input_config(
        session_key=session_key,
        current_input_name=helper.get_arg("name"),
        current_types=current_alert_types,
        current_account=helper.get_arg("global_account"),
        stanza_to_search="netskope_alerts_v2://",
        is_event=False,
        is_csv_input=True
    )


def collect_events(helper, ew):
    """Implement your data collection logic here"""
    try:
        global hist_type_complete
        script_start_time = time.time()

        # to make sure that error logs always gets printed in log file
        utility.disable_external_lib_logging()

        input_name = helper.get_arg("name")

        is_notification_sent = None
        conf_file_stanzas = read_conf_file(helper.context_meta["session_key"], "inputs")
        for input_stanza in conf_file_stanzas:
            if input_stanza.split("://")[-1] == input_name:
                is_notification_sent = conf_file_stanzas[input_stanza].get("is_notification_sent", None)

        # check if JSON input of same type is already configured or not
        if is_notification_sent is None:
            check_existing_input(helper)

        logger.debug("message=validate_input_params | Validating input parameters: input={}".format(input_name))
        # validate input params
        validate = validate_input_params(helper)
        if not validate:
            logger.info(
                "message=validation | Execution of script is finished due to invalid input configuation: "
                "input={}".format(input_name)
            )
            return

        logger.info("message=data_collection_start | Script invoked: input={}".format(input_name))

        alert_types = ["alert"] if "All" in helper.get_arg("alert_type") else helper.get_arg("alert_type")

        # initialize the object
        ec = netskope_iterator_collector_csv.AlertsCollector(helper, ew)
        workers = []

        lock = threading.Lock()
        for alert_type in alert_types:
            t = threading.Thread(target=netskope_iterator_collector_csv.BaseCollector.thread_runner, args=(alert_type, ec, hist_type_complete, lock))
            t.daemon = True
            t.start()
            workers.append(t)

        # wait till execution of all the thread
        for worker in workers:
            worker.join()

        logger.info(
            "message=data_collection_end | Execution of the script is finished: input={} time_taken={} "
            "seconds.".format(input_name, time.time() - script_start_time)
        )

    except Exception as e:
        logger.error(
            "message=unknown_error | Exception occurred while collection of data:"
            ' input={} error="{}" error_trace="{}"'.format(input_name, e, traceback.format_exc())
        )
