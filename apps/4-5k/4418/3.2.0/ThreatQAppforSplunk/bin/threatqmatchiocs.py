import hashlib
import os
import re
import sys
import time
import json
from functools import partial
from multiprocessing import Pool, cpu_count
import itertools
import string

import logger_manager as log
from splunklib.searchcommands import (
    Configuration,
    EventingCommand,
    Option,
    dispatch,
    validators,
)
from threatq_utils import (
    get_kv_store_query,
    get_matched_indicators,
    get_unmatched_indicators,
    lock_lookup,
    is_iterator_empty,
    put_indicators,
    unlock_lookup,
    get_encoded_str,
    get_conf_file,
    get_all_indicators,
    get_indicator_matching_variants,
)
from threatq_match_utils import (
    get_process_count,
)

logger = log.setup_logging("ta_threatquotient_add_on_threatqmatchiocs")
app_name = __file__.split(os.sep)[-3]


# Create hashes of an event
def _get_event_value_hashes(lengths, event):
    parts_re = re.compile(r"\w+|\W")
    parts = parts_re.findall(event["_raw"])
    result = set()
    if lengths:
        seq_len = len(parts)
        for start in range(seq_len - min(lengths) + 1):
            max_length = seq_len - start
            for end in (
                start + length for length in lengths if length <= max_length
            ):
                result.add(
                    hashlib.sha1(get_encoded_str(parts[start:end])).hexdigest()
                )
    return result, event


def _tokenize_partial(value):
    raw_tokens = str(value).lower().split()
    tokens = []
    for token in raw_tokens:
        cleaned = token.strip(string.punctuation)
        if cleaned:
            tokens.append(cleaned)
    return tokens


