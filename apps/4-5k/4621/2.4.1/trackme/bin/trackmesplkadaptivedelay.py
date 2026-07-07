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

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_adaptive_delay.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
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

# Pure helpers — moved into a lib in #1717 so importing them no longer
# drags the trackmesplkvariabledelay custom command's module-load
# root-logger rebind into this command's process.
from trackme_libs_variable_delay import compute_threshold, recompute_existing_slot_thresholds

from trackme_libs import (
    trackme_reqinfo,
    trackme_register_tenant_object_summary,
    trackme_vtenant_account,
    trackme_idx_for_tenant,
    run_splunk_search,
    trackme_handler_events,
    trackme_audit_event,
    is_ai_feed_lifecycle_covering,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds


@Configuration(distributed=False)
class AdaptiveDelay(GeneratingCommand):
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
        **Description:** Specify the TrackMe component.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(dsm|dhm)$"),
    )

    min_delay_sec = Option(
        doc="""
        **Syntax:** **min_delay_sec=<integer>****
        **Description:** The minimal delay value for a given entity to be taken into account, expressed in seconds.""",
        require=False,
        default="3600",
        validate=validators.Match("min_hours_delay", r"^\d*$"),
    )

    max_auto_delay_sec = Option(
        doc="""
        **Syntax:** **max_auto_delay_sec=<integer>****
        **Description:** The maximal delay value that the adaptive backend can set, if the automated delay calculation goes beyond it, this value will be used instead to set the delay, expressed in seconds.""",
        require=False,
        default="604800",
        validate=validators.Match("max_auto_delay_sec", r"^\d*$"),
    )

    max_changes_past_7days = Option(
        doc="""
        **Syntax:** **max_changes_past_7days=<integer>****
        **Description:** The maximal number of changes that can be performed in a 7 days time frame, once reached we will not update this entity again until the counter is reset.""",
        require=False,
        default="10",
        validate=validators.Match("max_changes_past_7days", r"^\d*$"),
    )

    min_historical_metrics_days = Option(
        doc="""
        **Syntax:** **min_historical_metrics_days=<integer>****
        **Description:** The minimal number of accumulated days of metrics before we start updating the delay threshold, expressed in days.""",
        require=False,
        default="7",
        validate=validators.Match("min_historical_metrics_days", r"^\d*$"),
    )

    max_sla_percentage = Option(
        doc="""
        **Syntax:** **max_sla_percentage=<integer>****
        **Description:** The maximum SLA percentage for entities, if the SLA percentage is greater than this value, the delay threshold will not be updated to avoid updating highly stable entities.""",
        require=False,
        default="90",
        validate=validators.Match("max_sla_percentage", r"^\d*$"),
    )

    earliest_time_mstats = Option(
        doc="""
        **Syntax:** **earliest_time_mstats=****
        **Description:** The earliest time to use for the mstats search.""",
        require=False,
        default="-30d",
    )

    max_runtime = Option(
        doc="""
        **Syntax:** **max_runtime=****
        **Description:** The max runtime for the job in seconds, defaults to 15 minutes less 120 seconds of margin.""",
        require=False,
        default="900",
        validate=validators.Match("max_runtime", r"^\d*$"),
    )

    review_period_no_days = Option(
        doc="""
        **Syntax:** **review_period_no_days=****
        **Description:** The relative time period for review. When entities were updated, TrackMe will review over time the behaviour and eventually adapt the threshold to take into account new patterns, expressed in number of days, valid options: 7, 15, 30""",
        require=False,
        default="30",
        validate=validators.Match("review_period_no_days", r"^(7|15|30)$"),
    )

    def _entity_passes_adaptive_eligibility(self, item, min_delay_sec):
        """
        Shared eligibility check for the static and variable-delay paths.

        Returns True when the entity is red on delay_threshold_breached, its
        current delay is in the actionable band, the lagging-class override
        is not held, the per-entity opt-in (allow_adaptive_delay) is on, and
        the operator has not pinned the delay threshold (intent lock).
        """

        current_delay = float(item.get("data_last_lag_seen", 0))
        data_override_lagging_class = item.get(
            "data_override_lagging_class", "true"
        )
        allow_adaptive_delay = item.get("allow_adaptive_delay", "true")
        # Threshold intent lock — when the operator has pinned the delay
        # threshold, adaptive delay must never overwrite it. Defence-in-depth:
        # the SPL candidate query already filters these out, this guards the
        # in-memory path too. Missing field defaults to "not locked".
        data_max_delay_allowed_locked = item.get(
            "data_max_delay_allowed_locked", "false"
        )
        anomaly_reason = item.get("anomaly_reason")
        if isinstance(anomaly_reason, str):
            anomaly_reason = anomaly_reason.split("|")
        elif anomaly_reason is None:
            anomaly_reason = []

        return (
            item.get("monitored_state") == "enabled"
            and item.get("object_state") == "red"
            and "delay_threshold_breached" in anomaly_reason
            and current_delay > float(min_delay_sec)
            and current_delay <= float(self.max_auto_delay_sec)
            and data_override_lagging_class != "true"
            and allow_adaptive_delay == "true"
            and str(data_max_delay_allowed_locked).strip().lower() != "true"
        )

    def get_collection_records(self, collection, min_delay_sec):
        """
        Queries and processes records from a collection based on specific criteria.

        :param collection: The collection object to query.
        :param min_delay_sec: Minimum delay seconds for processing.
        :return: Tuple containing collection records and a dictionary of records.

        Variable-delay entities are routed to the parallel honour-existing-slots
        path (see _process_variable_delay_entities) and intentionally skipped here.
        """
        collection_records = []
        collection_records_dict = {}
        count_to_process_list = []

        end = False
        skip_tracker = 0
        while not end:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if process_collection_records:
                for item in process_collection_records:
                    if (
                        self._entity_passes_adaptive_eligibility(item, min_delay_sec)
                        and item.get("variable_delay_policy", "static") != "variable"
                    ):
                        collection_records.append(item)
                        collection_records_dict[item.get("_key")] = {
                            "object": item.get("object"),
                            "current_max_lag_event_sec": item.get(
                                "data_max_delay_allowed"
                            ),
                        }
                        count_to_process_list.append(item.get("object"))
                skip_tracker += len(process_collection_records)
            else:
                end = True

        return collection_records, collection_records_dict, count_to_process_list

    def get_variable_delay_candidates(
        self, main_collection, vd_collection, min_delay_sec
    ):
        """
        Select variable-delay entities eligible for an adaptive review.

        Same eligibility filters as get_collection_records, but selects
        entities with variable_delay_policy="variable" and joins each
        candidate with its variable_delay record (carrying the slot
        configuration). Entities without a matching variable_delay record,
        or with variable_delay_enabled != "true", are skipped — adaptive
        delay should not invent a slot layout where the operator has not
        configured one.

        Returns: list of dicts with keys
            - main_record: the entity's main collection record (for fields
              like object, anomaly_reason)
            - vd_record: the matching variable_delay collection record
            - object: entity name
            - object_key: main collection _key
            - current_slots: parsed slot list from vd_record
            - current_default: int seconds, current default fallback
        """

        candidates = []
        # First sweep: enumerate eligible main-collection entities. Mirrors
        # get_collection_records but with the variable_delay branch.
        eligible_keys = []
        eligible_main = {}
        end = False
        skip_tracker = 0
        while not end:
            batch = main_collection.data.query(skip=skip_tracker)
            if not batch:
                end = True
                continue
            for item in batch:
                if (
                    self._entity_passes_adaptive_eligibility(item, min_delay_sec)
                    and item.get("variable_delay_policy", "static") == "variable"
                ):
                    key = item.get("_key")
                    if key:
                        eligible_keys.append(key)
                        eligible_main[key] = item
            skip_tracker += len(batch)

        if not eligible_keys:
            return []

        # Second sweep: pull the matching variable_delay records. The
        # collection is keyed by main-collection _key, so we query per key
        # in small batches. Per-tenant entity counts are typically modest;
        # a per-key fetch is simpler than building an `$in` query.
        for key in eligible_keys:
            try:
                vd_matches = vd_collection.data.query(query=json.dumps({"_key": key}))
            except Exception as e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object_id="{key}", failed to read variable_delay record, '
                    f'exception="{str(e)}"'
                )
                continue
            if not vd_matches:
                # Orphan — variable_delay_policy=variable on the main record
                # but no record in the variable_delay collection. Nothing to
                # honour; skip rather than fabricate a layout.
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object_id="{key}", variable_delay_policy=variable but no '
                    f'variable_delay record found, skipping'
                )
                continue

            vd_record = vd_matches[0]
            if str(vd_record.get("variable_delay_enabled", "false")).lower() != "true":
                continue

            try:
                slots_payload = json.loads(vd_record.get("variable_delay_slots", "{}"))
            except (ValueError, TypeError):
                slots_payload = {}
            current_slots = slots_payload.get("slots") if isinstance(slots_payload, dict) else None
            if not isinstance(current_slots, list) or not current_slots:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object_id="{key}", variable_delay_slots is empty or invalid, '
                    f'skipping'
                )
                continue

            try:
                current_default = int(float(vd_record.get("variable_delay_default", 3600)))
            except (TypeError, ValueError):
                current_default = 3600

            main_item = eligible_main[key]
            candidates.append(
                {
                    "main_record": main_item,
                    "vd_record": vd_record,
                    "object": main_item.get("object"),
                    "object_key": key,
                    "current_slots": current_slots,
                    "current_default": current_default,
                }
            )

        return candidates

    def _process_variable_delay_entities(
        self, main_collection, metric_index, start_ts, max_runtime_sec
    ):
        """
        Honour-existing-slots adaptive review for variable-delay entities.

        For each eligible candidate, runs a per-(day, hour) percentile query
        scoped to the same lookback/method the operator configured on the
        variable_delay record (defaults: -30d / perc95), then refreshes
        max_delay_allowed per slot using the shared
        recompute_existing_slot_thresholds() helper. Slot names / days /
        hours are never modified.

        Skips entities whose variable_delay record was touched in the last
        24 hours — gives manual edits and prior adaptive updates a settling
        window and avoids back-to-back rewrites if a single cycle fails to
        clear the red state.

        Runs under a runtime budget capped at half of max_runtime_sec so
        the static pipeline that runs after this branch keeps at least
        half the cron window to make progress. Remaining candidates are
        deferred to the next cycle and counted under
        vd_count_skipped_runtime (bugbot R2 on #1611).

        Returns a counter dict for inclusion in the command's yield_results.
        """

        result = {
            "vd_count_candidates": 0,
            "vd_count_skipped_cooldown": 0,
            "vd_count_skipped_no_data": 0,
            "vd_count_skipped_no_change": 0,
            "vd_count_skipped_runtime": 0,
            "vd_count_updated": 0,
            "vd_count_failed": 0,
            "vd_updated_entities": [],
            "vd_failed_entities": [],
        }

        vd_collection_name = (
            f"kv_trackme_{self.component}_variable_delay_tenant_{self.tenant_id}"
        )
        try:
            vd_collection = self.service.kvstore[vd_collection_name]
        except Exception as e:
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'variable_delay collection "{vd_collection_name}" not accessible '
                f'(likely not provisioned for this tenant), skipping variable-delay '
                f'adaptive review, exception="{str(e)}"'
            )
            return result

        candidates = self.get_variable_delay_candidates(
            main_collection, vd_collection, self.min_delay_sec
        )
        result["vd_count_candidates"] = len(candidates)

        if not candidates:
            return result

        now_epoch = time.time()
        max_threshold_sec = int(self.max_auto_delay_sec)
        # 24-hour cool-off — covers both manual edits and previous adaptive
        # updates, so the field semantics stay simple ("any recent change
        # to the slot config wins for 24h").
        cooldown_sec = 24 * 3600

        # Cap the VD branch at half the cron's max_runtime so the static
        # pipeline downstream always has at least the other half. 60s
        # floor avoids starving VD when max_runtime is very short.
        try:
            max_runtime_sec_f = float(max_runtime_sec)
        except (TypeError, ValueError):
            max_runtime_sec_f = 0.0
        vd_budget_sec = max(60.0, max_runtime_sec_f / 2.0) if max_runtime_sec_f > 0 else float("inf")

        for cand in candidates:
            # Per-iteration runtime guard. Checked at the top so a single
            # slow search cannot push us past the budget by very much.
            if vd_budget_sec != float("inf"):
                elapsed_in_run = time.time() - start_ts
                if elapsed_in_run >= vd_budget_sec:
                    remaining_candidates = len(candidates) - (
                        result["vd_count_skipped_cooldown"]
                        + result["vd_count_skipped_no_data"]
                        + result["vd_count_skipped_no_change"]
                        + result["vd_count_updated"]
                        + result["vd_count_failed"]
                    )
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'variable-delay budget {vd_budget_sec:.0f}s reached at '
                        f'{elapsed_in_run:.0f}s elapsed, deferring {remaining_candidates} '
                        f'remaining candidate(s) to the next cycle to preserve runtime '
                        f'for the static pipeline'
                    )
                    result["vd_count_skipped_runtime"] = remaining_candidates
                    break

            obj = cand["object"]
            obj_key = cand["object_key"]
            vd_record = cand["vd_record"]

            try:
                mtime = float(vd_record.get("variable_delay_mtime", 0))
            except (TypeError, ValueError):
                mtime = 0.0
            if mtime > 0 and (now_epoch - mtime) < cooldown_sec:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", variable_delay was modified '
                    f'{int(now_epoch - mtime)}s ago, within 24h cool-off, skipping'
                )
                result["vd_count_skipped_cooldown"] += 1
                continue

            # Reuse the operator's auto-review preferences if present, so a
            # tenant who tuned the periodic reviewer gets the same shape of
            # query here.
            lookback = vd_record.get("variable_delay_auto_review_period") or "-30d"
            method = vd_record.get("variable_delay_auto_review_method") or "perc95"
            if method not in ("perc95", "perc99"):
                method = "perc95"
            stat_func = method
            min_samples = 10

            search_query = remove_leading_spaces(
                f"""
                | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec
                  where index="{metric_index}"
                  tenant_id="{self.tenant_id}"
                  object_category="splk-{self.component}"
                  object="{obj}"
                  earliest="{lookback}" latest="now"
                  by object span=5m
                | eval day_of_week=tonumber(strftime(_time, "%w"))
                | eval day_of_week=if(day_of_week==0, 6, day_of_week-1)
                | eval hour_of_day=tonumber(strftime(_time, "%H"))
                | stats {stat_func}(lag_event_sec) as stat_delay,
                        count as sample_count
                  by object, day_of_week, hour_of_day
                | where sample_count >= {min_samples}
                """
            )
            # count=0 returns all rows. Up to 7*24 = 168 rows are possible;
            # the Splunk default of 100 would silently truncate.
            kwargs_search = {
                "earliest_time": lookback,
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            try:
                reader = run_splunk_search(
                    self.service, search_query, kwargs_search, 24, 5,
                )
                rows = [r for r in reader if isinstance(r, dict)]
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", per-(day,hour) percentile query failed, '
                    f'exception="{str(e)}"'
                )
                result["vd_count_failed"] += 1
                result["vd_failed_entities"].append(obj)
                continue

            # Build hourly thresholds dict using the shared compute_threshold
            # rounding semantics.
            hourly_thresholds = {}
            for row in rows:
                try:
                    day = int(float(row.get("day_of_week", 0)))
                    hour = int(float(row.get("hour_of_day", 0)))
                    stat_delay = float(row.get("stat_delay", 0))
                except (TypeError, ValueError):
                    continue
                threshold = compute_threshold(stat_delay)
                if threshold > max_threshold_sec:
                    threshold = max_threshold_sec
                hourly_thresholds[(day, hour)] = threshold

            if not hourly_thresholds:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", no per-(day,hour) data above min_samples, '
                    f'skipping (no signal to revise slots)'
                )
                result["vd_count_skipped_no_data"] += 1
                continue

            refreshed_slots, new_default = recompute_existing_slot_thresholds(
                cand["current_slots"], hourly_thresholds, max_threshold_sec
            )

            # Detect actual change so we don't pay a KV write + audit event
            # for a no-op (and don't restart the 24h cool-off needlessly).
            cur_by_name = {
                s.get("slot_name"): int(s.get("max_delay_allowed", 0))
                for s in cand["current_slots"]
            }
            has_change = False
            for s in refreshed_slots:
                if int(s.get("max_delay_allowed", 0)) != cur_by_name.get(s.get("slot_name")):
                    has_change = True
                    break
            # Also force a write when the record is not yet stamped "auto",
            # even if every threshold matches — otherwise a record stuck in
            # "manual" mode whose percentiles happen to land on its current
            # values would escape the mode flip and the
            # "all three backends stamp auto" invariant would silently
            # break (bugbot R1 on #1616).
            current_mode = str(vd_record.get("variable_delay_mode", "")).lower()
            mode_needs_update = current_mode != "auto"
            if (
                (not has_change)
                and int(new_default) == cand["current_default"]
                and not mode_needs_update
            ):
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", refreshed thresholds match current values '
                    f'and mode already "auto", no update needed'
                )
                result["vd_count_skipped_no_change"] += 1
                continue

            new_slots_config = {"slots": refreshed_slots}
            try:
                vd_record["variable_delay_slots"] = json.dumps(new_slots_config)
                vd_record["variable_delay_default"] = str(int(new_default))
                # Mark the record as auto-generated. trackmesplkvariabledelay
                # and trackmesplkvariabledelayreview both stamp "auto" on
                # write — without this an adaptive-delay refresh on a
                # record currently in "manual" mode would update the slot
                # thresholds with auto-computed values but leave the mode
                # flag at "manual", so operators / downstream tooling can
                # no longer trust mode as the "auto-generated?" signal.
                vd_record["variable_delay_mode"] = "auto"
                vd_record["variable_delay_mtime"] = str(int(now_epoch))
                vd_record["variable_delay_updated_by"] = "trackmesplkadaptivedelay"
                vd_collection.data.update(str(obj_key), json.dumps(vd_record))
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", failed to update variable_delay record, '
                    f'exception="{str(e)}"'
                )
                result["vd_count_failed"] += 1
                result["vd_failed_entities"].append(obj)
                continue

            # Audit. Distinct change_type from the static path's
            # "automated adaptive delay update" so the recent-activity SPL
            # in get_recent_activity_search does not contaminate the
            # static throttling history.
            try:
                trackme_audit_event(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "trackmesplkadaptivedelay",
                    "success",
                    "variable delay adaptive update",
                    str(obj),
                    f"splk-{self.component}",
                    json.dumps(new_slots_config),
                    (
                        f"Adaptive delay refreshed {len(refreshed_slots)} slot "
                        f"threshold(s) honouring existing layout "
                        f"(method={method}, lookback={lookback}, default={int(new_default)})"
                    ),
                    "adaptive-delay-variable",
                )
            except Exception as e:
                # Non-fatal — KV write is the source of truth; audit is
                # best-effort. Logged so operators can chase audit-index
                # misconfiguration without losing the actual rewrite.
                logging.warning(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object="{obj}", failed to emit audit event, '
                    f'exception="{str(e)}"'
                )

            result["vd_count_updated"] += 1
            result["vd_updated_entities"].append(obj)
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'object="{obj}", variable_delay adaptive review applied, '
                f'updated_slots={len(refreshed_slots)}, new_default={int(new_default)}'
            )

            # Optional Markdown summary note describing the slot-threshold
            # refresh (gated by the per-tenant adaptive_delay_notes toggle).
            # Best-effort and self-contained — must never break the VD review.
            if getattr(self, "adaptive_delay_notes_enabled", 1):
                self._create_variable_delay_note(
                    obj_key,
                    obj,
                    cand["current_slots"],
                    refreshed_slots,
                    cand["current_default"],
                    new_default,
                    method,
                    lookback,
                )

        return result

    def get_recent_activity_item(
        self,
        item,
        collection_records_dict,
        count_to_process_list,
        collection_records,
        object_processed_past30days_threshold_increased,
        object_processed_past30days_threshold_decreased,
        object_processed_past15days_threshold_increased,
        object_processed_past15days_threshold_decreased,
        object_processed_past7days_threshold_increased,
        object_processed_past7days_threshold_decreased,
        object_processed_past24hours_threshold_increased,
        object_processed_past24hours_threshold_decreased,
        object_processed_past4hours_threshold_increased,
        object_processed_past4hours_threshold_decreased,
        object_processed_past4hours,
        object_processed_past24hours,
        object_processed_past7days,
        object_processed_past15days,
        object_processed_past30days,
    ):
        """
        Processes a single item from recent activity results and updates various lists and dictionaries accordingly.

        :param self: The instance of the class where this function is used.
        :param item: A dictionary representing a single record from recent activity results.
        :param object_summary_dict: Dictionary to store summary of objects.
        :param collection_records_dict: Dictionary to store collection records.
        :param count_to_process_list: List to store counts of objects to process.
        :param collection_records: List to store collection records.
        :param object_processed_past30days_threshold_increased: List to store objects processed in the past 30 days with increased threshold.
        :param object_processed_past30days_threshold_decreased: List to store objects processed in the past 30 days with decreased threshold.
        :param object_processed_past15days_threshold_increased: List to store objects processed in the past 15 days with increased threshold.
        :param object_processed_past15days_threshold_decreased: List to store objects processed in the past 15 days with decreased threshold.
        :param object_processed_past7days_threshold_increased: List to store objects processed in the past 7 days with increased threshold.
        :param object_processed_past7days_threshold_decreased: List to store objects processed in the past 7 days with decreased threshold.
        :param object_processed_past24hours_threshold_increased: List to store objects processed in the past 24 hours with increased threshold.
        :param object_processed_past24hours_threshold_decreased: List to store objects processed in the past 24 hours with decreased threshold.
        :param object_processed_past4hours_threshold_increased: List to store objects processed in the past 4 hours with increased threshold.
        :param object_processed_past4hours_threshold_decreased: List to store objects processed in the past 4 hours with decreased threshold.
        :param object_processed_past4hours: List to store objects processed in the past 4 hours.
        :param object_processed_past24hours: List to store objects processed in the past 24 hours.
        :param object_processed_past7days: List to store objects processed in the past 7 days.
        :param object_processed_past15days: List to store objects processed in the past 15 days.
        :param object_processed_past30days: List to store objects processed in the past 30 days.
        """

        object_summary_dict = {}

        # Extracting information from the item
        object_key = item.get("key")
        object_value = item.get("object")
        current_max_lag_event_sec = item.get("current_max_lag_event_sec")
        object_summary_dict["current_max_lag_event_sec"] = current_max_lag_event_sec

        # Processing past 7 days changes
        past7days_changes_count = int(item.get("past7days_changes_count", 0))
        object_summary_dict["past7days_changes_count"] = past7days_changes_count

        # Process past 15 days changes
        past15days_changes_count = int(item.get("past15days_changes_count", 0))
        object_summary_dict["past7days_changes_count"] = past15days_changes_count

        # Process past 30 days changes
        past30days_changes_count = int(item.get("past30days_changes_count", 0))
        object_summary_dict["past7days_changes_count"] = past30days_changes_count

        # Processing status flags
        processed_past30days = item.get("processed_past30days")
        object_summary_dict["processed_past30days"] = processed_past30days

        processed_past15days = item.get("processed_past15days")
        object_summary_dict["processed_past15days"] = processed_past15days

        processed_past7days = item.get("processed_past7days")
        object_summary_dict["processed_past7days"] = processed_past7days

        processed_past24hours = item.get("processed_past24hours")
        object_summary_dict["processed_past24hours"] = processed_past24hours

        processed_past4hours = item.get("processed_past4hours")
        object_summary_dict["processed_past4hours"] = processed_past4hours

        # Processing threshold changes
        increased_past30days = item.get("increased_past30days")
        object_summary_dict["increased_past30days"] = increased_past30days
        decreased_past30days = item.get("decreased_past30days")
        object_summary_dict["decreased_past30days"] = decreased_past30days

        increased_past15days = item.get("increased_past15days")
        object_summary_dict["increased_past15days"] = increased_past15days
        decreased_past15days = item.get("decreased_past15days")
        object_summary_dict["decreased_past15days"] = decreased_past15days

        increased_past7days = item.get("increased_past7days")
        object_summary_dict["increased_past7days"] = increased_past7days
        decreased_past7days = item.get("decreased_past7days")
        object_summary_dict["decreased_past7days"] = decreased_past7days

        increased_past24hours = item.get("increased_past24hours")
        object_summary_dict["increased_past24hours"] = increased_past24hours
        decreased_past24hours = item.get("decreased_past24hours")
        object_summary_dict["decreased_past24hours"] = decreased_past24hours

        increased_past4hours = item.get("increased_past4hours")
        object_summary_dict["increased_past4hours"] = increased_past4hours
        decreased_past4hours = item.get("decreased_past4hours")
        object_summary_dict["decreased_past4hours"] = decreased_past4hours

        # Adding to lists based on conditions

        if increased_past30days == "true":
            object_processed_past30days_threshold_increased.append(object_value)
        if decreased_past30days == "true":
            object_processed_past30days_threshold_decreased.append(object_value)

        if increased_past15days == "true":
            object_processed_past15days_threshold_increased.append(object_value)
        if decreased_past15days == "true":
            object_processed_past15days_threshold_decreased.append(object_value)

        if increased_past7days == "true":
            object_processed_past7days_threshold_increased.append(object_value)
        if decreased_past7days == "true":
            object_processed_past7days_threshold_decreased.append(object_value)

        if increased_past24hours == "true":
            object_processed_past24hours_threshold_increased.append(object_value)
        if decreased_past24hours == "true":
            object_processed_past24hours_threshold_decreased.append(object_value)

        if increased_past4hours == "true":
            object_processed_past4hours_threshold_increased.append(object_value)
        if decreased_past4hours == "true":
            object_processed_past4hours_threshold_decreased.append(object_value)
        if processed_past4hours == "true":
            object_processed_past4hours.append(object_value)

        if processed_past24hours == "true":
            object_processed_past24hours.append(object_value)

        if processed_past30days == "true":
            object_processed_past30days.append(object_value)
            if object_key not in collection_records_dict:
                logging.info(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", recent activity inspection, this object was inspected in the past 30 days, adding for this object for review if conditions are met.'
                )
                collection_records_dict[object_key] = {
                    "object": object_value,
                    "current_max_lag_event_sec": current_max_lag_event_sec,
                }
                count_to_process_list.append(object_value)
                collection_records.append(item)

        if processed_past15days == "true":
            object_processed_past15days.append(object_value)
            if object_key not in collection_records_dict:
                logging.info(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", recent activity inspection, this object was inspected in the past 15 days, adding for this object for review if conditions are met.'
                )
                collection_records_dict[object_key] = {
                    "object": object_value,
                    "current_max_lag_event_sec": current_max_lag_event_sec,
                }
                count_to_process_list.append(object_value)
                collection_records.append(item)

        if processed_past7days == "true":
            object_processed_past7days.append(object_value)
            if object_key not in collection_records_dict:
                logging.info(
                    f'tenant_id="{self.tenant_id}", object="{object_value}", recent activity inspection, this object was inspected in the past 7 days, adding for this object for review if conditions are met.'
                )
                collection_records_dict[object_key] = {
                    "object": object_value,
                    "current_max_lag_event_sec": current_max_lag_event_sec,
                }
                count_to_process_list.append(object_value)
                collection_records.append(item)

        return object_summary_dict

    def get_recent_activity_search(self, tenant_audit_idx):
        """
        Generates a search string to get the recent activity for a given tenant.

        :param tenant_audit_idx: The name of the tenant audit index.
        :return: A string containing the search query.

        """

        search_string = f"""\
            search index={tenant_audit_idx} tenant_id={self.tenant_id} object_category=* "automated adaptive delay update" action="success"
            | table _time, tenant_id, object_category, object, action, change_type, comment
            | sort - 0 _time | trackmeprettyjson fields=comment
            | spath input=comment
            | rename results.adaptive_delay as adaptive_delay, results.current_max_lag_event_sec as updated_max_lag_event_sec

            ``` define the direction of the threshold change ```
            | eval direction=case(
            adaptive_delay>updated_max_lag_event_sec, "increase",
            adaptive_delay<updated_max_lag_event_sec, "decrease",
            1=1, "undetermined"
            )

            ``` get latest ```
            | stats count as past7days_changes_count, max(_time) as mtime, latest(adaptive_delay) as adaptive_delay, latest(updated_max_lag_event_sec) as updated_max_lag_event_sec, latest(direction) as direction, latest(comment) as comment by tenant_id, object_category, object

            ``` lookup KV ```
            | lookup trackme_{self.component}_tenant_{self.tenant_id} object OUTPUT _key as key, monitored_state, allow_adaptive_delay, data_max_delay_allowed as current_max_lag_event_sec

            ``` filter out ```
            | where monitored_state="enabled" AND allow_adaptive_delay="true" AND isnotnull(key) AND isnotnull(current_max_lag_event_sec)

            ``` calculated time of inspection ```
            | eval time_since_inspection=now()-mtime

            ``` define if processed within the past 30 days, 15 days, 7 days, past 24 hours, past 4 hours ```
            | eval processed_past30days=if(time_since_inspection<2592000, "true", "false")
            | eval processed_past15days=if(time_since_inspection<1296000, "true", "false")
            | eval processed_past7days=if(time_since_inspection<604800, "true", "false")
            | eval processed_past24hours=if(time_since_inspection<86400, "true", "false")
            | eval processed_past4hours=if(time_since_inspection<14400, "true", "false")

            ``` define if threshold was increased/decreased in the past 30 days ```
            | eval increased_past30days=if(processed_past30days=="true" AND direction=="increase", "true", "false")
            | eval decreased_past30days=if(processed_past30days=="true" AND direction=="decrease", "true", "false")

            ``` define if threshold was increased/decreased in the past 15 days ```
            | eval increased_past15days=if(processed_past15days=="true" AND direction=="increase", "true", "false")
            | eval decreased_past15days=if(processed_past15days=="true" AND direction=="decrease", "true", "false")

            ``` define if threshold was increased/decreased in the past 7 days ```
            | eval increased_past7days=if(processed_past7days=="true" AND direction=="increase", "true", "false")
            | eval decreased_past7days=if(processed_past7days=="true" AND direction=="decrease", "true", "false")

            ``` define if threshold was increased/decreased in the past 24 hours ```
            | eval increased_past24hours=if(processed_past24hours=="true" AND direction=="increase", "true", "false")
            | eval decreased_past24hours=if(processed_past24hours=="true" AND direction=="decrease", "true", "false")

            ``` define if threshold was increased/decreased in the past 4 hours ```
            | eval increased_past4hours=if(processed_past4hours=="true" AND direction=="increase", "true", "false")
            | eval decreased_past4hours=if(processed_past4hours=="true" AND direction=="decrease", "true", "false")                

            ``` final ```
            | dedup object
            | fields key, object, current_max_lag_event_sec, updated_max_lag_event_sec, adaptive_delay, mtime, time_since_inspection, past30days_changes_count, processed_past30days, past15days_changes_count, processed_past15days, past7days_changes_count, processed_past7days, processed_past24hours, processed_past4hours, increased_past30days, decreased_past30days, increased_past15days, decreased_past15days, increased_past7days, decreased_past7days, increased_past24hours, decreased_past24hours, increased_past4hours, decreased_past4hours, direction, comment
            """

        return search_string

    def get_ml_condidence_search(self, object_name):
        """
        Generates a search string to get the confidence level for a given object.

        :param object_name: The name of the object for which to generate the search string.
        :return: A string containing the search query.
        """

        search_string = f"""\
            | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec where index="{self.tenant_trackme_metric_idx}" tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{object_name}" by object span=1d
            | stats min(_time) as first_time by object
            | eval metrics_duration=now()-first_time
            | eval confidence=if(metrics_duration<({self.min_historical_metrics_days}*86400), "low", "normal")
            | eval metrics_duration=tostring(metrics_duration, "duration")
            | head 1
            """

        return search_string

    def get_sla_percentage_search(self, object_id):
        """
        Generates a search string to get the SLA percentage for a given object.

        :param object_id: The id of the object for which to generate the search string.
        :return: A string containing the search query.
        """

        search_string = f"""\
            | `trackme_get_sla_pct_metrics_per_entity_key({self.tenant_id},splk-{self.component},{object_id})`
            """

        return search_string

    def get_mstats_ml_advanced_search(self, object_name):
        """
        Generates an advanced mstats machine learning search string for a given object.

        :param object_name: The name of the object for which to generate the search string.
        :return: A string containing the advanced mstats ML search query.
        """

        search_string = f"""\
            | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec where index="{self.tenant_trackme_metric_idx}" tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{object_name}" earliest="-30d" latest="now" by object span=5m

            ``` ML calculations for this object ```
            | trackmefit feature="lag_event_sec" by="object" lower_threshold=0.005 upper_threshold=0.005
            ``` trackmefit emits UpperBound directly — use it (numeric-guarded). Do NOT re-parse BoundaryRanges via rex: trackmefit returns it as a single newline-joined string (not the multivalue field MLTK fit DensityFunction produced), so the old rex only captured LowerBound and silently floored UpperBound to 0. ```
            | eval UpperBound = if(isnum(UpperBound), UpperBound, 0)
            | fields _time object lag_event_sec UpperBound

            ``` retain the UpperBound and perform additional calculations ```
            | stats first(UpperBound) as UpperBound, perc95(lag_event_sec) as perc95_lag_event_sec, min(lag_event_sec) as min_lag_event_sec, max(lag_event_sec) as max_lag_event_sec, stdev(lag_event_sec) as stdev_lag_event_sec by object | eval UpperBound=round(UpperBound, 0)
            | foreach *_lag_event_sec [ eval <<FIELD>> = round('<<FIELD>>', 0) ]

            ``` round by the hour, and go at the next hour range ```
            | eval adaptive_delay = (round(UpperBound/3600, 0) * 3600) + 3600, adaptive_delay_duration = tostring(adaptive_delay, "duration")

            ``` rename ```
            | rename LowerBound as LowerBound_30d, UpperBound as UpperBound_30d, perc95_lag_event_sec as perc95_lag_event_sec_30d, min_lag_event_sec as min_lag_event_sec_30d, max_lag_event_sec as max_lag_event_sec_30d, stdev_lag_event_sec as stdev_lag_event_sec_30d, adaptive_delay as adaptive_delay_30d, adaptive_delay_duration as adaptive_delay_duration_30d

            | join type=outer object [
            
                | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec where index="{self.tenant_trackme_metric_idx}" tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{object_name}" earliest="-7d" latest="now" by object span=5m

                ``` ML calculations for this object ```
                | trackmefit feature="lag_event_sec" by="object" lower_threshold=0.005 upper_threshold=0.005
                ``` trackmefit emits UpperBound directly — use it (numeric-guarded). Do NOT re-parse BoundaryRanges via rex: trackmefit returns it as a single newline-joined string (not the multivalue field MLTK fit DensityFunction produced), so the old rex only captured LowerBound and silently floored UpperBound to 0. ```
                | eval UpperBound = if(isnum(UpperBound), UpperBound, 0)
                | fields _time object lag_event_sec UpperBound

                ``` retain the UpperBound and perform additional calculations ```
                | stats first(UpperBound) as UpperBound, perc95(lag_event_sec) as perc95_lag_event_sec, min(lag_event_sec) as min_lag_event_sec, max(lag_event_sec) as max_lag_event_sec, stdev(lag_event_sec) as stdev_lag_event_sec by object | eval UpperBound=round(UpperBound, 0)
                | foreach *_lag_event_sec [ eval <<FIELD>> = round('<<FIELD>>', 0) ]

                ``` round by the hour, and go at the next hour range ```
                | eval adaptive_delay = (round(UpperBound/3600, 0) * 3600) + 3600, adaptive_delay_duration = tostring(adaptive_delay, "duration")

                ``` rename ```
                | rename LowerBound as LowerBound_7d, UpperBound as UpperBound_7d, perc95_lag_event_sec as perc95_lag_event_sec_7d, min_lag_event_sec as min_lag_event_sec_7d, max_lag_event_sec as max_lag_event_sec_7d, stdev_lag_event_sec as stdev_lag_event_sec_7d, adaptive_delay as adaptive_delay_7d, adaptive_delay_duration as adaptive_delay_duration_7d

            ]

            | join type=outer object [
            
                | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec where index="{self.tenant_trackme_metric_idx}" tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{object_name}" earliest="-24h" latest="now" by object span=5m

                ``` ML calculations for this object ```
                | trackmefit feature="lag_event_sec" by="object" lower_threshold=0.005 upper_threshold=0.005
                ``` trackmefit emits UpperBound directly — use it (numeric-guarded). Do NOT re-parse BoundaryRanges via rex: trackmefit returns it as a single newline-joined string (not the multivalue field MLTK fit DensityFunction produced), so the old rex only captured LowerBound and silently floored UpperBound to 0. ```
                | eval UpperBound = if(isnum(UpperBound), UpperBound, 0)
                | fields _time object lag_event_sec UpperBound

                ``` retain the UpperBound and perform additional calculations ```
                | stats first(UpperBound) as UpperBound, perc95(lag_event_sec) as perc95_lag_event_sec, min(lag_event_sec) as min_lag_event_sec, max(lag_event_sec) as max_lag_event_sec, stdev(lag_event_sec) as stdev_lag_event_sec by object | eval UpperBound=round(UpperBound, 0)
                | foreach *_lag_event_sec [ eval <<FIELD>> = round('<<FIELD>>', 0) ]

                ``` round by the hour, and go at the next hour range ```
                | eval adaptive_delay = (round(UpperBound/3600, 0) * 3600) + 3600, adaptive_delay_duration = tostring(adaptive_delay, "duration")

                ``` rename ```
                | rename LowerBound as LowerBound_24h, UpperBound as UpperBound_24h, perc95_lag_event_sec as perc95_lag_event_sec_24h, min_lag_event_sec as min_lag_event_sec_24h, max_lag_event_sec as max_lag_event_sec_24h, stdev_lag_event_sec as stdev_lag_event_sec_24h, adaptive_delay as adaptive_delay_24h, adaptive_delay_duration as adaptive_delay_duration_24h

            ]

            ``` aggregate the UpperBound, if for any reason one the UpperBound is not returned as expected, we will use the 7d value ```
            | eval UpperBound=case(
            isnum(UpperBound_30d) AND isnum(UpperBound_7d) AND isnum(UpperBound_24h), round((UpperBound_30d+UpperBound_7d+UpperBound_24h)/3, 2),
            1=1, UpperBound_7d
            )
            | eval adaptive_delay = (round(UpperBound/3600, 0) * 3600) + 3600, adaptive_delay_duration = tostring(adaptive_delay, "duration")

            ``` only consider results with a valid numerical adaptive_delay ```
            | where isnum(adaptive_delay)            
        """

        return search_string

    def get_mstats_ml_simple_search(self, object_name):
        """
        Generates a simple mstats machine learning search string for a given object.

        :param object_name: The name of the object for which to generate the search string.
        :return: A string containing the simple mstats ML search query.
        """

        search_string = f"""\
            | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec where index="{self.tenant_trackme_metric_idx}" tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{object_name}" by object span=5m

            ``` ML calculations for this object ```
            | trackmefit feature="lag_event_sec" by="object" lower_threshold=0.005 upper_threshold=0.005
            ``` trackmefit emits UpperBound directly — use it (numeric-guarded). Do NOT re-parse BoundaryRanges via rex: trackmefit returns it as a single newline-joined string (not the multivalue field MLTK fit DensityFunction produced), so the old rex only captured LowerBound and silently floored UpperBound to 0. ```
            | eval UpperBound = if(isnum(UpperBound), UpperBound, 0)
            | fields _time object lag_event_sec UpperBound

            ``` retain the UpperBound and perform additional calculations ```
            | stats first(UpperBound) as UpperBound, perc95(lag_event_sec) as perc95_lag_event_sec, min(lag_event_sec) as min_lag_event_sec, max(lag_event_sec) as max_lag_event_sec, stdev(lag_event_sec) as stdev_lag_event_sec by object | eval UpperBound=round(UpperBound, 0)
            | foreach *_lag_event_sec [ eval <<FIELD>> = round('<<FIELD>>', 0) ]

            ``` round by the hour, and go at the next hour range ```
            | eval adaptive_delay = (round(UpperBound/3600, 0) * 3600) + 3600, adaptive_delay_duration = tostring(adaptive_delay, "duration")

            ``` only consider results with a valid numerical adaptive_delay ```
            | where isnum(adaptive_delay)
        """

        return search_string

    def construct_url_for_lag_policy_update(self):
        """
        Constructs the URL for updating the lag policy based on the component.
        :return: URL string.
        """
        if self.component == "dsm":
            return (
                "%s/services/trackme/v2/splk_dsm/write/ds_update_lag_policy"
                % self._metadata.searchinfo.splunkd_uri
            )
        elif self.component == "dhm":
            return (
                "%s/services/trackme/v2/splk_dhm/write/dh_update_lag_policy"
                % self._metadata.searchinfo.splunkd_uri
            )
        else:
            # Handle other components or raise an error
            raise ValueError("Invalid component type")

    @staticmethod
    def _safe_float(value, default=None):
        """Best-effort float coercion for values that may arrive as strings
        from Splunk search results (or be missing entirely)."""
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (ValueError, TypeError):
            return default

    @classmethod
    def _format_duration(cls, seconds):
        """Format a number of seconds into a compact human-readable duration
        such as "45m", "1h 15m" or "2h". Returns "n/a" when the value cannot
        be coerced to a number."""
        secs = cls._safe_float(seconds)
        if secs is None:
            return "n/a"
        secs = int(round(secs))
        if secs <= 0:
            return "0s"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, sec = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if sec and not days and not hours:
            # only surface seconds for sub-hour durations to keep it compact
            parts.append(f"{sec}s")
        return " ".join(parts) if parts else "0s"

    def _build_adaptive_delay_note_markdown(
        self, entity_dict, direction, old_sec, new_sec, was_capped
    ):
        """Compose the Markdown body of the automated adaptive-delay summary
        note. Tolerant of both the advanced (30d/7d/24h windows) and the
        simple (single window) ML result shapes."""

        entity_name = entity_dict.get("object", "")
        arrow = "▲ increased" if direction == "increase" else "▼ decreased"

        lines = []
        lines.append(f"### 🤖 Automated adaptive delay update — threshold {arrow}")
        lines.append("")
        lines.append(
            f"_Generated automatically by the TrackMe adaptive delay framework "
            f"(`trackme_{self.component}_adaptive_delay_tracker`)._"
        )
        lines.append("")
        lines.append(
            f"The delay threshold for **{entity_name}** was **{direction}d** from "
            f"**{self._format_duration(old_sec)}** "
            f"(`{int(round(self._safe_float(old_sec, 0)))}s`) to "
            f"**{self._format_duration(new_sec)}** "
            f"(`{int(round(self._safe_float(new_sec, 0)))}s`)."
        )
        lines.append("")

        # Summary reason
        if direction == "increase":
            reason = (
                "Recent observed lag behaviour exceeded the current threshold. "
                "The threshold was raised so the entity stays green under normal "
                "conditions while still catching genuine delays."
            )
        else:
            reason = (
                "Recent observed lag behaviour was comfortably below the current "
                "threshold. The threshold was lowered so genuine delays are "
                "detected sooner, without generating false positives."
            )
        lines.append(f"**Summary reason:** {reason}")
        lines.append("")

        # Key reasoning table — prefer the advanced per-window shape, fall back
        # to the simple single-window shape.
        has_windows = any(
            f"perc95_lag_event_sec_{w}" in entity_dict for w in ("30d", "7d", "24h")
        )
        lines.append("**Key reasoning**")
        lines.append("")
        if has_windows:
            lines.append(
                "| Window | p95 lag | max lag | stdev | density upper bound |"
            )
            lines.append("|---|---|---|---|---|")
            for w, label in (("30d", "30 days"), ("7d", "7 days"), ("24h", "24 hours")):
                p95 = entity_dict.get(f"perc95_lag_event_sec_{w}")
                mx = entity_dict.get(f"max_lag_event_sec_{w}")
                sd = entity_dict.get(f"stdev_lag_event_sec_{w}")
                ub = entity_dict.get(f"UpperBound_{w}")
                if p95 is None and mx is None and ub is None:
                    continue
                lines.append(
                    f"| {label} | {self._format_duration(p95)} | "
                    f"{self._format_duration(mx)} | {self._format_duration(sd)} | "
                    f"{self._format_duration(ub)} |"
                )
        else:
            lines.append("| Metric | Value |")
            lines.append("|---|---|")
            lines.append(
                f"| p95 lag | {self._format_duration(entity_dict.get('perc95_lag_event_sec'))} |"
            )
            lines.append(
                f"| max lag | {self._format_duration(entity_dict.get('max_lag_event_sec'))} |"
            )
            lines.append(
                f"| stdev | {self._format_duration(entity_dict.get('stdev_lag_event_sec'))} |"
            )
            lines.append(
                f"| density upper bound | {self._format_duration(entity_dict.get('UpperBound'))} |"
            )
        lines.append("")

        # Decision detail — wording matches the ML result shape (advanced
        # aggregates 30d/7d/24h upper bounds; simple uses a single window).
        if has_windows:
            lines.append(
                "- New threshold derived from the aggregated density-function "
                "upper bound across the 30d/7d/24h windows, rounded up to the "
                "next hour with a +1h safety buffer."
            )
        else:
            lines.append(
                "- New threshold derived from the single-window density-function "
                "upper bound, rounded up to the next hour with a +1h safety buffer."
            )
        if was_capped:
            lines.append(
                f"- The computed value exceeded the configured maximum auto delay "
                f"(`max_auto_delay_sec={self.max_auto_delay_sec}s`); the threshold "
                f"was capped at the maximum allowed."
            )
        lines.append(
            "- ML confidence was **normal** (the framework requires sufficient "
            "historical metrics before changing any threshold)."
        )
        lines.append("")
        lines.append(
            "_The adaptive delay framework re-evaluates eligible entities on a "
            "schedule and only updates a threshold when the change is material and "
            "within the configured guardrails._"
        )

        return "\n".join(lines)

    def _create_adaptive_delay_note(
        self, object_id, entity_dict, old_sec, new_sec, was_capped
    ):
        """Best-effort creation of a Markdown summary note on the entity that
        was just updated by the adaptive delay framework. Never raises — a
        failure here must not break the threshold update flow."""

        try:
            old_f = self._safe_float(old_sec)
            new_f = self._safe_float(new_sec)
            if old_f is None or new_f is None or old_f == new_f:
                # Nothing meaningful to describe — should not happen on the
                # update path (equal values return earlier) but guard anyway.
                return

            direction = "increase" if new_f > old_f else "decrease"

            note_md = self._build_adaptive_delay_note_markdown(
                entity_dict, direction, old_f, new_f, was_capped
            )

            collection_name = f"kv_trackme_notes_tenant_{self.tenant_id}"
            collection = self.service.kvstore[collection_name]
            note_record = {
                "object_id": object_id,
                "note": note_md,
                "created_by": "trackmesplkadaptivedelay",
                "mtime": time.time(),
            }
            collection.data.insert(json.dumps(note_record))

            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'object="{entity_dict.get("object")}", object_id="{object_id}", '
                f'adaptive delay summary note created (direction="{direction}").'
            )

            # Best-effort audit event so the note shows up in the per-entity
            # Audit changes tab — must not break the update flow.
            #
            # CRITICAL — collision avoidance: get_recent_activity_search()
            # drives the throttling history with a FULL-TEXT match on the
            # literal phrase "automated adaptive delay update" + action="success".
            # This "create note" event MUST NOT contain that phrase anywhere in
            # its _raw, or it would be counted as a second threshold change and
            # corrupt the change counters / direction history. So we deliberately:
            #   - keep change_type="create note" (distinct from the threshold update),
            #   - use a comment/result without the phrase, and
            #   - pass a minimal object_attrs descriptor instead of note_record
            #     (the note Markdown title itself contains the phrase).
            try:
                trackme_audit_event(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "trackmesplkadaptivedelay",
                    "success",
                    "create note",
                    entity_dict.get("object"),
                    f"splk-{self.component}",
                    {
                        "object_id": object_id,
                        "direction": direction,
                        "created_by": "trackmesplkadaptivedelay",
                    },
                    "Note created successfully",
                    f"adaptive delay summary note ({direction})",
                    object_id=object_id,
                )
            except Exception as audit_e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object_id="{object_id}", failed to emit audit event for '
                    f'adaptive delay note, exception="{str(audit_e)}"'
                )

        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'object_id="{object_id}", failed to create adaptive delay summary '
                f'note, exception="{str(e)}"'
            )

    @staticmethod
    def _format_days(days):
        """Format a variable-delay slot's day list (ints 0=Mon … 6=Sun) into a
        compact human label, compressing contiguous runs (e.g. "Mon–Fri",
        "Sat, Sun"). Returns "n/a" on missing/garbage input."""
        names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        try:
            ints = sorted({int(d) for d in days if 0 <= int(d) <= 6})
        except (TypeError, ValueError):
            return "n/a"
        if not ints:
            return "n/a"
        runs = []
        start = prev = ints[0]
        for d in ints[1:]:
            if d == prev + 1:
                prev = d
            else:
                runs.append((start, prev))
                start = prev = d
        runs.append((start, prev))
        return ", ".join(
            names[a] if a == b else f"{names[a]}–{names[b]}" for a, b in runs
        )

    @staticmethod
    def _format_hours(hours):
        """Format a variable-delay slot's hour list (ints 0–23) into compact
        ranges (e.g. "08–19", "20–23, 00–07"). Returns "n/a" on bad input."""
        try:
            ints = sorted({int(h) for h in hours if 0 <= int(h) <= 23})
        except (TypeError, ValueError):
            return "n/a"
        if not ints:
            return "n/a"
        runs = []
        start = prev = ints[0]
        for h in ints[1:]:
            if h == prev + 1:
                prev = h
            else:
                runs.append((start, prev))
                start = prev = h
        runs.append((start, prev))
        return ", ".join(
            f"{a:02d}" if a == b else f"{a:02d}–{b:02d}" for a, b in runs
        )

    def _build_variable_delay_note_markdown(
        self, object_name, current_slots, refreshed_slots, current_default,
        new_default, method, lookback
    ):
        """Compose the Markdown body of the automated variable-delay summary
        note. Unlike the static path (a single increase/decrease), this
        describes the per-slot threshold refresh while the slot layout
        (names / days / hours) is preserved."""

        prev_by_name = {}
        for s in current_slots or []:
            if isinstance(s, dict):
                prev_by_name[s.get("slot_name")] = s.get("max_delay_allowed")

        changed = 0
        rows = []
        for s in refreshed_slots or []:
            if not isinstance(s, dict):
                continue
            name = s.get("slot_name")
            new_v = s.get("max_delay_allowed")
            prev_v = prev_by_name.get(name)
            if self._safe_float(prev_v) != self._safe_float(new_v):
                changed += 1
            marker = " ✱" if self._safe_float(prev_v) != self._safe_float(new_v) else ""
            rows.append(
                f"| {name}{marker} | {self._format_days(s.get('days', []))} "
                f"@ {self._format_hours(s.get('hours', []))} | "
                f"{self._format_duration(prev_v)} | {self._format_duration(new_v)} |"
            )

        lines = []
        lines.append(
            "### 🤖 Automated adaptive delay update — variable-delay slots refreshed"
        )
        lines.append("")
        lines.append(
            f"_Generated automatically by the TrackMe adaptive delay framework "
            f"(`trackme_{self.component}_adaptive_delay_tracker`)._"
        )
        lines.append("")
        lines.append(
            f"The time-based delay thresholds for **{object_name}** were refreshed "
            f"from observed behaviour. The slot **layout** (names, days, hours) is "
            f"unchanged — only the per-slot delay thresholds were recomputed "
            f"({changed} of {len(rows)} slot(s) changed)."
        )
        lines.append("")
        lines.append(
            f"**Summary reason:** each slot threshold was recomputed from the "
            f"**{method}** of historical lag over **{lookback}**, rounded up to the "
            f"next hour with a +1h buffer (capped at the configured maximum auto "
            f"delay), so each time window stays green under normal conditions while "
            f"still catching genuine delays."
        )
        lines.append("")
        lines.append("**Slot thresholds** (✱ = changed this cycle)")
        lines.append("")
        lines.append("| Slot | When (days @ hours) | Previous | New |")
        lines.append("|---|---|---|---|")
        lines.extend(rows)
        lines.append("")
        lines.append(
            f"- Default (fallback) threshold: **{self._format_duration(current_default)}** "
            f"→ **{self._format_duration(new_default)}**"
        )
        lines.append(
            f"- Review window: **{lookback}**, method **{method}**, minimum 10 "
            f"samples per (day, hour) cell."
        )
        lines.append("")
        lines.append(
            "_The adaptive delay framework re-evaluates eligible entities on a "
            "schedule and only updates a slot when the change is material and "
            "within the configured guardrails._"
        )
        return "\n".join(lines)

    def _create_variable_delay_note(
        self, object_id, object_name, current_slots, refreshed_slots,
        current_default, new_default, method, lookback
    ):
        """Best-effort Markdown summary note for a variable-delay slot refresh.
        Never raises — a failure here must not break the VD review flow."""

        try:
            note_md = self._build_variable_delay_note_markdown(
                object_name, current_slots, refreshed_slots, current_default,
                new_default, method, lookback
            )

            collection_name = f"kv_trackme_notes_tenant_{self.tenant_id}"
            collection = self.service.kvstore[collection_name]
            note_record = {
                "object_id": object_id,
                "note": note_md,
                "created_by": "trackmesplkadaptivedelay",
                "mtime": time.time(),
            }
            collection.data.insert(json.dumps(note_record))

            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'object="{object_name}", object_id="{object_id}", '
                f"variable-delay adaptive summary note created."
            )

            # Best-effort, collision-safe audit event (see _create_adaptive_delay_note
            # for the full-text-search rationale): change_type="create note",
            # minimal object_attrs, phrase-free comment/result.
            try:
                trackme_audit_event(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "trackmesplkadaptivedelay",
                    "success",
                    "create note",
                    object_name,
                    f"splk-{self.component}",
                    {
                        "object_id": object_id,
                        "kind": "variable_delay",
                        "created_by": "trackmesplkadaptivedelay",
                    },
                    "Note created successfully",
                    "adaptive delay summary note (variable delay)",
                    object_id=object_id,
                )
            except Exception as audit_e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'object_id="{object_id}", failed to emit audit event for '
                    f'variable-delay note, exception="{str(audit_e)}"'
                )

        except Exception as e:
            logging.warning(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'object_id="{object_id}", failed to create variable-delay summary '
                f'note, exception="{str(e)}"'
            )

    def run_post_api_call(
        self,
        object_id,
        entity_dict,
        header,
        max_auto_delay_sec,
        count_updated,
        count_failed,
        count_updated_list,
        count_updated_msg_list,
        count_failed_list,
        count_processed,
        count_processed_list,
        count_processed_msg_list,
        count_failed_msg_list,
    ):
        """
        Runs a POST API call to update the lag policy for a given entity.

        :param object_id: The entity key (used for the optional summary note).
        :param entity_dict: Dictionary containing the entity details.
        :param header: Authorization header for the request.
        :param max_auto_delay_sec: Maximum allowed delay for checks.
        :param count_updated: Counter for successful updates.
        :param count_failed: Counter for failed updates.
        :param count_updated_list: List to keep track of updated entities.
        :param count_updated_msg_list: List to keep track of updated messages.
        :param count_failed_list: List to keep track of failed entities.
        :param count_processed: Counter for processed entities.
        :param count_processed_list: List to keep track of processed entities.
        :param count_processed_msg_list: List to keep track of processed messages.
        :param count_failed_msg_list: List to keep track of failure messages.
        :return: Updated counters and lists.
        """
        entity_name = entity_dict.get("object")
        adaptive_delay = float(entity_dict.get("adaptive_delay"))
        current_max_lag_event_sec = float(entity_dict.get("current_max_lag_event_sec"))

        # Track whether the computed value had to be capped at the configured
        # maximum (surfaced in the summary note for transparency).
        was_capped = False

        # Proceed only if adaptive_delay != current_max_lag_event_sec
        if adaptive_delay == current_max_lag_event_sec:
            log_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_name}", adaptive_delay="{adaptive_delay}", current_max_lag_event_sec="{current_max_lag_event_sec}", no need to update the lag policy as it already defined to the target value'
            logging.info(log_msg)
            count_processed += 1
            count_processed_list.append(entity_name)
            count_processed_msg_list.append(log_msg)
            return (
                count_updated,
                count_failed,
                count_updated_list,
                count_updated_msg_list,
                count_failed_list,
                count_processed,
                count_processed_list,
                count_processed_msg_list,
                count_failed_msg_list,
            )

        # If the adaptive_delay is bigger than the max_auto_delay_sec, the adaptive_delay will be set to the max_auto_delay_sec
        elif adaptive_delay > int(max_auto_delay_sec):
            log_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_name}", adaptive_delay="{adaptive_delay}", current_max_lag_event_sec="{current_max_lag_event_sec}", max_auto_delay_sec={max_auto_delay_sec} has been reached while performing the delay calculation, will be applying the max allowed delay instead.'
            logging.info(log_msg)
            adaptive_delay = int(max_auto_delay_sec)
            was_capped = True

        # Construct URL based on component
        url = self.construct_url_for_lag_policy_update()

        # Prepare data for the POST request
        update_comment_json = {
            "context": "automated adaptive delay update",
            "results": entity_dict,
        }
        data = {
            "tenant_id": self.tenant_id,
            "object_list": entity_name,
            "data_max_delay_allowed": adaptive_delay,
            "update_comment": json.dumps(update_comment_json, indent=0),
        }

        # Make the POST request and handle response
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": header,
                    "Content-Type": "application/json",
                },
                data=json.dumps(data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                log_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_name}", updating lag policy has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(log_msg)
                count_failed += 1
                count_failed_list.append(entity_name)
                count_failed_msg_list.append(log_msg)
            else:
                log_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_name}", lag policy updated successfully, adaptive_delay="{adaptive_delay}", response.status_code="{response.status_code}"'
                logging.info(log_msg)
                count_processed += 1
                count_processed_list.append(entity_name)
                count_processed_msg_list.append(log_msg)
                count_updated += 1
                count_updated_list.append(entity_name)
                count_updated_msg_list.append(log_msg)

                # Optionally add a Markdown summary note on the entity that
                # describes the change and its key reasoning. Best-effort and
                # gated by the per-tenant adaptive_delay_notes toggle.
                if getattr(self, "adaptive_delay_notes_enabled", 1):
                    self._create_adaptive_delay_note(
                        object_id,
                        entity_dict,
                        current_max_lag_event_sec,
                        adaptive_delay,
                        was_capped,
                    )
        except Exception as e:
            log_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_name}", updating lag policy has failed, exception="{str(e)}"'
            logging.error(log_msg)
            count_failed += 1
            count_failed_list.append(entity_name)
            count_failed_msg_list.append(log_msg)

        return (
            count_updated,
            count_failed,
            count_updated_list,
            count_updated_msg_list,
            count_failed_list,
            count_processed,
            count_processed_list,
            count_processed_msg_list,
            count_failed_msg_list,
        )

    def call_component_register(self, action_result, action_message, run_time):
        """
        Call the component register function

        :param action_result: The result of the action, success or failure
        :param action_message: The message to be displayed in the action
        :param run_time: The time it took to run the action

        :return: None
        """

        trackme_register_tenant_object_summary(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
            f"splk-{self.component}",
            f"trackme_{self.component}_adaptive_delay_tracker_tenant_{self.tenant_id}",
            action_result,
            time.time(),
            run_time,
            action_message,
            "-5m",
            "now",
        )

    def generate(self, **kwargs):
        if self:

            # Track execution times
            execution_times = []
            average_execution_time = 0

            # performance counter
            start = time.time()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", trackmesplkadaptivedelay is starting now.'
            )

            # max runtime
            max_runtime = int(self.max_runtime)

            # Retrieve the search cron schedule
            savedsearch_name = f"trackme_{self.component}_adaptive_delay_tracker_tenant_{self.tenant_id}"
            savedsearch = self.service.saved_searches[savedsearch_name]
            savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

            # get the cron_exec_sequence_sec
            try:
                cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", failed to convert the cron schedule to seconds, error="{str(e)}"'
                )
                cron_exec_sequence_sec = max_runtime

            # the max_runtime cannot be bigger than the cron_exec_sequence_sec
            if max_runtime > cron_exec_sequence_sec:
                max_runtime = cron_exec_sequence_sec

            logging.info(
                f'max_runtime="{max_runtime}",  savedsearch_name="{savedsearch_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
            )

            # Get tenant indexes
            tenant_indexes = trackme_idx_for_tenant(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
            )
            tenant_audit_idx = tenant_indexes.get("trackme_audit_idx", "trackme_audit")
            self.tenant_trackme_metric_idx = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # Get the vtenant account
            vtenant_account = trackme_vtenant_account(
                session_key, self._metadata.searchinfo.splunkd_uri, self.tenant_id
            )
            adaptive_delay_enabled = int(vtenant_account.get("adaptive_delay", 1))

            # Whether to write a Markdown summary note on each entity whose
            # threshold the framework updates (per-tenant, default enabled).
            try:
                self.adaptive_delay_notes_enabled = int(
                    vtenant_account.get("adaptive_delay_notes", 1)
                )
            except (ValueError, TypeError):
                self.adaptive_delay_notes_enabled = 1

            # if adaptive_delay_enabled is not enabled, we will skip the execution, log the information and exit immediately
            if adaptive_delay_enabled == 0:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", adaptive_delay is disabled for this tenant, skipping execution'
                )
                yield_results = {
                    "action": "success",
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "msg": "adaptive_delay is disabled for this tenant, skipping execution",
                }

                yield {
                    "_time": time.time(),
                    "_raw": yield_results,
                }
                return

            # Mutex with the AI Feed Lifecycle Advisor.
            #
            # When the AI Feed Lifecycle Advisor (under the Components
            # Advisor umbrella) covers this component on this tenant, AI
            # is the authority for delay management — legacy mechanical
            # Adaptive Delay must stand down. The save-time hook in
            # ``trackme_rh_vtenants_handler.py`` flips ``adaptive_delay``
            # to 0 whenever the AI advisor is turned on, so under normal
            # operation we never reach this point with both flags set.
            # This block is defence-in-depth — it catches drift from
            # direct KV pokes or any API path that bypasses the UCC
            # hook. The Configuration Guardian check
            # ``ai_feed_lifecycle_delay_conflict`` raises a warning on
            # the same drift so the admin sees the inconsistency in the
            # UI within one health-tracker cycle.
            if is_ai_feed_lifecycle_covering(vtenant_account, self.component):
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'skipping execution because AI Feed Lifecycle Advisor covers '
                    f'this component (ai_components_advisor_enabled=1 + '
                    f'"{self.component}" in ai_components_advisor_list). '
                    f'Persisted state of adaptive_delay=1 is inconsistent — see '
                    f'Configuration Guardian alert ai_feed_lifecycle_delay_conflict.'
                )
                # Audit the runtime override — best-effort, must not break
                # the no-op return path on audit-index misconfiguration.
                try:
                    trackme_audit_event(
                        session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "trackmesplkadaptivedelay",
                        "skipped",
                        "adaptive_delay_runtime_gate",
                        f"adaptive_delay_tracker_tenant_{self.tenant_id}",
                        f"splk-{self.component}",
                        "{}",
                        "success",
                        (
                            "Adaptive Delay short-circuited at runtime because the AI "
                            "Feed Lifecycle Advisor covers this component. Persisted "
                            "adaptive_delay=1 is inconsistent — disable adaptive_delay "
                            "or remove this component from ai_components_advisor_list."
                        ),
                    )
                except Exception as e:
                    logging.warning(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", '
                        f'failed to emit audit event for adaptive_delay_runtime_gate, '
                        f'exception="{str(e)}"'
                    )
                yield_results = {
                    "action": "success",
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "msg": (
                        "adaptive_delay skipped — AI Feed Lifecycle Advisor "
                        "covers this component"
                    ),
                }
                yield {
                    "_time": time.time(),
                    "_raw": yield_results,
                }
                return

            # Add the session_key to the reqinfo
            reqinfo["session_key"] = session_key

            # Splunk header
            header = f"Splunk {session_key}"

            # Data collection
            collection_name = f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
            collection = self.service.kvstore[collection_name]

            # get all records
            (
                collection_records,
                collection_records_dict,
                count_to_process_list,
            ) = self.get_collection_records(collection, self.min_delay_sec)
            logging.debug(
                f'retrieving records to be processed, collection_records="{json.dumps(collection_records, indent=2)}"'
            )

            # Variable-delay branch: runs every cycle, independent of the
            # static path's outcome. Catches its own exceptions so a failure
            # here can never block the static review (or vice versa). The
            # branch enforces its own runtime budget (capped at half of
            # max_runtime) so a large set of variable-delay candidates
            # cannot starve the static pipeline that runs afterwards
            # (bugbot R2 on #1611).
            try:
                vd_result = self._process_variable_delay_entities(
                    collection,
                    self.tenant_trackme_metric_idx,
                    start,
                    max_runtime,
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", '
                    f'variable-delay adaptive review failed, exception="{str(e)}"'
                )
                vd_result = {
                    "vd_count_candidates": 0,
                    "vd_count_skipped_cooldown": 0,
                    "vd_count_skipped_no_data": 0,
                    "vd_count_skipped_no_change": 0,
                    "vd_count_skipped_runtime": 0,
                    "vd_count_updated": 0,
                    "vd_count_failed": 0,
                    "vd_updated_entities": [],
                    "vd_failed_entities": [],
                    "vd_error": str(e),
                }
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", '
                f'variable-delay adaptive review summary={json.dumps(vd_result)}'
            )

            """
            Logic description:
            - First, we select entities that are monitored, red, have breached the delay threshold and have a current delay bigger than the min_delay_sec
            - Variable-delay entities (variable_delay_policy=variable) are routed to the parallel honour-existing-slots path (_process_variable_delay_entities); they no longer block on the static ML pipeline
            - We exclude entities that have data_override_lagging_class=true or allow_adaptive_delay!=true
            - We then exclude entities that have been processed in the past 24 hours
            - We process to a ML confidence inspection, if the confidence is low, we will skip the entity, if the entity has been processed in the past 24 hours, we will skip the entity
            - If the entity has been processed in the past 7 days, we will run the ML search with a restricted time range of 7 days to review if the behaviour has changed
            """

            # A list to store object processed in the past 30 days prior to -1d
            object_processed_past30days = []

            # A list to store object processed in the past 15 days prior to -1d
            object_processed_past15days = []

            # A list to store object processed in the past 7 days prior to -1d
            object_processed_past7days = []

            # A list to store object processed in the past 24 hours
            object_processed_past24hours = []

            # A list to store object processed in the past 4 hours
            object_processed_past4hours = []

            # A list to store object processed in the past 15 days and where the threshold was increased
            object_processed_past15days_threshold_increased = []

            # A list to store object processed in the past 15 days and where the threshold was decreased
            object_processed_past15days_threshold_decreased = []

            # A list to store object processed in the past 30 days and where the threshold was increased
            object_processed_past30days_threshold_increased = []

            # A list to store object processed in the past 30 days and where the threshold was decreased
            object_processed_past30days_threshold_decreased = []

            # A list to store object processed in the past 7 days and where the threshold was increased
            object_processed_past7days_threshold_increased = []

            # A list to store object processed in the past 7 days and where the threshold was decreased
            object_processed_past7days_threshold_decreased = []

            # A list to store object processed in the past 24 hours and where the threshold was increased
            object_processed_past24hours_threshold_increased = []

            # A list to store object processed in the past 24 hours and where the threshold was decreased
            object_processed_past24hours_threshold_decreased = []

            # A list to store object processed in the past 4 hours and where the threshold was increased
            object_processed_past4hours_threshold_increased = []

            # A list to store object processed in the past 4 hours and where the threshold was decreased
            object_processed_past4hours_threshold_decreased = []

            # An integer counter of the number of changes performed during the past 7 days for each object
            past7days_changes_count = 0

            # An object summary dict
            object_summary_dict = {}

            #
            # 0. Check in our logs, identify entities we have recently managed to verify if the status has changed and should be updated
            # - entities processed in the last past 24 hours are added to a special list for further exclusion
            # - entities processed in the last past 7 days are added to a special list for review processing
            # - entities processed in the last past 15 days are added to a special list for review processing
            # - entities processed in the last past 30 days are added to a special list for review processing
            #

            # kwargs
            kwargs_recent_activity = {
                "earliest_time": "-31d",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # conditionally add the earliest_time
            if int(self.review_period_no_days) == 7:
                kwargs_recent_activity["earliest_time"] = "-8d"
            elif int(self.review_period_no_days) == 15:
                kwargs_recent_activity["earliest_time"] = "-16d"
            elif int(self.review_period_no_days) == 30:
                kwargs_recent_activity["earliest_time"] = "-31d"

            recent_activity_search = remove_leading_spaces(
                self.get_recent_activity_search(tenant_audit_idx)
            )
            # log
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", recent activity inspection, recent_activity_search="{recent_activity_search}", kwargs="{json.dumps(kwargs_recent_activity, indent=0)}"'
            )

            try:
                search_start = time.time()
                reader = run_splunk_search(
                    self.service,
                    recent_activity_search,
                    kwargs_recent_activity,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        object_summary_dict = self.get_recent_activity_item(
                            item,
                            collection_records_dict,
                            count_to_process_list,
                            collection_records,
                            object_processed_past30days_threshold_increased,
                            object_processed_past30days_threshold_decreased,
                            object_processed_past15days_threshold_increased,
                            object_processed_past15days_threshold_decreased,
                            object_processed_past7days_threshold_increased,
                            object_processed_past7days_threshold_decreased,
                            object_processed_past24hours_threshold_increased,
                            object_processed_past24hours_threshold_decreased,
                            object_processed_past4hours_threshold_increased,
                            object_processed_past4hours_threshold_decreased,
                            object_processed_past4hours,
                            object_processed_past24hours,
                            object_processed_past7days,
                            object_processed_past15days,
                            object_processed_past30days,
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", Processing results from recent_activity_results, result="{json.dumps(item, indent=2)}"'
                        )

            except Exception as e:
                logging.error(f"Failed to execute Splunk search with error: {str(e)}")
                msg = f'tenant_id="{self.tenant_id}", component="{self.component}", recent activity search failed with exception="{str(e)}", run_time="{time.time() - search_start}"'
                logging.error(msg)
                raise Exception(msg)

            #
            # 1. If we have entities to manage, loop though entities, run an mstats search and use ML dentisy function to define the adaptive_delay value
            # Store results in a dict which will be used to update the KVstore calling the API endpoint
            #

            # if we have entities to be managed

            # create a results dict
            adaptive_delay_results = {}

            # debug
            logging.debug(
                f'tenant_id="{self.tenant_id}", component="{self.component}", before processing, our collection_records_dict is: {json.dumps(collection_records_dict, indent=2)}'
            )

            # counters for pending, we will store and render these for additional context
            count_pending = 0
            count_pending_list = []
            count_pending_msg_list = []

            # Initialize sum of execution times and count of iterations
            total_execution_time = 0
            iteration_count = 0

            # Other initializations
            max_runtime = int(self.max_runtime)

            if len(collection_records) != 0:
                for object_id in collection_records_dict:

                    # iteration start
                    iteration_start_time = time.time()

                    object_name = collection_records_dict.get(object_id).get("object")

                    # log
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", adaptive delay inspection, we will proceed to ML calculations for this entity'
                    )

                    # get current_max_lag_event_sec
                    object_current_max_lag_event_sec = collection_records_dict.get(
                        object_id
                    ).get("current_max_lag_event_sec")

                    #
                    # Confidence: Verify if we have enough historical metrics to proceed
                    #

                    # boolean to defined if ML confidence check is passed
                    ml_confidence_check_passed = False

                    # initiate to low
                    ml_confidence = "low"

                    # initiate to unknown
                    ml_metrics_duration = "unknown"

                    # If the entity has been processed in the past 7 days, ML confidence check is passed already
                    if object_name in object_processed_past7days:
                        ml_confidence_check_passed = True
                        ml_confidence = "normal"
                        ml_confidence_reason = f"ML confidence is passed as this entity was processed in the past 7 days."
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection, ml_confidence="{ml_confidence}", ml_confidence_reason="{ml_confidence_reason}"'
                        )

                    # verify ML confidence
                    else:
                        # kwargs
                        kwargs_confidence = {
                            "earliest_time": "-30d",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        }

                        ml_confidence_search = remove_leading_spaces(
                            self.get_ml_condidence_search(object_name)
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection, ml_confidence_search="{ml_confidence_search}"'
                        )

                        try:
                            search_start = time.time()
                            reader = run_splunk_search(
                                self.service,
                                ml_confidence_search,
                                kwargs_confidence,
                                24,
                                5,
                            )

                            for item in reader:
                                if isinstance(item, dict):
                                    logging.info(
                                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", Processing results from ML confidence inspection, result="{json.dumps(item, indent=2)}"'
                                    )
                                    # log
                                    logging.info(
                                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection results, ml_confidence="{item.get("confidence")}", metrics_duration="{item.get("metrics_duration")}"'
                                    )
                                    ml_confidence = item.get("confidence", "low")
                                    ml_metrics_duration = item.get(
                                        "metrics_duration", "unknown"
                                    )

                        except Exception as e:
                            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection search failed with exception="{str(e)}", run_time="{time.time() - search_start}"'
                            logging.error(msg)
                            raise Exception(msg)

                        # set the ml_confidence_reason
                        if ml_confidence == "low":
                            ml_confidence_check_passed = False
                            ml_confidence_reason = f"ML has insufficient historical metrics to proceed (metrics_duration={ml_metrics_duration}, required={self.min_historical_metrics_days} days)"
                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection, ml_confidence="{ml_confidence}", ml_confidence_reason="{ml_confidence_reason}", we will wait for confidence to be normal before proceeding this entity'
                            )
                            if object_name not in count_pending_list:
                                count_pending += 1
                                count_pending_list.append(object_name)
                                count_pending_msg_list.append(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection, ml_confidence="{ml_confidence}", ml_confidence_reason="{ml_confidence_reason}", we will wait for confidence to be normal before proceeding this entity'
                                )

                        elif ml_confidence == "normal":
                            ml_confidence_check_passed = True
                            ml_confidence_reason = f'ML has sufficient historical metrics to proceed (metrics_duration="{ml_metrics_duration}", required="{self.min_historical_metrics_days}" days)'
                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML confidence inspection, ml_confidence="{ml_confidence}", ml_confidence_reason="{ml_confidence_reason}", we will proceed this entity'
                            )

                    #
                    # SLA percentage: Verify if the SLA percentage is lower than the max_sla_percentage, if not we will not proceed with this entity
                    #

                    # boolean to defined if SLA percentage check is passed, default is True unless proven otherwise
                    sla_percentage_check_passed = True
                    sla_percentage = 0

                    # kwargs
                    kwargs_sla_percentage = {
                        "earliest_time": "-90d",
                        "latest_time": "now",
                        "output_mode": "json",
                        "count": 0,
                    }

                    sla_percentage_search = remove_leading_spaces(
                        self.get_sla_percentage_search(object_id)
                    )
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection, sla_percentage_search="{sla_percentage_search}"'
                    )

                    try:
                        search_start = time.time()
                        reader = run_splunk_search(
                            self.service,
                            sla_percentage_search,
                            kwargs_sla_percentage,
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", Processing results from SLA percentage inspection, result="{json.dumps(item, indent=2)}"'
                                )
                                sla_percentage = float(item.get("percent_sla", 100))
                                # log
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection results, sla_percentage="{item.get("sla_percentage")}"'
                                )

                    except Exception as e:
                        msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection search failed with exception="{str(e)}", run_time="{time.time() - search_start}"'
                        logging.error(msg)
                        raise Exception(msg)

                    # set the sla_percentage_check_passed and reason
                    if sla_percentage > int(self.max_sla_percentage):
                        sla_percentage_check_passed = False
                        sla_percentage_reason = f"SLA percentage {sla_percentage} is greater than the max_sla_percentage {self.max_sla_percentage}, we will not proceed with this entity"
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection, sla_percentage="{sla_percentage}", sla_percentage_reason="{sla_percentage_reason}", we will not proceed with this entity'
                        )

                        if object_name not in count_pending_list:
                            count_pending += 1
                            count_pending_list.append(object_name)
                            count_pending_msg_list.append(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection, sla_percentage="{sla_percentage}", sla_percentage_reason="{sla_percentage_reason}", we will not proceed with this entity'
                            )

                    else:
                        sla_percentage_check_passed = True
                        sla_percentage_reason = f"SLA percentage {sla_percentage} is lower than the max_sla_percentage {self.max_sla_percentage}, we will proceed with this entity"
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", SLA percentage inspection, sla_percentage="{sla_percentage}", sla_percentage_reason="{sla_percentage_reason}", we will proceed this entity'
                        )

                    #
                    # Proceed ML investigations
                    #

                    # boolean proceed investigations (True by default)
                    proceed_investigations = True

                    # If updated in the past 4 hours, we will wait whatever the direction of the change and other conditions
                    if object_name in object_processed_past4hours:
                        proceed_investigations = False
                        count_pending += 1
                        count_pending_list.append(object_name)
                        count_pending_msg_list.append(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", This entity has been updated in the past 4 hours, we will wait before processing this entity again.'
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", This entity has been updated in the past 4 hours, we will wait before processing this entity again.'
                        )

                    # else if updated in the past 24 hours and the threshold was increased in the past 24 hours, we will review
                    elif (
                        object_name in object_processed_past24hours_threshold_increased
                        and past7days_changes_count < int(self.max_changes_past_7days)
                    ):
                        proceed_investigations = True
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", This entity has been updated in the past 24 hours and the threshold was increased, we will review this entity again.'
                        )

                    # else if we have reached the number of changes allowed for a 7 days time frame, we will wait
                    elif past7days_changes_count > int(self.max_changes_past_7days):
                        proceed_investigations = False
                        count_pending += 1
                        count_pending_list.append(object_name)
                        count_pending_msg_list.append(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", This entity has reached the number of changes allowed for a 7 days time frame, we will wait before processing this entity again.'
                        )
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", This entity has reached the number of changes allowed for a 7 days time frame, we will wait before processing this entity again.'
                        )

                    else:
                        # proceed if ml confidence check is passed
                        if (
                            ml_confidence_check_passed == True
                            and sla_percentage_check_passed == True
                        ):
                            proceed_investigations = True
                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", object_summary_dict="{json.dumps(object_summary_dict, indent=0)}", conditions are met for this entity to be processed.'
                            )
                        else:
                            proceed_investigations = False

                    #
                    # Proceed to ML investigations
                    #

                    if (
                        proceed_investigations
                        and ml_confidence_check_passed
                        and sla_percentage_check_passed
                    ):
                        # kwargs
                        kwargs_ml_mstats = {
                            "earliest_time": self.earliest_time_mstats,
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        }

                        # search the search string

                        # if object has been processed in the past 7 days, we will run a more complex adaptive logic
                        if object_name in object_processed_past7days:
                            ml_mstats_search = self.get_mstats_ml_advanced_search(
                                object_name
                            )
                        else:
                            ml_mstats_search = self.get_mstats_ml_simple_search(
                                object_name
                            )

                        # set a version of the search but remove carriage returns for logging purposes
                        ml_mstats_search_for_logging = remove_leading_spaces(
                            ml_mstats_search
                        )
                        # remove any carriage returns
                        ml_mstats_search_for_logging = (
                            ml_mstats_search_for_logging.replace("\n", " ")
                        )

                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", running mstats search_string="{remove_leading_spaces(ml_mstats_search)}", kwargs_ml_mstats="{json.dumps(kwargs_ml_mstats, indent=2)}")'
                        )

                        try:
                            search_start = time.time()
                            reader = run_splunk_search(
                                self.service,
                                remove_leading_spaces(ml_mstats_search),
                                kwargs_ml_mstats,
                                24,
                                5,
                            )

                            for item in reader:
                                if isinstance(item, dict):
                                    logging.info(
                                        f'tenant_id="{self.tenant_id}", component="{self.component}", Processing results from ML mstats, result="{json.dumps(item, indent=2)}"'
                                    )

                                    # add per entity results in the dict with the key object

                                    # add all fields returned in item to adaptive_delay_results[object_id]

                                    # init
                                    adaptive_delay_results[object_id] = {}

                                    for k, v in item.items():
                                        adaptive_delay_results[object_id][k] = v

                                    # add current_max_lag_event_sec which is not part of the search results
                                    adaptive_delay_results[object_id][
                                        "current_max_lag_event_sec"
                                    ] = object_current_max_lag_event_sec

                                    # add ml_mstats_search_for_logging and kwargs_ml_mstats
                                    adaptive_delay_results[object_id][
                                        "search_string"
                                    ] = ml_mstats_search_for_logging
                                    adaptive_delay_results[object_id][
                                        "search_kwargs"
                                    ] = kwargs_ml_mstats

                                    logging.info(
                                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", results="{json.dumps(item, indent=2)}"'
                                    )

                                    # Surface a likely ML fit failure. A valid
                                    # density fit yields a positive UpperBound;
                                    # UpperBound<=0 means the per-object fit did
                                    # not produce a usable boundary, so the
                                    # computed adaptive_delay floors to the +1h
                                    # buffer and the entity is silently skipped
                                    # later as "no need to update". Logging a
                                    # WARNING here makes that observable instead
                                    # of looking like a healthy no-op.
                                    try:
                                        upperbound_val = float(
                                            item.get("UpperBound", 0) or 0
                                        )
                                    except (ValueError, TypeError):
                                        upperbound_val = 0
                                    if upperbound_val <= 0:
                                        logging.warning(
                                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_name}", object_id="{object_id}", ML fit returned no usable UpperBound (UpperBound="{item.get("UpperBound")}"); adaptive_delay cannot be computed from historical behaviour and the entity will be skipped. Check the native fit log (index=_internal source="*trackme_splk_native_fit.log").'
                                        )

                        except Exception as e:
                            logging.error(
                                f"Failed to execute Splunk search with error: {str(e)}"
                            )
                            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", ML mstats search failed with exception="{str(e)}", run_time="{time.time() - search_start}"'
                            logging.error(msg)
                            raise Exception(msg)

                    # Calculate the execution time for this iteration
                    iteration_end_time = time.time()
                    execution_time = iteration_end_time - iteration_start_time

                    # Update total execution time and iteration count
                    total_execution_time += execution_time
                    iteration_count += 1

                    # Calculate average execution time
                    if iteration_count > 0:
                        average_execution_time = total_execution_time / iteration_count
                    else:
                        average_execution_time = 0

                    # Check if there is enough time left to continue
                    current_time = time.time()
                    elapsed_time = current_time - start
                    if elapsed_time + average_execution_time + 120 >= max_runtime:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                        )
                        break

                #
                # 2. Loop through the list adaptive_records_results_list and call the API endpoint to update the lag policy
                #

                logging.debug(
                    f"adaptive_delay_results={json.dumps(adaptive_delay_results, indent=2)}"
                )

                count_updated = 0
                count_updated_list = []
                count_updated_msg_list = []
                count_processed = 0
                count_processed_list = []
                count_processed_msg_list = []
                count_failed = 0
                count_failed_list = []
                count_failed_msg_list = []

                for object_id in adaptive_delay_results:
                    entity_dict = adaptive_delay_results.get(object_id)
                    (
                        count_updated,
                        count_failed,
                        count_updated_list,
                        count_updated_msg_list,
                        count_failed_list,
                        count_processed,
                        count_processed_list,
                        count_processed_msg_list,
                        count_failed_msg_list,
                    ) = self.run_post_api_call(
                        object_id,
                        entity_dict,
                        header,
                        self.max_auto_delay_sec,
                        count_updated,
                        count_failed,
                        count_updated_list,
                        count_updated_msg_list,
                        count_failed_list,
                        count_processed,
                        count_processed_list,
                        count_processed_msg_list,
                        count_failed_msg_list,
                    )

                # action results
                if count_failed == 0:
                    action = "success"
                else:
                    action = "failure"

                # set run_time
                run_time = round(time.time() - start, 3)

                # call the component register
                if action == "success":
                    self.call_component_register(
                        "success", "The report was executed successfully", run_time
                    )
                else:
                    self.call_component_register(
                        "failure", json.dumps(count_failed_msg_list, indent=0), run_time
                    )

                yield_results = {
                    "action": action,
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "count_to_process": len(collection_records),
                    "count_to_process_list": count_to_process_list,
                    "count_processed": count_processed,
                    "count_processed_list": count_processed_list,
                    "count_processed_msg_list": count_processed_msg_list,
                    "count_failed": count_failed,
                    "count_failed_list": count_failed_list,
                    "count_failed_msg_list": count_failed_msg_list,
                    "count_updated": count_updated,
                    "count_updated_list": count_updated_list,
                    "count_updated_msg_list": count_updated_msg_list,
                    "count_pending": count_pending,
                    "count_pending_list": count_pending_list,
                    "count_pending_msg_list": count_pending_msg_list,
                    "count_processed_past30days": object_processed_past30days,
                    "count_processed_past15days": object_processed_past15days,
                    "count_processed_past7days": object_processed_past7days,
                    "count_processed_past24hours": object_processed_past24hours,
                    "run_time": run_time,
                    **vd_result,
                }

                yield {
                    "_time": time.time(),
                    "_raw": yield_results,
                    "run_time": run_time,
                }

                # handler event
                handler_events_records = []
                for object_name in count_processed_list:
                    # Find the object_id by looking up in collection_records_dict
                    object_id = None
                    for key, value in collection_records_dict.items():
                        if value.get("object") == object_name:
                            object_id = key
                            break

                    handler_events_records.append(
                        {
                            "object": object_name,
                            "object_id": object_id,
                            "object_category": f"splk-{self.component}",
                            "handler": f"trackme_{self.component}_adaptive_delay_tracker_tenant_{self.tenant_id}",
                            "handler_message": "Entity was processed by the adaptive delay tracker.",
                            "handler_troubleshoot_search": f'index=_internal (sourcetype=trackme:custom_commands:trackmesplkadaptivedelay) tenant_id={self.tenant_id} object="{object_name}"',
                            "handler_time": time.time(),
                        }
                    )

                # notification event
                try:
                    trackme_handler_events(
                        session_key=self._metadata.searchinfo.session_key,
                        splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                        tenant_id=self.tenant_id,
                        sourcetype="trackme:handler",
                        source=f"trackme:handler:{self.tenant_id}",
                        handler_events=handler_events_records,
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", could not send notification event, exception="{e}"'
                    )

            else:
                # set run_time
                run_time = round(time.time() - start, 3)

                # Call the component register
                self.call_component_register(
                    "success", "The report was executed successfully", run_time
                )

                yield_results = {
                    "action": "success",
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "count_to_process": len(collection_records),
                    "msg": "no static entities to manage currently",
                    "run_time": run_time,
                    **vd_result,
                }

                yield {
                    "_time": time.time(),
                    "_raw": yield_results,
                    "run_time": run_time,
                }

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", trackmesplkadaptivedelay has terminated, run_time={run_time}, results="{json.dumps(yield_results, indent=2)}"'
        )


dispatch(AdaptiveDelay, sys.argv, sys.stdin, sys.stdout, __name__)
