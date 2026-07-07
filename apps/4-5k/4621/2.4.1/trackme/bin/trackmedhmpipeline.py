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
import ast
import fnmatch
import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

# Third-party imports
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_dhm_pipeline.log" % splunkhome,
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
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, trackme_idx_for_tenant

# Import trackme libs for feeds
from trackme_libs_splk_feeds import trackme_splk_dhm_gen_metrics


# Static cap on per-host combo cardinality in splk_dhm_st_summary. Each
# DHM record carries a JSON dict of combo_id → combo_state; extras-aware
# trackers (breakby_extra_fields) push that count up by appending
# dimensions to the combo grain. The cap is non-configurable by design:
# operators get a uniform ceiling on KV row size and on downstream
# decision-maker iteration cost. Combos beyond the cap are dropped LRU
# (oldest last_time first). For pre-extras trackers the typical combo
# count per host is << 100, so the cap is effectively inert.
_COMBO_CAP_PER_HOST = 100


def _unquote_extras_value(value):
    """Reverse the URL-encoding the SPL emitter applies to extras values.

    The emitter (see _build_dhm_extras_eval_fragments in
    trackme_libs_splk_feeds.py) encodes, in order:
        "%"  → "%25" first
        "\\" → "%5C"  (so backslash-in-value can't trigger Python
                        escape interpretation in the single-quoted
                        dict literal that current_summary embeds —
                        `\\U`, `\\n`, `\\t` etc. would otherwise crash
                        or corrupt ast.literal_eval)
        "'"  → "%27"  (so single-quote-in-value can't break the
                        single-quoted dict literal itself)
        "|"  → "%7C"  (pair delimiter)
        "=" → "%3D"   (key=value separator)
    Decoding undoes the non-`%25` substitutions first, then `%25` → `%`
    last, so a legitimate "%XX" elsewhere in the value isn't disturbed.
    We decode by hand (instead of urllib.parse.unquote) because the
    emitter only escapes those five sentinel characters — any other
    `%XX` in a real value (e.g. URL-style log lines) must pass through
    untouched.
    """
    if value is None:
        return ""
    s = str(value)
    if not s:
        return s
    # Order matters: non-`%25` substitutions first so their `%25`-style
    # escapes only decode if they actually were our sentinels, then
    # `%25` → `%` so a legitimate `%XX` elsewhere isn't disturbed.
    s = (
        s.replace("%7C", "|")
        .replace("%3D", "=")
        .replace("%27", "'")
        .replace("%5C", "\\")
    )
    s = s.replace("%25", "%")
    return s


