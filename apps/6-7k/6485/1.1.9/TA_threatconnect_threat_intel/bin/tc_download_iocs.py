"""Indicator Download Module"""

# standard library
import json
import operator
import os
import sys
import traceback
from datetime import datetime

# third-party
from tc_download_ioc_tracker import Tracker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))

# third-party
from base_script import BaseScript
from splunklib.modularinput import Argument, Event, Scheme


class IndicatorDownloadService(BaseScript):
    """Indicator Download Service Class"""

    tracker = None
    result_limit = 10_000
    default_fields = [
        "id",
        "rating",
        "confidence",
        "ownerName",
        "summary",
        "type",
        "webLink",
    ]

    def get_scheme(self):
        """Overloaded splunklib modularinput method"""
        scheme = Scheme("tc_download_iocs")
        scheme.title = "ThreatConnect Indicators"
        scheme.description = "Modular input to pull events from ThreatConnect API"
        scheme.streaming_mode = "xml"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        arguments = [
            Argument("name", title="Name", description="", required_on_create=True),
            Argument(
                "owners",
                title="Owners",
                required_on_create=True,
                required_on_edit=True,
                description="The Owner(s) to use for the search. This is comma delimited.",
            ),
            Argument(
                "tql",
                title="TQL",
                required_on_create=True,
                required_on_edit=True,
                description="The TQL query to search on.",
            ),
            Argument(
                "fields",
                title="Fields (Optional)",
                required_on_create=False,
                required_on_edit=True,
                description=f"The fields to store in the index. {self.default_fields} "
                "are always included.",
            ),
            Argument(
                "from",
                title="From",
                required_on_create=True,
                required_on_edit=True,
                description="DO NOT EDIT.",
            ),
            Argument(
                "version",
                title="Version",
                required_on_create=False,
                required_on_edit=False,
                description="",
            ),
        ]

        for argument in arguments:
            scheme.add_argument(argument)

        return scheme

    def validate_input(self, definition):
        """Validate the inputs for the module import."""

        definition = definition.parameters

        if "ownerName" in definition.get("tql"):
            raise ValueError("Use the owner input field to specify Owner(s)")

        return None

    def configure_session(self):
        """Configure the session using the provided params."""

        tc_api_secret_key = self.password_manager.get_password(
            self.service, "tc_api_secret_key"
        )
        tc_proxy_password = self.password_manager.get_password(
            self.service, "tc_proxy_password"
        )
        self.session.proxies = self.session.configure_proxies(
            self.settings.get("proxy_enabled"),
            self.settings.get("proxy_host"),
            self.settings.get("proxy_port"),
            self.settings.get("proxy_user"),
            tc_proxy_password,
        )
        self.session.base_url = self.settings.get("base_url")
        self.session.auth = self.session.hmac_auth(
            self.settings.get("api_access_id"), tc_api_secret_key
        )

    def populate_stored_uuid5s(self):
        """Get the stored uuid5s from the checkpoint manager."""
        spl = (
            f'search index="tc_indicator_data" "metadata.search_uuid5"="{self.tracker.search_uuid5}"'
            "| dedup metadata.uuid5"
            '| search "metadata.deleted"=false'
            '| rename "metadata.uuid5" as uuid5'
            "| table uuid5"
        )
        job = self.search(spl)

        for event in self.iterate(job):
            self.tracker.stored_uuid5s.add(event.get("uuid5"))

    def stream_events(self, inputs, ew):
        """Stream events into summary index"""
        self.event_writer = ew

        for input_name, input_item in inputs.inputs.items():
            try:
                if self.settings.get("valid") is False:
                    err_msg = "Invalid settings. Please verify your settings in the settings page."
                    self.log(
                        "error", "skipping-job", self.settings.get("message") or err_msg
                    )
                    break
                self.configure_session()
                self.result_limit = int(input_item.get("resultLimit", 10_000))

                additional_tc_fields = {
                    "dateAdded",
                    "lastModified",
                    "privateFlag",
                    "active",
                    "activeLocked",
                }
                default_fields = [
                    "id",
                    "rating",
                    "confidence",
                    "ownerName",
                    "summary",
                    "type",
                    "webLink",
                ]
                self.tracker = Tracker(
                    start_time=datetime.utcnow(),
                    job_name=input_name.split("//")[-1],
                    fields=input_item.get("fields"),
                    owners=input_item.get("owners"),
                    version=input_item.get("version"),
                    tql=input_item.get("tql"),
                )
                tracker_fields = []
                for field in set(self.tracker.fields):
                    if field in additional_tc_fields:
                        default_fields.append(field)
                    else:
                        tracker_fields.append(field)
                self.tracker.fields = tracker_fields
                # Set the job_uuid to the job_name and start_time used for logging purposes
                self.job_uuid = (
                    f"{self.tracker.job_name}:{self.tracker.start_time.timestamp()}"
                )
                # Returns last_run as a datetime
                last_run = self.checkpoint_manager.get_checkpoint(
                    self.tracker.file_name
                )
                if last_run:
                    if not isinstance(last_run, datetime):
                        last_run = datetime.strptime(
                            last_run, self.tracker.datetime_format
                        )
                    self.tracker.last_run = last_run

                self.log("info", "starting-job:details", self.tracker.details)
                self.populate_stored_uuid5s()

                counter = 0
                for indicator in self.process_indicators():
                    counter += 1
                    if counter % 10_000 == 0:
                        self.log(
                            "info",
                            "running-job:progress-tracker",
                            {"current-count": counter},
                        )
                    event = Event()
                    event.stanza = input_name

                    fields = set(self.tracker.fields)
                    fields.update(set(default_fields))
                    pruned_indicator = self.utils.prune_indicator(indicator, fields)
                    pruned_indicator["metadata"] = indicator["metadata"]
                    pruned_indicator["metadata"].update(
                        {
                            "epoch": self.tracker.start_time_formatted,
                            "search_uuid5": self.tracker.search_uuid5,
                            "search_name": self.tracker.job_name,
                            "uuid5": self.utils.generate_uuid_from_indicator(indicator),
                        }
                    )
                    if pruned_indicator["metadata"]["deleted"] is False:
                        self.tracker.added += 1
                    else:
                        self.tracker.removed += 1

                    event.data = json.dumps(pruned_indicator)
                    ew.write_event(event)
                self.log("info", "job-metrics:metrics", self.tracker.metrics)
                self.checkpoint_manager.save_checkpoint(
                    self.tracker.file_name, self.tracker.start_time_formatted
                )
            except Exception:
                if self.request.request and not self.request.request.ok:
                    self.log("error", "job-error", self.request.request.text)
                err_msg = [e.strip() for e in traceback.format_exc().split("\n")]
                self.log("error", "job-error", err_msg)
                self.log(
                    "error",
                    "job-error",
                    "Job failed. Please view logs for more information.",
                )

    def process_indicators(self):
        """Yield the indicators as appropriate."""

        if self.tracker.last_run is None:
            self.log("info", "starting-job:action", {"action": "initial-run"})
            for indicator in self.process_all_indicators():
                yield indicator
        else:
            self.log("info", "starting-job:action", {"action": "subsequent-run"})
            for indicator in self.process_changed_indicators():
                yield indicator

    def get_relevant_updated_indicators(self):
        """Retrieve a dict of indicators updated since the last execution."""

        relevant_updated_indicators = set()
        for indicator in self.request.get_indicators(
            tql=self.tracker.tql_enhance,
            max_result_limit=self.result_limit,
            request_type="updated",
        ):
            indicator_uuid5 = self.utils.generate_uuid_from_indicator(indicator)
            self.tracker.updated_indicators_subset.add(indicator_uuid5)
        return relevant_updated_indicators

    def process_changed_indicators(self):
        """Retrieve a dict of indicators updated since the last execution."""
        self.get_relevant_updated_indicators()
        self.log(
            "info",
            "running-job:updated-indicators-subset",
            {
                "updated-indicators-subset-count": len(
                    self.tracker.updated_indicators_subset
                )
            },
        )

        # Process Deleted Indicators
        for indicator in self.request.get_deleted_indicators(
            self.tracker.last_run_formatted,
            self.tracker.start_time,
            owners=self.tracker.owners,
        ):
            indicator_uuid5 = self.utils.generate_uuid_from_indicator(indicator)

            # If it was deleted but was not stored to begin with we don't care.
            if indicator_uuid5 not in self.tracker.stored_uuid5s:
                continue

            indicator["metadata"] = {"deleted": True, "uuid5": indicator_uuid5}
            self.tracker.deleted_indicators[indicator_uuid5] = indicator.get(
                "dateAdded"
            )

            # Add the deleted indicator to the summary index.
            yield indicator

        # process all indicators that changed since the last run. this query doesn't not include
        # the filtering TQL so we can compare all updated indicators with those that were downloaded
        # with the TQL and those that were previously stored.
        for indicator in self.request.get_indicators(
            self.tracker.fields,
            self.tracker.tql_base,
            max_result_limit=self.result_limit,
        ):
            indicator_uuid5 = self.utils.generate_uuid_from_indicator(indicator)
            deleted_indicator = self.tracker.deleted_indicators.get(indicator_uuid5)

            # validated that the indicator was not deleted and if so that the updated
            # indicator timestamp is newer than the deleted indicator timestamp
            if deleted_indicator is not None and self.utils.compare_times(
                indicator.get("lastModified"), operator.lt, deleted_indicator
            ):
                continue

            if indicator_uuid5 in self.tracker.updated_indicators_subset:
                # indicator matched TQL query, so it was added or updated.
                indicator["metadata"] = {"deleted": False}
            elif indicator_uuid5 in self.tracker.stored_uuid5s:
                # was not pulled from the TQL query, but was previously stored. this indicates
                # that the indicator was deleted or filters values dropped below threshold.
                indicator["metadata"] = {"deleted": True}
            else:
                # indicator did not match TQL query and was not previously stored.
                continue

            yield indicator

    def process_all_indicators(self):
        """Add all indicators from TC into the summary index if they match the provided tql."""
        for indicator in self.request.get_indicators(
            self.tracker.fields,
            self.tracker.tql_initial,
            max_result_limit=self.result_limit,
        ):
            indicator_uuid5 = self.utils.generate_uuid_from_indicator(indicator)
            indicator["metadata"] = {"uuid5": indicator_uuid5, "deleted": False}
            yield indicator


if __name__ == "__main__":
    sys.exit(IndicatorDownloadService().run(sys.argv))
