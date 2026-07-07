"""Module containing Alert action for submitting an URL to Splunk Attack Analyzer"""

import sys

import import_declare_test  # noqa: F401

from splunktaucclib.alert_actions_base import ModularAlertBase
from saa_client import get_configured_client
from saa_exceptions import SAAAlertActionException
import logging
import time
import splunklib.client as client
from splunklib.results import JSONResultsReader, Message

from saa_utils import dict_to_markdown_table, Resource, ResourceTree
from saa_consts import NOTABLE_QUERY


class SubmitUrlAlert(ModularAlertBase):
    """Alert action for submitting an URL to Splunk Attack Analyzer"""

    def validate_params(self):
        """Validate provided arguments"""
        if not self.get_param("account"):
            self.log_error("account is a mandatory parameter, but its value is None.")
            return False
        return True

    def build_http_connection(self, config, timeout=120, disable_ssl_validation=False):
        """
        Needs to be implemented since its abstract on ModularAlertBase but
        is unused in this code so we simply do a no-op
        """

    def is_adhoc_notable(self, events):
        """
        Detect whether the action is executed ad-hoc in the context of an ES notable
        """

        if len(events) != 1:
            return False

        the_event = events[0]
        is_notable = (
            the_event.get("index") == "notable" and "event_id" in the_event and "notable" in the_event.get("event_id")
        )

        return the_event.get("event_id") if is_notable else None

    def write_to_incident_review_lookup(
        self, rule_name, rule_id, comment, status, current_time, user="SAA Add-On for Splunk"
    ):
        service = self.get_splunk_client()
        collection = service.kvstore["incident_review"]
        collection.data.insert(
            {
                "_key": str(current_time),
                "rule_name": rule_name,
                "rule_id": rule_id,
                "comment": comment,
                "status": status,
                "time": int(current_time),
                "user": user,
            }
        )

    def get_splunk_client(self):
        return client.connect(token=self.session_key)

    def find_corresponding_notable(self, events):
        if len(events) == 0:
            return None

        the_event = events[0]

        orig_bkt = the_event.get("_bkt")
        orig_time = the_event.get("_time")

        if not orig_bkt or not orig_time:
            return None

        notable_query = NOTABLE_QUERY.format(orig_time=orig_time, orig_bkt=orig_bkt)

        service = self.get_splunk_client()

        rr = JSONResultsReader(service.jobs.oneshot(notable_query, output_mode="json"))

        notable_query_results = []
        for result in rr:
            if isinstance(result, Message):
                # Diagnostic messages may be returned in the results
                pass
            elif isinstance(result, dict):
                # Normal events are returned as dicts
                notable_query_results.append(result)

        if len(notable_query_results) > 0 and "event_id" in notable_query_results[0]:
            return notable_query_results[0]["event_id"]

        return None

    def draw_resource_tree(self, job):
        resources = []

        for entry in job["Resources"]:
            resource = Resource(
                entry["ID"], entry["Name"], entry["InjectionMetadata"], entry["ParentID"], entry["DisplayScore"]
            )
            resources.append(resource)

        resource_tree = ResourceTree(resources)

        return resource_tree._build_tree_str()

    def process_event(self, *args, **kwargs):
        # import debugpy

        # debugpy.listen(("0.0.0.0", 5678))
        # debugpy.wait_for_client()
        # debugpy.breakpoint()

        self.set_log_level(logging.INFO)
        status = 0
        try:
            if not self.validate_params():
                return 3

            # Actual work here
            account_str = self.get_param("account")
            url = self.get_param("url")

            events = [event for event in self.get_events()]
            self.addinfo()
            self.addjobinfo()

            if not account_str:
                err_msg = "Could not retrieve account parameter"
                self.log_error(err_msg)
                raise SAAAlertActionException(err_msg)

            self.log_info(f"alert_account={account_str} url={url}")

            saa_client = get_configured_client(self.session_key, self._logger, account_str)

            result = saa_client.submit_url(url)
            job_id = result.get("JobID")

            corresponding_notable_event_id = self.find_corresponding_notable(events)
            adhoc_notable_event_id = self.is_adhoc_notable(events)

            if adhoc_notable_event_id is not None or corresponding_notable_event_id is not None:
                notable_event_id = corresponding_notable_event_id or adhoc_notable_event_id

                link_endpoint = saa_client.base_url.replace("https://api", "https://app")
                link = f"{link_endpoint}/job/{job_id}"
                self.write_to_incident_review_lookup("SAA - Submit URL", notable_event_id, link, "success", time.time())

                out = saa_client.query_for_completed_job(job_id)
                job_summary = {
                    "JobID": out["ID"],
                    "Submission": out["Submission"]["Name"],
                    "State": out["State"],
                    "Score": out["DisplayScore"],
                    "Verdict": out["Verdict"],
                    "CreatedAt": out["CreatedAt"],
                    "StartedAt": out["StartedAt"],
                    "CompletedAt": out["CompletedAt"],
                }

                summary_table = dict_to_markdown_table(job_summary)

                resources_analyzed_header = "### Resources Analyzed\n"

                intro_message = f"Full Job Information: {link}\n"
                summary = (
                    intro_message
                    + "\n"
                    + summary_table
                    + resources_analyzed_header
                    + "\n"
                    + "```\n"
                    + self.draw_resource_tree(out)
                    + "```\n"
                )

                self.write_to_incident_review_lookup(
                    "SAA - Submit URL",
                    notable_event_id,
                    summary,
                    "success",
                    time.time(),
                    "Splunk Attack Analyzer Summary",
                )

            self.log_info(f"submitted url - response: {result}")

        except (AttributeError, TypeError) as exc:
            self.log_error(
                f"Error: {exc}. Please double check spelling and also verify that a"
                " compatible version of Splunk_SA_CIM is installed.",
            )
            return 4
        except Exception as exc:  # pylint: disable=broad-exception-caught
            msg = "Unexpected error: {}."
            if str(exc):
                self.log_error(msg.format(str(exc)))  # e.message replaced with str(ae)
            else:
                import traceback  # pylint: disable=import-outside-toplevel

                self.log_error(msg.format(traceback.format_exc()))
            return 5
        return status


if __name__ == "__main__":
    EXIT_CODE = SubmitUrlAlert("Splunk_TA_SAA", "saa_alert_submit_url").run(sys.argv)
    sys.exit(EXIT_CODE)