@Configuration(distributed=False)
class TrackMeDhmPipeline(StreamingCommand):
    """
    Unified DHM pipeline command that replaces the expand/process/collapse pattern.

    Performs in-memory: merge current+previous summaries, apply blocklists,
    evaluate per-combo state, resolve host-level thresholds, compute host aggregates,
    build splk_dhm_st_summary + display views, and collect metrics.

    Input: One record per host with current_summary, previous_summary (from combined lookup),
           entity fields, default thresholds, and 5m metrics.
    Output: Same record enriched with computed fields (no record expansion).
    """

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
    )

    field_host = Option(
        doc="""
        **Syntax:** **field_host=****
        **Description:** field name containing the host value.""",
        require=False,
        default="host",
    )

    field_current = Option(
        doc="""
        **Syntax:** **field_current=****
        **Description:** field name containing the current summary dictionary.""",
        require=False,
        default="current_summary",
    )

    field_previous = Option(
        doc="""
        **Syntax:** **field_previous=****
        **Description:** field name containing the previous summary dictionary.""",
        require=False,
        default="previous_summary",
    )

    gen_metrics = Option(
        doc="""
        **Syntax:** **gen_metrics=****
        **Description:** Generate and index metrics details.""",
        require=False,
        default="False",
        validate=validators.Match("gen_metrics", r"^(True|False)$"),
    )

    def stream(self, records):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        # Load tenant indexes if metrics generation is enabled
        if self.gen_metrics == "True" and self.tenant_id:
            tenant_indexes = trackme_idx_for_tenant(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
            )
        else:
            tenant_indexes = None

        # Accumulate metrics records for batch generation at end
        records_metrics = []
        output_records = []
        record_count = 0
        total_combos = 0

        # Cumulative sub-task timers (seconds)
        time_parse = 0.0
        time_merge_blocklist = 0.0
        time_combo_processing = 0.0
        time_output_build = 0.0

        # Init phase timing
        init_run_time = round(time.time() - start, 3)

        logging.info(
            f'tenant_id="{self.tenant_id}", trackmedhmpipeline starting, '
            f'gen_metrics="{self.gen_metrics}", init_run_time={init_run_time}'
        )

        # Performance: track streaming phase
        stream_start = time.time()

        # Iterate over records (one per host)
        for subrecord in records:
            record_count += 1
            host = subrecord.get(self.field_host, "")

            # --- PARSE ---
            t0 = time.time()
            current_dict = self._parse_dict(
                subrecord.get(self.field_current), "current", host
            )
            previous_dict = self._parse_dict(
                subrecord.get(self.field_previous), "previous", host
            )
            time_parse += time.time() - t0

            # --- MERGE: preserve previous combos not in current ---
            t0 = time.time()
            if current_dict and previous_dict:
                for p_id, p_info in previous_dict.items():
                    if p_id not in current_dict:
                        current_dict[p_id] = p_info
            elif not current_dict and previous_dict:
                # current_dict is None/empty but previous has data — use previous as base
                current_dict = previous_dict

            if not current_dict:
                time_merge_blocklist += time.time() - t0
                # No data to process — buffer with empty summary fields
                subrecord["splk_dhm_st_summary"] = "{}"
                subrecord["object_category"] = "splk-dhm"
                # Clean up input fields
                subrecord.pop(self.field_current, None)
                subrecord.pop(self.field_previous, None)
                output_records.append(subrecord)
                continue

            # --- BLOCKLISTS ---
            # Entries are matched with fnmatch.fnmatchcase, so plain values
            # ("foo") behave like literal matches and patterns ("foo_*",
            # "*-temp", "nginx:*:error") fan out across families. Pre-wildcard
            # blocklists keep working unchanged.
            host_idx_blocklists = subrecord.get("host_idx_blocklists", [])
            host_st_blocklists = subrecord.get("host_st_blocklists", [])
            if isinstance(host_idx_blocklists, str):
                host_idx_blocklists = (
                    host_idx_blocklists.split(",") if host_idx_blocklists else []
                )
            if isinstance(host_st_blocklists, str):
                host_st_blocklists = (
                    host_st_blocklists.split(",") if host_st_blocklists else []
                )

            host_idx_blocklists = [
                p.strip() for p in host_idx_blocklists if isinstance(p, str) and p.strip()
            ]
            host_st_blocklists = [
                p.strip() for p in host_st_blocklists if isinstance(p, str) and p.strip()
            ]

            if host_idx_blocklists or host_st_blocklists:
                def _blocklist_match(value, patterns):
                    if not patterns:
                        return False
                    return any(fnmatch.fnmatchcase(value, p) for p in patterns)

                current_dict = {
                    key: val
                    for key, val in current_dict.items()
                    if not _blocklist_match(val.get("idx", ""), host_idx_blocklists)
                    and not _blocklist_match(val.get("st", ""), host_st_blocklists)
                }
            # --- EMPTY PLACEHOLDER CLEANUP ---
            # Injected expected hosts start with empty idx/st combos. Once real
            # data arrives (non-empty idx AND st), remove the empty placeholders
            # from current_dict so they are no longer persisted in the summary.
            # Only remove when at least one non-empty combo exists — otherwise
            # the entity is still awaiting data and the placeholder must stay.
            if len(current_dict) > 1:
                has_real = any(
                    v.get("idx", "") and v.get("st", "")
                    for v in current_dict.values()
                )
                if has_real:
                    current_dict = {
                        k: v for k, v in current_dict.items()
                        if v.get("idx", "") and v.get("st", "")
                    }

            time_merge_blocklist += time.time() - t0

            if not current_dict:
                subrecord["splk_dhm_st_summary"] = "{}"
                subrecord["object_category"] = "splk-dhm"
                subrecord.pop(self.field_current, None)
                subrecord.pop(self.field_previous, None)
                output_records.append(subrecord)
                continue

            # --- PER-HOST COMBO CARDINALITY CAP (LRU by last_time) ---
            # Extras-aware DHM trackers (breakby_extra_fields) extend the per-host
            # combo grain beyond (index, sourcetype). High-cardinality dimensions
            # like `source` can balloon a host's splk_dhm_st_summary dict and the
            # downstream JSON column. Cap is static and applies uniformly to all
            # DHM trackers: the per-host combo dict carries the 100 combos with
            # the most recent last_time and older combos drop off. For trackers
            # without extras the typical combo count per host is << 100, so this
            # is effectively a no-op.
            if len(current_dict) > _COMBO_CAP_PER_HOST:
                # Sort by last_time desc (fall back to time_measure for combos
                # whose last_time is missing — e.g. empty placeholder rows).
                # The previous-summary merge has already happened above, so this
                # cap operates on the union of current and previous combos.
                # Use ``self._safe_float`` rather than a bare ``float()`` —
                # ``last_time`` / ``time_measure`` come from KV-persisted
                # combo summaries which could in theory carry non-numeric
                # strings (corrupted record, schema-migration glitch,
                # manual edit). A ValueError inside the sort key would
                # crash the entire per-host pipeline iteration for that
                # host. The rest of this file already uses ``_safe_float``
                # for the same two fields (see lines ~386-395). Falling
                # back to 0 sorts the offending combo to the end, which
                # is the same end-state as a missing-key fall-through.
                sorted_combos = sorted(
                    current_dict.items(),
                    key=lambda kv: self._safe_float(
                        kv[1].get("last_time")
                        or kv[1].get("time_measure")
                        or 0,
                        0,
                    ),
                    reverse=True,
                )
                truncated = len(current_dict) - _COMBO_CAP_PER_HOST
                current_dict = dict(sorted_combos[:_COMBO_CAP_PER_HOST])
                # WARNING (not INFO) because dropping combos is silent
                # monitoring-coverage degradation — the operator loses
                # lag/latency/quality signal on the evicted combos until
                # they reappear in the top-N by last_time. Matches the
                # codebase convention (same file at line 691; analogous
                # unusual-condition events across package/bin/) and stays
                # visible on operator dashboards that filter to WARNING+.
                logging.warning(
                    f'tenant_id="{self.tenant_id}", host="{host}", '
                    f'event="combo_cap_truncated", cap={_COMBO_CAP_PER_HOST}, '
                    f'dropped={truncated}'
                )

            # --- GET THRESHOLDS ---
            # Default thresholds come from upstream macros on the record
            default_max_lag = self._safe_float(
                subrecord.get("data_max_lag_allowed"), 3600
            )
            default_max_delay = self._safe_float(
                subrecord.get("data_max_delay_allowed"), 86400
            )

            # Host-level overrides from KV lookup
            host_level_lag = self._safe_float(
                subrecord.get("current_host_level_data_max_lag_allowed"), None
            )
            host_level_delay = self._safe_float(
                subrecord.get("current_host_level_data_max_delay_allowed"), None
            )

            now_epoch = time.time()

            # --- PER-COMBO PROCESSING ---
            t0 = time.time()
            # Track host-level aggregates
            max_ingest = 0
            min_first_time = float("inf")
            max_last_time = 0
            sum_ingest_lag = 0
            sum_eventcount = 0
            combo_count = 0
            indexes = set()
            sourcetypes = set()
            # max_combo thresholds: currently all combos use default thresholds,
            # so max across combos always equals the default. We initialize from
            # defaults directly; if per-combo thresholds are added later, the
            # max-tracking inside the loop will pick up overrides correctly.
            max_combo_lag = default_max_lag
            max_combo_delay = default_max_delay

            # Build the raw summary dict
            raw_summary = {}

            for combo_id, combo_info in current_dict.items():
                # Extract combo metrics
                idx = str(combo_info.get("idx", ""))
                st = str(combo_info.get("st", ""))
                first_time = self._safe_float(combo_info.get("first_time"), 0)
                last_time = self._safe_float(combo_info.get("last_time"), 0)
                last_ingest_lag = self._safe_float(
                    combo_info.get("last_ingest_lag"), 0
                )
                last_ingest = self._safe_float(combo_info.get("last_ingest"), 0)
                last_eventcount = self._safe_float(
                    combo_info.get("last_eventcount"), 0
                )
                time_measure = self._safe_float(combo_info.get("time_measure"), now_epoch)

                # Compute event lag as now - last_time (when last_time is 0/missing, use very large lag to mark combo unhealthy)
                last_event_lag = now_epoch - last_time if last_time > 0 else now_epoch

                # Use default thresholds for combo level
                combo_max_lag = default_max_lag
                combo_max_delay = default_max_delay

                # Evaluate combo state
                combo_state = "green"
                if last_event_lag > combo_max_delay or last_ingest_lag > combo_max_lag:
                    combo_state = "red"

                # Track max combo thresholds for host-level resolution
                if combo_max_lag > max_combo_lag:
                    max_combo_lag = combo_max_lag
                if combo_max_delay > max_combo_delay:
                    max_combo_delay = combo_max_delay

                # Update host aggregates
                if last_ingest > max_ingest:
                    max_ingest = last_ingest
                if first_time > 0 and first_time < min_first_time:
                    min_first_time = first_time
                if last_time > max_last_time:
                    max_last_time = last_time
                sum_ingest_lag += last_ingest_lag
                sum_eventcount += last_eventcount
                combo_count += 1
                indexes.add(idx)
                sourcetypes.add(st)

                # Build raw summary entry (single-quoted Python dict format)
                raw_entry = {
                    "idx": idx,
                    "st": st,
                    "last_eventcount": str(combo_info.get("last_eventcount", "0")),
                    "max_lag_allowed": str(combo_max_lag),
                    "max_delay_allowed": str(combo_max_delay),
                    "last_ingest": str(combo_info.get("last_ingest", "0")),
                    "first_time": str(combo_info.get("first_time", "0")),
                    "last_time": str(combo_info.get("last_time", "0")),
                    "last_ingest_lag": str(combo_info.get("last_ingest_lag", "0")),
                    "last_event_lag": str(round(last_event_lag, 2)),
                    "time_measure": str(round(now_epoch)),
                    "state": combo_state,
                }

                # Preserve 5m metrics fields if present
                for metric_field in (
                    "avg_eventcount_5m",
                    "latest_eventcount_5m",
                    "perc95_eventcount_5m",
                    "avg_latency_5m",
                    "latest_latency_5m",
                    "perc95_latency_5m",
                    "stdev_latency_5m",
                    "stdev_eventcount_5m",
                ):
                    if metric_field in combo_info:
                        raw_entry[metric_field] = str(combo_info[metric_field])

                # Preserve the per-combo extras emitted by the
                # trackme_dhm_tracker_abstract macro for extras-aware
                # trackers. Parse the "<field>=<value>|<field>=<value>"
                # encoding produced by the SPL generator into a structured
                # dict so REST handlers (_full view), UI donut charts, and
                # the decision-maker red-list message can label each extra
                # by its source field name. Values are URL-encoded by the
                # SPL emitter ("%" → "%25", "|" → "%7C", "=" → "%3D") so a
                # raw `|` inside a log path or `=` inside a free-form
                # value can't poison the pair / key=value parse here.
                # Falls back to a single anonymous `_raw` entry if the
                # value doesn't carry "=" (e.g. an older payload caught
                # mid-upgrade) — the JSON column stays parseable either
                # way.
                if "extras" in combo_info:
                    extras_raw = combo_info["extras"]
                    if isinstance(extras_raw, dict):
                        # Already structured (e.g. re-merged from a
                        # previous-summary entry written by this same
                        # pipeline). Re-emit as-is.
                        raw_entry["extras"] = {
                            str(k): str(v) for k, v in extras_raw.items()
                        }
                    else:
                        extras_str = str(extras_raw or "")
                        if "=" in extras_str:
                            extras_dict = {}
                            for pair in extras_str.split("|"):
                                if "=" in pair:
                                    k, _, v = pair.partition("=")
                                    k = k.strip()
                                    if k:
                                        # str.partition splits on the first
                                        # literal "=" only — values may still
                                        # carry "%3D" which decodes back to
                                        # "=" here without re-splitting.
                                        extras_dict[k] = _unquote_extras_value(v)
                            if extras_dict:
                                raw_entry["extras"] = extras_dict
                            elif extras_str:
                                raw_entry["extras"] = {"_raw": extras_str}
                        elif extras_str:
                            # Defensive fallback — value without an "=" is
                            # not the documented format; surface it under
                            # `_raw` so it stays visible without breaking
                            # downstream consumers that iterate the dict.
                            raw_entry["extras"] = {"_raw": extras_str}

                raw_summary[combo_id] = raw_entry

            # Track total combos processed
            total_combos += combo_count
            time_combo_processing += time.time() - t0

            # --- RESOLVE HOST-LEVEL THRESHOLDS ---
            t0 = time.time()
            # Host-level overrides always win (regardless of value)
            if host_level_lag is not None:
                resolved_lag = host_level_lag
            else:
                resolved_lag = max_combo_lag

            if host_level_delay is not None:
                resolved_delay = host_level_delay
            else:
                resolved_delay = max_combo_delay

            # --- COMPUTE HOST AGGREGATES ---
            avg_ingest_lag = sum_ingest_lag / combo_count if combo_count > 0 else 0

            # --- UPDATE SUMMARY THRESHOLDS AND RE-EVALUATE STATE ---
            # Propagate the entity's resolved thresholds into each sourcetype summary entry
            # and re-evaluate combo state against the resolved thresholds. This ensures the
            # summary reflects the actual thresholds in effect (variable delay, host-level
            # overrides, lagging classes) rather than stale defaults.
            for combo_id in raw_summary:
                entry = raw_summary[combo_id]
                entry["max_lag_allowed"] = str(resolved_lag)
                entry["max_delay_allowed"] = str(resolved_delay)
                # Re-evaluate state with resolved thresholds
                entry_event_lag = float(entry.get("last_event_lag", "0"))
                entry_ingest_lag = float(entry.get("last_ingest_lag", "0"))
                entry["state"] = "red" if (entry_event_lag > resolved_delay or entry_ingest_lag > resolved_lag) else "green"

            # --- BUILD OUTPUT FIELDS ---
            # splk_dhm_st_summary in JSON format for fast parsing by REST handler and decision maker
            # Display views (_full, _minimal) are generated on-demand by the REST handler
            subrecord["splk_dhm_st_summary"] = json.dumps(raw_summary)

            # Host-level aggregate fields
            subrecord["data_last_ingest"] = str(max_ingest)
            # Preserve historical data_first_time_seen from KV store (set by macro on first discovery)
            # Only compute from current data if the record has no KV value
            existing_first = subrecord.get("data_first_time_seen")
            if not existing_first or existing_first in ("", "0", "0.0", "None"):
                subrecord["data_first_time_seen"] = str(min_first_time) if min_first_time != float("inf") else "0"
            subrecord["data_last_time_seen"] = str(max_last_time)
            subrecord["data_last_ingestion_lag_seen"] = str(int(round(avg_ingest_lag)))
            subrecord["data_eventcount"] = str(round(sum_eventcount))
            subrecord["data_max_lag_allowed"] = str(resolved_lag)
            subrecord["data_max_delay_allowed"] = str(resolved_delay)
            subrecord["summary_max_lag_allowed"] = str(max_combo_lag)
            subrecord["summary_max_delay_allowed"] = str(max_combo_delay)

            # Multi-value fields as comma-separated strings
            subrecord["data_index"] = ",".join(sorted(indexes))
            subrecord["data_sourcetype"] = ",".join(sorted(sourcetypes))

            # Aggregate 5m metrics from combos
            sum_avg_ec_5m = 0
            sum_latest_ec_5m = 0
            sum_perc95_ec_5m = 0
            sum_stdev_ec_5m = 0
            sum_avg_lat_5m = 0
            sum_latest_lat_5m = 0
            sum_perc95_lat_5m = 0
            sum_stdev_lat_5m = 0
            lat_count = 0

            for combo_info in current_dict.values():
                sum_avg_ec_5m += self._safe_float(combo_info.get("avg_eventcount_5m"), 0)
                sum_latest_ec_5m += self._safe_float(combo_info.get("latest_eventcount_5m"), 0)
                sum_perc95_ec_5m += self._safe_float(combo_info.get("perc95_eventcount_5m"), 0)
                sum_stdev_ec_5m += self._safe_float(combo_info.get("stdev_eventcount_5m"), 0)
                avg_lat = self._safe_float(combo_info.get("avg_latency_5m"), None)
                if avg_lat is not None:
                    sum_avg_lat_5m += avg_lat
                    sum_latest_lat_5m += self._safe_float(combo_info.get("latest_latency_5m"), 0)
                    sum_perc95_lat_5m += self._safe_float(combo_info.get("perc95_latency_5m"), 0)
                    sum_stdev_lat_5m += self._safe_float(combo_info.get("stdev_latency_5m"), 0)
                    lat_count += 1

            subrecord["avg_eventcount_5m"] = str(sum_avg_ec_5m)
            subrecord["latest_eventcount_5m"] = str(sum_latest_ec_5m)
            subrecord["perc95_eventcount_5m"] = str(sum_perc95_ec_5m)
            subrecord["stdev_eventcount_5m"] = str(sum_stdev_ec_5m)
            if lat_count > 0:
                subrecord["avg_latency_5m"] = str(sum_avg_lat_5m / lat_count)
                subrecord["latest_latency_5m"] = str(sum_latest_lat_5m / lat_count)
                subrecord["perc95_latency_5m"] = str(sum_perc95_lat_5m / lat_count)
                subrecord["stdev_latency_5m"] = str(sum_stdev_lat_5m / lat_count)
            else:
                subrecord["avg_latency_5m"] = "0"
                subrecord["latest_latency_5m"] = "0"
                subrecord["perc95_latency_5m"] = "0"
                subrecord["stdev_latency_5m"] = "0"

            # Set object_category
            subrecord["object_category"] = "splk-dhm"

            # Clean up input fields no longer needed
            subrecord.pop(self.field_current, None)
            subrecord.pop(self.field_previous, None)
            subrecord.pop("current_host_level_data_max_lag_allowed", None)
            subrecord.pop("current_host_level_data_max_delay_allowed", None)
            time_output_build += time.time() - t0

            # Collect metrics data for batch generation
            if self.gen_metrics == "True":
                records_metrics.append(
                    {
                        "object": subrecord.get("object", host),
                        "object_id": subrecord.get("key"),
                        "object_category": "splk-dhm",
                        "alias": subrecord.get("alias", host),
                        "metrics_dict": raw_summary,
                    }
                )

            # Buffer records for post-stream processing safety
            output_records.append(subrecord)

        # --- BATCH METRICS GENERATION (before yielding, guaranteed to run) ---
        # Running metrics generation before yield ensures it completes even if the
        # downstream pipeline terminates early or the search is cancelled after yields start.
        stream_run_time = round(time.time() - stream_start, 3)
        metrics_run_time = 0
        if self.gen_metrics == "True" and records_metrics and tenant_indexes:
            metrics_gen_start = time.time()
            try:
                gen_metrics = trackme_splk_dhm_gen_metrics(
                    self.tenant_id,
                    tenant_indexes.get("trackme_metric_idx"),
                    records_metrics,
                )
                metrics_run_time = round(time.time() - metrics_gen_start, 3)
                logging.info(
                    f'context="gen_metrics", tenant_id="{self.tenant_id}", '
                    f"function trackme_splk_dhm_gen_metrics success {gen_metrics}, "
                    f"run_time={metrics_run_time}, "
                    f"no_entities={len(records_metrics)}"
                )
            except Exception as e:
                metrics_run_time = round(time.time() - metrics_gen_start, 3)
                logging.error(
                    f'context="gen_metrics", tenant_id="{self.tenant_id}", '
                    f"function trackme_splk_dhm_gen_metrics failed, "
                    f'tenant_indexes="{tenant_indexes}", exception {str(e)}'
                )

        # Yield all buffered records
        for subrecord in output_records:
            yield subrecord

        # Log the total run time with full performance breakdown
        total_run_time = round(time.time() - start, 3)
        logging.info(
            f'tenant_id="{self.tenant_id}", trackmedhmpipeline has terminated, '
            f"hosts={record_count}, total_combos={total_combos}, "
            f"avg_combos_per_host={round(total_combos / record_count, 1) if record_count > 0 else 0}, "
            f"init_run_time={init_run_time}, "
            f"task_parse={round(time_parse, 3)}, "
            f"task_merge_blocklist={round(time_merge_blocklist, 3)}, "
            f"task_combo_processing={round(time_combo_processing, 3)}, "
            f"task_output_build={round(time_output_build, 3)}, "
            f"stream_run_time={stream_run_time}, "
            f"metrics_run_time={metrics_run_time}, "
            f"total_run_time={total_run_time}"
        )

    def _parse_dict(self, value, label, host):
        """Parse a string into a Python dict, trying JSON first (fast) then ast.literal_eval (legacy)."""
        if not value:
            return None
        # Try JSON first (new format, ~10-100x faster than ast.literal_eval)
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        # Fall back to ast.literal_eval for legacy Python dict format
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError) as e:
            if label == "previous":
                logging.info(
                    f'tenant_id="{self.tenant_id}", '
                    f"No {label}_dict found for host '{host}', "
                    f"this can be expected for new entities."
                )
            else:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", '
                    f"Failed to parse {label}_dict for host '{host}', "
                    f"exception: {e}"
                )
            return None

    @staticmethod
    def _safe_float(value, default):
        """Convert value to float, returning default on failure."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


dispatch(TrackMeDhmPipeline, sys.argv, sys.stdin, sys.stdout, __name__)
