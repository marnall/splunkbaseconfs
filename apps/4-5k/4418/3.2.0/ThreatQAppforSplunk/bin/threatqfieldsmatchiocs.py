import os
import sys
import time
import re
from multiprocessing import Pool, cpu_count
from functools import partial
import traceback
import itertools

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
    get_all_indicators,
    get_conf_file,
    get_indicator_matching_variants,
)
from threatq_match_utils import (
    get_process_count,
)

logger = log.setup_logging("ta_threatquotient_add_on_threatqfieldsmatchiocs")
app_name = __file__.split(os.sep)[-3]


# Return set of events key i.e. to be matched with events, and the events_count dict
def _get_event_values(event_count):
    if isinstance(event_count, dict):
        return set(event_count.keys()), event_count
    return set(), {}


@Configuration()
class ThreatQFieldsMatchIOCSCommand(EventingCommand):
    """ThreatQ match IOCS custom command."""

    is_update = Option(name="is_update", default=False, validate=validators.Boolean())
    pull_both_lookups_iocs = Option(
        name="pull_both_lookups_iocs", default=True, validate=validators.Boolean()
    )
    batch_size = Option(
        name="batch_size", default=500, validate=validators.Integer(minimum=1)
    )
    match_fields = Option(name="match_fields", validate=validators.List())
    indicator_types = Option(
        name="indicator_types", default=[], validate=validators.List()
    )
    chunk_size = Option(
        name="chunk_size", default=0, validate=validators.Integer(minimum=0)
    )
    process_count = Option(name="process_count", default=None)
    trigger_partial_url_match = Option(
        name="trigger_partial_url_match", default=False, validate=validators.Boolean()
    )
    datamodel_name = Option(
        name="datamodel_name", default=None
    )

    events = iter([])
    check_empty = True

    # Upload indicators using lock and adding count
    def upload_indicators(self, matched_indicators):
        """Upload Idicators using lock and adding count."""    

        lock_key = lock_lookup(self.splunkd_uri, self.session_key, app_name)
        try:
            query = get_kv_store_query("type", self.indicator_types)
            indicators = get_matched_indicators(
                self.splunkd_uri, self.session_key, app_name, query=query
            )

            if not self.is_update or self.pull_both_lookups_iocs:
                indicators = indicators + get_unmatched_indicators(
                    self.splunkd_uri, self.session_key, app_name, query=query
                )
            
            settings_conf_file = get_conf_file(self.session_key, app_name, "threatquotient_app_settings")
            splunk_cust_fields = settings_conf_file.get("custom_splunk_fields").get("splunk_additional_fields")
            matching_type = settings_conf_file.get("match_algo_detail").get("match_type")

            keys = None
            if splunk_cust_fields and splunk_cust_fields.strip() and matching_type in ["tstats", "datamodel"]:
                keys = splunk_cust_fields.split(",")
                keys = [key.strip() for key in keys]

            indicators_to_upload = []
            run_time = int(time.time())

            # Generate composite key for datamodel_name
            datamodel_name = self.datamodel_name or "Unknown"
            # Sanitize datamodel_name for use in key (remove special chars that could break KV Store keys)
            datamodel_name_safe = re.sub(r'[^a-zA-Z0-9_-]', '_', datamodel_name)
            current_dm_normalized = datamodel_name.strip()

            # Track which ioc_values we've already processed for this datamodel
            processed_iocs = set()

            for indicator in indicators:

                # Avoid processing the same ioc_value more than once per run
                ioc_val = indicator.get("ioc_value")
                if not ioc_val or ioc_val in processed_iocs:
                    continue

                if not matched_indicators.get(indicator["ioc_value"]):
                    continue

                # Generate composite key: ioc_value_datamodel_name
                composite_key = f"{indicator['ioc_value']}_{datamodel_name_safe}"
                
                # Check if entry with this ioc_value and datamodel_name already exists
                # (could have old key format or new composite key format)
                existing_indicator = None
                for existing in indicators:
                    existing_ioc = existing.get("ioc_value")
                    existing_dm = existing.get("datamodel_name")
                    existing_key = existing.get("_key", "")
                    
                    # Normalize datamodel names for comparison
                    existing_dm_normalized = (existing_dm or "Unknown").strip()

                    # Must match same ioc_value
                    if existing_ioc != indicator["ioc_value"]:
                        continue

                    # Only consider entries for the same datamodel (or exact composite key)
                    if existing_dm_normalized != current_dm_normalized and existing_key != composite_key:
                        continue

                    existing_indicator = existing
                    break
                
                if existing_indicator:
                    # Update existing entry - add to existing match_count
                    indicator = existing_indicator
                    indicator["match_count"] = (
                        int(indicator.get("match_count", 0))
                        + matched_indicators[indicator["ioc_value"]][0]
                    )
                    # Ensure composite key is set (updates old format keys to new format)
                    indicator["_key"] = composite_key
                else:
                    # New entry - set match_count and composite key
                    indicator["match_count"] = matched_indicators[indicator["ioc_value"]][0]
                    indicator["_key"] = composite_key
                
                indicator["sid"] = self.sid
                indicator["last_run_match_count"] = matched_indicators[
                    indicator["ioc_value"]
                ][0]
                indicator["last_run_first_seen"] = self.earliest_time
                indicator["last_run_last_seen"] = self.latest_time

                if int(indicator.get("match_time", 0)) < run_time:
                    indicator["match_time"] = run_time

                if int(indicator.get("last_seen", 0)) < self.latest_time:
                    indicator["last_seen"] = self.latest_time

                if indicator.get("first_seen") is None:
                    indicator["first_seen"] = self.earliest_time
                
                indicator["datamodel_name"] = datamodel_name

                # raw_event is only meaningful for raw matching (threatqmatchiocs).
                # Ensure datamodel entries do not carry over any raw_event value
                # from previous raw matches against the same IOC document.
                if "raw_event" in indicator:
                    indicator["raw_event"] = ""

                if keys:
                    for key in keys:
                        key1 = key.split('.')[-1]
                        indicator[key1] = dict(matched_indicators[indicator["ioc_value"]][1]).get(key1, None)
                indicators_to_upload.append(indicator)
                processed_iocs.add(ioc_val)

            for batch_i in range(0, len(indicators_to_upload), self.batch_size):
                put_indicators(
                    self.splunkd_uri,
                    self.session_key,
                    app_name,
                    indicators_to_upload[batch_i: batch_i + self.batch_size],
                )

        finally:
            unlock_lookup(self.splunkd_uri, self.session_key, app_name, lock_key)

    # Function which will be invoked when custom command runs
    def transform(self, events):
        """Transform method of Eventing Command."""
        # Tell Python this is a generator

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
        self.process_fieldmatch()

    def process_fieldmatch(self):
        """Process field matching."""
        it = 0
        try:
            def datamodel_events_wrapper(events):
                for event in events:
                    for field in self.match_fields:
                        if "count" not in event.keys():
                            raise Exception(
                                "Invalid Query! The provided query doesn't have count field!"
                            )
                        try:
                            if not event.get(field):
                                continue
                            if isinstance(event[field], list):
                                for list_item in event[field]:
                                    events_count[list_item] = [
                                        events_count.get(list_item, [0, None])[0] + int(event["count"]),
                                        event
                                    ]
                            else:
                                events_count[event[field]] = [
                                    events_count.get(event[field], [0, None])[0] + int(event["count"]),
                                    event
                                ]
                        except Exception as e:
                            logger.error(
                                "message=process_field_match_invalid_query |"
                                " Query is Invalid, Invalid data format is given Error: %s"
                                % str(e)
                            )
                if not events_count:
                    yield []
                else:
                    yield events_count

            datamodel_events = datamodel_events_wrapper(self.events)
            self.process_count = get_process_count(self.process_count)
            if self.chunk_size == 0:
                self.chunk_size = 50000 // self.process_count
            events_count = {}

            self.session_key = self.search_results_info.auth_token
            self.splunkd_uri = self.search_results_info.splunkd_uri
            self.sid = self.metadata.searchinfo.sid
            self.earliest_time = int(self.metadata.searchinfo.earliest_time)
            self.latest_time = int(self.metadata.searchinfo.latest_time)
            indicators = []
            query = get_kv_store_query("type", self.indicator_types)

            if self.latest_time == 0:
                self.latest_time = int(time.time())

            if self.is_update and not self.pull_both_lookups_iocs:
                indicators = get_matched_indicators(
                    self.splunkd_uri,
                    self.session_key,
                    app_name,
                    query=query,
                )
            elif not self.pull_both_lookups_iocs:
                indicators = get_unmatched_indicators(
                    self.splunkd_uri,
                    self.session_key,
                    app_name,
                    query=query,
                )
            else:
                indicators = get_all_indicators(
                    self.splunkd_uri,
                    self.session_key,
                    app_name,
                    query=query,
                )

            if not indicators:
                return

            url_match_dict = {}
            # Map from variant value to original ioc_value for port-based matching
            variant_to_ioc = {}
            indicator_values = set()
            
            # Build indicator values with port-based variants
            for indicator in indicators:
                # Get all matching variants (including port-based)
                variants = get_indicator_matching_variants(indicator)
                # Debug logging
                logger.debug(
                    "Indicator: ioc_value={}, type={}, port={}, variants={}".format(
                        indicator.get("ioc_value"),
                        indicator.get("type"),
                        indicator.get("port"),
                        variants
                    )
                )
                for variant in variants:
                    variant_to_ioc[variant] = indicator["ioc_value"]
                    indicator_values.add(variant)
                
                # Handle URL partial matching if enabled
                if self.trigger_partial_url_match:
                    stripped_ioc = indicator["ioc_value"]
                    if indicator["type"] == "URL" and "://" in indicator["ioc_value"]:
                        stripped_ioc = re.match(r"(\w*://)?(\S*)", stripped_ioc).group(
                            2
                        )
                        if stripped_ioc in url_match_dict.keys():
                            url_match_dict[stripped_ioc].append(indicator["ioc_value"])
                        else:
                            url_match_dict[stripped_ioc] = [indicator["ioc_value"]]
                        # Also add stripped variant to indicator_values
                        indicator_values.add(stripped_ioc)
                        variant_to_ioc[stripped_ioc] = indicator["ioc_value"]

            logger.info(
                "message=field_matching_process_count |"
                " Process count: {}".format(self.process_count))
            logger.info(
                "message=field_matching_cpu_count |"
                "Chunk Size: {}".format(self.chunk_size))
            pool = Pool(self.process_count)
            matched_indicators = {}  # Accumulate across all batches

            event_values = partial(_get_event_values)

            try:
                for event_value_set, current_events_count in pool.imap(
                    event_values, datamodel_events, chunksize=self.chunk_size
                ):

                    values = indicator_values & event_value_set
                    logger.debug("Matched variants in this batch: {}".format(values))

                    # Map variant values back to original ioc_value
                    # Accumulate counts for all variants that map to the same ioc_value
                    for variant_value in values:
                        if variant_value not in current_events_count:
                            continue
                        # Map variant back to original ioc_value
                        ioc_value = variant_to_ioc.get(variant_value, variant_value)
                        logger.debug("Variant '{}' maps to ioc_value '{}', count={}".format(
                            variant_value, ioc_value, current_events_count[variant_value][0]
                        ))
                        # Accumulate counts for all variants mapping to same ioc_value
                        # (e.g., "192.168.1.100" and "192.168.1.100:8000" both map to same ioc_value)
                        if ioc_value not in matched_indicators:
                            matched_indicators[ioc_value] = current_events_count[variant_value].copy()
                            it += current_events_count[variant_value][0]
                        else:
                            # Accumulate the count from this variant
                            matched_indicators[ioc_value][0] += current_events_count[variant_value][0]
                            it += current_events_count[variant_value][0]

                    # If match found, and some URL is stripped so we'll replace
                    # stripped URL indicators with the original indicators with scheme
                    if matched_indicators:
                        if url_match_dict:
                            for url_stripped in url_match_dict.keys():
                                for matched_ioc in list(matched_indicators.keys()):
                                    if matched_ioc == url_stripped:
                                        for value in url_match_dict[url_stripped]:
                                            matched_indicators[
                                                value
                                            ] = matched_indicators[matched_ioc]
                                        matched_indicators.pop(matched_ioc)
                    if len(matched_indicators) >= self.batch_size:
                        self.upload_indicators(matched_indicators)
                        matched_indicators = {}

            except Exception:
                logger.error(
                    "message=process_field_match_error |"
                    " {}".format(traceback.format_exc()))

            logger.info("Total events processed - {}".format(it))

            if matched_indicators:
                self.upload_indicators(matched_indicators)
            pool.close()
            pool.join()
            logger.info("finished execution")
        except Exception as e:
            logger.error("ThreatQ 'threatqfieldsmatchiocs' command error: %s" % str(e))
            raise


if __name__ == "__main__":
    dispatch(ThreatQFieldsMatchIOCSCommand, sys.argv, sys.stdin, sys.stdout, __name__)
