"""Authentic8 module starting point."""
# encoding = utf-8

import datetime

from config import FIELDS, log_type_list
from splunk_utils import extract_input_fields
from utils import processing_auth8_logs, update_log_type_list

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''


def validate_input(helper, definition):
    """Implement your own validation logic to
     validate the input stanza configurations"""
    pass


def collect_events(helper, ew):
    """Implement your data collection logic here.
    :param helper: Splunk helper object through
    logger and user input will be accessed.
    :param ew: Event writer object for writing in splunk.

    """
    helper.log_info("Process started at {}.".format(datetime.datetime.now()))
    for i in range(1, 91):
        try:
            if helper.get_global_setting("kname_{}".format(i)):
                key_name = helper.get_global_setting("kname_{}".format(i))
                pvt_key = helper.get_global_setting("pkey_{}".format(i))
                helper.save_check_point(key_name, pvt_key)
            else:
                continue
        except Exception as err:
            helper.log_info("data not found from "
                            "global setting, getting error {} ".format(err))

    options = extract_input_fields(helper, FIELDS)
    update_log_type_list(options, helper)

    if isinstance(options["log_type"], list):
        process_log_list(options, options["log_type"], helper, ew)

    elif options['log_type'] and options['log_type'].lower() == "all":
        helper.log_info("Processing all input")
        process_log_list(options, log_type_list, helper, ew)
    else:
        helper.log_info("Invalid input-- {}.".format(options["log_type"]))

    helper.log_info("Process completed.")


def process_log_list(options, log_list, helper, ew):
    """
    Processing each log.
    :param options: a dictionary containing token, organisation name etc.
    :param log_list: log types list
    :param helper: Splunk helper object through
    logger and user input will be accessed.
    :param ew: Event writer object for writing in splunk.
    :return: None
    """
    for each in log_list:
        log_type = each.upper()
        helper.log_info("Processing user input and log"
                        " type is {} ".format(each))
        if log_type in log_type_list:
            processing_auth8_logs(log_type, options, helper, ew)
            if log_type == "ENC":
                processing_auth8_older_logs(log_type, options, helper, ew)
        else:
            helper.log_info("Invalid log. ")


def processing_auth8_older_logs(log_type, options, helper, ew):
    """
    processing authentic8 log
    :param log_type: Type of log
    :param options: Configuration dictionary
    :param helper: Splunk helper object.
    :param ew: Splunk event writer.
    :return: None
    """
    unprocessed_keys = helper.get_check_point('lost_key')
    if unprocessed_keys:
        helper.log_info("unprocessed key are {}".format(unprocessed_keys))
        for key in list(unprocessed_keys):
            helper.log_info("Processing older key {}".format(key))
            pvt_key = helper.get_check_point(key)
            helper.log_debug("Private key found for key_name '{}'".format(key))
            if pvt_key:
                processing_auth8_logs(log_type,
                                      options, helper, ew,
                                      start_seq_flag=1, old_key_name=key)
                unprocessed_keys.remove(key)
                helper.log_info("Unprocessed key list "
                                "is {}".format(unprocessed_keys))
                helper.save_check_point('lost_key', unprocessed_keys)
            else:
                helper.log_debug("Pvt key not found for "
                                 "old key_name {}".format(key))
