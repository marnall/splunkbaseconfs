# Copyright 2026 Cisco, Inc.
import json
import logging
import math
import os
import random
import re
import sys
import time
import uuid
from collections import namedtuple
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence, Tuple

import splunk
from splunk import ResourceNotFound, SplunkdConnectionException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.constants import DATA_ID_INDEX_METADATA, DATA_ID_SOURCETYPE_METADATA
from spl_gen.remote.factory import SaiaApiFactory
from spl_gen.remote.v2alpha1 import SAIAApiV2
from spl_gen.saia_field_summary_collection import SaiaFieldSummaryCollection
from spl_gen.utils import deterministic_hash, get_app_version, log_kwargs
from spl_gen.utils.log import add_log_extra_metadata, setup_logger
from spl_gen.utils.modinput.fields import BooleanField
from spl_gen.utils.modinput.json_modinput import JsonModularInput
from spl_gen.utils.requests import OutputMode, send_request
from spl_gen.utils.splunk_search import create_search_job, get_search_results
from splunklib.binding import handler
from splunklib.client import connect
from splunklib.searchcommands import environment

FIELD_SUMMARIES_CONTEXT_NAME = "spl_field_summaries"

SECONDS_IN_DAY = 86400
SECONDS_IN_HOUR = 3600
DEFAULT_MAX_SEARCH_RANGE_SECONDS = 7 * SECONDS_IN_DAY
DEFAULT_MAX_CHUNK_RANGE_SECONDS = SECONDS_IN_DAY

# default Values for search parameters
D_MIN_MINIMUM_EVENT_COUNT_PER_TUPLE = 10
D_MAX_MINIMUM_EVENT_COUNT_PER_TUPLE = 50
D_MAXIMUM_EVENT_BATCH_SIZE = 15000
D_TARGET_SEARCH_COUNT = 500
D_MAXIMUM_SEARCH_COUNT = 100
D_MAXIMUM_TUPLES_FOR_SEARCH = 500
D_MAXIMUM_COUNT_NO_SAMPLING = 100
D_MAXIMUM_EVENTS_SEARCH_COUNT = 7000000000
LARGEST_SAMPLING_RATIO = 100000
SAMPLING_INTERVAL_SECONDS = 14 * SECONDS_IN_DAY
TARGET_EVENTS_PER_RUN = 1000
MIN_EVENTS_NO_SAMPLING = 1000
HIGH_EVENT_THRESHOLD = 100000000
HIGH_EVENT_INITIAL_LOOKBACK_SECONDS = 1
HIGH_EVENT_LOOKBACK_MULTIPLIER = 2
HIGH_EVENT_LOOKBACK_ATTEMPTS = 5
FALLBACK_LOOKBACK_SECONDS = SECONDS_IN_HOUR
FALLBACK_EVENT_TARGET = 10
COALESCE_MIN_SHARED_LENGTH = 18
COALESCE_MIN_SHARED_RATIO = 0.6
SAMPLING_SEARCH_MAX_RUNTIME = 10
STATE_BATCH_SAVE_SIZE = 1000
FIELD_SUMMARY_DATA_IDS = (
    DATA_ID_SOURCETYPE_METADATA,
    DATA_ID_INDEX_METADATA,
)

SA_CONF_URL = f"{splunk.rest.makeSplunkdUri()}servicesNS/nobody/Splunk_AI_Assistant_Cloud/configs/conf-saiafieldsummary"

logger = setup_logger("saia_field_summary_modinput")
LOGGER_METADATA_TAG = "saia_field_summary_modinput"


