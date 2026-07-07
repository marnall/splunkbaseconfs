#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Datamodel Fields"""

# standard library
import os
import sys
import traceback

# must be imported before packages in bin/lib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
import splunklib.results as results
from base_generating_command import BaseGeneratingCommand
from splunklib.searchcommands import dispatch


class TAPreflightCommand(BaseGeneratingCommand):
    """Command to generate Datamodel field.

    This command create a KV Store with all Datamodel fields to be used in the
    Datamodel search configuration page to increase the performance of the dropdown.
    The command is run on as a saved search on a schedule.

    Usage:
    | tcdmu

    e.g.,
    | tcdmu
    """

    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for Collection KV Store Stats."""
        yield from self.check_indexes()
        yield from self.check_settings()
        yield from self.check_data_input()

    def check_data_input(self):
        """Validate tc_download_iocs modulular input exists."""
        try:
            spl = "| rest services/data/modular-inputs/tc_download_iocs splunk_server=local"
            kwargs = {"output_mode": "json"}
            job = self.service.jobs.oneshot(spl, **kwargs)
            reader = results.JSONResultsReader(job)

            result = [r for r in reader]
            if not result:
                yield {
                    "order": 5,
                    "title": "Check ThreatConnect Indicators Modular Input exits.",
                    "status": "Failure",
                    "message": "ThreatConnect Indicators Modular Input does not exist.",
                }
                return
            result = result[0]
            if not isinstance(result, dict):
                yield {
                    "order": 5,
                    "title": "Check ThreatConnect Indicators Modular Input exits.",
                    "status": "Failure",
                    "message": "ThreatConnect Indicators Modular Input does not exist.",
                }
                return

            if result.get("title") != "tc_download_iocs":
                yield {
                    "order": 5,
                    "title": "Check ThreatConnect Indicators Modular Input exits.",
                    "status": "Failure",
                    "message": "ThreatConnect Indicators Modular Input does not exist.",
                }
                return

            yield {
                "order": 5,
                "title": "Check ThreatConnect Indicators Modular Input exits.",
                "status": "Success",
                "message": None,
            }
        except Exception as e:
            traceback.print_exc()
            yield {
                "order": 5,
                "title": "Check ThreatConnect Indicators Modular Input exits.",
                "status": "Failure",
                "message": f"Unable to retrieve inputs: {e}",
            }
            return

    def check_settings(self):
        """Validate settings are set and valid."""
        settings = None
        try:
            settings = self.settings
            # do this to create the session and catch any errors
            self.configure_session()  # pylint: disable=pointless-statement
        except (Exception, KeyError) as e:
            traceback.print_exc()
            yield {
                "order": 3,
                "title": "Check settings exist.",
                "status": "Failure",
                "message": f"No settings found.  Go to Settings to configure. {e}",
            }
            return

        # validate settings have been given
        if not settings:
            yield {
                "order": 3,
                "title": "Check settings exist.",
                "status": "Failure",
                "message": "No settings found.  Go to Configure > Settings to configure.",
            }
            return
        else:
            yield {
                "order": 3,
                "title": "Check settings exist.",
                "status": "Success",
                "message": None,
            }

        # validate API connectivity
        try:
            self.configure_session()
            r = self.session.get("/v2/owners")
            if not r.ok:
                response = None
                try:
                    response = r.text
                except Exception:
                    pass

                yield {
                    "order": 4,
                    "title": "Check ThreatConnect API connectivity.",
                    "status": "Failure",
                    "message": f"Unable to connect to ThreatConnect API: {r.status_code} - {response}",
                }
            else:
                yield {
                    "order": 4,
                    "title": "Check ThreatConnect API connectivity.",
                    "status": "Success",
                    "message": None,
                }
        except Exception as e:
            traceback.print_exc()
            yield {
                "order": 4,
                "title": "Check ThreatConnect API connectivity.",
                "status": "Failure",
                "message": f"Unable to connect to ThreatConnect API: {e}",
            }

        # validate gateway service is available
        try:
            r = self.session.get(
                self.service_path, params={"splunk_id": self.settings.get("serviceId")}
            )
            if not r.ok:
                if r.status_code == 400:
                    yield {
                        "order": 5,
                        "title": "Check gateway service is available.",
                        "status": "Failure",
                        "message": 'Gateway service is running in multitennant mode.  Validate that "Splunk Instance Name" is set on the Settings page and that its value matches the "Splunk Instance Name" value in the Settings page of ThreatConnect App for Splunk.',
                    }
                else:
                    yield {
                        "order": 5,
                        "title": "Check gateway service is available.",
                        "status": "Failure",
                        "message": "Gateway service is not available.  Validate service is created and running in ThreatConnect.",
                    }
            else:
                if r.json() == []:
                    yield {
                        "order": 5,
                        "title": "Check gateway service is available.",
                        "status": "Warning",
                        "message": 'Gateway service is available but no data has been synced.  Validate that at least one Indicator Collection has been defined in ThreatConnect App For Splunk.  Validate that the "Splunk Instance Name" is set on the Settings page and that its value matches the "Splunk Instance Name" value in the Settings page of ThreatConnect App for Splunk.  If the "Splunk Instance Name" is correct, validate that the "TC-Gateway-Push" saved search in from ThreatConnect App For Splunk has successfully run and is enabled, and that the "TC-ModuleImportSync" saved search from TA ThreatConnect Threat Intel has successfully run and is enabled.',
                    }

                else:
                    yield {
                        "order": 5,
                        "title": "Check gateway service is available.",
                        "status": "Success",
                        "message": None,
                    }
        except Exception as e:
            traceback.print_exc()
            yield {
                "order": 5,
                "title": "Check gateway service is available.",
                "status": "Failure",
                "message": "Gateway service is not available.  Validate service is created and running in ThreatConnect.",
            }

    def check_indexes(self):
        """Validate that all indexes are available."""
        check_indexes = ["tc_indicator_data"]
        try:
            spl = "| rest /services/data/indexes | fields title "
            kwargs = {"output_mode": "json"}
            job = self.service.jobs.oneshot(spl, **kwargs)
            reader = results.JSONResultsReader(job)

            # retrieve results from Splunk
            indexes = [r.get("title") for r in reader]
            for index in check_indexes:
                if index not in indexes:
                    yield {
                        "order": 1,
                        "title": "Check indexes exists.",
                        "status": "Warning",
                        "message": (
                            f"Could not validate that {index}"
                            " exist, please manually verify."
                        ),
                    }
                else:
                    yield {
                        "order": 1,
                        "title": f"Check index {index} exists.",
                        "status": "Success",
                        "message": None,
                    }
        except Exception:
            for index in check_indexes:
                yield {
                    "order": 1,
                    "title": "Check indexes exists.",
                    "status": "Warning",
                    "message": (
                        f"Could not validate that {index}"
                        " exist, please manually verify."
                    ),
                }

    @staticmethod
    def is_base(parent_name):
        """Return True is parent is BaseEvent."""
        return parent_name == "BaseEvent"

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return False

    @property
    def service_path(self):
        path = f"""{self.settings.get("servicePath").rstrip("/")}/sync"""
        return path


if __name__ == "__main__":
    dispatch(TAPreflightCommand, sys.argv, sys.stdin, sys.stdout, __name__)