@Configuration()
class ThreatQMatchIOCSCommand(EventingCommand):
    """ThreatQ match IOCS custom command."""

    is_update = Option(
        name="is_update", default=False, validate=validators.Boolean()
    )
    batch_size = Option(
        name="batch_size", default=500, validate=validators.Integer(minimum=1)
    )
    chunk_size = Option(
        name="chunk_size", default=0, validate=validators.Integer(minimum=0)
    )
    process_count = Option(name="process_count", default=None)

    indicator_types = Option(
        name="indicator_types", default=[], validate=validators.List()
    )
    events = iter([])
    check_empty = True

    # Upload indicators using lock and adding count
    def upload_indicators(
        self, matched_indicators, matched_indicators_last_run
    ):
        """Upload indicators using lock and adding count."""
        lock_key = lock_lookup(self.splunkd_uri, self.session_key, app_name)
        try:
            query = (
                get_kv_store_query("type", self.indicator_types)
                if self.indicator_types
                else None
            )

            if self.is_update:
                # Update mode: only work with already matched indicators
                indicators = get_matched_indicators(
                    self.splunkd_uri, self.session_key, app_name, query=query
                )
            else:
                # Non-update mode: only work with previously unmatched indicators
                indicators = get_unmatched_indicators(
                    self.splunkd_uri, self.session_key, app_name, query=query
                )

            settings_conf_file = get_conf_file(self.session_key, app_name, "threatquotient_app_settings")
            splunk_cust_fields = settings_conf_file.get("custom_splunk_fields").get("splunk_additional_fields", "")
            matching_type = settings_conf_file.get("match_algo_detail").get("match_type")
            keys = None
            if splunk_cust_fields and splunk_cust_fields.strip() and matching_type == "raw":
                keys = splunk_cust_fields.split(",")
                keys = [key.strip() for key in keys]

            indicators_to_upload = []
            run_time = int(time.time())
            
            # Raw matching doesn't have a datamodel, use "Raw" as identifier
            raw_matching_identifier = "Raw"
            raw_matching_key_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_matching_identifier)

            # Track which ioc_values we've already processed in this upload to
            # avoid double-incrementing match_count when multiple indicator
            # docs share the same ioc_value (e.g. raw + datamodel entries).
            processed_iocs = set()

            for indicator in indicators:

                ioc_val = indicator.get("ioc_value")
                if not ioc_val or ioc_val in processed_iocs:
                    continue

                if not matched_indicators.get(ioc_val):
                    continue

                # Generate composite key for raw matching: ioc_value_Raw
                composite_key = f"{ioc_val}_{raw_matching_key_safe}"
                
                # Check if entry with this composite key already exists
                existing_indicator = None
                for existing in indicators:
                    existing_ioc = existing.get("ioc_value")
                    existing_key = existing.get("_key", "")
                    existing_dm = existing.get("datamodel_name")
                    
                    # Match if: same ioc_value AND (key matches OR old format with no datamodel_name)
                    if (existing_ioc == ioc_val and 
                        (existing_key == composite_key or
                         (existing_key == ioc_val and not existing_dm))):
                        existing_indicator = existing
                        break
                
                if existing_indicator:
                    # Update existing entry
                    indicator = existing_indicator
                    indicator["match_count"] = (
                        int(indicator.get("match_count", 0))
                        + matched_indicators[ioc_val][0]
                    )
                    indicator["_key"] = composite_key  # Ensure composite key is set
                else:
                    # New entry
                    indicator["match_count"] = matched_indicators[ioc_val][0]
                    indicator["_key"] = composite_key

                indicator["sid"] = self.sid
                indicator[
                    "last_run_match_count"
                ] = matched_indicators_last_run[ioc_val]
                indicator["last_run_first_seen"] = self.earliest_time
                indicator["last_run_last_seen"] = self.latest_time

                if int(indicator.get("match_time", 0)) < run_time:
                    indicator["match_time"] = run_time

                if int(indicator.get("last_seen", 0)) < self.latest_time:
                    indicator["last_seen"] = self.latest_time

                if indicator.get("first_seen") is None:
                    indicator["first_seen"] = self.earliest_time

                # Don't set datamodel_name for raw matching (set to empty string)
                # This distinguishes raw matching from datamodel matching
                # Empty string ensures it won't be sent to ThreatQ portal (threatqconsumeindicatorsnew.py line 154)
                indicator["datamodel_name"] = ""
                
                indicator["raw_event"] = matched_indicators[ioc_val][1].get("_raw")
                if keys:
                    for key in keys:
                        key1 = key.replace(".", "_")
                        indicator[key1] = matched_indicators[ioc_val][1].get(key, None)
                indicators_to_upload.append(indicator)
                processed_iocs.add(ioc_val)

            for batch_i in range(
                0, len(indicators_to_upload), self.batch_size
            ):
                put_indicators(
                    self.splunkd_uri,
                    self.session_key,
                    app_name,
                    indicators_to_upload[batch_i: batch_i + self.batch_size],
                )

        finally:
            unlock_lookup(
                self.splunkd_uri, self.session_key, app_name, lock_key
            )

    # Function which will be invoked when custom command runs
    def transform(self, events):
        """Transform method of Eventing Command."""
        if False:
            yield

        if not self.search_results_info or self.metadata.preview:
            return

        events = is_iterator_empty(events)
        if self.check_empty:
            if events is None:
                return
            else:
                self.check_empty = False
        self.events = itertools.chain(self.events, events)
        if self._finished:
            self.process_rawmatch()

    def process_rawmatch(self):
        """Process raw matching."""
        try:
            def raw_events_wrapper(events):
                for event in events:
                    yield event

            raw_events = raw_events_wrapper(self.events)

            self.process_count = get_process_count(self.process_count)
            if self.chunk_size == 0:
                self.chunk_size = 50000 // self.process_count

            self.session_key = self.search_results_info.auth_token
            self.splunkd_uri = self.search_results_info.splunkd_uri
            self.earliest_time = int(
                self.metadata.searchinfo.earliest_time
            )
            self.latest_time = int(self.metadata.searchinfo.latest_time)

            if self.latest_time == 0:
                self.latest_time = int(time.time())

            self.sid = self.metadata.searchinfo.sid
            indicators = []

            query = (
                get_kv_store_query("type", self.indicator_types)
                if self.indicator_types
                else None
            )

            # For raw matching, always consider all indicators (matched + unmatched)
            # so that a separate _Raw entry can be created even if a datamodel
            # match already exists for the same IOC value.
            indicators = get_all_indicators(
                self.splunkd_uri,
                self.session_key,
                app_name,
                query=query,
            )
            if not indicators:
                return
            ind_value_lengths = set()
            indicators_by_hash = {}
            parts_re = re.compile(r"\w+|\W")

            settings_conf_file = get_conf_file(
                self.session_key, app_name, "threatquotient_app_settings"
            )
            partial_chkbox = settings_conf_file.get("match_algo_detail").get("partial_matching_checkbox")
            partial_enabled = str(partial_chkbox).lower() in ["1", "true", "yes"]

            regex_chkbox = settings_conf_file.get("match_algo_detail").get("regex_matching_checkbox")
            regex_enabled = str(regex_chkbox).lower() in ["1", "true", "yes"]

            regex_indicators = []
            normal_indicators = []
            for indicator in indicators:
                ioc_val = str(indicator.get("ioc_value", ""))
                # Use a stripped, lowercased version only for detection so we are tolerant to spaces
                ioc_val_lower_stripped = ioc_val.strip().lower()

                is_regex = False

                if regex_enabled and (
                    ioc_val_lower_stripped.startswith("(regex)")
                    or ioc_val_lower_stripped.endswith("(regex)")
                ):
                    is_regex = True

                if is_regex:
                    regex_indicators.append(indicator)
                else:
                    normal_indicators.append(indicator)

            # Separate out IP/URL indicators that have an associated port so we can
            # apply port-aware matching logic to them instead of generic base-variant
            # hashing, which would otherwise match IP:other_port as well.
            port_aware_indicators = []
            for indicator in list(normal_indicators):
                indicator_type = str(indicator.get("type", ""))
                port = indicator.get("port")
                if port and indicator_type in ["IP Address", "IPv6 Address", "URL"]:
                    port_aware_indicators.append(indicator)
                    # Remove from normal_indicators so they are not handled by the
                    # generic hash/partial logic.
                    normal_indicators.remove(indicator)
            partial_match_tokens = {}
            indicator_hashes = set()
            # Map from variant value to original ioc_value for port-based matching
            variant_to_ioc = {}

            # Always build hashes for normal (non-regex) indicators so that
            # normal matching is available regardless of partial matching.
            # Port-aware indicators are excluded here and handled separately.
            for indicator in normal_indicators:
                parts = parts_re.findall(
                    str(indicator["ioc_value"]).replace("\\\\", "\\")
                )
                ind_value_lengths.add(len(parts))
                indicators_by_hash[
                    hashlib.sha1(get_encoded_str(parts)).hexdigest()
                ] = indicator["ioc_value"]
            indicator_hashes = set(indicators_by_hash.keys())

            if partial_enabled:
                # Prepare token sets for partial matching only for indicators
                # whose type is explicitly "String". Port-aware IP/URL indicators
                # are handled by dedicated regex logic.
                for indicator in normal_indicators:
                    if str(indicator.get("type", "")) != "String":
                        continue

                    ioc_val = indicator["ioc_value"]
                    # Get all matching variants (non-port-based for these types)
                    variants = get_indicator_matching_variants(indicator)
                    for variant in variants:
                        variant_to_ioc[variant] = ioc_val
                        partial_match_tokens[variant] = set(
                            _tokenize_partial(variant)
                        )
            else:
                # Build hashes for all variants of normal indicators (port-aware
                # indicators are excluded and handled via regex).
                for indicator in normal_indicators:
                    variants = get_indicator_matching_variants(indicator)
                    for variant in variants:
                        variant_to_ioc[variant] = indicator["ioc_value"]
                        parts = parts_re.findall(
                            str(variant).replace("\\\\", "\\")
                        )
                        ind_value_lengths.add(len(parts))
                        variant_hash = hashlib.sha1(get_encoded_str(parts)).hexdigest()
                        indicators_by_hash[variant_hash] = indicator["ioc_value"]
                indicator_hashes = set(indicators_by_hash.keys())

            compiled_regexes = []
            for indicator in regex_indicators:
                original_ioc_val = str(indicator.get("ioc_value", ""))
                pattern_str = original_ioc_val
                pattern_lower = pattern_str.lower()

                if pattern_lower.startswith("(regex)"):
                    pattern_str = pattern_str[len("(regex)") :].lstrip()
                    pattern_lower = pattern_str.lower()

                if pattern_lower.endswith("(regex)"):
                    pattern_str = pattern_str[: -len("(regex)")].rstrip()

                try:
                    compiled_regexes.append(
                        (re.compile(pattern_str), original_ioc_val)
                    )
                except re.error as regex_err:
                    logger.warning(
                        "Invalid regex IOC '%s': %s",
                        original_ioc_val,
                        str(regex_err),
                    )

            # Build internal regexes for port-aware IP/URL indicators so that they
            # match the base value and specific configured ports, but avoid
            # matching the same IP/URL with different ports.
            compiled_port_regexes = []
            for indicator in port_aware_indicators:
                base_value = str(indicator.get("ioc_value", ""))
                port = indicator.get("port")

                ports = []
                if port:
                    if isinstance(port, list):
                        # Already a list of ports
                        ports = [str(p) for p in port if p]
                    else:
                        # Port may be a simple string (e.g. "8000") or a JSON
                        # representation of a list (e.g. "[\"8000\",\"9000\"]").
                        port_str = str(port).strip()
                        if port_str.startswith("[") and port_str.endswith("]"):
                            try:
                                parsed = json.loads(port_str)
                                if isinstance(parsed, list):
                                    ports = [str(p) for p in parsed if p]
                                else:
                                    ports = [port_str]
                            except Exception:
                                # Fall back to treating the raw string as a
                                # single port if JSON parsing fails.
                                ports = [port_str]
                        else:
                            ports = [port_str]

                if not ports:
                    continue

                base_escaped = re.escape(base_value)

                if len(ports) == 1:
                    port_pattern = re.escape(ports[0])
                else:
                    port_pattern = "(?:" + "|".join(re.escape(p) for p in ports) + ")"

                # Pattern: \bIP(?: :allowedPort)?(?=$|\s|[^0-9.:])
                # Use a real word boundary and simple colon/port handling so we
                # match base_value and the configured ports, but not other ports
                # or longer IP-like strings (e.g. 1.2.3.44 when IOC is 1.2.3.4).
                # The lookahead ensures the next character is end-of-string,
                # whitespace, or not in [0-9.:].
                pattern_str = (
                    r"\b" + base_escaped +
                    r"(?::" + port_pattern + r")?" +
                    r"(?=$|\s|[^0-9.:])"
                )

                try:
                    compiled_port_regexes.append(
                        (re.compile(pattern_str), indicator["ioc_value"])
                    )
                except re.error as regex_err:
                    logger.warning(
                        "Error compiling internal port-aware regex for IOC '%s': %s",
                        indicator.get("ioc_value", ""),
                        str(regex_err),
                    )
            logger.info("Process count: {}".format(self.process_count))
            logger.info("Chunk Size: {}".format(self.chunk_size))
            pool = Pool(self.process_count)
            matched_indicators = {}
            matched_indicators_last_run = {}
            get_event_value_hashes = partial(
                _get_event_value_hashes, ind_value_lengths
            )
            it = 0
            last_event_time = 0
            for event_value_hashes, event_returned in pool.imap(
                get_event_value_hashes,
                raw_events,
                chunksize=self.chunk_size,
            ):  
                whole_dict_resp = dict(event_returned)
                # Track which IOC values have already been matched for this event
                matched_iocs_this_event = set()
                if float(whole_dict_resp["_time"]) >= last_event_time:
                    last_event_time = float(whole_dict_resp["_time"])
                # Hash-based matching for normal indicators
                matched_hashes = event_value_hashes & indicator_hashes
                for matched_hash in matched_hashes:
                    ioc_value = indicators_by_hash[matched_hash]
                    # Only count once per event per ioc_value (even if multiple variants match)
                    if ioc_value in matched_iocs_this_event:
                        continue

                    existing = matched_indicators.get(ioc_value)
                    new_count = (existing[0] if existing else 0) + 1

                    event_to_store = whole_dict_resp
                    if existing:
                        try:
                            prev_time = float(existing[1].get("_time", 0))
                            curr_time = float(whole_dict_resp.get("_time", 0))
                            if prev_time > curr_time:
                                event_to_store = existing[1]
                        except (TypeError, ValueError):
                            pass

                    matched_indicators[ioc_value] = [new_count, event_to_store]

                    matched_indicators_last_run[ioc_value] = (
                        int(
                            matched_indicators_last_run.get(
                                ioc_value, 0
                            )
                        )
                        + 1
                    )

                    matched_iocs_this_event.add(ioc_value)

                # Regex-based matching for regex indicators
                event_text = whole_dict_resp.get("_raw", "")
                for pattern, ioc_value in compiled_regexes:
                    try:
                        if ioc_value in matched_iocs_this_event:
                            continue

                        if pattern.search(event_text):
                            existing = matched_indicators.get(ioc_value)
                            new_count = (existing[0] if existing else 0) + 1

                            event_to_store = whole_dict_resp
                            if existing:
                                try:
                                    prev_time = float(existing[1].get("_time", 0))
                                    curr_time = float(whole_dict_resp.get("_time", 0))
                                    if prev_time > curr_time:
                                        event_to_store = existing[1]
                                except (TypeError, ValueError):
                                    pass

                            matched_indicators[ioc_value] = [new_count, event_to_store]

                            matched_indicators_last_run[ioc_value] = (
                                int(
                                    matched_indicators_last_run.get(
                                        ioc_value, 0
                                    )
                                )
                                + 1
                            )

                            matched_iocs_this_event.add(ioc_value)
                    except Exception as regex_match_err:
                        logger.warning(
                            "Error applying regex IOC '%s': %s",
                            ioc_value,
                            str(regex_match_err),
                        )
                # Port-aware matching for IP/URL+port indicators
                for pattern, ioc_value in compiled_port_regexes:
                    try:
                        if ioc_value in matched_iocs_this_event:
                            continue

                        if pattern.search(event_text):
                            existing = matched_indicators.get(ioc_value)
                            new_count = (existing[0] if existing else 0) + 1

                            event_to_store = whole_dict_resp
                            if existing:
                                try:
                                    prev_time = float(existing[1].get("_time", 0))
                                    curr_time = float(whole_dict_resp.get("_time", 0))
                                    if prev_time > curr_time:
                                        event_to_store = existing[1]
                                except (TypeError, ValueError):
                                    pass

                            matched_indicators[ioc_value] = [new_count, event_to_store]

                            matched_indicators_last_run[ioc_value] = (
                                int(
                                    matched_indicators_last_run.get(
                                        ioc_value, 0
                                    )
                                )
                                + 1
                            )

                            matched_iocs_this_event.add(ioc_value)
                    except Exception as port_match_err:
                        logger.warning(
                            "Error applying port-aware IOC '%s': %s",
                            ioc_value,
                            str(port_match_err),
                        )
                if partial_enabled:
                    event_tokens = set(_tokenize_partial(event_text))
                    for variant_value, ioc_tokens in partial_match_tokens.items():
                        # Map variant back to original ioc_value
                        ioc_value = variant_to_ioc.get(variant_value, variant_value)
                        if ioc_value in matched_iocs_this_event:
                            continue
                        if ioc_tokens.issubset(event_tokens):
                            existing = matched_indicators.get(ioc_value)
                            new_count = (existing[0] if existing else 0) + 1

                            event_to_store = whole_dict_resp
                            if existing:
                                try:
                                    prev_time = float(existing[1].get("_time", 0))
                                    curr_time = float(whole_dict_resp.get("_time", 0))
                                    if prev_time > curr_time:
                                        event_to_store = existing[1]
                                except (TypeError, ValueError):
                                    pass

                            matched_indicators[ioc_value] = [new_count, event_to_store]

                            matched_indicators_last_run[ioc_value] = (
                                int(
                                    matched_indicators_last_run.get(
                                        ioc_value, 0
                                    )
                                )
                                + 1
                            )

                            matched_iocs_this_event.add(ioc_value)
                if len(matched_indicators) >= self.batch_size:
                    self.upload_indicators(
                        matched_indicators, matched_indicators_last_run
                    )
                    matched_indicators = {}
                it += 1

            logger.info("Total events processed - {}".format(it))
            if matched_indicators:
                self.upload_indicators(
                    matched_indicators, matched_indicators_last_run
                )
            pool.close()
            pool.join()
            logger.info("finished execution")
        except Exception as e:
            logger.error(
                "ThreatQ 'threatqmatchiocs' command error: %s" % str(e)
            )
            raise


if __name__ == "__main__":
    dispatch(
        ThreatQMatchIOCSCommand, sys.argv, sys.stdin, sys.stdout, __name__
    )
