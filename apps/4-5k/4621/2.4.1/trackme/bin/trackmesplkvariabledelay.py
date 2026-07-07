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
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_variable_delay.log" % splunkhome,
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
    trackme_idx_for_tenant,
    trackme_reqinfo,
    run_splunk_search,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# Pure helpers shared with `trackmesplkvariabledelayreview`,
# `trackmesplkadaptivedelay`, and `trackme_rest_handler_splk_variable_delay_user`.
# These used to live in this file; they were moved to a lib in #1717 so that
# the REST handler — and by transitive import the Health Tracker's
# API-catalog warmup — no longer drags this custom command's module-load
# code (which rebinds the root logger to trackme_variable_delay.log) into
# the caller's Python process.
from trackme_libs_variable_delay import (
    aggregate_slots,
    compute_threshold,
)


@Configuration(distributed=False)
class VariableDelay(GeneratingCommand):
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

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** The entity name to compute variable delay for. If not specified, compute for all entities with variable delay enabled.""",
        require=False,
        default=None,
    )

    method = Option(
        doc="""
        **Syntax:** **method=****
        **Description:** The statistical method to use: perc95 (default), perc99.""",
        require=False,
        default="perc95",
        validate=validators.Match("method", r"^(perc95|perc99)$"),
    )

    lookback = Option(
        doc="""
        **Syntax:** **lookback=****
        **Description:** The lookback period for metrics query (default: -30d).""",
        require=False,
        default="-30d",
    )

    min_samples = Option(
        doc="""
        **Syntax:** **min_samples=****
        **Description:** Minimum number of metric samples per hour/day to consider it valid (default: 10).""",
        require=False,
        default="10",
        validate=validators.Match("min_samples", r"^\d+$"),
    )

    dry_run = Option(
        doc="""
        **Syntax:** **dry_run=****
        **Description:** If true, returns proposed slots without saving (default: true).""",
        require=False,
        default="true",
        validate=validators.Match("dry_run", r"^(true|false)$"),
    )

    def generate(self):
        """Main entry point for the custom command."""

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        # get instance id
        instance_id = str(time.time())

        logging.info(
            f"instance_id={instance_id}, starting variable delay computation, "
            f'tenant_id="{self.tenant_id}", component="{self.component}", '
            f'object="{self.object}", method="{self.method}", lookback="{self.lookback}", '
            f'dry_run="{self.dry_run}"'
        )

        # get metric index for tenant
        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        metric_index = tenant_indexes.get("trackme_metric_idx", "trackme_metrics")

        # Build the SPL query to aggregate delay metrics per day/hour
        stat_func = "perc95" if self.method == "perc95" else "perc99"

        if self.object:
            object_filter = f'object="{self.object}"'
        else:
            object_filter = ""

        # Splunk %w: 0=Sunday, 1=Monday... We convert to Python weekday (0=Monday, 6=Sunday)
        search_query = remove_leading_spaces(
            f"""
            | mstats latest(trackme.splk.feeds.lag_event_sec) as lag_event_sec
              where index="{metric_index}"
              tenant_id="{self.tenant_id}"
              object_category="splk-{self.component}"
              {object_filter}
              earliest="{self.lookback}" latest="now"
              by object span=5m
            | eval day_of_week=tonumber(strftime(_time, "%w"))
            | eval day_of_week=if(day_of_week==0, 6, day_of_week-1)
            | eval hour_of_day=tonumber(strftime(_time, "%H"))
            | stats {stat_func}(lag_event_sec) as stat_delay,
                    avg(lag_event_sec) as avg_delay,
                    count as sample_count
              by object, day_of_week, hour_of_day
            | where sample_count >= {self.min_samples}
            """
        )

        logging.info(
            f"instance_id={instance_id}, running metrics query for variable delay computation"
        )

        # Run the search
        kwargs_search = {
            "earliest_time": self.lookback,
            "latest_time": "now",
            "output_mode": "json",
            # count=0 returns all rows. The stats produces up to 7*24 = 168
            # rows (day_of_week x hour_of_day); the Splunk default of 100
            # would silently truncate and yield incomplete hourly thresholds.
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
                f"instance_id={instance_id}, metrics query failed, exception=\"{str(e)}\""
            )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "error",
                        "message": f"Metrics query failed: {str(e)}",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "object": self.object or "all",
                    }
                ),
            }
            return

        if not search_results:
            logging.warning(
                f"instance_id={instance_id}, no metric results returned for variable delay computation"
            )
            yield {
                "_time": time.time(),
                "_raw": json.dumps(
                    {
                        "action": "no_data",
                        "message": "No metric data available for the specified parameters",
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "object": self.object or "all",
                    }
                ),
            }
            return

        # Group results by object
        objects_data = {}
        for result in search_results:
            obj = result.get("object")
            if obj not in objects_data:
                objects_data[obj] = {}

            try:
                day = int(float(result.get("day_of_week", 0)))
                hour = int(float(result.get("hour_of_day", 0)))
                stat_delay = float(result.get("stat_delay", 0))
                sample_count = int(float(result.get("sample_count", 0)))
            except (ValueError, TypeError):
                continue

            objects_data[obj][(day, hour)] = {
                "stat_delay": stat_delay,
                "sample_count": sample_count,
            }

        logging.info(
            f"instance_id={instance_id}, computed metrics for {len(objects_data)} entities"
        )

        # For each entity, compute thresholds and aggregate slots
        for obj, hourly_data in objects_data.items():

            # Compute per-hour thresholds
            hourly_thresholds = {}
            for (day, hour), data in hourly_data.items():
                threshold = compute_threshold(data["stat_delay"])
                hourly_thresholds[(day, hour)] = threshold

            # Aggregate into slots
            slots = aggregate_slots(hourly_thresholds)

            # Compute default (for uncovered hours) as max of all thresholds
            if hourly_thresholds:
                default_threshold = max(hourly_thresholds.values())
            else:
                default_threshold = 3600

            slots_config = {"slots": slots}

            result = {
                "_time": time.time(),
                "object": obj,
                "tenant_id": self.tenant_id,
                "component": self.component,
                "method": self.method,
                "lookback": self.lookback,
                "dry_run": self.dry_run,
                "variable_delay_default": str(default_threshold),
                "variable_delay_slots": json.dumps(slots_config),
                "slot_count": len(slots),
                "covered_hours": len(hourly_thresholds),
            }

            # If not dry_run, save to KVstore
            if self.dry_run != "true":
                try:
                    # Get entity _key from main collection first
                    main_collection_name = (
                        f"kv_trackme_{self.component}_tenant_{self.tenant_id}"
                    )
                    main_collection = self.service.kvstore[main_collection_name]
                    main_query = {"object": obj}
                    main_records = main_collection.data.query(
                        query=json.dumps(main_query)
                    )
                    if not main_records or len(main_records) == 0:
                        logging.warning(
                            f'instance_id={instance_id}, object="{obj}", entity not found in main collection, skipping KVstore write'
                        )
                        continue
                    main_record = main_records[0]
                    entity_key = main_record.get("_key")

                    collection_name = f"kv_trackme_{self.component}_variable_delay_tenant_{self.tenant_id}"
                    collection = self.service.kvstore[collection_name]

                    # Check if record exists (lookup by entity _key)
                    existing = collection.data.query(
                        query=json.dumps({"_key": entity_key})
                    )

                    now_epoch = str(time.time())
                    record = {
                        "_key": entity_key,
                        "object": obj,
                        "object_category": f"splk-{self.component}",
                        "tenant_id": self.tenant_id,
                        "variable_delay_enabled": "true",
                        "variable_delay_mode": "auto",
                        "variable_delay_default": str(default_threshold),
                        "variable_delay_slots": json.dumps(slots_config),
                        "variable_delay_auto_review_enabled": "false",
                        "variable_delay_auto_review_period": self.lookback,
                        "variable_delay_auto_review_method": self.method,
                        "variable_delay_mtime": now_epoch,
                        "variable_delay_updated_by": "trackmesplkvariabledelay",
                    }

                    if existing and len(existing) > 0:
                        record["variable_delay_ctime"] = existing[0].get(
                            "variable_delay_ctime", now_epoch
                        )
                        record["variable_delay_last_auto_review"] = now_epoch
                        record["variable_delay_auto_review_enabled"] = existing[
                            0
                        ].get("variable_delay_auto_review_enabled", "false")
                        collection.data.update(str(entity_key), json.dumps(record))
                    else:
                        record["variable_delay_ctime"] = now_epoch
                        record["variable_delay_last_auto_review"] = now_epoch
                        collection.data.insert(json.dumps(record))

                    # Update main entity collection. Only set the delay policy —
                    # allow_adaptive_delay is an independent per-entity opt-in
                    # (default "true") that is no longer coupled to variable
                    # delay (the adaptive framework handles variable-delay
                    # entities since PR #1611). Preserve the operator's value.
                    main_record["variable_delay_policy"] = "variable"
                    main_collection.data.update(
                        str(entity_key), json.dumps(main_record)
                    )

                    # Audit event
                    trackme_audit_event(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "trackmesplkvariabledelay",
                        "success",
                        "auto-compute variable delay",
                        str(obj),
                        f"splk-{self.component}",
                        json.dumps(slots_config),
                        f"Variable delay auto-computed with {len(slots)} slots using {self.method} over {self.lookback}",
                        "auto-computation",
                    )

                    result["action"] = "saved"
                    logging.info(
                        f'instance_id={instance_id}, saved variable delay for object="{obj}", slots={len(slots)}'
                    )

                except Exception as e:
                    result["action"] = "error"
                    result["error"] = str(e)
                    logging.error(
                        f'instance_id={instance_id}, failed to save variable delay for object="{obj}", exception="{str(e)}"'
                    )
            else:
                result["action"] = "dry_run"

            yield result

        logging.info(
            f"instance_id={instance_id}, variable delay computation complete"
        )


dispatch(VariableDelay, sys.argv, sys.stdin, sys.stdout, __name__)
