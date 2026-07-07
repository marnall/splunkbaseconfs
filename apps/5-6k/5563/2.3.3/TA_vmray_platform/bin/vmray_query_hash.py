import csv
import gzip
import json
import logging
import os
import re
import sys
import time

# pylint: disable=import-error, wrong-import-position

from splunk.clilib import cli_common as cli
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, make_splunkhome_path(["etc", "apps", "Splunk_SA_CIM", "lib"]))

from cim_actions import ModularAction, ModularActionTimer
from splunklib.client import connect
from vmraylib.rest_api import VMRayRESTAPI

# Retrieve a logging instance from ModularAction
# It is required that this endswith _modalert
LOGGER = ModularAction.setup_logger("vmray_platform_query_hash_modalert")


# Subclass ModularAction for purposes of implementing
# a script specific dowork() method
class VMRayQueryModularAction(ModularAction):
    VALID_HASHTYPES = ["md5", "sha1", "sha256"]

    # This method will initialize VMRayModularAction
    def __init__(self, settings, logger, action_name=None):
        # Call ModularAction.__init__
        super().__init__(settings, logger, action_name)
        # Initialize param.limit
        try:
            self.limit = int(self.configuration.get("limit", 10))
            if self.limit < 1 or self.limit > 100:
                self.limit = 100
        except Exception:  # pylint: disable=broad-except
            self.limit = 1

    def _load_api_key(self):
        match = re.match(r"https?://(.*?):(\d*)", self.settings["server_uri"])
        host = match.group(1)
        port = int(match.group(2))

        service = connect(host=host, port=port, app="TA_vmray_platform",
                          sharing="app", token=self.session_key)
        for secret in service.storage_passwords.list():
            if secret.username == "vmray" and secret.realm == "adaptive-response":
                return secret.clear_password

        return None

    @staticmethod
    def _get_hashes(hash_field, result):
        hash_field_mv = "__mv_" + hash_field

        # MV results are encoded using the following scheme: $value0$,$value1$
        # Dollar signs within a value are represented by a pair of dollar signs ($$)
        # see https://docs.splunk.com/DocumentationStatic/PythonSDK/1.3.0/searchcommands.html
        if hash_field_mv in result and result[hash_field_mv]:
            # this is taken from search_command.py from Splunk SDK
            regex = re.compile(r"\$(?P<item>(?:\$\$|[^$])*)\$(?:;|$)")  # matches a single value in an encoded list
            hashes = [match.replace("$$", "$") for match in regex.findall(result[hash_field_mv])]
        else:
            hashes = [result[hash_field]]

        return [hash.strip() for hash in hashes]

    # This method will handle validation
    def validate(self, result):
        if self.configuration.get("hash_value", "") not in result:
            raise Exception("Parameter hash_value does not exist in result")

        if self.configuration.get("hash_type", "") not in VMRayQueryModularAction.VALID_HASHTYPES:
            raise Exception("Parameter hash_type does not exist is invalid")

        api_key = self._load_api_key()
        if api_key is None or not api_key.strip():
            raise Exception("API Key does not exist or is empty")

        # Hash value check
        hashes = self._get_hashes(self.configuration.get("hash_value"), result)
        if not hashes or any(not hash.isalnum() for hash in hashes):
            raise Exception("Parameter hash_value does not contain a valid hash value")

    # This method will do the actual work itself
    def dowork(self, result):
        analyzer_general = cli.getConfStanza("vmray_platform_app_config", "vmray_platform_general")
        # get parameter value
        verify_ssl = int(analyzer_general["disable_verify"]) != 1

        api_key = self._load_api_key()
        server_ip = analyzer_general["server_ip"]

        # get parameter value
        hashes = self._get_hashes(self.configuration.get("hash_value"), result)
        hash_type = self.configuration.get("hash_type")

        # invoke VMRAy API
        api = VMRayRESTAPI(server_ip, api_key, verify_ssl)
        for value in hashes:
            request_url = "/rest/sample/" + hash_type + "/" + value
            try:
                data = api.call("GET", request_url)
            except Exception as exc:  # pylint: disable=broad-except
                self.message("Failed to query for Hash", status="failure, " + str(exc))
                data = None

            if data:
                for sample in data:
                    self.message("Successfully queried for Hash", status="success")
                    self.addevent(json.dumps(sample), sourcetype="vmray:ar:queryhash")


def main(argv):
    # This is standard chrome for validating that
    # the script is being executed by splunkd accordingly
    if len(argv) < 2 or argv[1] != "--execute":
        print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
    analyzer_general = cli.getConfStanza("vmray_platform_app_config", "vmray_platform_general")
    splunk_index = analyzer_general["index"]
    vmray_server = analyzer_general["server_ip"]

    # The entire execution is wrapped in an outer try/except
    try:
        # Retrieve an instanced of VMRayModularAction and name it modaction
        # pass the payload (sys.stdin) and logging instance
        modaction = VMRayQueryModularAction(sys.stdin.read(), LOGGER, "VMRayQuery")
        LOGGER.info(modaction.settings)
        LOGGER.info(argv)
        splunk_index = analyzer_general["index"]
        # Add a duration message for the "main" component using modaction.start_timer as
        # the start time
        with ModularActionTimer(modaction, "main", modaction.start_timer):
            # Process the result set by opening results_file with gzip
            with gzip.open(modaction.results_file, "rt", encoding="utf-8") as filep:
                # Iterate the result set using a dictionary reader
                # We also use enumerate which provides "num" which
                # can be used as the result ID (rid)
                for num, result in enumerate(csv.DictReader(filep)):
                    # results limiting
                    if num >= modaction.limit:
                        break
                    # Set rid to row # (0->n) if unset
                    result.setdefault("rid", str(num))
                    # Update the ModularAction instance
                    # with the current result.  This sets
                    # orig_sid/rid/orig_rid accordingly.
                    modaction.update(result)
                    # Generate an invocation message for each result.
                    # Tells splunkd that we are about to perform the action
                    # on said r
                    modaction.invoke()
                    # Validate the invocation
                    modaction.validate(result)
                    # This is where we do the actual work.  In this case
                    # we are calling out to an external API and creating
                    # events based on the information returned
                    modaction.dowork(result)
                    # rate limiting
                    time.sleep(1.6)

            # Once we're done iterating the result set and making
            # the appropriate API calls we will write out the events
            modaction.writeevents(index=splunk_index, host=vmray_server, source="vmray_platform_actions")

    # This is standard chrome for outer exception handling
    except Exception as exc:  # pylint: disable=broad-except
        # adding additional logging since adhoc search invocations do not write to stderr
        try:
            modaction.message(exc, status="failure", level=logging.CRITICAL)
        except Exception:  # pylint: disable=broad-except
            LOGGER.critical(exc)
        print(f"ERROR: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv)
