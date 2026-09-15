# File: cyberintpremiumioc_consts.py
#
# Copyright (c) 2025-2026 Splunk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

# API Endpoints
IOC_ENRICHMENT_ENDPOINT = "/ioc-intel/enrichment-api/v1/enrichment"
IOC_FEED_JSONL_ENDPOINT = "/ioc-intel/feed-api/v1/feed/jsonl"

# Default page size for feed pagination (max 100000 per the API spec)
IOC_FEED_PAGE_SIZE = 10000

# Indicator type constants used by the enrichment endpoint
IOC_TYPE_SHA256 = "sha256"
IOC_TYPE_SHA1 = "sha1"
IOC_TYPE_MD5 = "md5"
IOC_TYPE_IPV4 = "ipv4"
IOC_TYPE_URL = "url"
IOC_TYPE_DOMAIN = "domain"

# Maps a feed indicator_type onto the standard CEF field SOAR expects, the
# "contains" types that drive playbook action recommendations, and the artifact
# type used for grouping in the UI. IOC types absent from this map are skipped
# during ingestion and reported in the action summary.
IOC_CEF_MAPPING = {
    IOC_TYPE_IPV4: ("sourceAddress", ["ip"], "network"),
    IOC_TYPE_DOMAIN: ("destinationDnsDomain", ["domain"], "network"),
    IOC_TYPE_URL: ("requestURL", ["url"], "network"),
    IOC_TYPE_SHA256: ("fileHashSha256", ["hash", "sha256"], "file"),
    IOC_TYPE_SHA1: ("fileHashSha1", ["hash", "sha1"], "file"),
    IOC_TYPE_MD5: ("fileHashMd5", ["hash", "md5"], "file"),
}

# The API reports severity on a 0-5 scale (0 is returned for benign indicators);
# SOAR containers and artifacts use low / medium / high.
IOC_SEVERITY_MAP = {0: "low", 1: "low", 2: "low", 3: "medium", 4: "high", 5: "high"}
DEFAULT_SEVERITY = "medium"

# Label applied to every artifact created by the feed.
FEED_ARTIFACT_LABEL = "ioc"

# On-poll feed ingestion
# State-file key holding the ISO-8601 timestamp of the last successful ingestion,
# used as the "added_to_feed_after" cursor on the next scheduled poll.
FEED_STATE_CURSOR_KEY = "last_ingested_time"
# State-file key holding the pagination offset to resume at when a run was cut
# short by an ingestion limit. The feed writes many indicators with an identical
# `added_to_feed`, so a truncated run cannot checkpoint on the timestamp alone
# without skipping the rest of that batch; it keeps the window start and records
# how far into it the run got. Cleared once a pass completes.
FEED_STATE_OFFSET_KEY = "resume_offset"
# How far back to look on the very first scheduled poll (no checkpoint yet).
FEED_FIRST_FETCH_DAYS = 3
# Lookback window for a manual "poll now" run (does not advance the checkpoint).
POLL_NOW_LOOKBACK_DAYS = 1
# Artifact ceiling for a manual "poll now" when SOAR supplies no artifact_count.
POLL_NOW_ARTIFACT_LIMIT = 100
# Container source_data_identifier prefix for a day's feed ingestion.
FEED_CONTAINER_SDI_PREFIX = "cyberint_premium_ioc_feed_"
