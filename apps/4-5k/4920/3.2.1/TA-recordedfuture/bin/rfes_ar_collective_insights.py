# encoding = utf-8
"""Implement Collective Insights AR - DO NOT MOVE THIS FILE"""

import os
import sys
import datetime
import math

from recordedfuture.core.exceptions import ValidationError
from requests import RequestException
from typing import List, Dict, Any

sys.path.insert(0, os.path.dirname(__file__))
from recordedfuture.es.adaptive_response import (  # noqa
    AdaptiveModularAction,
    ModularAction,
    mktimegm,
    ModularActionTimer,
    main_execution,
)

from recordedfuture.core.utils import (  # noqa
    get_category,  # noqa
    get_instance_guid,  # noqa
    CategoryParseException,  # noqa
)  # noqa


class RecordedFutureCollectiveInsightsAction(AdaptiveModularAction):
    """Recorded Future Modular Action."""

    def dowork(self, results: List[Dict[str, Any]]):
        """Do the actual writeback for all events in batch."""
        instance_guid = get_instance_guid(self.app_env)
        param_entity_type = self.configuration.get("category", "auto")
        tracking_payload = []
        for result in results:
            field = self.configuration.get("ioc_value")
            entity = result.get(field)

            if entity is None:
                continue

            if param_entity_type == "auto":
                try:
                    entity_type = get_category("auto", entity)
                except CategoryParseException:
                    self.app_env.logger.error(
                        f"Failed to detect category for {result}, skipping"
                    )
                    continue
            else:
                entity_type = param_entity_type

            track_entry = {
                "iocs": {entity_type: [entity]},
                "integration_instance_id": instance_guid,
                "field": field,
            }
            use_case_name_field = self.configuration.get("use_case_name", "")
            use_case_name = result.get(use_case_name_field, use_case_name_field)
            if use_case_name is not None:
                track_entry["use_case_name"] = use_case_name
                track_entry["use_case"] = "_".join(use_case_name.split())

            timestamp_field = self.configuration.get("timestamp")
            current_time = math.floor(
                datetime.datetime.now(tz=datetime.timezone.utc).timestamp()
            )
            if timestamp_field is None:
                track_entry["timestamp"] = current_time
            else:
                track_entry["timestamp"] = result.get(timestamp_field, current_time)

            for optional_field in ["source_type", "detection_action"]:
                value = self.configuration.get(optional_field)
                if value is not None:
                    track_entry[optional_field] = result.get(value, value)

            tracking_payload.append(track_entry)

        try:
            if tracking_payload and self.app_env.privacy.share_intelligence:
                self.rfclient.adaptive_response.track(tracking_payload)
                self.message(
                    f"Successfully sent {len(tracking_payload)} indicators to Collective Insights",
                    rids=self.rids,
                    status="success",
                )
        except RequestException as err:
            self.app_env.logger.error("Data sharing call failed: %s", err)
            self.message("Failed to send indicators.", rids=self.rids, status="failure")

    def validate(self, result: Dict[str, Any]):
        """Validates that required params are provided and that entity param value exist in result dict"""
        required_fields = ["ioc_type", "ioc_value", "use_case_name"]
        for field in required_fields:
            if self.configuration.get(field) is None:
                id_to_label_map = {
                    "ioc_type": "Entity Type",
                    "ioc_value": "Entity",
                    "use_case_name": "Description",
                }
                message = f"'{id_to_label_map[field]}' is a mandatory parameter, but its value is None."
                raise ValidationError(message)

        if self.configuration.get("ioc_type") not in [
            "auto",
            "ip",
            "domain",
            "url",
            "hash",
        ]:
            message = (
                "'Entity Type' must be one of ['auto', 'ip', 'domain', 'url', 'hash']"
            )
            raise ValidationError(message)

        if result.get(self.configuration.get("ioc_value")) is None:
            message = f"'{self.configuration.get('ioc_value')}' is not present in notable, 'Entity' value must correspond to an event-field."
            raise ValidationError(message)


def main_callback(modaction):
    # No callback needed, only share the data.
    pass


if __name__ == "__main__":
    main_execution(
        RecordedFutureCollectiveInsightsAction,
        name="rfes_ar_collective_insights",
        execution_callback=main_callback,
        batch=True,
    )
