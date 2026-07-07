#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import hashlib
import pymd5

from snow_consts import LOGFILE_PREFIX
import snow_incident_base as sib  # noqa: E402


class ModSnowIncident(sib.SnowIncidentBase):
    def __init__(self, payload, invocation_id, log_filename=""):
        self._payload = payload
        self.log_filename = (
            log_filename if log_filename else f"{LOGFILE_PREFIX}_snow_incident"
        )
        self._config = payload["configuration"]
        self.account = payload["configuration"]["account"]
        self._config["splunk_url"] = (
            payload["configuration"].get("splunk_url") or payload["results_link"]
        )
        # FIXME Should refactor base class
        self._config["ciIdentifier"] = self._config.get("configuration_item", "")
        self.invocation_id = invocation_id
        super(ModSnowIncident, self).__init__()

    def _get_session_key(self):
        return self._payload["session_key"]

    def _get_correlation_id(self, event):
        unique_name = "/".join(
            (self._payload["search_name"], self._payload["owner"], self._payload["app"])
        )
        # semgrep ignore reason: this is used to generate identifier for snow incident
        # and should not cause security issue but
        # considered as a bug already reported as ADDON-36125
        return self.md5(  # nosemgrep: fips-python-detect-crypto, splunk.insecure-hash-algorithm-md5
            unique_name
        ).hexdigest()

    def md5(self, string_to_encode):
        try:
            return hashlib.new(
                name="md5", data=string_to_encode.encode(), usedforsecurity=False
            )
        except ValueError:
            # Only happens on python less than 39 and FIPS enabled
            return pymd5.md5(string_to_encode.encode())

    def _get_events(self):
        return (self._config,)

    def _get_log_file(self):
        """Return the log filename"""
        return self.log_filename

    def _process_results(self):
        processed_results = []
        while not self.results.empty():
            content = self.results.get(timeout=5)
            resp = self._get_resp_record(content)
            if resp:
                processed_results.append(resp)
            else:
                self.fail_count += 1
        return processed_results


def process_event(helper, *args, **kwargs):

    # Initialize the class and execute the code for alert action.
    helper.log_info("Alert action snow_incident started.")
    handler = ModSnowIncident(
        helper.settings, helper.invocation_id, helper.log_filename
    )
    handler.handle()

    # TODO: Implement your alert action logic here
    return 0