def time_modifier_from_timestamp(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


Macro = namedtuple("Macro", ["name", "use_time_range"])
TimeModifiers = namedtuple("TimeModifiers", ["earliest", "latest"])
Index_Sourcetype_Size = namedtuple(
    "Index_Sourcetype_Size", ["index", "sourcetype", "size", "latest_time"]
)
Stack_Server = namedtuple("Stack_Server", ["stack", "server"])
CoalescedGroup = namedtuple(
    "CoalescedGroup", ["index", "pattern", "sourcetype", "sourcetypes", "size"]
)


class SAIAFieldSummaryModularInputConfig:
    """
    A class responsible for managing the Security Assistant mod_input configuration.
    """

    def __init__(self, session_key: str, this_logger: logging.Logger = logger):
        self.session_key = session_key
        self.logger = this_logger
        config_data = self._retrieve_sa_config_data()
        config = self._parse_sa_config_data(config_data)
        self.settings = config["settings"]
        self.status = config["status"]
        self.search_params = config["search_params"]

    def _retrieve_sa_config_data(self) -> Dict:
        self.logger.debug(f"Fetching SA configuration data from {SA_CONF_URL}")
        return send_request(
            url=SA_CONF_URL,
            method="get",
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _update_sa_config_data(self) -> Dict:
        self.logger.debug(f"Updating SA configuration data at {SA_CONF_URL}/status")
        return send_request(
            url=f"{SA_CONF_URL}/status",
            method="post",
            data={
                "last_context_update_timestamp": self.status[
                    "last_context_update_timestamp"
                ],
            },
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _parse_sa_config_data(self, config_data: Dict) -> Dict:
        self.logger.debug(
            "Parsing configuration entries into structured settings and status"
        )
        config = {}
        for entry in config_data["entry"]:
            content = entry["content"]
            if entry["name"] == "settings":
                config["settings"] = {
                    "context_update_interval_seconds": int(
                        content["context_update_interval_seconds"].strip() or 0
                    ),
                    "max_search_range_seconds": int(
                        content["max_search_range_seconds"].strip()
                        or DEFAULT_MAX_SEARCH_RANGE_SECONDS
                    )
                    or DEFAULT_MAX_SEARCH_RANGE_SECONDS,
                    "max_chunk_range_seconds": int(
                        content["max_chunk_range_seconds"].strip()
                        or DEFAULT_MAX_CHUNK_RANGE_SECONDS
                    )
                    or DEFAULT_MAX_CHUNK_RANGE_SECONDS,
                }
            elif entry["name"] == "status":
                config["status"] = {
                    "last_context_update_timestamp": int(
                        content["last_context_update_timestamp"].strip() or 0
                    ),
                }
            elif entry["name"] == "search_params":
                config["search_params"] = {
                    "min_minimum_event_count_per_tuple": int(
                        content["min_minimum_event_count_per_tuple"].strip()
                        or D_MIN_MINIMUM_EVENT_COUNT_PER_TUPLE
                    ),
                    "max_minimum_event_count_per_tuple": int(
                        content["max_minimum_event_count_per_tuple"].strip()
                        or D_MAX_MINIMUM_EVENT_COUNT_PER_TUPLE
                    ),
                    "maximum_event_batch_size": int(
                        content["maximum_event_batch_size"].strip()
                        or D_MAXIMUM_EVENT_BATCH_SIZE
                    ),
                    "target_search_count": int(
                        content["target_search_count"].strip() or D_TARGET_SEARCH_COUNT
                    ),
                    "maximum_search_count": int(
                        content["maximum_search_count"].strip()
                        or D_MAXIMUM_SEARCH_COUNT
                    ),
                    "maximum_tuples_for_search": int(
                        content["maximum_tuples_for_search"].strip()
                        or D_MAXIMUM_TUPLES_FOR_SEARCH
                    ),
                    "maximum_count_no_sampling": int(
                        content["maximum_count_no_sampling"].strip()
                        or D_MAXIMUM_COUNT_NO_SAMPLING
                    ),
                    "maximum_events_search_count": int(
                        content["maximum_events_search_count"].strip()
                        or D_MAXIMUM_EVENTS_SEARCH_COUNT
                    ),
                }

        return config

    def update(
        self,
        *,
        last_context_update_timestamp: Optional[int] = None,
    ) -> None:
        if last_context_update_timestamp is not None:
            self.status["last_context_update_timestamp"] = last_context_update_timestamp
        try:
            self._update_sa_config_data()
        except Exception as e:
            self.logger.exception("Failed to update SA configuration data: %s", e)

    def get_search_params(self) -> dict:
        return self.search_params

    def is_context_update_due(self) -> bool:
        return (
            int(time.time()) - self.status["last_context_update_timestamp"]
            >= self.settings["context_update_interval_seconds"]
        )

    def __str__(self):
        return f"settings={self.settings}, status={self.status}, search_params={self.search_params}"


class SAIAFieldSummaryModularInput(JsonModularInput):
    def __init__(self, this_logger: logging.Logger = logger):
        """Initialize the modular input schema and default runtime state."""
        environment.app_root = os.path.join(os.path.dirname(__file__), "..")
        scheme_args = {
            "title": "Splunk AI Assistant Field Summary Modular Input",
            "description": "Collects field summary context for personalized SPL generation",
            "use_external_validation": "true",
            "streaming_mode": "json",
            "use_single_instance": "true",
            "supported_on_cloud": "true",
            "supported_on_onprem": "true",
            "supported_on_fedramp": "true",
            # "skip_wait_for_es": "true", # Doesn't matter, we're not ES
        }
        self._chunk_count = 0
        self.search_params = dict()
        args = [
            BooleanField(
                "debug",
                "Debug",
                "If true, debug logging is enabled.",
                required_on_create=False,
            )
        ]
        super().__init__(scheme_args, args, this_logger)

    def create_search(
        self,
        spl: str,
        time_modifiers: TimeModifiers,
        spl_name: str,
        sample_ratio=None,
        max_time=None,
    ) -> str:
        """
        creates a splunk search and returns the sid of the search
        :param spl: str -> spl string to generate a search fo
        :param time_modifiers: TimeModifers -> TimeModifiers tuple which contains earliest and latest times for the search
        :param spl_name: str -> name of the spl to log
        :param sample_ratio: int -> species how many samples should we sample
        :return sid: str -> a list of search results
        """

        self.logger.info(f"Creating search job for '{spl_name}'")
        try:
            sid = create_search_job(
                search=spl,
                earliest=time_modifiers.earliest,
                latest=time_modifiers.latest,
                sample_ratio=sample_ratio,
                max_time=max_time,
                session_key=self._input_config.session_key,
                logger=self.logger,
            )
            if not sid:
                raise Exception(
                    f"Failed to create search job for '{spl_name}' SPL context"
                )
            return sid
        except SplunkdConnectionException as e:
            raise Exception(
                f"Failed to create search job for '{spl_name}' SPL context"
            ) from e

    def create_search_and_get_results(
        self,
        spl: str,
        time_modifiers: TimeModifiers,
        spl_name: str,
        sample_ratio=None,
        max_time=None,
    ) -> list:
        """
        creates a splunk search and returns the results of the search
        :param spl: str -> spl string to generate a search fo
        :param time_modifiers: TimeModifers -> TimeModifiers tuple which contains earliest and latest times for the search
        :param spl_name: str -> name of the spl to log
        :param sample_ratio: int -> species how many samples should we sample
        :return content: list[dict[str,str]] -> a list of search results
        """

        try:
            sid = self.create_search(
                spl=spl,
                time_modifiers=time_modifiers,
                spl_name=spl_name,
                sample_ratio=sample_ratio,
                max_time=max_time,
            )
            self.logger.info(f"Fetching search result for '{spl_name}' SPL context")

            content = get_search_results(
                sid=sid,
                session_key=self._input_config.session_key,
                logger=self.logger,
                strict_unicode=False,
            )
            if content is None:
                self.logger.warning(
                    f"Failed to fetch search result for '{spl_name}' SPL context"
                )
                return []
            self.logger.info(
                "Search completed",
                extra={
                    "metadata": {
                        "spl_name": spl_name,
                        "row_count": len(content),
                    }
                },
            )
            return content
        except (SplunkdConnectionException, ResourceNotFound) as e:
            raise Exception(
                f"Failed to fetch search result for '{spl_name}' SPL context"
            ) from e

    # TODO: Can we share code below somewhere between MC and SAIA?
    def get_spl_context(
        self, *, earliest: int, latest: int, service=None, collection=None, api=None
    ) -> Dict[str, Dict]:
        """
        runs several searches to gather splunk environement context
        :param earliest: int-> the earliest time to run all the searches for
        :param latest: int -> the latest time to run all the searches for
        :return spl_context dict[str,Dict]] -> a dictionary containing the context for each of the types
        """
        spl_context = {}

        # process field summaries spl context differently
        field_summaries_content = self.get_field_summaries_spl_context(
            earliest=earliest,
            latest=latest,
            service=service,
            collection=collection,
            api=api,
        )

        spl_context[FIELD_SUMMARIES_CONTEXT_NAME] = field_summaries_content

        return spl_context

    def get_field_summaries_spl_context(
        self, *, earliest: int, latest: int, service=None, collection=None, api=None
    ):
        """
        Build field summary context using a round-robin, per-index/sourcetype sampling strategy with dynamic scaling.
        """

        field_summaries_context = []
        index_sourcetype_size_tuples = []
        index_sourcetype_size_dict: Dict[str, Dict[str, int]] = {}
        pending_sampled_pairs: Dict[Tuple[str, str], int] = {}

        if service is None or collection is None:
            service, collection = self._get_service_and_collection()
        if api is None:
            api = self._create_saia_api(service)

        logger.info("Loading last sampled map from collection")
        last_sampled_map = self._load_last_sampled_map(collection)
        logger.info("Loaded last sampled map from collection")

        time_modifiers = TimeModifiers(
            earliest=time_modifier_from_timestamp(earliest),
            latest=time_modifier_from_timestamp(latest),
        )
        listing_spl = (
            "| tstats count latest(_time) as latest_time where "
            "`saias_field_summary_indexes` by sourcetype index "
            "| dedup sourcetype, index"
        )

        self.logger.info("Collecting index/sourcetype inventory for sampling")
        content = self.create_search_and_get_results(
            spl=listing_spl,
            time_modifiers=time_modifiers,
            spl_name="index_sourcetype_listing",
            max_time=120,
        )
        self._submit_index_metadata(api, content, str(uuid.uuid4()))

        for content_row in content:
            try:
                index_name = content_row.get("index") or content_row["indexname"]
                sourcetype_name = (
                    content_row.get("sourcetype") or content_row["sourcetypename"]
                )
                size = int(content_row.get("count") or content_row["size"])
                latest_time = int(
                    float(content_row.get("latest_time") or content_row["latest_time"])
                )
            except (KeyError, ValueError, TypeError) as e:
                raise Exception("Failed to parse index/sourcetype inventory row") from e

            idx_src_size_tuple = Index_Sourcetype_Size(
                index=index_name,
                sourcetype=sourcetype_name,
                size=size,
                latest_time=latest_time,
            )
            index_sourcetype_size_tuples.append(idx_src_size_tuple)
            index_sourcetype_size_dict.setdefault(index_name, {})[sourcetype_name] = (
                size
            )

        if not index_sourcetype_size_tuples:
            raise Exception(
                "Failed to fetch search result for field summaries SPL context, no index/sourcetype tuples"
            )

        self._sync_sampling_state_from_listing(
            collection=collection,
            index_sourcetype_size_tuples=index_sourcetype_size_tuples,
            last_sampled_map=last_sampled_map,
        )

        eligible_entries = self._filter_and_order_entries(
            index_sourcetype_size_tuples, last_sampled_map
        )
        max_searches = self.search_params.get(
            "target_search_count", D_TARGET_SEARCH_COUNT
        )
        sampling_cutoff = self.search_params.get(
            "maximum_events_search_count", D_MAXIMUM_EVENTS_SEARCH_COUNT
        )

        self.logger.info(
            "Prepared sampling plan",
            extra={
                "metadata": {
                    "eligible_pairs": len(eligible_entries),
                    "max_searches": max_searches,
                    "sampling_cutoff": sampling_cutoff,
                }
            },
        )

        searches_executed = 0
        for st_entry in eligible_entries:
            if searches_executed >= max_searches:
                self.logger.info(
                    "Executed more than max search count, stopping sampling for this run.",
                    extra={
                        "metadata": {
                            "index": st_entry.index,
                            "sourcetype": st_entry.sourcetype,
                            "size": st_entry.size,
                            "sampling_cutoff": sampling_cutoff,
                        }
                    },
                )
                break
            if st_entry.size > sampling_cutoff:
                self.logger.info(
                    "Skipping sampling because estimated size exceeds cutoff",
                    extra={
                        "metadata": {
                            "index": st_entry.index,
                            "sourcetype": st_entry.sourcetype,
                            "size": st_entry.size,
                            "sampling_cutoff": sampling_cutoff,
                        }
                    },
                )
                continue

            searches_executed += 1
            spl = self._fieldsummary_command(st_entry.index, st_entry.sourcetype)
            sampling_plan = self._build_sampling_plan(
                size=st_entry.size,
                earliest=earliest,
                latest=latest,
                latest_time=st_entry.latest_time,
            )
            spl_name = f"{st_entry.index}:{st_entry.sourcetype}"

            content = self.create_search_and_get_results(
                spl=spl,
                time_modifiers=sampling_plan["time_modifiers"],
                spl_name=spl_name,
                sample_ratio=sampling_plan["sample_ratio"],
                max_time=sampling_plan["max_time"],
            )

            if st_entry.size > HIGH_EVENT_THRESHOLD and not content:
                content = self._retry_high_volume_sampling(
                    spl=spl,
                    st_entry=st_entry,
                    spl_name=spl_name,
                    latest_time=st_entry.latest_time,
                    base_sample_ratio=sampling_plan["sample_ratio"],
                )
            if not content:
                self.logger.info(
                    "Sourcetype returned no results",
                    extra={
                        "metadata": {
                            "index": st_entry.index,
                            "sourcetype": st_entry.sourcetype,
                            "size": st_entry.size,
                            "sample_ratio": sampling_plan["sample_ratio"],
                        }
                    },
                )

            before_transpose_count = len(field_summaries_context)
            self.transpose_field_summaries_content(
                content=content,
                field_summaries_context=field_summaries_context,
                index_sourcetype_size_dict=index_sourcetype_size_dict,
                spl_name=spl_name,
            )
            if len(field_summaries_context) > before_transpose_count:
                pending_sampled_pairs[(st_entry.index, st_entry.sourcetype)] = (
                    st_entry.latest_time
                )

        self.logger.info("Successfully got field_summaries_context")

        return {
            "results": field_summaries_context,
            "last_sampled_map": last_sampled_map,
            "pending_sampled_pairs": pending_sampled_pairs,
        }

    def _get_service_and_collection(self):
        """Create a Splunk service client and the sampling-state KV collection wrapper."""
        user = "splunk-system-user"
        service = connect(
            token=self._input_config.session_key,
            handler=handler(timeout=30),
            host="127.0.0.1",
            app="Splunk_AI_Assistant_Cloud",
            owner=user,
            retries=2,
        )
        collection = SaiaFieldSummaryCollection(service)
        return service, collection

    def _load_last_sampled_map(self, collection) -> Dict:
        """Load the last-sampled timestamps keyed by (index, sourcetype) from KV store."""
        last_sampled_map = {}
        try:
            records = collection.get()
            for entry in records:
                idx = entry.get("index")
                sourcetype = entry.get("sourcetype")
                last_sampled = entry.get("last_sampled")
                if idx and sourcetype and last_sampled is not None:
                    try:
                        last_sampled_map[(idx, sourcetype)] = int(last_sampled)
                    except (TypeError, ValueError):
                        continue
        except Exception as e:
            self.logger.warning(
                "Unable to read last sampled map from KV store", exc_info=e
            )
        return last_sampled_map

    def _sync_sampling_state_from_listing(
        self, collection, index_sourcetype_size_tuples, last_sampled_map
    ) -> None:
        """Update KVStore state from the current listing search results."""
        entries_to_save = []
        seen_keys = set()

        for st_entry in index_sourcetype_size_tuples:
            sampling_key = (st_entry.index, st_entry.sourcetype)
            if sampling_key in seen_keys:
                continue
            seen_keys.add(sampling_key)

            last_sampled = int(last_sampled_map.get(sampling_key, 0) or 0)
            last_sampled_map.setdefault(sampling_key, last_sampled)
            entries_to_save.append(
                {
                    "_key": f"{st_entry.index}:{st_entry.sourcetype}",
                    "index": st_entry.index,
                    "sourcetype": st_entry.sourcetype,
                    "last_sampled": last_sampled,
                    "latest_time": st_entry.latest_time,
                }
            )

        for index in range(0, len(entries_to_save), STATE_BATCH_SAVE_SIZE):
            batch = entries_to_save[index : index + STATE_BATCH_SAVE_SIZE]
            collection.batch_save(batch)

    def _filter_and_order_entries(self, index_sourcetype_size_tuples, last_sampled_map):
        """Filter eligible pairs by sampling interval and prioritize never-sampled pairs first."""
        now_ts = int(time.time())
        eligible = []

        for st_entry in index_sourcetype_size_tuples:
            last_sampled = last_sampled_map.get(
                (st_entry.index, st_entry.sourcetype), 0
            )
            if last_sampled == 0 or now_ts - last_sampled >= SAMPLING_INTERVAL_SECONDS:
                eligible.append(
                    (
                        0 if last_sampled == 0 else 1,
                        last_sampled,
                        -st_entry.latest_time,
                        st_entry,
                    )
                )
                self.logger.info(
                    "Including sourcetype for sampling",
                    extra={
                        "metadata": {
                            "index": st_entry.index,
                            "sourcetype": st_entry.sourcetype,
                            "last_sampled": last_sampled,
                            "latest_time": st_entry.latest_time,
                        }
                    },
                )
            else:
                self.logger.info(
                    "Filtering out sourcetype from sampling",
                    extra={
                        "metadata": {
                            "index": st_entry.index,
                            "sourcetype": st_entry.sourcetype,
                            "last_sampled": last_sampled,
                            "latest_time": st_entry.latest_time,
                        }
                    },
                )

        eligible.sort(key=lambda item: item[:3])
        return [st_entry for *_, st_entry in eligible]

    def _longest_common_affix(self, lhs: str, rhs: str):
        """Return the longest shared prefix/suffix and which type it is, or (None, None)."""
        prefix = os.path.commonprefix([lhs, rhs])
        suffix = os.path.commonprefix([lhs[::-1], rhs[::-1]])[::-1]
        best = prefix if len(prefix) >= len(suffix) else suffix
        if best == lhs == rhs:
            return None, None

        if len(best) < COALESCE_MIN_SHARED_LENGTH:
            return None, None
        if len(best) < COALESCE_MIN_SHARED_RATIO * min(len(lhs), len(rhs)):
            return None, None
        return best, "prefix" if len(prefix) >= len(suffix) else "suffix"

    def _coalesce_sourcetypes(self, index_sourcetype_size_tuples):
        """Coalesce sourcetypes only when they differ by a numeric suffix."""
        groups = []
        tuples_by_index: Dict[str, list[Index_Sourcetype_Size]] = {}
        for entry in index_sourcetype_size_tuples:
            tuples_by_index.setdefault(entry.index, []).append(entry)

        for index, entries in tuples_by_index.items():
            grouped: Dict[str, Dict[str, Any]] = {}
            for entry in sorted(entries, key=lambda x: x.sourcetype):
                match = re.match(r"^(.*?)(\d+)$", entry.sourcetype)
                if match and match.group(1):
                    base = match.group(1)
                    key = base
                    pattern = f"{base}*"
                else:
                    key = entry.sourcetype
                    pattern = entry.sourcetype

                group = grouped.get(key)
                if group is None:
                    grouped[key] = {
                        "pattern": pattern,
                        "sourcetypes": [entry],
                        "size": entry.size,
                    }
                else:
                    group["sourcetypes"].append(entry)
                    group["size"] += entry.size

            for group in grouped.values():
                groups.append(
                    CoalescedGroup(
                        index=index,
                        pattern=group["pattern"],
                        sourcetype=group["pattern"],
                        sourcetypes=group["sourcetypes"],
                        size=group["size"],
                    )
                )
        return groups

    def _filter_and_order_groups(self, groups, last_sampled_map):
        """Filter eligible groups by sampling interval and order by oldest sample time.
        We do not sample groups where all sourcetypes were sampled within the interval."""
        now_ts = int(time.time())
        eligible = []
        for group in groups:
            stale_timestamps = []
            for st_entry in group.sourcetypes:
                last_sampled = last_sampled_map.get(
                    (st_entry.index, st_entry.sourcetype)
                )
                if (
                    last_sampled is None
                    or now_ts - last_sampled >= SAMPLING_INTERVAL_SECONDS
                ):
                    stale_timestamps.append(last_sampled or 0)
                    self.logger.info(
                        "Including sourcetype for sampling",
                        extra={
                            "metadata": {
                                "index": st_entry.index,
                                "sourcetype": st_entry.sourcetype,
                                "last_sampled": last_sampled,
                            }
                        },
                    )
                else:
                    self.logger.info(
                        "Filtering out sourcetype from sampling",
                        extra={
                            "metadata": {
                                "index": st_entry.index,
                                "sourcetype": st_entry.sourcetype,
                                "last_sampled": last_sampled,
                            }
                        },
                    )
            if stale_timestamps:
                eligible.append((min(stale_timestamps), group))
        eligible.sort(key=lambda x: x[0])
        return [group for _, group in eligible]

    def _fieldsummary_command(self, index: str, sourcetype_pattern: str) -> str:
        """Build the fieldsummary SPL for a single index/sourcetype (or pattern)."""
        index_fragment = f'index="{index}"'
        if "*" in sourcetype_pattern or "?" in sourcetype_pattern:
            sourcetype_fragment = f"sourcetype={sourcetype_pattern}"
        else:
            sourcetype_fragment = f'sourcetype="{sourcetype_pattern}"'
        return (
            f"search {index_fragment} {sourcetype_fragment} | fieldsummary "
            f'| eval index="{index}", sourcetype="{sourcetype_pattern}"'
        )

    def _build_sampling_plan(
        self, size: int, earliest: int, latest: int, latest_time: int
    ) -> Dict[str, Any]:
        """
        Compute the sampling plan for a given index/sourcetype size.

        Returns a dict with:
        - sample_ratio: None for unsampled searches, or an integer ratio targeting
          TARGET_EVENTS_PER_RUN results for medium-sized datasets.
        - time_modifiers: earliest/latest timestamps to bound the search.
        - max_time: per-search runtime cap (seconds).

        Behavior:
        - size < MIN_EVENTS_NO_SAMPLING: no sampling, full lookback (earliest/latest).
        - MIN_EVENTS_NO_SAMPLING <= size < HIGH_EVENT_THRESHOLD: sample ratio scales
          so that roughly TARGET_EVENTS_PER_RUN events are returned.
        - size >= HIGH_EVENT_THRESHOLD: no sampling ratio here; the caller uses a
          short lookback window ending at the most recent event time.
        """
        reference_latest = latest_time or latest
        if size < MIN_EVENTS_NO_SAMPLING:
            sample_ratio = None
        elif size < HIGH_EVENT_THRESHOLD:
            sample_ratio = min(
                LARGEST_SAMPLING_RATIO, max(1, math.ceil(size / TARGET_EVENTS_PER_RUN))
            )
        else:
            sample_ratio = None

        if size > HIGH_EVENT_THRESHOLD:
            lookback = HIGH_EVENT_INITIAL_LOOKBACK_SECONDS
            time_modifiers = TimeModifiers(
                earliest=time_modifier_from_timestamp(reference_latest - lookback),
                latest=time_modifier_from_timestamp(reference_latest),
            )
            return {
                "sample_ratio": sample_ratio,
                "time_modifiers": time_modifiers,
                "max_time": SAMPLING_SEARCH_MAX_RUNTIME,
            }

        window_size = max(0, latest - earliest)
        time_modifiers = TimeModifiers(
            earliest=time_modifier_from_timestamp(
                max(earliest, reference_latest - window_size)
            ),
            latest=time_modifier_from_timestamp(reference_latest),
        )
        return {
            "sample_ratio": sample_ratio,
            "time_modifiers": time_modifiers,
            "max_time": SAMPLING_SEARCH_MAX_RUNTIME,
        }

    def _retry_high_volume_sampling(
        self,
        spl: str,
        st_entry: Index_Sourcetype_Size,
        spl_name: str,
        latest_time: int,
        base_sample_ratio=None,
    ):
        """
        Retry high-volume sampling by progressively expanding the lookback window.

        Strategy:
        - Start with HIGH_EVENT_INITIAL_LOOKBACK_SECONDS and expand the lookback by
          HIGH_EVENT_LOOKBACK_MULTIPLIER for HIGH_EVENT_LOOKBACK_ATTEMPTS attempts.
        - Each retry reuses the same SPL and base_sample_ratio, and respects the
          SAMPLING_SEARCH_MAX_RUNTIME cap.
        - If all retries return empty results, fall back to a longer window
          (FALLBACK_LOOKBACK_SECONDS) with a much larger sampling ratio targeting
          roughly FALLBACK_EVENT_TARGET events.

        Returns the first non-empty result set, or the fallback attempt results.
        """
        lookback = HIGH_EVENT_INITIAL_LOOKBACK_SECONDS
        for attempt in range(HIGH_EVENT_LOOKBACK_ATTEMPTS):
            time_modifiers = TimeModifiers(
                earliest=time_modifier_from_timestamp(latest_time - lookback),
                latest=time_modifier_from_timestamp(latest_time),
            )
            self.logger.info(
                "Retrying high-volume sampling with expanded lookback",
                extra={
                    "metadata": {
                        "attempt": attempt + 1,
                        "lookback_seconds": lookback,
                        "sourcetype": st_entry.sourcetype,
                    }
                },
            )
            content = self.create_search_and_get_results(
                spl=spl,
                time_modifiers=time_modifiers,
                spl_name=f"{spl_name}_attempt_{attempt + 1}",
                sample_ratio=base_sample_ratio,
                max_time=SAMPLING_SEARCH_MAX_RUNTIME,
            )
            if content:
                return content
            lookback *= HIGH_EVENT_LOOKBACK_MULTIPLIER

        fallback_sample_ratio = max(1, math.ceil(st_entry.size / FALLBACK_EVENT_TARGET))
        fallback_time_modifiers = TimeModifiers(
            earliest=time_modifier_from_timestamp(
                latest_time - FALLBACK_LOOKBACK_SECONDS
            ),
            latest=time_modifier_from_timestamp(latest_time),
        )
        self.logger.info(
            "Retrying high-volume sampling with 1h fallback",
            extra={
                "metadata": {
                    "sourcetype": st_entry.sourcetype,
                    "sample_ratio": fallback_sample_ratio,
                    "lookback_seconds": FALLBACK_LOOKBACK_SECONDS,
                }
            },
        )
        return self.create_search_and_get_results(
            spl=spl,
            time_modifiers=fallback_time_modifiers,
            spl_name=f"{spl_name}_fallback",
            sample_ratio=fallback_sample_ratio,
            max_time=30,
        )

    def _submit_sourcetype_metadata(self, api, field_data, request_id: str):
        """Send field summary metadata to the backend in a single request."""
        if not field_data:
            return
        response = api.submit_sourcetype_metadata(
            field_data=field_data,
            request_id=request_id,
        )
        self._assert_successful_upload_response(response, "sourcetype metadata upload")

    def _submit_index_metadata(self, api, field_data, request_id: str) -> None:
        """Send index/sourcetype inventory metadata to the backend in a single request."""
        if not field_data:
            return
        response = api.submit_index_metadata(
            field_data=field_data,
            request_id=request_id,
        )
        self._assert_successful_upload_response(response, "index metadata upload")

    @staticmethod
    def _assert_successful_upload_response(response, upload_name: str) -> None:
        """Validate that the service accepted a metadata upload request."""
        if response is None:
            raise Exception(f"{upload_name} did not return a response")

        raise_for_status = getattr(response, "raise_for_status", None)
        if callable(raise_for_status):
            raise_for_status()

        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int) and not 200 <= status_code < 300:
            raise Exception(
                f"{upload_name} failed with unexpected status code {status_code}"
            )

    def _persist_sampled_pairs_after_upload(
        self,
        *,
        collection,
        field_data,
        pending_sampled_pairs: Dict[Tuple[str, str], int],
        sampled_at: int,
    ) -> None:
        """Persist last-sampled timestamps only for pairs that were actually uploaded."""
        if not field_data or not pending_sampled_pairs:
            return

        uploaded_pairs = set()
        for row in field_data:
            index = row.get("index")
            sourcetype = row.get("sourcetype")
            if not index or not sourcetype:
                continue
            uploaded_pairs.add((index, sourcetype))

        for index, sourcetype in sorted(uploaded_pairs):
            latest_time = pending_sampled_pairs.get((index, sourcetype))
            if latest_time is None:
                continue
            self._save_last_sampled_entry(
                collection=collection,
                index=index,
                sourcetype=sourcetype,
                last_sampled=sampled_at,
                latest_time=latest_time,
            )

    def _should_upload_for_tenant(self, api, request_id: str) -> bool:
        """Check whether the service wants this tenant to upload field-summary data."""
        if not isinstance(api, SAIAApiV2):
            self.logger.info(
                "Skipping field summary upload preflight because agent mode is disabled"
            )
            return True

        for data_id in FIELD_SUMMARY_DATA_IDS:
            should_upload = api.get_data_status(data_id=data_id, request_id=request_id)
            if not should_upload:
                self.logger.info(
                    "Skipping field summary run because tenant upload preflight denied upload",
                    extra={
                        "metadata": {
                            "data_id": data_id,
                            "request_id": request_id,
                            "should_upload": should_upload,
                        }
                    },
                )
                return False

        return True

    @staticmethod
    def _create_saia_api(service):
        user = "splunk-system-user"
        hashed_user = deterministic_hash(user)
        return SaiaApiFactory.from_agent_mode_setting(
            service,
            service,
            user,
            None,
            hashed_user,
        )

    @staticmethod
    def transpose_field_summaries_content(
        content, field_summaries_context, index_sourcetype_size_dict, spl_name
    ):
        """
        transpose the content returned by the field summaries search so it is in the following format:
        rows for each index, sourcetype, field, count group where each the columns for the row are
        stackname, splunk_server, index, sourcetype, field, count. The values for stackname and splunk server are only.
        populated in the first row. We also want to exclude index, sourcetype, field, count rows that contains count values
        of 0.
        :param content: list[dict[str,str]] -> content returned by the field summaries search
        the format of content: each result row contains the following columns: index, sourcetype, all the fields of
        events containing this particular index and sourcetype value. The value of the field columns are the counts of events
        containing this field value.
        stackname, splunk_server, index, sourcetype, field, count. The values for stackname and splunk server are only
        :param field_summaries_context: list[dict[str,str]] -> result content list to modify with transposed value
        :param index_sourcetype_size_dict: dict[dict[str]] -> dictionary that contains the information for sourcetypesize
        :param spl_name: str -> name of the spl to log
        :return : None
        """

        try:
            for data_row in content:
                if "field" in data_row:
                    try:
                        count_val = int(data_row.get("count", 0))
                    except (TypeError, ValueError):
                        continue
                    if count_val <= 0:
                        continue
                    index = data_row.get("index", "")
                    sourcetype = data_row.get("sourcetype", "")
                    sourcetypesize = index_sourcetype_size_dict.get(index, {}).get(
                        sourcetype, ""
                    )
                    field_summaries_context.append(
                        {
                            "index": index,
                            "sourcetype": sourcetype,
                            "field": data_row["field"],
                            "sourcetypesize": sourcetypesize,
                            "count": count_val,
                        }
                    )
                    continue

                index = data_row.get("index")
                sourcetype = data_row.get("sourcetype")
                for field in data_row:
                    if field not in ["index", "sourcetype"]:
                        try:
                            count_val = int(data_row[field])
                        except (TypeError, ValueError):
                            continue
                        if count_val > 0:
                            field_name = re.sub(r"^c\(|\)$", "", field)
                            sourcetypesize = ""
                            if index_sourcetype_size_dict.get(index):
                                sourcetypesize = index_sourcetype_size_dict.get(
                                    index
                                ).get(sourcetype, "")
                            field_summaries_context_row = {
                                "index": index,
                                "sourcetype": sourcetype,
                                "field": field_name,
                                "sourcetypesize": sourcetypesize,
                                "count": count_val,
                            }

                            field_summaries_context.append(field_summaries_context_row)

        except (IndexError, KeyError, ValueError) as e:
            raise Exception(
                f"Failed to fetch search result for '{spl_name}' for field summaries SPL context"
            ) from e

    def create_field_summary_batches(self, index_sourcetype_size_tuples):
        """
        runs several searches to gather splunk environement context
        :param index_sourcetype_size_tuples: list[Index_Sourcetype_Size]-> list of tuples containing the index sourcetype and size info
        :return sample ratio buckets dict[str, dict[str,str]]-> a dictionary containing one of size buckets as keys:
        1,10,100,1000,10000,10000. The values are dictionaries containing two keys "batches", and large_index_sourcetype_size_tuple_list", where
        the values of each are a list of Index_Sourcetype_Size tuples
        """

        minimum_event_count_per_tuple = self.search_params[
            "max_minimum_event_count_per_tuple"
        ]
        while True:
            sample_ratio_buckets, total_searches = (
                self.create_field_summary_batches_helper(
                    index_sourcetype_size_tuples,
                    minimum_event_count_per_tuple=minimum_event_count_per_tuple,
                )
            )
            if (
                total_searches > self.search_params["target_search_count"]
                and minimum_event_count_per_tuple
                > self.search_params["min_minimum_event_count_per_tuple"]
            ):
                minimum_event_count_per_tuple = self.search_params[
                    "min_minimum_event_count_per_tuple"
                ] + int(
                    (
                        minimum_event_count_per_tuple
                        - self.search_params["min_minimum_event_count_per_tuple"]
                    )
                    * 0.5
                )
            else:
                break

        # for logging
        metadata = {
            str(sample_ratio): json.dumps(batches_info)
            for sample_ratio, batches_info in sample_ratio_buckets.items()
        }
        self.logger.info(
            "Created batches per sample ratio bucket", extra={"metadata": metadata}
        )

        metadata = {
            search_param_key: str(search_param_value)
            for search_param_key, search_param_value in self.search_params.items()
        }
        metadata["minimum_event_count_per_tuple"] = minimum_event_count_per_tuple

        self.logger.info(
            "Parameters used to build batches", extra={"metadata": metadata}
        )

        metadata = {
            f"search count for sample ratio {sample_ratio}": str(
                len(batches_info["batches"])
                + len(batches_info["large_index_sourcetype_size_tuple_list"])
            )
            for sample_ratio, batches_info in sample_ratio_buckets.items()
        }

        self.logger.info(
            f"Total number of searches created: {total_searches}",
            extra={"metadata": metadata},
        )

        return sample_ratio_buckets

    def create_field_summary_batches_helper(
        self,
        index_sourcetype_size_tuples,
        minimum_event_count_per_tuple=D_MAX_MINIMUM_EVENT_COUNT_PER_TUPLE,
    ):
        """
        runs several searches to gather splunk environement context
        :param index_sourcetype_size_tuples: list[Index_Sourcetype_Size]-> list of tuples containing the index sourcetype and size info
        :param minimum_event_count_per_tuple: int -> minimum number of events per tuple which influence how much sampling gets applied to searches
        :return sample ratio buckets dict[str, dict[str,str]]-> a dictionary containing one of size buckets as keys:
        1,10,100,1000,10000,10000. The values are dictionaries containing two keys "batches", and large_index_sourcetype_size_tuple_list", where
        the values of each are a list of Index_Sourcetype_Size tuples
        :return total_searches: the total number of searches that will be run
        """

        # create batches
        # Sort each tuple into one of 6 sample size buckets depending on the counts field in the tuple and the minimum event count
        sample_ratios = [100000, 10000, 1000, 100, 10, 1]
        sample_ratio_buckets = {
            sample_ratio: {
                "index_sourcetype_size_tuple_list": [],
                "batches": [],
                "large_index_sourcetype_size_tuple_list": [],
            }
            for sample_ratio in sample_ratios
        }
        total_searches = 0
        self.logger.info(
            "sorting tuples into sample ratio buckets based on min event count per tuple and size"
        )
        for index_sourcetype_size_tuple in index_sourcetype_size_tuples:
            for sample_ratio in sample_ratios:
                if index_sourcetype_size_tuple.size >= (
                    minimum_event_count_per_tuple * sample_ratio
                ):
                    if (
                        sample_ratio == 1
                        and index_sourcetype_size_tuple.size
                        > self.search_params["maximum_count_no_sampling"]
                    ):
                        sample_ratio_buckets[10][
                            "index_sourcetype_size_tuple_list"
                        ].append(index_sourcetype_size_tuple)
                        break
                    sample_ratio_buckets[sample_ratio][
                        "index_sourcetype_size_tuple_list"
                    ].append(index_sourcetype_size_tuple)
                    break
            # for the case where the size value of the tuple is less that minimum_event_count_per_tuple, we still want to
            # query it with no sampling
            if index_sourcetype_size_tuple.size < minimum_event_count_per_tuple:
                sample_ratio_buckets[1]["index_sourcetype_size_tuple_list"].append(
                    index_sourcetype_size_tuple
                )

        self.logger.info("sorting tuples by index")
        # Sort each bucket by index, this will cause batches to be better organized by index.
        for sample_ratio in sample_ratio_buckets:
            sample_ratio_buckets[sample_ratio]["index_sourcetype_size_tuple_list"].sort(
                key=lambda x: x.index
            )
        self.logger.info("building batches for each bucket")
        # For each bucket, build batches by popping adding tuples until a maximum event batch size is reached
        for sample_ratio in sample_ratio_buckets:
            maximum_event_sample_ratio_batch_size = (
                sample_ratio * self.search_params["maximum_event_batch_size"]
            )
            index_sourcetype_size_tuple_list = sample_ratio_buckets[sample_ratio][
                "index_sourcetype_size_tuple_list"
            ]

            running_batch_event_count = 0
            current_batch = []
            for index_sourcetype_size_tuple in index_sourcetype_size_tuple_list:
                if (
                    index_sourcetype_size_tuple.size
                    > maximum_event_sample_ratio_batch_size
                ):
                    # a single sourcetype has so many events that it would exceed an entire batch for a particular sampling bin
                    # do not add tuple to main list of batches for a bin, run it with its own query as its own batch with | head <max_events_per_batch>.
                    sample_ratio_buckets[sample_ratio][
                        "large_index_sourcetype_size_tuple_list"
                    ].append([index_sourcetype_size_tuple])
                    continue

                running_batch_event_count += index_sourcetype_size_tuple.size
                # if batch would be over maximum event batch size OR the number of tuples would be too large, use a new search (create a new batch)
                if (
                    running_batch_event_count > maximum_event_sample_ratio_batch_size
                    or len(current_batch) + 1
                    > self.search_params["maximum_tuples_for_search"]
                ):
                    # finalize the nonempty batch, and start building the next batch
                    sample_ratio_buckets[sample_ratio]["batches"].append(current_batch)

                    # reset running batch count and create new empty batch list
                    running_batch_event_count = index_sourcetype_size_tuple.size
                    current_batch = [index_sourcetype_size_tuple]
                else:
                    current_batch.append(index_sourcetype_size_tuple)

            # add the final batch for the bucket
            if current_batch:
                sample_ratio_buckets[sample_ratio]["batches"].append(current_batch)
            total_searches += len(sample_ratio_buckets[sample_ratio]["batches"])
            total_searches += len(
                sample_ratio_buckets[sample_ratio][
                    "large_index_sourcetype_size_tuple_list"
                ]
            )

            sample_ratio_buckets[sample_ratio].pop("index_sourcetype_size_tuple_list")

        if total_searches > self.search_params["maximum_search_count"]:
            self.logger.info("maximum search count reached, popping off random batches")
            num_of_elements_to_remove = (
                total_searches - self.search_params["maximum_search_count"]
            )
            # From the list of proposed batches, pop off random batches until the length of proposed batches is equal to the maximum number of searches.
            all_batches = []
            for sample_ratio in sample_ratio_buckets:
                sample_ratio_batches = [
                    (sample_ratio, batch, "regular")
                    for batch in sample_ratio_buckets[sample_ratio]["batches"]
                ]
                sample_ratio_large_batches = [
                    (sample_ratio, batch, "large")
                    for batch in sample_ratio_buckets[sample_ratio][
                        "large_index_sourcetype_size_tuple_list"
                    ]
                ]
                sample_ratio_buckets[sample_ratio]["batches"] = []
                sample_ratio_buckets[sample_ratio][
                    "large_index_sourcetype_size_tuple_list"
                ] = []

                all_batches.extend(sample_ratio_batches)
                all_batches.extend(sample_ratio_large_batches)

            random.shuffle(all_batches)

            for index in range(num_of_elements_to_remove):
                all_batches.pop()

            # repopulate batches of each bucket with new list of batches
            for sample_ratio, batch, batch_type in all_batches:
                if batch_type == "regular":
                    sample_ratio_buckets[sample_ratio]["batches"].append(batch)
                if batch_type == "large":
                    sample_ratio_buckets[sample_ratio][
                        "large_index_sourcetype_size_tuple_list"
                    ].append(batch)

        # query plan is ready, log number of searches
        total_searches = (
            self.search_params["maximum_search_count"]
            if total_searches > self.search_params["maximum_search_count"]
            else total_searches
        )

        return sample_ratio_buckets, total_searches

    @staticmethod
    def index_sourcetype_fields_count_command(
        index_sourcetype_size_tuples, head_value: Optional[int] = None
    ) -> str:
        """
        returns an spl which returns the counts of unique fields within an index, sourcetype, field tuple.
        :param index_sourcetype_size_tuples: list(Index_Sourcetype_Size) -> list of tuples containing index, sourcetype, size
        :param head_value: int -> the number of events we should use to calculate the field counts
        :return spl: the spl which returns the field count values
        """
        indexes_str_set = set()
        sourcetypes_str_set = set()

        for index_sourcetype_size_tuple in index_sourcetype_size_tuples:
            indexes_str_set.add(f'index="{index_sourcetype_size_tuple.index}"')
            sourcetypes_str_set.add(f'"{index_sourcetype_size_tuple.sourcetype}"')

        indexes_str_set = sorted(indexes_str_set)
        sourcetypes_str_set = sorted(sourcetypes_str_set)

        indexes_str = " OR ".join(indexes_str_set)
        sourcetypes_list_str = ", ".join(sourcetypes_str_set)
        sourcetypes_str = f"sourcetype IN ({sourcetypes_list_str})"

        if head_value:
            return f"search {indexes_str} {sourcetypes_str} | head {head_value} | stats c(*) by index, sourcetype"
        return (
            f"search {indexes_str} {sourcetypes_str} | stats c(*) by index, sourcetype"
        )

    def update_spl_context(self, *, earliest: int, latest: int) -> bool:
        """Collect field summaries and upload metadata for the requested time range."""
        start = time_modifier_from_timestamp(earliest)
        end = time_modifier_from_timestamp(latest)
        request_id = str(uuid.uuid4())
        run_start = time.time()
        service, collection = self._get_service_and_collection()
        api = self._create_saia_api(service)
        if not self._should_upload_for_tenant(api, request_id):
            return False

        spl_context = self.get_spl_context(
            earliest=earliest,
            latest=latest,
            service=service,
            collection=collection,
            api=api,
        )
        run_end = time.time()
        logger.info(
            log_kwargs(
                apply_time=round((run_end - run_start), 5),
            )
        )
        field_summaries = spl_context[FIELD_SUMMARIES_CONTEXT_NAME]
        field_data = field_summaries["results"]
        pending_sampled_pairs = field_summaries.get("pending_sampled_pairs", {})

        unique_indexes = set()
        unique_sourcetypes = set()
        for row in field_data:
            idx = row.get("index")
            sourcetype = row.get("sourcetype")
            if idx:
                unique_indexes.add(idx)
            if sourcetype:
                unique_sourcetypes.add(sourcetype)

        self.logger.info("Connecting to SAIA service")

        app_version = get_app_version(service)

        self.logger.info(f"Updating SPL context in range {start} - {end}")
        self.logger.info(  # pyright: ignore
            "Preparing to submit sourcetype metadata",
            extra={
                "metadata": {
                    "request_id": request_id,
                    "anticipated_entry_count": len(field_data),
                    "collected_fields": len(field_data),
                    "collected_indexes": len(unique_indexes),
                    "collected_sourcetypes": len(unique_sourcetypes),
                    "saia_app_version": app_version,
                }
            },
        )

        self._submit_sourcetype_metadata(api, field_data, request_id)
        self._persist_sampled_pairs_after_upload(
            collection=collection,
            field_data=field_data,
            pending_sampled_pairs=pending_sampled_pairs,
            sampled_at=int(time.time()),
        )

        # TODO: Clean up logging
        self.logger.info(  # pyright: ignore
            log_kwargs(
                message="Sourcetype metadata submitted successfully.",
                saia_app_version=app_version,
            )
        )
        self.logger.info(f"Successfully updated SPL context in range {start} - {end}")
        return True

    def run(self, stanza: Sequence[Dict[str, Any]]):
        """Entry point for the modular input; runs when scheduled by Splunk."""
        self.logger.info("Starting Field Summary Modular Input")
        self.logger.setLevel(self.get_log_level(stanza))
        self.logger.debug(
            f"Input configuration: {self._input_config}, stanza: {stanza}"
        )
        config = SAIAFieldSummaryModularInputConfig(
            self._input_config.session_key, self.logger
        )
        self.search_params = config.get_search_params()
        if config.is_context_update_due():
            now = int(time.time())
            # for POC, setting max lookback to be 24 hours ago
            earliest = max(
                config.status["last_context_update_timestamp"],
                now - config.settings["max_chunk_range_seconds"],
            )
            latest = int(time.time())

            try:
                did_update = self.update_spl_context(earliest=earliest, latest=latest)
            except Exception as e:
                self.logger.exception("Error in updating field summary context: %s", e)
            else:
                if did_update:
                    config.update(last_context_update_timestamp=latest)
                    earliest = latest
                    self._chunk_count += 1

    def cache_results_to_kvstore(self, results, collection, last_sampled_map=None):
        """Persist lightweight sampling metadata to KV store."""
        # Only persist lightweight sampling metadata; avoid storing full field payloads in KV
        if not last_sampled_map:
            return

        entries_to_save = []
        for (index, sourcetype), last_sampled in last_sampled_map.items():
            entries_to_save.append(
                {
                    "_key": f"{index}:{sourcetype}",
                    "index": index,
                    "sourcetype": sourcetype,
                    "last_sampled": last_sampled,
                    "latest_time": 0,
                }
            )

        if entries_to_save:
            try:
                collection.batch_save(entries_to_save)
                logger.info("Successfully cached sampling metadata to KV store")
            except Exception as e:
                logger.exception("Failed to cache sampling metadata to KV store: %s", e)

    def _save_last_sampled_entry(
        self, collection, index, sourcetype, last_sampled, latest_time
    ):
        """Upsert one last-sampled record for the given index/sourcetype pair."""
        entry = {
            "_key": f"{index}:{sourcetype}",
            "index": index,
            "sourcetype": sourcetype,
            "last_sampled": last_sampled,
            "latest_time": latest_time,
        }
        try:
            collection.upsert(entry)
            self.logger.info(
                "Cached sampling metadata to KV store",
                extra={
                    "metadata": {"index": index, "sourcetype": sourcetype},
                },
            )
        except Exception as e:
            self.logger.exception(
                "Failed to cache sampling metadata to KV store: %s",
                e,
                extra={
                    "metadata": {"index": index, "sourcetype": sourcetype},
                },
            )


if __name__ == "__main__":
    add_log_extra_metadata("tag", LOGGER_METADATA_TAG)
    add_log_extra_metadata("context", "modinput")
    mod_input = SAIAFieldSummaryModularInput()
    mod_input.execute()
