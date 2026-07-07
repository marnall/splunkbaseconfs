"""
This module hanles configuration related stuff
"""

import logging

_LOGGER = logging.getLogger("data_loader")


def setup_logging(log_name, level_name="INFO"):
    """
    @log_name: which logger
    @level_name: log level, a string
    """

    import splunk.appserver.mrsparkle.lib.util as splunk_lib_util

    level_name = level_name.upper() if level_name else "INFO"
    loglevel_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARN,
        "ERROR": logging.ERROR,
    }

    if level_name in loglevel_map:
        loglevel = loglevel_map[level_name]
    else:
        loglevel = logging.INFO

    logfile = splunk_lib_util.make_splunkhome_path(["var", "log", "splunk",
                                                    "%s.log" % log_name])
    logger = logging.getLogger(log_name)
    logger.propagate = False
    logger.setLevel(loglevel)

    handler_exists = any([True for h in logger.handlers
                          if h.baseFilename == logfile])
    if not handler_exists:
        file_handler = logging.handlers.RotatingFileHandler(logfile, mode="a",
                                                            maxBytes=104857600,
                                                            backupCount=5)
        fmt_str = "%(asctime)s %(levelname)s %(thread)d - %(message)s"
        formatter = logging.Formatter(fmt_str)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def parse_modinput_configs(config_str):
    """
    @config_str: modinput XML configuration feed by splunkd
    """

    import xml.dom.minidom as xdm

    meta_configs = {
        "server_host": None,
        "server_uri": None,
        "session_key": None,
        "checkpoint_dir": None,
    }
    root = xdm.parseString(config_str).documentElement
    for tag in meta_configs.iterkeys():
        nodes = root.getElementsByTagName(tag)
        if not nodes:
            _LOGGER.error("Invalid config, missing %s section", tag)
            raise Exception("Invalid config, missing %s section", tag)

        if (nodes[0].firstChild and
                nodes[0].firstChild.nodeType == nodes[0].TEXT_NODE):
            meta_configs[tag] = nodes[0].firstChild.data
        else:
            _LOGGER.error("Invalid config, expect text ndoe")
            raise Exception("Invalid config, expect text ndoe")

    confs = root.getElementsByTagName("configuration")
    if not confs:
        _LOGGER.error("Invalid config, missing configuration section")
        raise Exception("Invalid config, missing configuration section")

    configs = []
    stanzas = confs[0].getElementsByTagName("stanza")
    for stanza in stanzas:
        config = {}
        stanza_name = stanza.getAttribute("name")
        if not stanza_name:
            _LOGGER.error("Invalid config, missing name")
            raise Exception("Invalid config, missing name")

        config["name"] = stanza_name
        params = stanza.getElementsByTagName("param")
        for param in params:
            name = param.getAttribute("name")
            if (name and param.firstChild and
                    param.firstChild.nodeType == param.firstChild.TEXT_NODE):
                config[name] = param.firstChild.data
        configs.append(config)
    return meta_configs, configs
