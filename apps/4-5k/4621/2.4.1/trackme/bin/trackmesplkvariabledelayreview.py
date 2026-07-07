#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json
import math

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_variable_delay_review.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()
for hdlr in log.handlers[:]:
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_register_tenant_object_summary,
    trackme_reqinfo,
    trackme_vtenant_account,
    trackme_idx_for_tenant,
    run_splunk_search,
    is_ai_feed_lifecycle_covering,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import shared pure helpers (#1717: moved out of trackmesplkvariabledelay
# so importing them no longer drags that custom command's module-load
# root-logger rebind into this process).
from trackme_libs_variable_delay import aggregate_slots, compute_threshold

# import threshold intent-lock helpers + bulk reader
from trackme_libs_threshold_intent import is_delay_threshold_locked
from trackme_libs_get_data import batch_find_records_by_key


def compute_slot_deviation(current_slots, new_slots):
    """
    Compare current and new slot configurations and return the maximum
    percentage deviation between them.

    Comparison is done on a per-(day, hour) basis using the effective
    max_delay_allowed for each combination.

    Args:
        current_slots: dict with "slots" key containing list of slot dicts
        new_slots: dict with "slots" key containing list of slot dicts

    Returns:
        (max_deviation_pct: float, details: str)
    """

    def build_hour_map(slots_config):
        """Build a dict mapping (day, hour) -> max_delay_allowed from slots.
        Uses first-match-wins semantics to align with resolve_variable_delay_threshold."""
        hour_map = {}
        for slot in slots_config.get("slots", []):
            for day in slot.get("days", []):
                for hour in slot.get("hours", []):
                    if (day, hour) not in hour_map:
                        hour_map[(day, hour)] = float(slot.get("max_delay_allowed", 3600))
        return hour_map

    current_map = build_hour_map(current_slots)
    new_map = build_hour_map(new_slots)

    # Combine all keys from both maps
    all_keys = set(current_map.keys()) | set(new_map.keys())

    if not all_keys:
        return 0.0, "no slots to compare"

    max_deviation = 0.0
    max_deviation_key = None

    for key in all_keys:
        current_val = current_map.get(key)
        new_val = new_map.get(key)

        if current_val is None or new_val is None:
            # A slot was added or removed - treat as 100% deviation
            max_deviation = 100.0
            max_deviation_key = key
            break

        if current_val == 0:
            if new_val > 0:
                max_deviation = 100.0
                max_deviation_key = key
                break
            continue

        deviation = abs(new_val - current_val) / current_val * 100.0
        if deviation > max_deviation:
            max_deviation = deviation
            max_deviation_key = key

    if max_deviation_key:
        details = (
            f"max deviation {max_deviation:.1f}% at day={max_deviation_key[0]}, "
            f"hour={max_deviation_key[1]}"
        )
    else:
        details = "no deviation detected"

    return max_deviation, details


@Configuration(distributed=False)
class VariableDelayReview(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** Specify the TrackMe component (dsm or dhm).""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(dsm|dhm)$"),
    )

    review_frequency_sec = Option(
        doc="""
        **Syntax:** **review_frequency_sec=****
        **Description:** Minimum seconds between reviews per entity (default: 604800 = 7 days).""",
        require=False,
        default="604800",
        validate=validators.Match("review_frequency_sec", r"^\d+$"),
    )

    deviation_threshold_pct = Option(
        doc="""
        **Syntax:** **deviation_threshold_pct=****
        **Description:** Minimum percentage change in thresholds to trigger an update (default: 20).""",
        require=False,
        default="20",
        validate=validators.Match("deviation_threshold_pct", r"^\d+$"),
    )

    lookback = Option(
        doc="""
        **Syntax:** **lookback=****
        **Description:** The lookback period for metrics query (default: -30d).""",
        require=False,
        default="-30d",
    )

    method = Option(
        doc="""
        **Syntax:** **method=****
        **Description:** The statistical method to use: perc95 (default), perc99.""",
        require=False,
        default="perc95",
        validate=validators.Match("method", r"^(perc95|perc99)$"),
    )

    min_samples = Option(
        doc="""
        **Syntax:** **min_samples=****
        **Description:** Minimum number of metric samples per hour/day to consider it valid (default: 10).""",
        require=False,
        default="10",
        validate=validators.Match("min_samples", r"^\d+$"),
    )

    max_threshold_sec = Option(
        doc="""
        **Syntax:** **max_threshold_sec=****
        **Description:** Safety cap for any computed threshold in seconds (default: 604800 = 7 days).""",
        require=False,
        default="604800",
        validate=validators.Match("max_threshold_sec", r"^\d+$"),
    )

    max_runtime = Option(
        doc="""
        **Syntax:** **max_runtime=****
        **Description:** Maximum runtime for the job in seconds (default: 7200 = 2 hours).""",
        require=False,
        default="7200",
        validate=validators.Match("max_runtime", r"^\d+$"),
    )

    def generate(self):
        """Main entry point for the auto-review custom command."""

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        # performance counter
        start = time.time()
        instance_id = str(time.time())

        logging.info(
            f"instance_id={instance_id}, starting variable delay auto-review, "
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'review_frequency_sec="{self.review_frequency_sec}", '
            f'deviation_threshold_pct="{self.deviation_threshold_pct}", '
            f'lookback="{self.lookback}", method="{self.method}"'
        )

        # get the vtenant account to check if auto-review is enabled at tenant level
        vtenant_account = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        variable_delay_auto_review_enabled = int(
            vtenant_account.get("variable_delay_auto_review", 1)
        )

        if variable_delay_auto_review_enabled == 0:
            logging.info(
                f'instance_id={instance_id}, tenant_id="{self.tenant_id}", '
                f"variable_delay_auto_review is disabled for this tenant, skipping execution"
            )
            run_time = round(time.time() - start, 3)
            # register
            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                f"trackme_{self.component}_variable_delay_review_tracker_tenant_{self.tenant_id}",
                "success",
                time.time(),
                run_time,
                "Variable delay auto-review is disabled for this tenant, skipping execution",
                "-5m",
                "now",
            )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "success",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "msg": "variable_delay_auto_review is disabled for this tenant, skipping execution",
                    }
                ),
            }
            return

        # Mutex with the AI Feed Lifecycle Advisor.
        #
        # When the AI Feed Lifecycle Advisor covers this component on this
        # tenant, AI is the authority for delay management — both legacy
        # mechanical Adaptive Delay and the variable-delay auto-review
        # must stand down. The save-time hook in
        # ``trackme_rh_vtenants_handler.py`` flips
        # ``variable_delay_auto_review`` to 0 whenever the AI advisor is
        # turned on for DSM/DHM, so under normal operation we never reach
        # this point with both flags set. This block is defence-in-depth
        # — drift from direct KV pokes or any API path that bypasses
        # the UCC hook still short-circuits here, and the
        # ``ai_feed_lifecycle_delay_conflict`` Guardian check raises a
        # warning on the inconsistency.
        if is_ai_feed_lifecycle_covering(vtenant_account, self.component):
            logging.info(
                f'instance_id={instance_id}, tenant_id="{self.tenant_id}", '
                f'component="{self.component}", skipping execution because '
                f'AI Feed Lifecycle Advisor covers this component '
                f'(ai_components_advisor_enabled=1 + "{self.component}" in '
                f'ai_components_advisor_list). Persisted state of '
                f'variable_delay_auto_review=1 is inconsistent — see '
                f'Configuration Guardian alert ai_feed_lifecycle_delay_conflict.'
            )
            run_time = round(time.time() - start, 3)
            # register
            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                f"trackme_{self.component}_variable_delay_review_tracker_tenant_{self.tenant_id}",
                "success",
                time.time(),
                run_time,
                (
                    "Variable delay auto-review short-circuited at runtime — "
                    "AI Feed Lifecycle Advisor authority on this component"
                ),
                "-5m",
                "now",
            )
            # Audit the runtime override — best-effort, must not break
            # the no-op return path on audit-index misconfiguration.
            try:
                trackme_audit_event(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "trackmesplkvariabledelayreview",
                    "skipped",
                    "variable_delay_auto_review_runtime_gate",
                    f"variable_delay_review_tracker_tenant_{self.tenant_id}",
                    f"splk-{self.component}",
                    "{}",
                    "success",
                    (
                        "Variable Delay Auto-Review short-circuited at runtime "
                        "because the AI Feed Lifecycle Advisor covers this "
                        "component. Persisted variable_delay_auto_review=1 is "
                        "inconsistent — disable variable_delay_auto_review or "
                        "remove this component from ai_components_advisor_list."
                    ),
                )
            except Exception as e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'failed to emit audit event for '
                    f'variable_delay_auto_review_runtime_gate, exception="{str(e)}"'
                )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "success",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "msg": (
                            "variable_delay_auto_review skipped — AI Feed "
                            "Lifecycle Advisor covers this component"
                        ),
                    }
                ),
            }
            return

        # get metric index for tenant
        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        metric_index = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

        # Load variable delay collection - get entities with auto-review enabled
        collection_name = (
            f"kv_trackme_{self.component}_variable_delay_tenant_{self.tenant_id}"
        )

        try:
            collection = self.service.kvstore[collection_name]
        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, tenant_id="{self.tenant_id}", '
                f'failed to access variable delay collection "{collection_name}", exception="{str(e)}"'
            )
            run_time = round(time.time() - start, 3)
            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                f"trackme_{self.component}_variable_delay_review_tracker_tenant_{self.tenant_id}",
                "failure",
                time.time(),
                run_time,
                f'Failed to access variable delay collection: {str(e)}',
                "-5m",
                "now",
            )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "failure",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "error": str(e),
                    }
                ),
            }
            return

        # Query entities with auto-review enabled
        query_filter = json.dumps(
            {
                "variable_delay_enabled": "true",
                "variable_delay_auto_review_enabled": "true",
            }
        )

        try:
            review_candidates = []
            skip_tracker = 0
            while True:
                batch = collection.data.query(query=query_filter, skip=skip_tracker)
                if not batch:
                    break
                review_candidates.extend(batch)
                skip_tracker += len(batch)
        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, failed to query variable delay collection, exception="{str(e)}"'
            )
            review_candidates = []

        now_epoch = time.time()
        review_frequency = int(self.review_frequency_sec)
        deviation_threshold = float(self.deviation_threshold_pct)
        max_threshold = int(self.max_threshold_sec)
        max_runtime = int(self.max_runtime)

        # Filter to entities due for review
        entities_to_review = []
        for record in review_candidates:
            last_review = float(record.get("variable_delay_last_auto_review", 0))
            time_since_review = now_epoch - last_review

            if time_since_review >= review_frequency:
                entities_to_review.append(record)
            else:
                logging.info(
                    f'instance_id={instance_id}, object="{record.get("object")}", '
                    f"skipping review, last reviewed {time_since_review:.0f}s ago "
                    f"(frequency: {review_frequency}s)"
                )

        # Threshold intent lock — exclude entities whose operator has pinned the
        # delay threshold. The lock flag lives on the MAIN entity record (not the
        # variable_delay record), so resolve the candidate subset against the
        # main collection in one batch read (cost scales with the due-for-review
        # subset, not the full collection). Missing entity / missing flag is
        # treated as "not locked". Fail-open on read error: better to review than
        # to silently stop honouring the schedule.
        if entities_to_review:
            main_collection_name = (
                f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
            )
            candidate_keys = [
                r.get("_key") for r in entities_to_review if r.get("_key")
            ]
            # Fail-open ONLY on the KV/batch read (a transient store failure must
            # not stall the schedule). The deterministic in-memory filter below
            # runs OUTSIDE the try, so a regression in is_delay_threshold_locked
            # or the record-shape assumptions surfaces loudly instead of silently
            # reintroducing overwrites of pinned thresholds.
            main_dict = None
            try:
                main_collection = self.service.kvstore[main_collection_name]
                main_dict, _ = batch_find_records_by_key(
                    main_collection, candidate_keys
                )
            except Exception as e:
                logging.warning(
                    f'instance_id={instance_id}, failed to read main collection for '
                    f'threshold intent-lock filter (proceeding without it), '
                    f'exception="{str(e)}"'
                )

            if main_dict is not None:
                unlocked = []
                locked_count = 0
                for record in entities_to_review:
                    main_record = main_dict.get(record.get("_key"))
                    if main_record is not None and is_delay_threshold_locked(
                        main_record
                    ):
                        locked_count += 1
                        logging.info(
                            f'instance_id={instance_id}, object="{record.get("object")}", '
                            f"skipping variable delay auto-review — delay threshold "
                            f"pinned by operator (intent lock)"
                        )
                        continue
                    unlocked.append(record)
                if locked_count:
                    logging.info(
                        f"instance_id={instance_id}, excluded {locked_count} "
                        f"intent-locked entities from variable delay auto-review"
                    )
                entities_to_review = unlocked

        logging.info(
            f"instance_id={instance_id}, found {len(entities_to_review)} entities "
            f"due for variable delay auto-review out of {len(review_candidates)} candidates"
        )

        if not entities_to_review:
            run_time = round(time.time() - start, 3)
            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                f"trackme_{self.component}_variable_delay_review_tracker_tenant_{self.tenant_id}",
                "success",
                time.time(),
                run_time,
                "No entities due for variable delay auto-review",
                "-5m",
                "now",
            )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "success",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "entities_reviewed": 0,
                        "entities_updated": 0,
                        "msg": "no entities due for auto-review",
                    }
                ),
            }
            return

        # Counters
        count_reviewed = 0
        count_updated = 0
        count_skipped = 0
        count_failed = 0
        updated_entities = []
        failed_entities = []

        # Track execution time for runtime management
        total_iteration_time = 0
        iteration_count = 0

        for record in entities_to_review:

            iteration_start = time.time()

            obj = record.get("object")
            obj_key = record.get("_key")

            # Use per-entity lookback/method if set, otherwise use command defaults
            entity_lookback = record.get("variable_delay_auto_review_period", self.lookback)
            entity_method = record.get("variable_delay_auto_review_method", self.method)
            entity_stat_func = "perc95" if entity_method == "perc95" else "perc99"

            logging.info(
                f'instance_id={instance_id}, reviewing object="{obj}", '
                f'lookback="{entity_lookback}", method="{entity_method}"'
            )

            # Build the per-day/hour mstats query for this entity
            search_query = remove_leading_spaces(
                f"""
                | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec
                  where index="{metric_index}"
                  tenant_id="{self.tenant_id}"
                  object_category="splk-{self.component}"
                  object="{obj}"
                  earliest="{entity_lookback}" latest="now"
                  by object span=5m
                | eval day_of_week=tonumber(strftime(_time, "%w"))
                | eval day_of_week=if(day_of_week==0, 6, day_of_week-1)
                | eval hour_of_day=tonumber(strftime(_time, "%H"))
                | stats {entity_stat_func}(lag_event_sec) as stat_delay,
                        avg(lag_event_sec) as avg_delay,
                        count as sample_count
                  by object, day_of_week, hour_of_day
                | where sample_count >= {self.min_samples}
                """
            )

            kwargs_search = {
                "earliest_time": entity_lookback,
                "latest_time": "now",
                "output_mode": "json",
                # count=0 returns all rows. The stats produces up to 7*24 =
                # 168 rows (day_of_week x hour_of_day); the Splunk default
                # of 100 would silently truncate and yield incomplete
                # hourly thresholds.
                "count": 0,
            }

            try:
                search_results_reader = run_splunk_search(
                    self.service,
                    search_query,
                    kwargs_search,
                    24,
                    5,
                )
                # Materialize the lazy JSONResultsReader into a list so that
                # JSON parse errors (e.g. empty response) are caught here.
                search_results = [
                    r for r in search_results_reader if isinstance(r, dict)
                ]
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, object="{obj}", '
                    f'metrics query failed, exception="{str(e)}"'
                )
                count_failed += 1
                failed_entities.append(obj)
                continue

            if not search_results:
                logging.warning(
                    f'instance_id={instance_id}, object="{obj}", '
                    f"no metric data returned, skipping review"
                )
                # Still update last_auto_review to avoid retrying immediately
                try:
                    record["variable_delay_last_auto_review"] = str(now_epoch)
                    record["variable_delay_mtime"] = str(now_epoch)
                    record["variable_delay_updated_by"] = "trackmesplkvariabledelayreview"
                    collection.data.update(str(obj_key), json.dumps(record))
                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, object="{obj}", '
                        f'failed to update last_auto_review timestamp, exception="{str(e)}"'
                    )
                count_skipped += 1
                count_reviewed += 1
                continue

            # Compute per-hour thresholds from the metrics
            hourly_thresholds = {}
            for result in search_results:
                try:
                    day = int(float(result.get("day_of_week", 0)))
                    hour = int(float(result.get("hour_of_day", 0)))
                    stat_delay = float(result.get("stat_delay", 0))
                except (ValueError, TypeError):
                    continue

                threshold = compute_threshold(stat_delay)
                # Apply safety cap
                if threshold > max_threshold:
                    threshold = max_threshold
                hourly_thresholds[(day, hour)] = threshold

            if not hourly_thresholds:
                logging.warning(
                    f'instance_id={instance_id}, object="{obj}", '
                    f"no valid hourly thresholds computed, skipping"
                )
                count_skipped += 1
                count_reviewed += 1
                continue

            # Aggregate into slots
            new_slots_list = aggregate_slots(hourly_thresholds)
            new_default = max(hourly_thresholds.values())
            if new_default > max_threshold:
                new_default = max_threshold

            new_slots_config = {"slots": new_slots_list}

            # Load current slots configuration
            try:
                current_slots_config = json.loads(
                    record.get("variable_delay_slots", "{}")
                )
            except (json.JSONDecodeError, TypeError):
                current_slots_config = {}

            # Compare current vs new
            max_deviation, deviation_details = compute_slot_deviation(
                current_slots_config, new_slots_config
            )

            logging.info(
                f'instance_id={instance_id}, object="{obj}", '
                f"deviation={max_deviation:.1f}%, threshold={deviation_threshold}%, "
                f"details={deviation_details}"
            )

            count_reviewed += 1

            # Update if deviation exceeds threshold
            if max_deviation >= deviation_threshold:
                logging.info(
                    f'instance_id={instance_id}, object="{obj}", '
                    f"deviation {max_deviation:.1f}% >= threshold {deviation_threshold}%, "
                    f"updating variable delay slots"
                )

                try:
                    record["variable_delay_slots"] = json.dumps(new_slots_config)
                    record["variable_delay_default"] = str(int(new_default))
                    record["variable_delay_mode"] = "auto"
                    record["variable_delay_last_auto_review"] = str(now_epoch)
                    record["variable_delay_mtime"] = str(now_epoch)
                    record["variable_delay_updated_by"] = "trackmesplkvariabledelayreview"

                    collection.data.update(str(obj_key), json.dumps(record))

                    # Audit event
                    trackme_audit_event(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "trackmesplkvariabledelayreview",
                        "success",
                        "variable delay auto-review update",
                        str(obj),
                        f"splk-{self.component}",
                        json.dumps(new_slots_config),
                        f"Variable delay auto-review updated slots (deviation: {max_deviation:.1f}%, "
                        f"{len(new_slots_list)} slots, method: {entity_method}, lookback: {entity_lookback})",
                        "auto-review",
                    )

                    count_updated += 1
                    updated_entities.append(obj)

                    logging.info(
                        f'instance_id={instance_id}, object="{obj}", '
                        f"variable delay slots updated successfully, "
                        f"new slot count={len(new_slots_list)}"
                    )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, object="{obj}", '
                        f'failed to update variable delay slots, exception="{str(e)}"'
                    )
                    count_failed += 1
                    failed_entities.append(obj)
            else:
                # No significant change - just update the review timestamp
                logging.info(
                    f'instance_id={instance_id}, object="{obj}", '
                    f"deviation {max_deviation:.1f}% < threshold {deviation_threshold}%, "
                    f"no update needed"
                )
                try:
                    record["variable_delay_last_auto_review"] = str(now_epoch)
                    record["variable_delay_mtime"] = str(now_epoch)
                    record["variable_delay_updated_by"] = "trackmesplkvariabledelayreview"
                    collection.data.update(str(obj_key), json.dumps(record))
                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, object="{obj}", '
                        f'failed to update review timestamp, exception="{str(e)}"'
                    )

            # Runtime management - check if we should stop
            iteration_end = time.time()
            iteration_time = iteration_end - iteration_start
            total_iteration_time += iteration_time
            iteration_count += 1
            avg_iteration_time = total_iteration_time / iteration_count

            elapsed = time.time() - start
            if elapsed + avg_iteration_time + 120 >= max_runtime:
                logging.info(
                    f'instance_id={instance_id}, max_runtime={max_runtime} is about to be reached, '
                    f"current_runtime={elapsed:.0f}s, stopping after {count_reviewed} entities"
                )
                break

        # Final summary
        run_time = round(time.time() - start, 3)
        action = "success" if count_failed == 0 else "partial_failure"

        summary_msg = (
            f"Variable delay auto-review completed: {count_reviewed} reviewed, "
            f"{count_updated} updated, {count_skipped} skipped, {count_failed} failed"
        )

        # Register with tenant object summary
        trackme_register_tenant_object_summary(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
            f"splk-{self.component}",
            f"trackme_{self.component}_variable_delay_review_tracker_tenant_{self.tenant_id}",
            "success" if count_failed == 0 else "failure",
            time.time(),
            run_time,
            summary_msg,
            "-5m",
            "now",
        )

        logging.info(
            f"instance_id={instance_id}, {summary_msg}, run_time={run_time}s"
        )

        yield {
            "_time": time.time(),
            "_raw": json.dumps(
                {
                    "action": action,
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "entities_candidates": len(review_candidates),
                    "entities_due_for_review": len(entities_to_review),
                    "entities_reviewed": count_reviewed,
                    "entities_updated": count_updated,
                    "entities_skipped": count_skipped,
                    "entities_failed": count_failed,
                    "updated_entities": updated_entities,
                    "failed_entities": failed_entities,
                    "run_time": run_time,
                    "review_frequency_sec": self.review_frequency_sec,
                    "deviation_threshold_pct": self.deviation_threshold_pct,
                    "method": self.method,
                    "lookback": self.lookback,
                }
            ),
        }


dispatch(VariableDelayReview, sys.argv, sys.stdin, sys.stdout, __name__)
