#!/usr/bin/python

"""
This is the main entry point for OKTA TA
"""
import sys
import os.path as op
sys.path.insert(0, op.join(op.dirname(op.abspath(__file__)), "splunktalib"))

import logging
from datetime import datetime, timedelta
import traceback
import okta_data_collector as odc
import okta_config
import re

from splunktalib.common import log
from splunktalib.common import util
_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

MAX = 5000
INPUT_NAME_PATTERN  = r"^[0-9a-zA-Z][0-9a-zA-Z_-]*$"

util.remove_http_proxy_env_vars()

def do_scheme():
    """
    Feed splunkd the TA's scheme
    """

    print """
    <scheme>
    <title>Splunk Add-on for Okta</title>
    <description>Splunk Add-on for Okta</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>false</use_single_instance>
    <endpoint>
      <args>
        <arg name="metrics">
        <required_on_create>1</required_on_create>
        <required_on_edit>1</required_on_edit>
        </arg>
        <arg name="name">
        <required_on_create>1</required_on_create>
        <required_on_edit>1</required_on_edit>
        </arg>
        <arg name="start_date">
           <required_on_create>0</required_on_create>
           <required_on_edit>0</required_on_edit>
        </arg>
        <arg name="end_date">
           <required_on_create>0</required_on_create>
           <required_on_edit>0</required_on_edit>
        </arg>
        <arg name="url">
           <required_on_create>1</required_on_create>
           <required_on_edit>1</required_on_edit>
        </arg>
        <arg name="token">
           <required_on_create>1</required_on_create>
           <required_on_edit>1</required_on_edit>
        </arg>
        <arg name="page_size">
           <required_on_create>0</required_on_create>
           <required_on_edit>0</required_on_edit>
        </arg>
        <arg name="batch_size">
           <required_on_create>0</required_on_create>
           <required_on_edit>0</required_on_edit>
        </arg>
      </args>
    </endpoint>
    </scheme>
    """

def parse_modinput_configs(config_str):
    """
    @config_str: modinput XML configuration feed by splunkd
    """

    import xml.dom.minidom as xdm

    config = {
        "server_host": None,
        "server_uri": None,
        "session_key": None,
        "checkpoint_dir": None,
    }
    root = xdm.parseString(config_str).documentElement
    for tag in config.iterkeys():
        nodes = root.getElementsByTagName(tag)
        if not nodes:
            _LOGGER.error("Invalid config, missing %s section", tag)
            raise Exception("Invalid config, missing %s section", tag)

        if (nodes[0].firstChild and
                nodes[0].firstChild.nodeType == nodes[0].TEXT_NODE):
            config[tag] = nodes[0].firstChild.data
        else:
            _LOGGER.error("Invalid config, expect text ndoe")
            raise Exception("Invalid config, expect text ndoe")

    confs = root.getElementsByTagName("configuration")

    if confs:
        stanzas = confs[0].getElementsByTagName("stanza")
        stanza = stanzas[0]
    else:
        items = root.getElementsByTagName("item")
        stanza = items[0]

    if not stanza:
        _LOGGER.error("Invalid config, missing <item> or <stanza> section")
        raise Exception("Invalid config, missing <item> or <stanza> section")

    stanza_name = stanza.getAttribute("name")
    if not stanza_name:
        _LOGGER.error("Invalid config, missing name")
        raise Exception("Invalid config, missing name")

    if not re.match(INPUT_NAME_PATTERN, stanza_name.replace("okta://", "").strip()):
        log_and_raise_value_exception("Name format is incorrect. The entered Name is {}".format(stanza_name))

    config["name"] = stanza_name
    params = stanza.getElementsByTagName("param")
    for param in params:
        name = param.getAttribute("name")
        if (name and param.firstChild and
                param.firstChild.nodeType == param.firstChild.TEXT_NODE):
            config[name] = param.firstChild.data
    return config


