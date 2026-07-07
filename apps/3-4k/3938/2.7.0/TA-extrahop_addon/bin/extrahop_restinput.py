# encoding = utf-8
"""Provides REST endpoint for 'extrahop' data input creation.

Used by ExtraHop App for Splunk's setup page.
"""
# This file is part of an ExtraHop Supported Integration. Make NO MODIFICATIONS below this line
import logging
import logging.handlers
import os

import splunk.admin as admin
import splunk.entity as entity


def log_function_invocation(fx):
    """Log function invocation."""
    def wrapper(self, *args, **kwargs):
        """Wrapper method."""
        LOGGER.debug("Entering: " + fx.__name__)
        r = fx(self, *args, **kwargs)
        LOGGER.debug("Exiting: " + fx.__name__)
        return r
    return wrapper


def setup_logging(level, name, filename):
    """Method to setup logger object."""
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)

    log_file_path = os.path.join(os.environ["SPLUNK_HOME"], 'var', 'log', 'splunk', filename)
    file_handler = logging.handlers.RotatingFileHandler(log_file_path, maxBytes=2500000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s ' + name + ' - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


LOGGER = setup_logging(logging.INFO, "RestHandler", "ta_extrahop_resthandler.log")


class ExtrahopEndpoint(admin.MConfigHandler):
    """REST API handler for Splunk internal to create 'extrahop' data input."""

    # See https://gist.github.com/LukeMurphey/5390638
    # for a template for how this class is written
    # Also https://answers.splunk.com/answering/366858/view.html
    # for how it works w/ ExtraHop App for Splunk setup page
    CONF_FILE = "inputs"

    REQUIRED_ARGS = [
        "interval",
        "index",
        "global_account",
        "object_type",
        "object_id",
        "metric_category",
        "metric_name",
        "stanzaname"
    ]
    OPTIONAL_ARGS = [
        "cyclesize",
    ]
    UNSAVED_ARGS = [
        "stanzaname",
    ]

    @log_function_invocation
    def setup(self):
        """Setup method."""
        if self.requestedAction == admin.ACTION_EDIT or self.requestedAction == admin.ACTION_CREATE:
            for arg in self.REQUIRED_ARGS:
                self.supportedArgs.addReqArg(arg)
            for arg in self.OPTIONAL_ARGS:
                self.supportedArgs.addOptArg(arg)

    @log_function_invocation
    def handleList(self, confInfo):
        """Handle list method."""
        conf_dict = self.readConf(self.CONF_FILE)

        if conf_dict is not None:
            for stanza, settings in conf_dict.items():
                for key, val in settings.items():
                    confInfo[stanza].append(key, val)

    @log_function_invocation
    def handleReload(self, confInfo):
        """Handle reload method."""
        entity.refreshEntities(
            f"properties/{self.CONF_FILE}", sessionKey=self.getSessionKey()
        )

    @log_function_invocation
    def handleEdit(self, confInfo):
        """Handle edit method."""
        args = self.callerArgs
        data = self.callerArgs.data
        stanzaname = "extrahop://" + data["stanzaname"][0]

        LOGGER.debug(f"{stanzaname} data:\n{data}")

        # Apply new settings
        new_settings = {}
        for key in data:
            LOGGER.debug(f"Key: {key}, arg: {args[key][0]}")
            new_settings[key] = args[key][0]

        cleaned_settings = self.checkConf(new_settings, stanzaname, confInfo)
        self.writeConf(self.CONF_FILE, stanzaname, cleaned_settings)

    @classmethod
    def checkConf(cls, settings, stanza=None, conf_info=None):
        """Check conf method."""
        # stripped-down from https://gist.github.com/LukeMurphey/5390638
        for key, val in settings.items():
            if stanza is not None and conf_info is not None:
                if key == 'eai:acl':
                    conf_info[stanza].setMetadata(key, val)

        required_fields = cls.REQUIRED_ARGS[:]
        for key, val in settings.items():
            try:
                required_fields.remove(key)
            except ValueError:
                pass  # field probably not required, ignore
        if len(required_fields) > 0:
            raise admin.ArgValidationException(
                f"The following fields must be defined in the configuration but were not: {required_fields}"
            )

        for field in cls.UNSAVED_ARGS:
            if field in settings:
                del settings[field]

        return settings


admin.init(ExtrahopEndpoint, admin.CONTEXT_NONE)
