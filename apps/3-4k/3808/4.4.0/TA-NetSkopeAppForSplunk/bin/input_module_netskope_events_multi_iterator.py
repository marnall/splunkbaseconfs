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

import netskope_multi_iterator_collector  # noqa: E402
import utility  # noqa: E402
from netskope_utils import check_input_config, get_conf_file, read_conf_file

logger = logging.getLogger()


def validate_input_params(helper):
    """Provide the validation logic to validate the input stanza configurations."""
    input_name = helper.get_arg("name")
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

    event_type = helper.get_arg("event_type")
    if not event_type:
        logger.error("message=validation | Event type not found: input={}".format(input_name))
        return False
    else:
        if event_type not in ["connection", "application", "network"]:
            logger.error(
                "message=validation | Invalid Event type found: invalid_event_type={} valid_event_types= "
                '["connection", "application", "network"] '
                "input={}".format(event_type, input_name)
            )
            return False
    return True


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    """
    This function collects data for the selected event type
    """
    try:
        script_start_time = time.time()

        # to make sure that error logs always gets printed in log file
        utility.disable_external_lib_logging()

        input_name = helper.get_arg("name")

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
        ec = netskope_multi_iterator_collector.EventsMultiIteratorCollector(helper, ew)
        event_type = helper.get_arg("event_type")
        data_type = const.EVENT_TYPE_MAPPING.get(event_type)

        netskope_multi_iterator_collector.BaseCollector.thread_runner(data_type, ec)
        
        logger.info(
            "message=data_collection_end | Execution of the script is finished: input={} time_taken={} "
            "seconds.".format(input_name, time.time() - script_start_time)
        )

    except Exception as e:
        logger.error(
            "message=unknown_error | Exception occurred while collection of data:"
            ' input={} error="{}" error_trace="{}"'.format(input_name, e, traceback.format_exc())
        )
