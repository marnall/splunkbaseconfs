#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
from typing import Any, Dict, List


def split_events(items_from_google_api_response: List[Dict[str, Any]]):
    """
    Splits events from list of items into multiple single events with
    the same metadata.
    :param items_from_google_api_response: List of items from Google Workspace API
    """
    result: List[Dict[str, Any]] = []
    for item in items_from_google_api_response:
        events = item["events"]
        item_keys = set(item.keys())
        # Taking every possible key without "events" to copy into our "raw"
        # event.
        # https://developers.google.com/admin-sdk/reports/reference/rest/v1/activities/list#activity
        # The link above contains JSON template for the activity resource.
        # This code can be faster using `frozenset` and directly specifying
        # the keys which need to be copied to the raw event. But if the
        # vendor updates an JSON template, we need to create another release
        # to support it.
        item_keys_without_events_id = item_keys - {"events", "id"}
        # We need to put `id` first, so Splunk can assign the correct time
        # during the indexing of the event. MAX_TIMESTAMP_LOOKAHEAD is 128
        # characters by default.
        # https://docs.splunk.com/Documentation/Splunk/9.0.4/Data/Configuretimestamprecognition
        id_from_item = item.get("id")
        for event in events:
            raw_event = {
                "id": id_from_item,
            }
            for item_key_without_events in item_keys_without_events_id:
                if item.get(item_key_without_events) is not None:
                    raw_event[item_key_without_events] = item[item_key_without_events]
            raw_event["event"] = event
            result.append(raw_event)
    return result
