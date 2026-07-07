"""Utility Splunk handlers."""

# ============================================================================
# Copyright (C) Lancope Inc.  All Rights Reserved.  Version 1.0
# api_utility.py script for use with Splunk enterprise to query StealthWatch
# using the SMC appliance REST API extension service
# ============================================================================

##############################################################################
# Get some libraries we will need
##############################################################################

import datetime
import logging
import logging.handlers
import math
import os
import time
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
import splunk
import splunk.Intersplunk
import sys

from distutils.util import strtobool

import splunk.clilib.cli_common as cli_common


###################################################
# Declare variables that may differ based on OS.
###################################################

path_delim = "/"
# If Splunk is installed on a Windows OS
if os.name == "nt":
    path_delim = "\\"

myapp = "cisco_sna_app"

number_of_decimal_places = 2

# Library-loading boilerplate

# splunkhome = os.environ['SPLUNK_HOME']
# apphome = os.path.join(splunkhome, 'etc', 'apps', myapp)
# sys.path.append(os.path.join(apphome, 'python/'))


def setup_logging(log_name):
    logger = logging.getLogger('splunk.' + log_name)
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = log_name + ".log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s -- %(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


def retrieve_password_secret(logger):
    import splunk.entity as entity

    try:
        # read session key sent from splunkd
        for line in sys.stdin:
            if line.startswith('sessionKey'):
                session_key = line.replace('sessionKey:', '').strip()

        if len(session_key) == 0:
            logger.info("Did not receive a session key from splunkd. " +
                        "Please enable passAuth in inputs.conf for this " +
                        "script")

    except Exception as e:
        logger.info('Problem retrieving Session key Error: ' + e)
        sys.exit()

    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords', 'cisco_sna_app_realm:nobody:'], namespace=myapp,
                                      owner='nobody', sessionKey=session_key)
    except Exception as e:
        logger.error("Could not get %s credentials from splunk. Error:" + str(e))
        sys.exit()

        # return first set of credentials
    for i, c in entities.items():
        return str(c['clear_password'])


###################################################
# Get the config sna_app_settings[smc_settings]
###################################################
def get_config(logger):
    # This is still deprecated
    logger.info("Reading smc_settings from cisco_sna_app")
    conf = cli_common.getAppConf('sna_app_settings', myapp)
    # Strip whitespace and remove all quotation marks from smc_settings config items
    # Why? Because we did it before and I'm afraid of breaking things
    smc_conf = {k: v.strip().replace('"', "") for k, v in conf.get('smc_settings', {}).items()}
    if not smc_conf:
        logger.error("Failed to read SMC configuration")
    return {
        # The urllib stuff is also out of fear of breaking things
        "smcIP": six.moves.urllib.parse.quote_plus(smc_conf.get('smc_host')),
        "smcDomainID": six.moves.urllib.parse.quote_plus(smc_conf.get('smc_domain_id')),
        "smcID": smc_conf.get('smc_id'),
        "smcPW": retrieve_password_secret(logger)
    }


