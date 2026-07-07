#!/usr/bin/env python
import json
import sys

from augur_command import AugurCommand
from cached_property import cached_property
from splunklib.searchcommands import Configuration, StreamingCommand, dispatch


@Configuration(distributed=False, local=True)
class FeedbackCommand(StreamingCommand, AugurCommand):
    """Use Search Command V2 protocol."""

    def __init__(self, *args, **kwargs):
        super(FeedbackCommand, self).__init__(*args, **kwargs)
        self._batch_events = []
        self._all_fields = set()
        self._sent_fields_hashes = set()
        self.timeout = 10

    def filter_fields(self, item):
        """Prepare item for sending to Augur.

        Remove confidential information if required.
        """
        if (
            not self.allowed_fields
            or "seclytics_permissive_mode" in self.allowed_fields
        ):
            return dict(item)
        return dict(
            {field_name: item.get(field_name) for field_name in self.allowed_fields}
        )

    @cached_property
    def allowed_fields(self):
        """Get all fields allowed by the API.

        By default send everything.
        """
        self.logger.info("Get splunk config.")
        config = {}
        try:
            url = "https://api.seclytics.com/events/splunk_config.json"
            config_response = self.augur_api.session.get(url, timeout=self.timeout)
            if config_response.status_code == 200:
                config = config_response.json()
        except Exception as exception:
            self.logger.error("Could not process config. %s", str(exception))
        return config.get("fields")

    def stream(self, events):
        """Process each event for feedback."""
        self.logger.info("Stream events for feedback")
        for event in events:
            self.add_event(event)
            yield event
        self.send_data()

    def add_event(self, event):
        # track all fieldnames
        self._all_fields.update(list(event.keys()))
        # track all events
        processed_item = self.filter_fields(event)
        processed_item["seen_at"] = event.get("_time")
        self._batch_events.append(processed_item)

    def send_data(self):
        """Send a batch of data to Augur."""
        self.logger.info("Stream events for feedback")
        if len(self._batch_events) == 0:
            return
        headers = {"Content-Type": "application/json"}

        url = "https://api.seclytics.com/events/splunk_feedback"
        data = json.dumps(self._batch_events)
        self.augur_api.session.post(
            url, data=data, headers=headers, timeout=self.timeout
        )

        # Only send fields if this combination hasn't been sent before
        current_fields_hash = hash(tuple(sorted(self._all_fields)))
        if current_fields_hash not in self._sent_fields_hashes:
            url = "https://api.seclytics.com/events/splunk_fields"
            data = json.dumps(list(self._all_fields))
            self.augur_api.session.post(
                url, data=data, headers=headers, timeout=self.timeout
            )
            self._sent_fields_hashes.add(current_fields_hash)

        self._batch_events = []
        self._all_fields = set()


dispatch(FeedbackCommand, sys.argv, sys.stdin, sys.stdout, __name__)