def get_okta_modinput_configs(modinputs):
    try:
        input_config = parse_modinput_configs(modinputs)

        config = okta_config.OktaConfig(input_config.get("server_uri"),
                    input_config.get("session_key"), input_config.get("checkpoint_dir"))

        config.remove_expired_credentials()
        config.remove_expired_ckpt()

        okta_conf = config.get_okta_conf()
        config.update_okta_conf(okta_conf)
        # set log level
        loglevel = okta_conf.get("loglevel", "INFO")
        _LOGGER.info("Set loglevel to %s", loglevel)
        log.Logs().set_level(loglevel)

        # this is a multi-instance TA
        input_name = input_config.get("name").replace("okta://", "").strip()
        input_conf = config.get_data_input(input_name)
        input_metric = input_conf.get("metrics", "event")
        input_modified = False
        if input_metric == "event" and not input_conf.get("start_date", ""):
            input_conf["start_date"] = (datetime.utcnow()-timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            input_modified = True
        if input_metric in ('user', 'group', 'application') and int(input_conf.get('interval'))<21600:
            input_conf['interval'] = '21600'
            input_modified = True

        okta_conf.update(input_conf)
        okta_conf["checkpoint_dir"] = input_config.get("checkpoint_dir")

        if input_conf.get("metrics") != "refresh_token":
            if input_conf.get('raw_token', '') != config.encrypted_display_str:
                config.encrypt_data_input(input_name, input_conf)
                input_modified = True

        if input_modified:
            config.update_data_input(input_name, input_conf)

        return okta_conf
    except Exception as ex:
        _LOGGER.error("Failed to get config for okta TA: %s", ex.message)
        _LOGGER.error(traceback.format_exc())
        raise

def log_and_raise_value_exception(msg):
    _LOGGER.error(msg)
    raise ValueError(msg)

def run():
    """
    Main loop. Run this TA for ever
    """
    _LOGGER.info("call the run")
    modinputs = sys.stdin.read(MAX)
    okta_conf = get_okta_modinput_configs(modinputs)
    metric = okta_conf.get("metrics", "event")
    if metric == "event":
        collector = odc.OktaEventCollector(okta_conf)
    elif metric == "user":
        collector = odc.OktaUserCollector(okta_conf)
    elif metric == "group":
        collector = odc.OktaGroupCollector(okta_conf)
    elif metric == "application":
        collector = odc.OktaAppCollector(okta_conf)
    elif metric == "refresh_token":
        collector = odc.OktaRefreshToken(okta_conf)
    else:
        return
    collector.collect_data(metric)

def validate_config():
    """
    Validate inputs.conf
    """

    modinputs = sys.stdin.read(MAX)
    if not modinputs:
        return 0

    input_config = parse_modinput_configs(modinputs)


    name = input_config.get('name','').strip()
    if not name or not re.match(INPUT_NAME_PATTERN, name.replace("okta://", "").strip()):
        log_and_raise_value_exception("Name format is incorrect. The entered Name is {}".format(name))

    token = input_config.get('token', '').strip()
    if not token:
        log_and_raise_value_exception("Error in data input [{}]. Token is required and it can not be "
                                      "********".format(name))

    try:
        limit = int(input_config.get("page_size", '1000').strip())
        assert limit > 0 and limit <= 1000
    except:
        log_and_raise_value_exception("Page size should be an integer between 0 and 1000")

    try:
        ret = int(input_config.get("batch_size", '10000').strip())
        assert ret >= limit
    except:
        log_and_raise_value_exception("Batch size should be an integer greater than or equal to page size")

    try:
        ret = int(input_config.get("interval", '3600').strip())
        assert ret > 0
        metric = input_config.get("metrics",'event')
        if metric in ('user', 'group', 'application') and ret < 21600:
            _LOGGER.info('The interval {0} for the metric {1} is too small, we will use 21600.'.format(ret, metric))

    except:
        log_and_raise_value_exception("interval should be an integer")

    try:
        sdate = input_config.get("start_date", "").strip()
        if sdate:
            datetime.strptime(sdate, '%Y-%m-%dT%H:%M:%S.%fZ')
    except:
        log_and_raise_value_exception("start_date format is incorrect.")

    try:
        edate = input_config.get("end_date", "").strip()
        if edate:
            datetime.strptime(edate, '%Y-%m-%dT%H:%M:%S.%fZ')
    except:
        log_and_raise_value_exception("end_date format is incorrect.")

    url = input_config.get("url","").strip()
    if not url or not re.match(r"^https?\://[\w\-\./%\&\?]+(?::\d{1,5})?$", url):
        log_and_raise_value_exception("url format is incorrect.")

    _LOGGER.info("Finished the validation. No errors.")

    return 0

def usage():
    """
    Print usage of this binary
    """

    hlp = "%s --scheme|--validate-arguments|-h"
    print >> sys.stderr, hlp % sys.argv[0]
    sys.exit(1)

def main():
    """
    Main entry point
    """
    args = sys.argv
    if len(args) > 1:
        if args[1] == "--scheme":
            do_scheme()
        elif args[1] == "--validate-arguments":
            sys.exit(validate_config())
        elif args[1] in ("-h", "--h", "--help"):
            usage()
        else:
            usage()
    else:
        _LOGGER.info("Start OKTA TA")
        run()
        _LOGGER.info("End OKTA TA")
    sys.exit(0)

if __name__ == "__main__":
    main()
