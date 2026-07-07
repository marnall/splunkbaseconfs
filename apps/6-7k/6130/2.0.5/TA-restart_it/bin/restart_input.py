#!/usr/bin/env python
"""restart_input.py — implements the `restartinput` custom search command."""

import logging
import logging.handlers
import os
import sys
import time

# Make bundled libs importable. Resolve relative to this file so the app
# directory can be renamed without breaking imports.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import splunk  # noqa: E402 — import must follow the sys.path.insert above
from splunklib import client  # noqa: E402
from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    GeneratingCommand,
    Option,
    dispatch,
    validators,
)

SPLUNK_HOME = os.environ["SPLUNK_HOME"]
MODULAR_INPUT_TYPES = ("modular-input", "modular-inputs")


def setup_logging():
    """Configure the add-on logger and return it."""
    logger = logging.getLogger("splunk.restart_it")
    log_format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, "var", "log", "splunk", "restart_it.log"),
        mode="a",
    )
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    splunk.setupSplunkLogger(
        logger,
        os.path.join(SPLUNK_HOME, "etc", "log.cfg"),
        os.path.join(SPLUNK_HOME, "etc", "log-local.cfg"),
        "python",
    )
    return logger


@Configuration()
class RestartInputCommand(GeneratingCommand):
    """Restart a Splunk input or scripted input by disabling then re-enabling it.

    ##Syntax
        For a standard or modular input:
            | restartinput app=<app> type=<type> input=<input>
        For a scripted input:
            | restartinput app=<app> type=script script=<script_name>

    ##Description
        The :code:`restartinput` command uses the REST API to disable and
        then re-enable an :code:`input` or :code:`script` in :code:`app`.
        Combined with Splunk's scheduler, this lets you automatically
        restart an input on a cadence without any command-line access.

    ##Example
        | restartinput app=TA-Your_App type=script script=myScript.sh
    """

    app = Option(require=True, validate=validators.Fieldname())
    type = Option(require=True)
    input = Option(require=False)
    script = Option(require=False)

    logger = setup_logging()

    def _resolve_input(self, service):
        """Look up the Input entity to restart via the Splunk SDK."""
        if self.type == "script":
            if not self.script:
                raise ValueError("script=<name> is required when type=script")
            name = os.path.join(SPLUNK_HOME, "etc", "apps", self.app, "bin", self.script)
            return service.inputs[name, "script"]

        if not self.input:
            raise ValueError("input=<name> is required for non-script types")

        # For modular inputs the original add-on looked up by name without a
        # kind filter, since the stanza name is unique across the collection.
        if self.type in MODULAR_INPUT_TYPES:
            return service.inputs[self.input]

        return service.inputs[self.input, self.type]

    def generate(self):
        label = self.script or self.input or "<missing>"
        self.logger.info("Restarting %s (type=%s) in %s", label, self.type, self.app)

        service = client.connect(
            token=self.metadata.searchinfo.session_key,
            app=self.app,
            owner="nobody",
        )

        try:
            target = self._resolve_input(service)
            target.disable()
            self.logger.info({"message": "Disabled.", "_time": time.time(), "name": target.name})
            target.enable()
            self.logger.info({"message": "Re-enabled.", "_time": time.time(), "name": target.name})
            yield {
                "_time": time.time(),
                "event_no": 0,
                "_raw": f"Restarted {target.name} (type={self.type}) in {self.app}",
            }
        except Exception as e:
            msg = f"Error restarting {self.type} '{label}' in {self.app}: {e}"
            self.logger.error({"_time": time.time(), "message": msg})
            yield {"_time": time.time(), "event_no": 0, "_raw": msg}


dispatch(RestartInputCommand, sys.argv, sys.stdin, sys.stdout, __name__)
