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

LOGGER = ModularAction.setup_logger("vmray_platform_submit_url_modalert")


# Subclass ModularAction for purposes of implementing
# a script specific dowork() method
class VMRayQueryModularAction(ModularAction):
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

    # This method will handle validation
    def validate(self, result):
        if self.configuration.get("url_value", "") not in result:
            raise Exception("Parameter url_value does not exist in result")

        # Basic check
        api_key = self._load_api_key()
        if api_key is None or not api_key.strip():
            raise Exception("API Key does not exist in conf or is empty")

    # This method will do the actual work itself
    def dowork(self, result):
        analyzer_general = cli.getConfStanza("vmray_platform_app_config", "vmray_platform_general")
        # get parameter value
        verify_ssl = int(analyzer_general["disable_verify"]) != 1

        url_field = self.configuration.get("url_value")
        url_field_mv = "__mv_" + url_field

        # MV results are encoded using the following scheme: $value0$,$value1$
        # Dollar signs within a value are represented by a pair of dollar signs ($$)
        # see https://docs.splunk.com/DocumentationStatic/PythonSDK/1.3.0/searchcommands.html
        if url_field_mv in result and result[url_field_mv]:
            # this is taken from search_command.py from Splunk SDK
            def decode_list(value):
                regex = re.compile(r"\$(?P<item>(?:\$\$|[^$])*)\$(?:;|$)")  # matches a single value in an encoded list
                return [match.replace("$$", "$") for match in regex.findall(value)]

            urls = decode_list(result[url_field_mv])
        else:
            urls = [result[url_field]]
        api_key = self._load_api_key()
        server_ip = analyzer_general["server_ip"]
        max_jobs = analyzer_general.get("max_jobs")

        # create VMRay REST API object
        api = VMRayRESTAPI(server_ip, api_key, verify_ssl)

        for url in urls:
            # add params
            params = {
                "sample_url": url,
                "tags": "Splunk,AdaptiveResponse",
            }

            if max_jobs:
                params["max_jobs"] = max_jobs

            try:
                data = api.call("POST", "/rest/sample/submit", params=params)
                sample = data["samples"][0]  # We expect exactly one sample to be returned
                self.addevent(json.dumps(sample), sourcetype="vmray:ar:submiturl")
                self.message("Submit URL was successful", status="success")
            except Exception as exc:
                self.message("API request Failed", status=f"failure: {exc}")
                raise Exception("API Request Failed") from exc


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
        # Retrieve an instance of VMRayQueryModularAction and name it modaction
        # pass the payload (sys.stdin) and logging instance
        modaction = VMRayQueryModularAction(sys.stdin.read(), LOGGER, "VMRaySubmitURL")
        LOGGER.debug(modaction.settings)
        splunk_index = analyzer_general["index"]

        # Add a duration message for the "main" component using modaction.start_timer as
        # the start time
        with ModularActionTimer(modaction, "main", modaction.start_timer):
            # Process the result set by opening results_file with gzip
            with gzip.open(modaction.results_file, "rt", encoding="utf-8") as fileh:
                # Iterate the result set using a dictionary reader
                # We also use enumerate which provides "num" which
                # can be used as the result ID (rid)
                for num, result in enumerate(csv.DictReader(fileh)):
                    # results limiting
                    if num >= modaction.limit:
                        break
                    # Set rid to row # (0->n) if unset
                    result.setdefault("rid", str(num))
                    # Update the ModularAction instance
                    # with the current result.  This sets
                    # orig_sid/rid/orig_rid accordingly.
                    #modaction.message(result)
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
