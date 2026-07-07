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
import json
import logging
import os
import sys
import time
import urllib.parse
from logging.handlers import RotatingFileHandler

# Third-party imports
import urllib3

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_mhm_pipeline.log" % splunkhome,
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
from trackme_libs import trackme_reqinfo, trackme_idx_for_tenant, get_splunkd_timeout

# Import trackme libs for feeds
from trackme_libs_splk_feeds import trackme_splk_mhm_gen_metrics

# Import splunklib for KV store access
import splunklib.client as client


@Configuration(distributed=False)
class TrackMeMhmPipeline(StreamingCommand):
    """
    Unified MHM pipeline command that replaces the merge/extract pattern.

    Performs in-memory: merge current+previous metric summaries,
    apply per-metric-category lagging class thresholds, evaluate per-metric state,
    build metric_details + display views (full/minimal/compact), compute host aggregates,
    and collect metrics.

    Input: One record per host with current_summary, previous_summary (from combined lookup),
           entity fields, default lag threshold, and lagging class overrides.
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

        # Load per-metric-category lagging class overrides from KV store (once at init)
        # Collection: kv_trackme_mhm_lagging_classes_tenant_{tid}
        # Fields: _key, metric_category, metric_max_lag_allowed, comment, mtime
        lagging_classes = {}
        if self.tenant_id:
            try:
                parsed_splunkd_uri = urllib.parse.urlparse(
                    self._metadata.searchinfo.splunkd_uri
                )
                service = client.connect(
                    token=self._metadata.searchinfo.session_key,
                    scheme=parsed_splunkd_uri.scheme,
                    host=parsed_splunkd_uri.hostname,
                    port=parsed_splunkd_uri.port,
                    app="trackme",
                    owner="nobody",
                    timeout=get_splunkd_timeout(reqinfo=reqinfo),
                )
                lagging_collection_name = f"kv_trackme_mhm_lagging_classes_tenant_{self.tenant_id}"
                lagging_collection = service.kvstore[lagging_collection_name]
                lagging_records = lagging_collection.data.query()
                for rec in lagging_records:
                    cat_name = rec.get("metric_category")
                    lag_val = rec.get("metric_max_lag_allowed")
                    if cat_name and lag_val is not None:
                        lagging_classes[cat_name] = lag_val
                logging.info(
                    f'tenant_id="{self.tenant_id}", loaded {len(lagging_classes)} '
                    f"lagging class overrides from {lagging_collection_name}"
                )
            except Exception as e:
                logging.warning(
                    f'tenant_id="{self.tenant_id}", failed to load lagging classes, '
                    f"using defaults only, exception: {e}"
                )

        # Accumulate metrics records for batch generation at end
        records_metrics = []
        output_records = []
        record_count = 0
        total_categories = 0

        # Cumulative sub-task timers (seconds)
        time_parse = 0.0
        time_merge = 0.0
        time_category_processing = 0.0
        time_output_build = 0.0

        # Init phase timing
        init_run_time = round(time.time() - start, 3)

        logging.info(
            f'tenant_id="{self.tenant_id}", trackmemhmpipeline starting, '
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

            # --- MERGE: preserve previous metric categories not in current ---
            t0 = time.time()
            if current_dict and previous_dict:
                for p_id, p_info in previous_dict.items():
                    if p_id not in current_dict:
                        current_dict[p_id] = p_info
            elif not current_dict and previous_dict:
                # current_dict is None/empty but previous has data — use previous as base
                current_dict = previous_dict

            if not current_dict:
                time_merge += time.time() - t0
                # No data to process — buffer with empty summary fields
                subrecord["metric_details"] = "{}"
                subrecord["metric_details_full"] = "{}"
                subrecord["metric_details_minimal"] = json.dumps({"green": 0, "red": 0})
                subrecord["metric_details_compact"] = "{}"
                subrecord["object_category"] = "splk-mhm"
                # Clean up input fields
                subrecord.pop(self.field_current, None)
                subrecord.pop(self.field_previous, None)
                output_records.append(subrecord)
                continue

            time_merge += time.time() - t0

            # --- GET THRESHOLDS ---
            # Default lag threshold from upstream macro on the record
            default_metric_max_lag = self._safe_float(
                subrecord.get("metric_max_lag_allowed"), 3600
            )

            # Per-metric-category lagging class overrides are loaded once at init
            # from the KV store (see lagging_classes dict above the loop)

            now_epoch = time.time()

            # --- PER-METRIC-CATEGORY PROCESSING ---
            t0 = time.time()
            # Track host-level aggregates
            max_last_time = 0
            min_first_time = float("inf")
            category_count = 0
            count_green = 0
            count_red = 0
            metric_indexes = set()
            metric_categories_set = set()

            # Build the raw metric_details dict (with state + lag_allowed)
            raw_details = {}

            for cat_hash, cat_info in current_dict.items():
                metric_category = cat_info.get("metric_category", "")
                metric_index = cat_info.get("idx", "")
                first_time = self._safe_float(cat_info.get("first_time"), 0)
                last_time = self._safe_float(cat_info.get("last_time"), 0)

                # Refresh last_metric_lag based on current time
                last_metric_lag = round(now_epoch - last_time, 2) if last_time > 0 else now_epoch

                # Determine lag threshold for this metric category
                # Priority: entity override > per-category lagging class > default
                metric_max_lag = default_metric_max_lag

                # Check per-category lagging class override
                cat_lag_override = lagging_classes.get(metric_category)
                if cat_lag_override is not None:
                    override_val = self._safe_float(cat_lag_override, None)
                    if override_val is not None:
                        metric_max_lag = override_val

                # Check entity-level override (applies to all categories)
                entity_override = subrecord.get("metric_override_lagging_class")
                if entity_override and entity_override != "false" and entity_override != "null":
                    override_val = self._safe_float(entity_override, None)
                    if override_val is not None:
                        metric_max_lag = override_val

                # Evaluate metric category state
                cat_state = "green"
                if last_metric_lag > metric_max_lag:
                    cat_state = "red"
                    count_red += 1
                else:
                    count_green += 1

                # Update host aggregates
                if last_time > max_last_time:
                    max_last_time = last_time
                if first_time > 0 and first_time < min_first_time:
                    min_first_time = first_time
                category_count += 1
                metric_indexes.add(metric_index)
                metric_categories_set.add(metric_category)

                # Build raw detail entry (stored in KV as metric_details)
                raw_details[cat_hash] = {
                    "metric_category": metric_category,
                    "idx": metric_index,
                    "first_time": str(int(first_time)) if first_time > 0 else "0",
                    "last_time": str(int(last_time)) if last_time > 0 else "0",
                    "last_metric_lag": str(last_metric_lag),
                    "time_measure": str(int(now_epoch)),
                    "state": cat_state,
                    "lag_allowed": str(metric_max_lag),
                }

            # Track total categories processed
            total_categories += category_count
            time_category_processing += time.time() - t0

            # --- BUILD OUTPUT FIELDS ---
            t0 = time.time()

            # metric_details: raw dict with all info (stored in KV, used by decision maker)
            subrecord["metric_details"] = json.dumps(raw_details)

            # metric_details_full: display view with formatted timestamps
            details_full = {}
            for cat_hash, cat_info in raw_details.items():
                last_time_val = int(float(cat_info["last_time"])) if cat_info["last_time"] != "0" else 0
                time_measure_val = int(float(cat_info["time_measure"])) if cat_info["time_measure"] != "0" else 0
                details_full[cat_hash] = {
                    "summary_idx": cat_info["idx"],
                    "summary_metric_category": cat_info["metric_category"],
                    "summary_last_time": time.strftime(
                        "%d %b %Y %H:%M:%S", time.localtime(last_time_val)
                    ) if last_time_val > 0 else "N/A",
                    "summary_last_metric_lag": cat_info["last_metric_lag"],
                    "summary_time_measure": time.strftime(
                        "%d %b %Y %H:%M:%S", time.localtime(time_measure_val)
                    ) if time_measure_val > 0 else "N/A",
                    "summary_max_lag_allowed": cat_info["lag_allowed"],
                    "state": cat_info["state"],
                }
            subrecord["metric_details_full"] = json.dumps(details_full)

            # metric_details_minimal: green/red counts
            subrecord["metric_details_minimal"] = json.dumps({
                "green": count_green,
                "red": count_red,
            })

            # metric_details_compact: one-line summary per category
            details_compact = {}
            for cat_hash, cat_info in raw_details.items():
                last_time_val = int(float(cat_info["last_time"])) if cat_info["last_time"] != "0" else 0
                details_compact[cat_hash] = {
                    "summary": f"idx:{cat_info['idx']} | last:{time.strftime('%d %b %Y %H:%M:%S', time.localtime(last_time_val)) if last_time_val > 0 else 'N/A'} | max:{cat_info['lag_allowed']} | state:{cat_info['state']}"
                }
            subrecord["metric_details_compact"] = json.dumps(details_compact)

            # Host-level aggregate fields
            subrecord["metric_last_time_seen"] = str(max_last_time)
            # Preserve historical metric_first_time_seen from KV store (set by macro on first discovery)
            # Only compute from current data if the record has no KV value
            existing_first = subrecord.get("metric_first_time_seen")
            if not existing_first or existing_first in ("", "0", "0.0", "None"):
                subrecord["metric_first_time_seen"] = str(min_first_time) if min_first_time != float("inf") else "0"

            # Compute host-level lag from most recent metric
            last_lag_seen = round(now_epoch - max_last_time, 2) if max_last_time > 0 else round(now_epoch, 2)
            subrecord["last_lag_seen"] = str(last_lag_seen)
            subrecord["metric_last_lag_seen"] = str(last_lag_seen)

            # Multi-value fields as comma-separated strings
            subrecord["metric_index"] = ",".join(sorted(metric_indexes))
            subrecord["metric_category"] = ",".join(sorted(metric_categories_set))

            # Set object_category
            subrecord["object_category"] = "splk-mhm"

            # Clean up input fields no longer needed
            subrecord.pop(self.field_current, None)
            subrecord.pop(self.field_previous, None)
            time_output_build += time.time() - t0

            # Collect metrics data for batch generation
            if self.gen_metrics == "True":
                records_metrics.append(
                    {
                        "object": subrecord.get("object", host),
                        "object_id": subrecord.get("key"),
                        "object_category": "splk-mhm",
                        "alias": subrecord.get("alias", host),
                        "metrics_dict": raw_details,
                    }
                )

            # Buffer records for post-stream processing safety
            output_records.append(subrecord)

        # --- BATCH METRICS GENERATION (before yielding, guaranteed to run) ---
        stream_run_time = round(time.time() - stream_start, 3)
        metrics_run_time = 0
        if self.gen_metrics == "True" and records_metrics and tenant_indexes:
            metrics_gen_start = time.time()
            try:
                gen_metrics = trackme_splk_mhm_gen_metrics(
                    self.tenant_id,
                    tenant_indexes.get("trackme_metric_idx"),
                    records_metrics,
                )
                metrics_run_time = round(time.time() - metrics_gen_start, 3)
                logging.info(
                    f'context="gen_metrics", tenant_id="{self.tenant_id}", '
                    f"function trackme_splk_mhm_gen_metrics success {gen_metrics}, "
                    f"run_time={metrics_run_time}, "
                    f"no_entities={len(records_metrics)}"
                )
            except Exception as e:
                metrics_run_time = round(time.time() - metrics_gen_start, 3)
                logging.error(
                    f'context="gen_metrics", tenant_id="{self.tenant_id}", '
                    f"function trackme_splk_mhm_gen_metrics failed, "
                    f'tenant_indexes="{tenant_indexes}", exception {str(e)}'
                )

        # Yield all buffered records
        for subrecord in output_records:
            yield subrecord

        # Log the total run time with full performance breakdown
        total_run_time = round(time.time() - start, 3)
        logging.info(
            f'tenant_id="{self.tenant_id}", trackmemhmpipeline has terminated, '
            f"hosts={record_count}, total_categories={total_categories}, "
            f"avg_categories_per_host={round(total_categories / record_count, 1) if record_count > 0 else 0}, "
            f"init_run_time={init_run_time}, "
            f"task_parse={round(time_parse, 3)}, "
            f"task_merge={round(time_merge, 3)}, "
            f"task_category_processing={round(time_category_processing, 3)}, "
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


dispatch(TrackMeMhmPipeline, sys.argv, sys.stdin, sys.stdout, __name__)