###################################################
# Get the datetimes as a dict
###################################################
def get_timerange(earliest, latest, logger):
    end_datetime = None
    start_datetime = None

    # Splunk has added rt- to realtime strings
    if 'rt' in earliest.lower():
        earliest = earliest.lower().replace('rt', '')

    if 'rt' in latest.lower():
        latest = latest.lower().replace('rt', 'now')
    # relative time
    if ("now" in latest and not earliest.isdigit()) or (
        "@" in latest and len(latest.split("@")[0]) == 0
    ):
        logger.info("Generating Relative Datetime Filter...")
        current_time = datetime.datetime.now()
        if "@" in latest:
            if latest.endswith("s"):
                end_datetime = datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour,
                    current_time.minute,
                    current_time.second,
                )
            elif latest.endswith("m"):
                end_datetime = datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour,
                    current_time.minute,
                )
            elif latest.endswith("h"):
                end_datetime = datetime.datetime(
                    current_time.year,
                    current_time.month,
                    current_time.day,
                    current_time.hour,
                )
            elif latest.endswith("d"):
                end_datetime = datetime.datetime(
                    current_time.year, current_time.month, current_time.day
                )
            elif latest.endswith("w") or latest.endswith("w0"):
                end_datetime = datetime.datetime(
                    current_time.year, current_time.month, current_time.day
                ) - datetime.timedelta(
                    days=(
                        datetime.datetime(
                            current_time.year, current_time.month, current_time.day
                        ).weekday()
                    ) - 1
                )
            elif latest.endswith("w1"):
                end_datetime = datetime.datetime(
                    current_time.year, current_time.month, current_time.day
                ) - datetime.timedelta(
                    days=datetime.datetime(
                        current_time.year, current_time.month, current_time.day
                    ).weekday()
                )
            elif latest.endswith("mon"):
                end_datetime = datetime.datetime(
                    current_time.year, current_time.month, 1
                )
            elif latest.endswith("q"):
                end_datetime = datetime.datetime(
                    current_time.year,
                    (int((current_time.month + 2) // 3) * 3) - 2,
                    current_time.day,
                    current_time.hour,
                )
            elif latest.endswith("y"):
                end_datetime = datetime.datetime(current_time.year, 1, 1)
        else:
            end_datetime = current_time
        earliest_tmp = earliest.split("@")[0]
        if len(earliest_tmp) == 0:
            start_datetime = current_time
        elif earliest_tmp.endswith("s"):
            start_datetime = current_time - datetime.timedelta(
                seconds=int(earliest_tmp.split("-")[1].replace("s", ""))
            )
        elif earliest_tmp.endswith("m"):
            start_datetime = current_time - datetime.timedelta(
                minutes=int(earliest_tmp.split("-")[1].replace("m", ""))
            )
        elif earliest_tmp.endswith("h"):
            start_datetime = current_time - datetime.timedelta(
                hours=int(earliest_tmp.split("-")[1].replace("h", ""))
            )
        elif earliest_tmp.endswith("d"):
            start_datetime = current_time - datetime.timedelta(
                days=int(earliest_tmp.split("-")[1].replace("d", ""))
            )
        elif earliest_tmp.endswith("w"):
            start_datetime = current_time - datetime.timedelta(
                weeks=int(earliest_tmp.split("-")[1].replace("w", ""))
            )
        elif earliest_tmp.endswith("mon"):
            start_month = current_time.month - int(
                earliest_tmp.split("-")[1].replace("mon", "")
            )
            start_year = current_time.year
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start_datetime = datetime.datetime(
                start_year,
                start_month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second,
            )
        elif earliest_tmp.endswith("q"):
            start_month = current_time.month - (
                int(earliest_tmp.split("-")[1].replace("q", "")) * 3
            )
            start_year = current_time.year
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            start_datetime = datetime.datetime(
                start_year,
                start_month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second,
            )
        elif earliest_tmp.endswith("y"):
            start_datetime = datetime.datetime(
                (current_time.year - int(earliest_tmp.split("-")[1].replace("y", ""))),
                current_time.month,
                current_time.day,
                current_time.hour,
                current_time.minute,
                current_time.second,
            )
        if "@" in earliest:
            if earliest.endswith("s"):
                start_datetime = datetime.datetime(
                    start_datetime.year,
                    start_datetime.month,
                    start_datetime.day,
                    start_datetime.hour,
                    start_datetime.minute,
                    start_datetime.second,
                )
            elif earliest.endswith("m"):
                start_datetime = datetime.datetime(
                    start_datetime.year,
                    start_datetime.month,
                    start_datetime.day,
                    start_datetime.hour,
                    start_datetime.minute,
                )
            elif earliest.endswith("h"):
                start_datetime = datetime.datetime(
                    start_datetime.year,
                    start_datetime.month,
                    start_datetime.day,
                    start_datetime.hour,
                )
            elif earliest.endswith("d"):
                start_datetime = datetime.datetime(
                    start_datetime.year, start_datetime.month, start_datetime.day
                )
            elif earliest.endswith("w") or earliest.endswith("w0"):
                start_datetime = datetime.datetime(
                    start_datetime.year, start_datetime.month, start_datetime.day
                ) - datetime.timedelta(
                    days=(
                        datetime.datetime(
                            start_datetime.year,
                            start_datetime.month,
                            start_datetime.day,
                        ).weekday()
                    ) - 1
                )
            elif earliest.endswith("w1"):
                start_datetime = datetime.datetime(
                    start_datetime.year, start_datetime.month, start_datetime.day
                ) - datetime.timedelta(
                    days=datetime.datetime(
                        start_datetime.year, start_datetime.month, start_datetime.day
                    ).weekday()
                )
            elif earliest.endswith("mon"):
                start_datetime = datetime.datetime(
                    start_datetime.year, start_datetime.month, 1
                )
            elif earliest.endswith("q"):
                start_datetime = datetime.datetime(
                    start_datetime.year,
                    (int((start_datetime.month + 2) // 3) * 3) - 2,
                    1,
                )
            elif earliest.endswith("y"):
                start_datetime = datetime.datetime(start_datetime.year, 1, 1)
        logger.info("Done Generating Relative Datetime Filter.")

    # absolute time
    else:
        logger.info("Generating Absolute Datetime Filter...")
        if latest == "now":
            end_datetime = datetime.datetime.now()
        else:
            end_datetime = datetime.datetime.fromtimestamp(int(latest))
        if len(earliest) == 0:
            start_datetime = datetime.datetime.fromtimestamp(0)
        else:
            start_datetime = datetime.datetime.fromtimestamp(int(earliest))
        logger.info("Generating Absolute Datetime Filter.")

    ts = time.time()
    utc_offset = (
        datetime.datetime.fromtimestamp(ts) - datetime.datetime.utcfromtimestamp(ts)
    ).total_seconds()

    # convert to UTC time
    start_datetime = start_datetime - datetime.timedelta(seconds=(utc_offset))
    end_datetime = end_datetime - datetime.timedelta(seconds=(utc_offset))

    # set the values to be returned
    timerange = {"start_datetime": start_datetime, "end_datetime": end_datetime}

    return timerange


def traverse_host_groups(tag, parent_path, host_group_dict):
    host_group = ""
    if len(parent_path) == 0 and tag["displayName"] == "Internal Host Tags":
        host_group = "Inside Hosts"
    elif len(parent_path) == 0 and tag["displayName"] == "External Host Tags":
        host_group = "Outside Hosts"
    elif len(parent_path) == 0 and tag["displayName"] == "External Geo Host Tags":
        host_group = "Countries"
    else:
        host_group = parent_path + tag["displayName"]
    host_group_dict[tag["id"]] = host_group
    for child_tag in tag["tags"]:
        traverse_host_groups(child_tag, host_group + "/", host_group_dict)
    return host_group_dict


def parse_args():
    """Gets arguments from the command line and returns a tuple of ([options], {kwarg_key: kwarg_value})"""
    args, kwargs = splunk.Intersplunk.getKeywordsAndOptions()
    return args, kwargs


def string_with_unit(val, units, base, n_decimal_places=number_of_decimal_places):
    """Converts a value to a string with a unit, rounded to n_decimal_places (default 2)

    The unit will be the highest order of magnitude for which val/base**magnitude_of_unit >= 1
    EX string_with_unit(1000, ["g", "kg"], 1000) will return 1.00kg
    """
    val = float(val)
    order = math.floor(math.log(abs(val), base)) if val else 0  # Log(0) is undefined
    index = min(order, len(units) - 1)
    return f"{round(val / base ** order, n_decimal_places)}{units[index]}"


def convert_bytes_to_string(input_bytes):
    SUFFIXES = ('B', 'KB', 'MB', 'GB', 'TB')
    return string_with_unit(input_bytes, SUFFIXES, 1024)


def convert_mhz_to_string(mhz):
    SUFFIXES = ('MHz', 'GHz', 'THz')
    return string_with_unit(mhz, SUFFIXES, 1000)


def process_host_group_dict(host_group_dict, parent_host_group, children):
    for child in children:
        this_group_name = parent_host_group + "/" + child["name"]
        if this_group_name == "Outside Hosts/Countries":
            this_group_name = "Countries"
        host_group_dict[int(child["id"])] = this_group_name
        if "host-group" in child:
            if not isinstance(child["host-group"], list):
                child["host-group"] = [child["host-group"]]
            host_group_dict = process_host_group_dict(
                host_group_dict, this_group_name, child["host-group"]
            )
    return host_group_dict


def str_to_bool(val, default=False):
    """Safely replace a True or False string with a boolean"""
    try:
        return bool(strtobool(val))
    except (AttributeError, ValueError):
        return default
