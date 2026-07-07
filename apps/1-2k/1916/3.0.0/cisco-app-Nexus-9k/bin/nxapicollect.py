"""Utility methods to collect the data from Cisco Servers."""

# Copyright (C) 2024 Cisco Systems Inc.
# All rights reserved

import json
import os
import platform
import subprocess
import sys
import time
import xml.sax.saxutils as xss

import logger_manager
import splunk.entity as entity
import splunk.Intersplunk

logger = logger_manager.get_logger("collect")

APP_NAME = __file__.split(os.sep)[-3]

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

try:
    from splunklib.searchcommands import (
        Configuration,
        GeneratingCommand,
        Option,
        dispatch,
    )
except Exception as e:
    logger.error("Error importing the required module: %s", str(e))
    raise

config = configparser.ConfigParser()
detect_platform = platform.system().lower()
if detect_platform == "linux":
    nexus_app_path = sys.path[0]
    python_path = nexus_app_path + "/../../../../bin/"
else:
    nexus_app_path = sys.path[0]
    python_path = nexus_app_path + "\\..\\..\\..\\..\\bin"

os.chdir(python_path)

python_path = (
    os.path.join(os.getcwd(), "python3")
    if sys.version_info > (3, 0)
    else os.path.join(os.getcwd(), "python")
)


@Configuration(local=True, retainsevents=True)
class NXAPICommand(GeneratingCommand):
    """Parse the user provided command and collect the data."""

    global file1
    command = Option(require=True)
    device = Option(require=False)
    username = Option(require=False)
    password = Option(require=False)
    device_credentials = dict()
    results, dummy, settings = splunk.Intersplunk.getOrganizedResults()
    sessionKey = settings.get("sessionKey")

    def _getCredentials(self):
        """Fetch credentials from endpoint."""
        try:
            # list all credentials
            entities = entity.getEntities(
                ["admin", "passwords"],
                namespace=APP_NAME,
                owner="nobody",
                sessionKey=self.sessionKey,
            )
        except Exception as e:
            logger.error(
                "Nexus Error: Could not get %s credentials from splunk. Error: %s"
                % (APP_NAME, str(e))
            )

        # return first set of credentials
        for i, c in list(entities.items()):
            if str(c["eai:acl"]["app"]) == APP_NAME:
                device_splitted_values = i.split(":")[0].split(",")
                device = device_splitted_values[0]
                try:
                    port = str(int(device_splitted_values[1]))
                except Exception:
                    port = None
                if port:
                    device = ":".join([device, port])
                username = xss.unescape(c["username"])
                password = c["clear_password"]
                credential = []
                credential = [username, password]
                self.device_credentials[device] = list(credential)

        self.device_credentials = json.dumps(self.device_credentials)

    def generate(self):
        """Perform the data collection for the executed command."""
        file = os.path.join(nexus_app_path, "collect.py")
        self._getCredentials()
        if self.username or self.password:
            proc = subprocess.Popen(
                [
                    python_path,
                    file,
                    self.device_credentials,
                    self.sessionKey,
                    "-u",
                    self.username,
                    "-p",
                    self.password,
                    "-cmd",
                    self.command,
                    "-device",
                    self.device,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        elif self.device:
            proc = subprocess.Popen(
                [
                    python_path,
                    file,
                    self.device_credentials,
                    self.sessionKey,
                    "-cmd",
                    self.command,
                    "-device",
                    self.device,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        elif self.command:
            proc = subprocess.Popen(
                [
                    python_path,
                    file,
                    self.device_credentials,
                    self.sessionKey,
                    "-cmd",
                    self.command,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

        outputlines = [x for x in (line.strip() for line in proc.stdout) if len(x) > 0]
        for d in outputlines:
            try:
                d = d.decode()
                json.loads(d)
                yield {"_time": time.time(), "_raw": d}
            except Exception as e:
                logger.error("Exception raised while writing the data. Error: %s.", e)
                raise Exception(d)


dispatch(NXAPICommand, sys.argv, "", sys.stdout, __name__)
