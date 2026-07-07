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

# Standard library
import os
import sys
import time
import json
import hashlib
import threading

# External libraries
import urllib3

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    os.path.join(splunkhome, "var", "log", "splunk", "trackme_persistentfields.log"),
    mode="a",
    maxBytes=10_000_000,
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
from trackme_libs import trackme_reqinfo, trackme_vtenant_account_from_service
from trackme_libs_utils import decode_unicode, get_uuid

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license

# import TrackMe get data libs
from trackme_libs_get_data import (
    search_kv_collection_restmode,
    search_kv_collection_searchmode,
    search_kv_collection_sdkmode,
)

# Import trackMe kvstore batch libs
from trackme_libs_kvstore_batch import batch_update_worker

# import trackme libs persistent fields definition
from collections_data import (
    persistent_fields_dsm,
    persistent_fields_dhm,
    persistent_fields_mhm,
    persistent_fields_flx,
    persistent_fields_fqm,
    persistent_fields_wlk,
    vtenant_account_default,
)

# Defensive merge helpers for FLX tracker-keyed fields (2.3.12+). The merge
# logic below relies on these to strip pre-2.3.12 legacy flat root keys from
# the existing KV value before union-merging with the new tracker-keyed
# wrapper. See trackme_libs_flx_tracker_keyed for the full rationale.
from trackme_libs_flx_tracker_keyed import (
    DROP_FIELD as _DROP_FIELD,
    strip_legacy_flat_keys as _strip_legacy_flat_keys,
    strip_legacy_flat_keys_from_raw as _strip_legacy_flat_keys_from_raw,
)


@Configuration(distributed=False)
class TrackMePersistentHandler(StreamingCommand):
    collection = Option(
        doc="""
        **Syntax:** **collection=****
        **Description:** Specify the collection.""",
        require=True,
        default="None",
        validate=validators.Match("collection", r"^.*$"),
    )

    key = Option(
        doc="""
        **Syntax:** **key=****
        **Description:** Specify the key.""",
        require=True,
        default="None",
        validate=validators.Match("key", r"^.*$"),
    )

    update_collection = Option(
        doc="""
        **Syntax:** **update_collection=****
        **Description:** Enables or disables updating and inserting innto the collection, this replaces the need from calling outputlookup.""",
        require=False,
        default=False,
        validate=validators.Match("key", r"^(True|False)$"),
    )

    preloaded_entity_fields = Option(
        doc="""
        **Syntax:** **preloaded_entity_fields=****
        **Description:** When True, skip the initial KV collection read and use _existing_mtime, _existing_ctime,
        _existing_data_last_time_seen fields from the input record for conflict/rejection detection.
        This avoids the expensive full-collection read when the upstream macro has already looked up entity fields.""",
        require=False,
        default="False",
        validate=validators.Match("preloaded_entity_fields", r"^(True|False)$"),
    )

    def get_component(self, collection_name):
        """
        Determine the component name based on the collection name.

        Args:
            collection_name (str): The name of the collection.

        Returns:
            str: The component name derived from the collection name.
        """
        # Define the prefix and corresponding component name
        if collection_name.startswith("trackme_dsm_"):
            component = "dsm"
        elif collection_name.startswith("trackme_dhm_"):
            component = "dhm"
        elif collection_name.startswith("trackme_mhm_"):
            component = "mhm"
        elif collection_name.startswith("trackme_flx_"):
            component = "flx"
        elif collection_name.startswith("trackme_fqm_"):
            component = "fqm"
        elif collection_name.startswith("trackme_wlk_"):
            component = "wlk"
        else:
            component = None  # or a default value if there's an expected default

        return component

    def get_tenant_id_from_collection(self, collection_name):
        """
        Extract tenant_id from collection name (e.g. trackme_dsm_tenant_mytenant -> mytenant).
        """
        for prefix in (
            "trackme_dsm_tenant_",
            "trackme_dhm_tenant_",
            "trackme_mhm_tenant_",
        ):
            if collection_name.startswith(prefix):
                return collection_name[len(prefix):]
        return None

    def get_tenant_default_delay_config(self, service, tenant_id, component=None):
        """
        Get tenant default delay configuration for a specific component (dsm/dhm).
        Reads component-prefixed fields first, falls back to shared fields, then to vtenant_account_default.
        Results are cached per (tenant_id, component) to avoid redundant Splunk SDK lookups
        when multiple entities are discovered in the same stream batch.
        Returns dict with default_delay_policy, default_delay_threshold_sec,
        variable_delay_default_slots, variable_delay_default, adaptive_delay.
        """
        cache = getattr(self, "_tenant_delay_config_cache", None)
        if cache is None:
            cache = {}
            self._tenant_delay_config_cache = cache
        cache_key = (tenant_id, component)
        if cache_key in cache:
            return cache[cache_key]

        pfx = f"{component}_" if component in ("dsm", "dhm") else ""
        dsm_fallback_threshold = 3600
        dhm_fallback_threshold = 86400
        fallback_threshold = dhm_fallback_threshold if component == "dhm" else dsm_fallback_threshold
        fallback_default = str(fallback_threshold)

        def _get(vtenant, field, default):
            prefixed = f"{pfx}{field}"
            val = vtenant.get(prefixed)
            if val is not None:
                return val
            val = vtenant.get(field)
            if val is not None:
                return val
            return vtenant_account_default.get(prefixed, vtenant_account_default.get(field, default))

        try:
            vtenant = trackme_vtenant_account_from_service(service, tenant_id)
            result = {
                "default_delay_policy": _get(vtenant, "default_delay_policy", "static"),
                "default_delay_threshold_sec": _get(vtenant, "default_delay_threshold_sec", fallback_threshold),
                "variable_delay_default_slots": _get(vtenant, "variable_delay_default_slots", "{}"),
                "variable_delay_default": _get(vtenant, "variable_delay_default", fallback_default),
                "adaptive_delay": vtenant.get("adaptive_delay", vtenant_account_default.get("adaptive_delay", 1)),
            }
        except Exception as e:
            logging.debug(
                f'instance_id="{getattr(self, "instance_id", "?")}", tenant_id="{tenant_id}", '
                f'could not load tenant default delay config, using system defaults: {e}'
            )
            result = {
                "default_delay_policy": vtenant_account_default.get(f"{pfx}default_delay_policy", vtenant_account_default.get("default_delay_policy", "static")),
                "default_delay_threshold_sec": vtenant_account_default.get(f"{pfx}default_delay_threshold_sec", vtenant_account_default.get("default_delay_threshold_sec", fallback_threshold)),
                "variable_delay_default_slots": vtenant_account_default.get(f"{pfx}variable_delay_default_slots", vtenant_account_default.get("variable_delay_default_slots", "{}")),
                "variable_delay_default": vtenant_account_default.get(f"{pfx}variable_delay_default", vtenant_account_default.get("variable_delay_default", fallback_default)),
                "adaptive_delay": vtenant_account_default.get("adaptive_delay", 1),
            }

        cache[cache_key] = result
        return result

    def apply_tenant_default_delay_to_new_entity(self, record, component, tenant_id, service):
        """
        Apply tenant default delay configuration to a new DSM/DHM entity.
        For static policy: sets data_max_delay_allowed, allow_adaptive_delay, variable_delay_policy.
        For variable policy: same + creates variable delay record.
        """
        if component not in ("dsm", "dhm"):
            return

        config = self.get_tenant_default_delay_config(service, tenant_id, component=component)
        fallback_threshold = 3600 if component == "dsm" else 86400
        policy = config.get("default_delay_policy", "static")
        try:
            threshold_sec = int(config.get("default_delay_threshold_sec", fallback_threshold))
        except (ValueError, TypeError):
            threshold_sec = fallback_threshold
        try:
            adaptive_delay = int(config.get("adaptive_delay", 1))
        except (ValueError, TypeError):
            adaptive_delay = 1
        try:
            variable_default = str(int(config.get("variable_delay_default", str(fallback_threshold))))
        except (ValueError, TypeError):
            variable_default = str(fallback_threshold)
        variable_slots_raw = config.get("variable_delay_default_slots", "{}")

        # Apply to main entity record
        record["variable_delay_policy"] = policy
        record["data_max_delay_allowed"] = threshold_sec if policy == "static" else int(variable_default)
        # allow_adaptive_delay defaults to the tenant adaptive_delay setting for
        # BOTH static and variable policies — it is no longer coupled to the
        # policy. Since PR #1611 the adaptive framework handles variable-delay
        # entities too, so a new variable-delay entity is eligible by default
        # when the tenant has adaptive delay enabled (operators opt a single
        # entity out by setting allow_adaptive_delay="false").
        record["allow_adaptive_delay"] = "true" if adaptive_delay == 1 else "false"

        if policy == "variable":
            # Queue variable delay record for deferred batch creation (fire-and-forget at end of stream)
            self._queue_variable_delay_record(
                tenant_id=tenant_id,
                component=component,
                record=record,
                variable_default=variable_default,
                variable_slots_raw=variable_slots_raw,
            )

    def _queue_variable_delay_record(
        self, tenant_id, component, record, variable_default, variable_slots_raw
    ):
        """Queue a variable delay record for deferred batch creation at end of stream."""
        entity_key = record.get("_key")
        object_value = record.get("object", "")
        if not entity_key:
            return

        slots_config = {}
        if variable_slots_raw:
            try:
                slots_config = json.loads(variable_slots_raw) if isinstance(variable_slots_raw, str) else variable_slots_raw
            except (json.JSONDecodeError, TypeError):
                slots_config = {"slots": []}
        if "slots" not in slots_config:
            slots_config["slots"] = []

        now_epoch = str(time.time())
        variable_delay_record = {
            "_key": entity_key,
            "object": object_value,
            "object_category": f"splk-{component}",
            "tenant_id": tenant_id,
            "variable_delay_enabled": "true",
            "variable_delay_mode": "manual",
            "variable_delay_default": str(variable_default),
            "variable_delay_slots": json.dumps(slots_config),
            "variable_delay_last_auto_review": "",
            "variable_delay_auto_review_enabled": "false",
            "variable_delay_auto_review_period": "-30d",
            "variable_delay_auto_review_method": "perc95",
            "variable_delay_ctime": now_epoch,
            "variable_delay_mtime": now_epoch,
            "variable_delay_updated_by": "entity_provisioning",
        }
        if not hasattr(self, "_pending_variable_delay_records"):
            self._pending_variable_delay_records = []
        self._pending_variable_delay_records.append(variable_delay_record)

    def _flush_variable_delay_records(self, service, tenant_id, component):
        """Flush pending variable delay records via a single batch_save in a fire-and-forget background thread."""
        records_to_create = getattr(self, "_pending_variable_delay_records", [])
        if not records_to_create:
            return

        instance_id = self.instance_id

        def _batch_save():
            collection_name = f"kv_trackme_{component}_variable_delay_tenant_{tenant_id}"
            try:
                var_delay_collection = service.kvstore[collection_name]
                var_delay_collection.data.batch_save(*records_to_create)
                logging.info(
                    f'instance_id="{instance_id}", tenant_id="{tenant_id}", component="{component}", '
                    f"variable delay batch provisioning complete, records={len(records_to_create)}"
                )
            except Exception as e:
                logging.warning(
                    f'instance_id="{instance_id}", tenant_id="{tenant_id}", component="{component}", '
                    f"variable delay batch provisioning failed: {e}"
                )

        thread = threading.Thread(target=_batch_save, daemon=False)
        thread.start()
        logging.info(
            f'instance_id="{instance_id}", tenant_id="{tenant_id}", component="{component}", '
            f"started background variable delay provisioning for {len(records_to_create)} entities"
        )

    def stream(self, records):
        # performance counter
        start_time = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Max multi thread workers
        max_multi_thread_workers = int(
            reqinfo["trackme_conf"]["trackme_general"]["max_multi_thread_workers"]
        )

        # set instance_id
        self.instance_id = get_uuid()

        # connect to the KVstore
        target_collection = f"kv_{self.collection}"
        collection = self.service.kvstore[target_collection]

        # set the component
        persistent_fields = []
        component = self.get_component(self.collection)

        if component == "dsm":
            persistent_fields = []
            for field in persistent_fields_dsm:
                persistent_fields.append(field)
        elif component == "dhm":
            for field in persistent_fields_dhm:
                persistent_fields.append(field)
        elif component == "mhm":
            for field in persistent_fields_mhm:
                persistent_fields.append(field)
        elif component == "flx":
            for field in persistent_fields_flx:
                persistent_fields.append(field)
        elif component == "fqm":
            for field in persistent_fields_fqm:
                persistent_fields.append(field)
        elif component == "wlk":
            for field in persistent_fields_wlk:
                persistent_fields.append(field)

        # Sourcetype explosion safeguard for DSM: read cap setting
        sourcetype_cap_per_index = 0
        if component == "dsm":
            try:
                sourcetype_cap_per_index = int(
                    reqinfo["trackme_conf"].get("splk_general", {}).get(
                        "splk_general_dsm_sourcetype_cap_per_index", "100"
                    )
                )
            except (ValueError, TypeError):
                sourcetype_cap_per_index = 100

        # Check license state to determine if we are in read-only mode
        # In read-only mode, we skip new entity creation (only update existing records)
        license_read_only = False
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"],
                self._metadata.searchinfo.session_key,
            )
            license_read_only = bool(check_license.get("license_read_only", False))
        except Exception as e:
            logging.error(
                f'instance_id="{self.instance_id}", collection="{self.collection}", failed to check license status, exception="{str(e)}"'
            )

        if license_read_only:
            logging.info(
                f'instance_id="{self.instance_id}", collection="{self.collection}", license is in read-only mode, new entity creation will be skipped'
            )

        # Preloaded mode: skip the expensive full-collection read when the upstream
        # macro has already looked up the necessary entity fields (_existing_mtime,
        # _existing_ctime, _existing_data_last_time_seen).
        use_preloaded = self.preloaded_entity_fields == "True"

        # Task timing: init phase complete
        init_run_time = round(time.time() - start_time, 3)

        if use_preloaded:
            logging.info(
                f'instance_id="{self.instance_id}", collection="{self.collection}", preloaded_entity_fields mode enabled, '
                f'skipping full collection read, init_run_time={init_run_time}'
            )
            collection_records = []
            collection_keys = set()
            collection_dict = {}
        else:
            # set task
            #
            task_start = time.time()
            task_instance_id = get_uuid()
            task_name = "get_collection_records"

            # get all records
            collection_records, collection_keys, collection_dict, last_page = (
                search_kv_collection_sdkmode(
                    logging, self.service, target_collection, page=1, page_count=0, orderby="keyid"
                )
            )

            # end task
            #
            task_end = time.time()
            task_run_time = round((task_end - task_start), 3)
            logging.info(
                f'instance_id="{self.instance_id}", collection="{self.collection}", '
                f'task="{task_name}", task_run_time={task_run_time}, '
                f'collection_records={len(collection_records)}'
            )

        # Task timing: collection read phase complete
        collection_read_run_time = round(time.time() - start_time, 3) - init_run_time

        # Sourcetype explosion safeguard: build per-index sourcetype counts from existing collection
        # In non-preloaded mode, collection_dict is populated with all existing records (already in memory).
        # In preloaded mode, collection_dict is empty — counts start at 0, only new entities are counted.
        #
        # Aggregate entities with the `:@all` convention (object ending with `:@all`)
        # are excluded: they are synthetic per-index aggregates produced by
        # merged-mode trackers, not distinct ingestion sourcetypes, so they
        # must not consume a cap slot. See the matching exemption in the per-
        # record cap check below.
        index_sourcetype_counts = {}
        capped_indexes = {}
        skipped_capped_entities = 0

        if sourcetype_cap_per_index > 0 and component == "dsm":
            for existing_record in collection_dict.values():
                idx = existing_record.get("data_index", "")
                if idx and not existing_record.get("object", "").endswith(":@all"):
                    index_sourcetype_counts[idx] = index_sourcetype_counts.get(idx, 0) + 1

        #
        # Define Meta
        #

        final_records = []

        # Track skipped new entities for logging
        skipped_new_entities = 0

        # Track existing vs new entity counts (especially important in preloaded mode
        # where we don't have collection_keys to count existing entities)
        existing_entity_count = 0
        new_entity_count = 0

        # Extract tenant_id from collection name once for the entire batch.
        # Used as a safeguard to ensure every record has tenant_id set before KVStore write.
        collection_tenant_id = self.get_tenant_id_from_collection(self.collection)

        # Task timing: record processing loop
        record_processing_start = time.time()

        # Loop in the results
        for record in records:
            if use_preloaded:
                # In preloaded mode, determine new-vs-existing from _existing_mtime
                record_is_new = not record.get("_existing_mtime")
            else:
                record_is_new = record.get(self.key) not in collection_keys

            # Track entity counts
            if record_is_new:
                new_entity_count += 1
            else:
                existing_entity_count += 1

            # In read-only mode, skip new entities entirely
            if license_read_only and record_is_new:
                skipped_new_entities += 1
                continue

            # Sourcetype explosion safeguard: block new DSM entities when
            # cap is exceeded for their data_index.
            #
            # The pseudo-`lookups` data_index is exempted: each sourcetype
            # under it identifies a distinct lookup (CSV file or KVstore
            # collection), not a misclassified ingestion sourcetype, so a
            # high cardinality is the normal mode of operation rather than
            # a symptom of pipeline mis-routing. A customer monitoring
            # several hundred lookups must not be blocked at 100.
            #
            # Aggregate entities with the `:@all` convention (object ending
            # in `:@all`) are likewise exempted: they are synthetic per-index
            # aggregates produced by merged-mode trackers, not real ingestion
            # sourcetypes. Without this exemption the documented remediation
            # for a triggered cap alert — blocklist the noisy sourcetypes
            # and re-cover the index with one merged-mode aggregate —
            # would silently fail, because the blocklisted records remain
            # in the collection and continue to consume cap slots.
            if (
                sourcetype_cap_per_index > 0
                and component == "dsm"
                and record_is_new
                and record.get("data_index") != "lookups"
                and not record.get("object", "").endswith(":@all")
            ):
                data_index = record.get("data_index", "")
                current_count = index_sourcetype_counts.get(data_index, 0)
                if current_count >= sourcetype_cap_per_index:
                    capped_indexes[data_index] = current_count
                    skipped_capped_entities += 1
                    continue
                else:
                    index_sourcetype_counts[data_index] = current_count + 1

            # ctime: if record is new, add a ctime field, otherwise ensure we have a ctime field set to the current time
            if record_is_new:
                record["ctime"] = time.time()
            else:
                ctime = record.get("ctime", None)
                if not ctime:
                    # In preloaded mode, use _existing_ctime if available
                    if use_preloaded and record.get("_existing_ctime"):
                        record["ctime"] = record["_existing_ctime"]
                    else:
                        record["ctime"] = time.time()

            # get time, if any
            time_event = None
            try:
                time_event = record["_time"]
            except Exception as e:
                time_event = time.time()

            logging.debug(f'instance_id="{self.instance_id}", inspecting record={json.dumps(record, indent=2)}')

            # always set an object_256 and add _key in the record
            record_object_value = decode_unicode(record["object"])
            record_alias = decode_unicode(record["alias"])
            logging.debug(
                f'instance_id="{self.instance_id}", object="{record["object"]}", decoded_object="{record_object_value}", alias="{record["alias"]}", decoded_alias="{record_alias}"'
            )

            # add the _key in the record if there is none
            if not record.get("_key"):
                object_256 = hashlib.sha256(
                    record_object_value.encode("utf-8")
                ).hexdigest()
                record["_key"] = object_256
                logging.debug(
                    f'instance_id="{self.instance_id}", adding _key="{object_256}" to record for object="{record_object_value}", alias="{record_alias}"'
                )

            # handle unicode for object and alias
            record["object"] = record_object_value
            record["alias"] = record_alias

            # get tracker_runtime, if any
            tracker_runtime = record.get("tracker_runtime", None)
            if tracker_runtime:
                try:
                    tracker_runtime = float(tracker_runtime)
                except Exception as e:
                    tracker_runtime = time.time()
            else:
                tracker_runtime = time.time()

            # rejected record: only applies to component dsm/dhm, if the value of data_last_time_seen in record is lower than the current value in the KVstore,
            # then the record should be rejected as it is outdated and might indicate a platform level temporary issue
            rejected_record = False
            if component in ["dsm", "dhm"]:

                try:

                    rejected_record_key = record.get(self.key)
                    logging.debug(f'instance_id="{self.instance_id}", record key="{rejected_record_key}"')

                    if use_preloaded:
                        # In preloaded mode, derive existence from _existing_mtime (consistent with record_is_new)
                        # An entity may exist in KV with a null data_last_time_seen, so we can't use that field alone
                        has_existing = not record_is_new
                        kvstore_data_last_time_seen = record.get("_existing_data_last_time_seen") if has_existing else None
                    else:
                        rejected_record_dict = collection_dict.get(rejected_record_key)
                        logging.debug(f'instance_id="{self.instance_id}", rejected_record_dict="{rejected_record_dict}"')
                        has_existing = rejected_record_dict is not None
                        kvstore_data_last_time_seen = rejected_record_dict.get("data_last_time_seen", None) if has_existing else None

                    if has_existing:
                        logging.debug(
                            f'instance_id="{self.instance_id}", kvstore_data_last_time_seen="{kvstore_data_last_time_seen}"'
                        )

                        if kvstore_data_last_time_seen:
                            kvstore_data_last_time_seen = float(
                                kvstore_data_last_time_seen
                            )

                        # get current_data_last_time_seen
                        current_data_last_time_seen = record.get(
                            "data_last_time_seen", None
                        )
                        if current_data_last_time_seen:
                            current_data_last_time_seen = float(
                                current_data_last_time_seen
                            )

                        # process if we have values
                        if kvstore_data_last_time_seen and current_data_last_time_seen:
                            if (
                                current_data_last_time_seen
                                < kvstore_data_last_time_seen
                            ):
                                rejected_record = True
                                logging.warning(
                                    f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", record key="{record.get(self.key)}", rejected record detected, epoch value in kVstore {kvstore_data_last_time_seen} is bigger than record submitted value {current_data_last_time_seen}, record="{json.dumps(record, indent=2)}"'
                                )
                            else:
                                rejected_record = False
                                logging.debug(
                                    f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", record key="{record.get(self.key)}", rejected record not detected'
                                )
                        else:
                            rejected_record = False
                            logging.debug(
                                f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", record key="{record.get(self.key)}", object="{record.get("object")}", rejected record not detected, values are None'
                            )

                    else:
                        rejected_record = False
                        if record_is_new:
                            logging.debug(
                                f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", record key="{record.get(self.key)}", object="{record.get("object")}", no KVstore entry yet for this object, skipping rejected record check.'
                            )
                        else:
                            logging.warning(
                                f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", record key="{record.get(self.key)}", object="{record.get("object")}", this object could not be found in the dictionary while not marked as new; KVstore entry may be missing or corrupted.'
                            )

                except Exception as e:
                    logging.error(
                        f'instance_id="{self.instance_id}", collection="{target_collection}", component="{component}", failed to extract and convert data_last_time_seen, record key="{record.get(self.key)}", object="{record.get("object")}", exception message="{str(e)}"'
                    )
                    rejected_record = False

            # detect conflict update
            conflict_update = False
            if not record_is_new:
                # attempt to retrieve and convert mtime value, if fails for any reason, set conflict_update to False
                try:
                    if use_preloaded:
                        mtime = float(record.get("_existing_mtime", 0))
                    else:
                        mtime = float(collection_dict[record.get(self.key)].get("mtime"))
                    if mtime > float(tracker_runtime):
                        conflict_update = True
                        logging.info(
                            f'instance_id="{self.instance_id}", collection="{self.collection}", record key="{record.get(self.key)}", conflict update detected, preserving persistent fields="{persistent_fields}", record="{json.dumps(record, indent=2)}"'
                        )
                    else:
                        conflict_update = False

                except Exception as e:
                    logging.error(
                        f'instance_id="{self.instance_id}", failed to extract and convert mtime, tracker_runtime="{tracker_runtime}", exception message="{str(e)}"'
                    )
                    conflict_update = False

            # create a summary record
            summary_record = {}

            # Add _time first
            summary_record["_time"] = float(time_event)

            # if not rejected
            if not rejected_record:

                # Apply tenant default delay to new DSM/DHM entities (entity provisioning)
                if record_is_new and component in ["dsm", "dhm"]:
                    tenant_id = self.get_tenant_id_from_collection(self.collection)
                    if tenant_id:
                        self.apply_tenant_default_delay_to_new_entity(
                            record, component, tenant_id, self.service
                        )

                # Handle merging of tracker-keyed JSON fields for FLX concurrent trackers support
                # This must be done before the main loop to properly merge tracker-specific data
                if component == "flx" and not record_is_new:
                    existing_record = collection_dict.get(record.get(self.key), {})
                    
                    # Merge metrics (JSON object keyed by tracker_name)
                    if "metrics" in record and "metrics" in existing_record:
                        try:
                            new_metrics_str = record.get("metrics")
                            existing_metrics_str = existing_record.get("metrics")
                            
                            # Parse both as JSON objects
                            new_metrics = {}
                            existing_metrics = {}
                            
                            if new_metrics_str:
                                if isinstance(new_metrics_str, str):
                                    try:
                                        new_metrics = json.loads(new_metrics_str)
                                    except (json.JSONDecodeError, TypeError):
                                        # If parsing fails, try to treat as regular metrics dict
                                        new_metrics = {}
                                elif isinstance(new_metrics_str, dict):
                                    new_metrics = new_metrics_str
                            
                            if existing_metrics_str:
                                if isinstance(existing_metrics_str, str):
                                    try:
                                        existing_metrics = json.loads(existing_metrics_str)
                                    except (json.JSONDecodeError, TypeError):
                                        # If parsing fails, might be old format, skip merge
                                        existing_metrics = {}
                                elif isinstance(existing_metrics_str, dict):
                                    existing_metrics = existing_metrics_str

                            # Defensive: strip pre-2.3.12 legacy flat root keys
                            # (e.g. {"metric_a": 1.0}) so they don't survive the
                            # union merge with the new tracker-keyed wrapper.
                            existing_metrics = _strip_legacy_flat_keys(
                                "metrics", existing_metrics
                            )

                            # Merge: existing trackers preserved, new tracker updates/overwrites its entry
                            merged_metrics = existing_metrics.copy()
                            merged_metrics.update(new_metrics)
                            
                            # Remove internal "status" field from metrics
                            # This is an internal field, not a user metric
                            # Handle tracker-keyed format: {"tracker1": {"metric1": 123, "status": 1}, ...}
                            # Handle old format: {"metric1": 123, "status": 1}
                            if merged_metrics:
                                # Check if it's tracker-keyed format (values are dicts with metrics)
                                is_tracker_keyed = False
                                for tracker_name, tracker_metrics in merged_metrics.items():
                                    if isinstance(tracker_metrics, dict):
                                        # Check if this looks like a metrics dict (has numeric/string values)
                                        # If all values are simple types, it's likely tracker-keyed metrics format
                                        if all(isinstance(v, (int, float, str, bool)) or v is None for v in tracker_metrics.values()):
                                            # This is tracker-keyed format, remove "status" from each tracker's metrics
                                            is_tracker_keyed = True
                                            if "status" in tracker_metrics:
                                                cleaned_metrics = tracker_metrics.copy()
                                                del cleaned_metrics["status"]
                                                merged_metrics[tracker_name] = cleaned_metrics
                                
                                # If old format (not tracker-keyed), remove "status" from top level
                                if not is_tracker_keyed and "status" in merged_metrics:
                                    cleaned_metrics = merged_metrics.copy()
                                    del cleaned_metrics["status"]
                                    merged_metrics = cleaned_metrics
                            
                            # Store merged metrics as JSON string
                            record["metrics"] = json.dumps(merged_metrics)
                            
                            logging.debug(
                                f'instance_id="{self.instance_id}", merged metrics for object="{record.get("object")}", '
                                f'existing_trackers={list(existing_metrics.keys())}, '
                                f'new_trackers={list(new_metrics.keys())}, '
                                f'merged_trackers={list(merged_metrics.keys())}'
                            )
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge metrics for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "metrics" in record:
                        # New record or existing record doesn't have metrics, clean "status" from incoming metrics
                        try:
                            new_metrics_str = record.get("metrics")
                            if new_metrics_str:
                                new_metrics = {}
                                if isinstance(new_metrics_str, str):
                                    try:
                                        new_metrics = json.loads(new_metrics_str)
                                    except (json.JSONDecodeError, TypeError):
                                        pass
                                elif isinstance(new_metrics_str, dict):
                                    new_metrics = new_metrics_str
                                
                                # Remove internal "status" field from metrics
                                if new_metrics:
                                    # Check if it's tracker-keyed format
                                    is_tracker_keyed = False
                                    for tracker_name, tracker_metrics in new_metrics.items():
                                        if isinstance(tracker_metrics, dict):
                                            if all(isinstance(v, (int, float, str, bool)) or v is None for v in tracker_metrics.values()):
                                                is_tracker_keyed = True
                                                if "status" in tracker_metrics:
                                                    cleaned_metrics = tracker_metrics.copy()
                                                    del cleaned_metrics["status"]
                                                    new_metrics[tracker_name] = cleaned_metrics
                                    
                                    # If old format, remove "status" from top level
                                    if not is_tracker_keyed and "status" in new_metrics:
                                        cleaned_metrics = new_metrics.copy()
                                        del cleaned_metrics["status"]
                                        new_metrics = cleaned_metrics
                                    
                                    # Store cleaned metrics back
                                    if isinstance(new_metrics_str, str):
                                        record["metrics"] = json.dumps(new_metrics)
                                    else:
                                        record["metrics"] = new_metrics
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to clean status from metrics for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "metrics" in existing_record:
                        # Field not in incoming record, preserve existing — but still
                        # strip legacy flat keys so self-healing applies even when no
                        # tracker writes metrics to this entity in the current cycle.
                        # Symmetric with the equivalent branches for object_description,
                        # status_description, and status_description_short below.
                        _stripped_raw = _strip_legacy_flat_keys_from_raw(
                            "metrics",
                            existing_record.get("metrics"),
                        )
                        if _stripped_raw is _DROP_FIELD:
                            record.pop("metrics", None)
                        else:
                            record["metrics"] = _stripped_raw

                    # Merge status_description (JSON object keyed by tracker_name)
                    if "status_description" in record:
                        # Field exists in incoming record, try to merge
                        try:
                            new_status_desc_str = record.get("status_description")
                            existing_status_desc_str = existing_record.get("status_description") if "status_description" in existing_record else None
                            
                            # If incoming value is None or empty, preserve existing and skip merge
                            if not new_status_desc_str:
                                if existing_status_desc_str:
                                    record["status_description"] = existing_status_desc_str
                                else:
                                    # No existing, remove empty field
                                    record.pop("status_description", None)
                            else:
                                # We have incoming data, proceed with merge
                                new_status_desc = None
                                existing_status_desc = {}
                                
                                if isinstance(new_status_desc_str, str):
                                    # Skip empty strings (they're not valid JSON)
                                    if new_status_desc_str.strip():
                                        try:
                                            new_status_desc = json.loads(new_status_desc_str)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, skip merge
                                            new_status_desc = None
                                    else:
                                        # Empty string, preserve existing if available
                                        if existing_status_desc_str:
                                            record["status_description"] = existing_status_desc_str
                                        else:
                                            # No existing, remove empty field
                                            record.pop("status_description", None)
                                        new_status_desc = None
                                elif isinstance(new_status_desc_str, dict):
                                    new_status_desc = new_status_desc_str
                                
                                # Parse existing status_description if available
                                if existing_status_desc_str:
                                    if isinstance(existing_status_desc_str, str):
                                        # Skip empty strings
                                        if existing_status_desc_str.strip():
                                            try:
                                                existing_status_desc = json.loads(existing_status_desc_str)
                                            except (json.JSONDecodeError, TypeError):
                                                # If parsing fails, might be old format string, skip merge
                                                existing_status_desc = {}
                                        else:
                                            existing_status_desc = {}
                                    elif isinstance(existing_status_desc_str, dict):
                                        existing_status_desc = existing_status_desc_str

                                # Defensive: strip pre-2.3.12 legacy flat root keys
                                # (e.g. {"status": "online", "last_event": "..."})
                                # so they don't survive the union merge with the
                                # new tracker-keyed wrapper.
                                existing_status_desc = _strip_legacy_flat_keys(
                                    "status_description", existing_status_desc
                                )

                                # Merge: existing trackers preserved, new tracker updates/overwrites its entry.
                                # Fallback "preserve existing" branches must re-serialize the
                                # stripped `existing_status_desc` (NOT existing_record.get(...))
                                # so they don't re-introduce the contamination just stripped.
                                if new_status_desc is not None:
                                    if new_status_desc:
                                        merged_status_desc = existing_status_desc.copy() if existing_status_desc else {}
                                        merged_status_desc.update(new_status_desc)

                                        # Store merged status_description as JSON string (only if we have content)
                                        if merged_status_desc:
                                            # Check if merged dict has any non-empty values
                                            has_content = any(v for v in merged_status_desc.values() if v)
                                            if has_content:
                                                record["status_description"] = json.dumps(merged_status_desc)
                                            elif existing_status_desc:
                                                # Merged is empty, preserve stripped existing if available
                                                record["status_description"] = json.dumps(existing_status_desc)
                                        elif existing_status_desc:
                                            # If new is empty but existing has content, preserve stripped existing
                                            record["status_description"] = json.dumps(existing_status_desc)
                                    elif existing_status_desc:
                                        # New is empty but existing has content, preserve stripped existing
                                        record["status_description"] = json.dumps(existing_status_desc)
                                    else:
                                        # Both are empty, remove field to avoid storing {}
                                        record.pop("status_description", None)
                                elif existing_status_desc:
                                    # No new data but existing has content, preserve stripped existing
                                    record["status_description"] = json.dumps(existing_status_desc)
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge status_description for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "status_description" in existing_record:
                        # Field not in incoming record, preserve existing — but still
                        # strip legacy flat keys so self-healing applies even when no
                        # tracker writes to this entity in the current cycle.
                        _stripped_raw = _strip_legacy_flat_keys_from_raw(
                            "status_description",
                            existing_record.get("status_description"),
                        )
                        if _stripped_raw is _DROP_FIELD:
                            record.pop("status_description", None)
                        else:
                            record["status_description"] = _stripped_raw
                    
                    # Merge status_description_short (JSON object keyed by tracker_name)
                    if "status_description_short" in record:
                        try:
                            new_status_desc_short_str = record.get("status_description_short")
                            existing_status_desc_short_str = existing_record.get("status_description_short") if "status_description_short" in existing_record else None
                            
                            # If incoming value is None or empty, preserve existing and skip merge
                            if not new_status_desc_short_str:
                                if existing_status_desc_short_str:
                                    record["status_description_short"] = existing_status_desc_short_str
                                else:
                                    # No existing, remove empty field
                                    record.pop("status_description_short", None)
                            else:
                                # We have incoming data, proceed with merge
                                new_status_desc_short = None
                                existing_status_desc_short = {}
                                
                                if isinstance(new_status_desc_short_str, str):
                                    # Skip empty strings (they're not valid JSON)
                                    if new_status_desc_short_str.strip():
                                        try:
                                            new_status_desc_short = json.loads(new_status_desc_short_str)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, skip merge
                                            new_status_desc_short = None
                                    else:
                                        # Empty string, preserve existing if available
                                        if existing_status_desc_short_str:
                                            record["status_description_short"] = existing_status_desc_short_str
                                        else:
                                            # No existing, remove empty field
                                            record.pop("status_description_short", None)
                                        new_status_desc_short = None
                                elif isinstance(new_status_desc_short_str, dict):
                                    new_status_desc_short = new_status_desc_short_str
                                
                                # Parse existing status_description_short if available
                                if existing_status_desc_short_str:
                                    if isinstance(existing_status_desc_short_str, str):
                                        # Skip empty strings
                                        if existing_status_desc_short_str.strip():
                                            try:
                                                existing_status_desc_short = json.loads(existing_status_desc_short_str)
                                            except (json.JSONDecodeError, TypeError):
                                                # If parsing fails, might be old format string, skip merge
                                                existing_status_desc_short = {}
                                        else:
                                            existing_status_desc_short = {}
                                    elif isinstance(existing_status_desc_short_str, dict):
                                        existing_status_desc_short = existing_status_desc_short_str

                                # Defensive: strip pre-2.3.12 legacy flat root keys
                                # so they don't survive the union merge with the
                                # new tracker-keyed wrapper.
                                existing_status_desc_short = _strip_legacy_flat_keys(
                                    "status_description_short", existing_status_desc_short
                                )

                                # Merge: existing trackers preserved, new tracker updates/overwrites its entry.
                                # Fallback "preserve existing" branches must re-serialize the
                                # stripped `existing_status_desc_short` (NOT existing_record.get(...))
                                # so they don't re-introduce the contamination just stripped.
                                if new_status_desc_short is not None:
                                    if new_status_desc_short:
                                        merged_status_desc_short = existing_status_desc_short.copy() if existing_status_desc_short else {}
                                        merged_status_desc_short.update(new_status_desc_short)

                                        # Store merged status_description_short as JSON string (only if we have content)
                                        if merged_status_desc_short:
                                            # Check if merged dict has any non-empty values
                                            has_content = any(v for v in merged_status_desc_short.values() if v)
                                            if has_content:
                                                record["status_description_short"] = json.dumps(merged_status_desc_short)
                                            elif existing_status_desc_short:
                                                # Merged is empty, preserve stripped existing if available
                                                record["status_description_short"] = json.dumps(existing_status_desc_short)
                                        elif existing_status_desc_short:
                                            # If new is empty but existing has content, preserve stripped existing
                                            record["status_description_short"] = json.dumps(existing_status_desc_short)
                                    elif existing_status_desc_short:
                                        # New is empty but existing has content, preserve stripped existing
                                        record["status_description_short"] = json.dumps(existing_status_desc_short)
                                    else:
                                        # Both are empty, remove field to avoid storing {}
                                        record.pop("status_description_short", None)
                                elif existing_status_desc_short:
                                    # No new data but existing has content, preserve stripped existing
                                    record["status_description_short"] = json.dumps(existing_status_desc_short)
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge status_description_short for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "status_description_short" in existing_record:
                        # Field not in incoming record, preserve existing — but still
                        # strip legacy flat keys so self-healing applies even when no
                        # tracker writes to this entity in the current cycle.
                        _stripped_raw = _strip_legacy_flat_keys_from_raw(
                            "status_description_short",
                            existing_record.get("status_description_short"),
                        )
                        if _stripped_raw is _DROP_FIELD:
                            record.pop("status_description_short", None)
                        else:
                            record["status_description_short"] = _stripped_raw
                    
                    # Merge object_description (JSON object keyed by tracker_name)
                    if "object_description" in record:
                        # Field exists in incoming record, try to merge
                        try:
                            new_object_desc_str = record.get("object_description")
                            existing_object_desc_str = existing_record.get("object_description") if "object_description" in existing_record else None
                            
                            # If incoming value is None or empty, preserve existing and skip merge
                            if not new_object_desc_str:
                                if existing_object_desc_str:
                                    record["object_description"] = existing_object_desc_str
                                else:
                                    # No existing, remove empty field
                                    record.pop("object_description", None)
                            else:
                                # We have incoming data, proceed with merge
                                new_object_desc = None
                                existing_object_desc = {}
                                
                                if isinstance(new_object_desc_str, str):
                                    # Skip empty strings (they're not valid JSON)
                                    if new_object_desc_str.strip():
                                        try:
                                            new_object_desc = json.loads(new_object_desc_str)
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format string, skip merge
                                            new_object_desc = None
                                    else:
                                        # Empty string, preserve existing if available
                                        if existing_object_desc_str:
                                            record["object_description"] = existing_object_desc_str
                                        else:
                                            # No existing, remove empty field
                                            record.pop("object_description", None)
                                        new_object_desc = None
                                elif isinstance(new_object_desc_str, dict):
                                    new_object_desc = new_object_desc_str
                                
                                # Parse existing object_description if available
                                if existing_object_desc_str:
                                    if isinstance(existing_object_desc_str, str):
                                        # Skip empty strings
                                        if existing_object_desc_str.strip():
                                            try:
                                                existing_object_desc = json.loads(existing_object_desc_str)
                                            except (json.JSONDecodeError, TypeError):
                                                # If parsing fails, might be old format string, skip merge
                                                existing_object_desc = {}
                                        else:
                                            existing_object_desc = {}
                                    elif isinstance(existing_object_desc_str, dict):
                                        existing_object_desc = existing_object_desc_str

                                # Defensive: strip pre-2.3.12 legacy flat root keys
                                # (e.g. {"indexes": "...", "last_event_time": 1234567,
                                # "sourcetypes": "...", "last_ingest_time": 1234567})
                                # so they don't survive the union merge with the new
                                # tracker-keyed wrapper. Without this, templates that
                                # read object_description back via `spath` (e.g.
                                # splk_hosts_tracking, cribl_edge_fleet_metrics)
                                # observe stale top-level values frozen at the
                                # upgrade timestamp.
                                existing_object_desc = _strip_legacy_flat_keys(
                                    "object_description", existing_object_desc
                                )

                                # Merge: existing trackers preserved, new tracker updates/overwrites its entry.
                                # Fallback "preserve existing" branches must re-serialize the
                                # stripped `existing_object_desc` (NOT existing_record.get(...))
                                # so they don't re-introduce the contamination just stripped.
                                if new_object_desc is not None:
                                    if new_object_desc:
                                        merged_object_desc = existing_object_desc.copy() if existing_object_desc else {}
                                        merged_object_desc.update(new_object_desc)

                                        # Store merged object_description as JSON string (only if we have content)
                                        if merged_object_desc:
                                            # Check if merged dict has any non-empty values
                                            has_content = any(v for v in merged_object_desc.values() if v)
                                            if has_content:
                                                record["object_description"] = json.dumps(merged_object_desc)
                                            elif existing_object_desc:
                                                # Merged is empty, preserve stripped existing if available
                                                record["object_description"] = json.dumps(existing_object_desc)
                                        elif existing_object_desc:
                                            # If new is empty but existing has content, preserve stripped existing
                                            record["object_description"] = json.dumps(existing_object_desc)
                                    elif existing_object_desc:
                                        # New is empty but existing has content, preserve stripped existing
                                        record["object_description"] = json.dumps(existing_object_desc)
                                    else:
                                        # Both are empty, remove field to avoid storing {}
                                        record.pop("object_description", None)
                                elif existing_object_desc:
                                    # No new data but existing has content, preserve stripped existing
                                    record["object_description"] = json.dumps(existing_object_desc)
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge object_description for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "object_description" in existing_record:
                        # Field not in incoming record, preserve existing — but still
                        # strip legacy flat keys so self-healing applies even when no
                        # tracker writes to this entity in the current cycle.
                        _stripped_raw = _strip_legacy_flat_keys_from_raw(
                            "object_description",
                            existing_record.get("object_description"),
                        )
                        if _stripped_raw is _DROP_FIELD:
                            record.pop("object_description", None)
                        else:
                            record["object_description"] = _stripped_raw
                    
                    # Merge status (JSON object keyed by tracker_name)
                    if "status" in record:
                        # Field exists in incoming record, try to merge
                        try:
                            new_status_str = record.get("status")
                            existing_status_str = existing_record.get("status") if "status" in existing_record else None
                            
                            # Parse incoming status
                            new_status = None
                            existing_status = {}
                            
                            if isinstance(new_status_str, str):
                                # Try to parse as JSON (tracker-keyed format)
                                if new_status_str.strip():
                                    try:
                                        new_status = json.loads(new_status_str)
                                        if not isinstance(new_status, dict):
                                            # If not a dict, treat as old format (simple integer)
                                            try:
                                                status_value = int(new_status_str)
                                                # Need tracker name to create tracker-keyed format
                                                if "tracker_name" in record:
                                                    tracker_name_value = record.get("tracker_name")
                                                    if isinstance(tracker_name_value, str):
                                                        try:
                                                            tracker_names = json.loads(tracker_name_value)
                                                            if isinstance(tracker_names, list) and tracker_names:
                                                                new_status = {tracker_names[-1]: status_value}
                                                        except (json.JSONDecodeError, TypeError):
                                                            pass
                                            except (ValueError, TypeError):
                                                pass
                                    except (json.JSONDecodeError, TypeError):
                                        # If parsing fails, might be old format integer string
                                        try:
                                            status_value = int(new_status_str)
                                            # Need tracker name to create tracker-keyed format
                                            if "tracker_name" in record:
                                                tracker_name_value = record.get("tracker_name")
                                                if isinstance(tracker_name_value, str):
                                                    try:
                                                        tracker_names = json.loads(tracker_name_value)
                                                        if isinstance(tracker_names, list) and tracker_names:
                                                            new_status = {tracker_names[-1]: status_value}
                                                    except (json.JSONDecodeError, TypeError):
                                                        pass
                                        except (ValueError, TypeError):
                                            pass
                            elif isinstance(new_status_str, dict):
                                new_status = new_status_str
                            elif isinstance(new_status_str, int):
                                # Old format integer, need tracker name to create tracker-keyed format
                                if "tracker_name" in record:
                                    tracker_name_value = record.get("tracker_name")
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list) and tracker_names:
                                                new_status = {tracker_names[-1]: new_status_str}
                                        except (json.JSONDecodeError, TypeError):
                                            pass
                            
                            # Parse existing status if available
                            if existing_status_str:
                                if isinstance(existing_status_str, str):
                                    if existing_status_str.strip():
                                        try:
                                            existing_status = json.loads(existing_status_str)
                                            if not isinstance(existing_status, dict):
                                                # If not a dict, treat as old format (simple integer)
                                                try:
                                                    status_value = int(existing_status_str)
                                                    # Convert to tracker-keyed format using existing tracker_name
                                                    if "tracker_name" in existing_record:
                                                        tracker_name_value = existing_record.get("tracker_name")
                                                        if isinstance(tracker_name_value, str):
                                                            try:
                                                                tracker_names = json.loads(tracker_name_value)
                                                                if isinstance(tracker_names, list) and tracker_names:
                                                                    existing_status = {tracker_names[-1]: status_value}
                                                            except (json.JSONDecodeError, TypeError):
                                                                existing_status = {}
                                                except (ValueError, TypeError):
                                                    existing_status = {}
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, might be old format integer string
                                            try:
                                                status_value = int(existing_status_str)
                                                # Convert to tracker-keyed format using existing tracker_name
                                                if "tracker_name" in existing_record:
                                                    tracker_name_value = existing_record.get("tracker_name")
                                                    if isinstance(tracker_name_value, str):
                                                        try:
                                                            tracker_names = json.loads(tracker_name_value)
                                                            if isinstance(tracker_names, list) and tracker_names:
                                                                existing_status = {tracker_names[-1]: status_value}
                                                        except (json.JSONDecodeError, TypeError):
                                                            existing_status = {}
                                            except (ValueError, TypeError):
                                                existing_status = {}
                                    else:
                                        existing_status = {}
                                elif isinstance(existing_status_str, dict):
                                    existing_status = existing_status_str
                                elif isinstance(existing_status_str, int):
                                    # Old format integer, convert to tracker-keyed format
                                    if "tracker_name" in existing_record:
                                        tracker_name_value = existing_record.get("tracker_name")
                                        if isinstance(tracker_name_value, str):
                                            try:
                                                tracker_names = json.loads(tracker_name_value)
                                                if isinstance(tracker_names, list) and tracker_names:
                                                    existing_status = {tracker_names[-1]: existing_status_str}
                                            except (json.JSONDecodeError, TypeError):
                                                existing_status = {}
                            
                            # Merge: existing trackers preserved, new tracker updates/overwrites its entry
                            # Ensure new_status is a dict before merging (if it's not None)
                            if new_status is not None:
                                if isinstance(new_status, dict) and new_status:
                                    merged_status = existing_status.copy() if existing_status else {}
                                    merged_status.update(new_status)
                                    
                                    # Store merged status as JSON string
                                    if merged_status:
                                        record["status"] = json.dumps(merged_status)
                                    elif existing_status:
                                        # New is empty but existing has content, preserve existing
                                        record["status"] = existing_record.get("status")
                                elif isinstance(new_status, dict) and not new_status:
                                    # New is empty dict but existing has content, preserve existing
                                    if existing_status:
                                        record["status"] = existing_record.get("status")
                                elif existing_status:
                                    # New is not a dict (e.g., integer from old format without tracker_name)
                                    # Preserve existing status
                                    record["status"] = existing_record.get("status")
                            elif existing_status:
                                # No new data but existing has content, preserve existing
                                record["status"] = existing_record.get("status")
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge status for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "status" in existing_record:
                        # Field not in incoming record, preserve existing
                        record["status"] = existing_record.get("status")

                    # NOTE: the "preserve existing metrics if not in incoming
                    # record" fallback that used to live here is now folded
                    # into the `elif "metrics" in existing_record:` self-heal
                    # branch up in the metrics merge block (around line 852).
                    # That branch parses + strip_legacy_flat_keys + re-serializes
                    # (or pops the field on collapse to {}), so a second
                    # unconditional copy of the raw KV here would re-introduce
                    # legacy contamination that the strip just removed.

                    # Merge tracker_name (JSON array of tracker names)
                    if "tracker_name" in record:
                        try:
                            new_tracker_name_str = record.get("tracker_name")
                            existing_tracker_name_str = existing_record.get("tracker_name") if "tracker_name" in existing_record else None
                            
                            # Parse both as JSON arrays
                            new_tracker_names = []
                            existing_tracker_names = []
                            
                            if new_tracker_name_str:
                                if isinstance(new_tracker_name_str, str):
                                    try:
                                        new_tracker_names = json.loads(new_tracker_name_str)
                                        if not isinstance(new_tracker_names, list):
                                            # If not a list, treat as single tracker name (backward compatibility)
                                            new_tracker_names = [new_tracker_name_str] if new_tracker_name_str else []
                                    except (json.JSONDecodeError, TypeError):
                                        # If parsing fails, treat as single tracker name (backward compatibility)
                                        new_tracker_names = [new_tracker_name_str] if new_tracker_name_str else []
                                elif isinstance(new_tracker_name_str, list):
                                    new_tracker_names = new_tracker_name_str
                            
                            if existing_tracker_name_str:
                                if isinstance(existing_tracker_name_str, str):
                                    try:
                                        existing_tracker_names = json.loads(existing_tracker_name_str)
                                        if not isinstance(existing_tracker_names, list):
                                            # If not a list, treat as single tracker name (backward compatibility)
                                            existing_tracker_names = [existing_tracker_name_str] if existing_tracker_name_str else []
                                    except (json.JSONDecodeError, TypeError):
                                        # If parsing fails, treat as single tracker name (backward compatibility)
                                        existing_tracker_names = [existing_tracker_name_str] if existing_tracker_name_str else []
                                elif isinstance(existing_tracker_name_str, list):
                                    existing_tracker_names = existing_tracker_name_str
                            
                            # Merge: combine both arrays and remove duplicates
                            merged_tracker_names = list(set(existing_tracker_names + new_tracker_names))
                            merged_tracker_names.sort()  # Sort for consistency
                            
                            # Store merged tracker_name as JSON array
                            if merged_tracker_names:
                                record["tracker_name"] = json.dumps(merged_tracker_names)
                            elif existing_tracker_names:
                                # New is empty, preserve existing
                                record["tracker_name"] = existing_record.get("tracker_name")
                            else:
                                # Both are empty, remove field
                                record.pop("tracker_name", None)
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge tracker_name for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "tracker_name" in existing_record:
                        # Field not in incoming record, preserve existing
                        record["tracker_name"] = existing_record.get("tracker_name")
                    
                    # Convert and merge tracker_runtime (store as tracker-keyed JSON)
                    # tracker_runtime comes from macro as simple value (now()), need to convert to tracker-keyed JSON
                    if "tracker_runtime" in record:
                        try:
                            new_tracker_runtime_value = record.get("tracker_runtime")
                            existing_tracker_runtime_str = existing_record.get("tracker_runtime") if "tracker_runtime" in existing_record else None
                            
                            # Get tracker_name from incoming record to use as key
                            incoming_tracker_name = None
                            if "tracker_name" in record:
                                try:
                                    tracker_name_value = record.get("tracker_name")
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list) and tracker_names:
                                                # Use the last tracker name (most recent) as the key
                                                incoming_tracker_name = tracker_names[-1]
                                        except (json.JSONDecodeError, TypeError):
                                            # If parsing fails, treat as single tracker name
                                            incoming_tracker_name = tracker_name_value
                                    elif isinstance(tracker_name_value, list) and tracker_name_value:
                                        incoming_tracker_name = tracker_name_value[-1]
                                except:
                                    pass
                            
                            # If we have a tracker name and runtime value, convert to tracker-keyed JSON
                            if incoming_tracker_name and new_tracker_runtime_value:
                                try:
                                    new_runtime = float(new_tracker_runtime_value)
                                    
                                    # Parse existing tracker_runtime (might be tracker-keyed JSON or simple value)
                                    existing_runtimes = {}
                                    if existing_tracker_runtime_str:
                                        if isinstance(existing_tracker_runtime_str, str):
                                            try:
                                                existing_runtimes = json.loads(existing_tracker_runtime_str)
                                                if not isinstance(existing_runtimes, dict):
                                                    # If not a dict, treat as simple value (backward compatibility)
                                                    # Convert to tracker-keyed format using existing tracker_name if available
                                                    existing_tracker_name = None
                                                    if "tracker_name" in existing_record:
                                                        try:
                                                            existing_tn = existing_record.get("tracker_name")
                                                            if isinstance(existing_tn, str):
                                                                try:
                                                                    existing_tn_list = json.loads(existing_tn)
                                                                    if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                        existing_tracker_name = existing_tn_list[-1]
                                                                except:
                                                                    existing_tracker_name = existing_tn
                                                        except:
                                                            pass
                                                    if existing_tracker_name:
                                                        existing_runtimes = {existing_tracker_name: float(existing_tracker_runtime_str)}
                                                    else:
                                                        existing_runtimes = {}
                                            except (json.JSONDecodeError, TypeError):
                                                # If parsing fails, might be simple numeric value (backward compatibility)
                                                existing_tracker_name = None
                                                if "tracker_name" in existing_record:
                                                    try:
                                                        existing_tn = existing_record.get("tracker_name")
                                                        if isinstance(existing_tn, str):
                                                            try:
                                                                existing_tn_list = json.loads(existing_tn)
                                                                if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                    existing_tracker_name = existing_tn_list[-1]
                                                            except:
                                                                existing_tracker_name = existing_tn
                                                    except:
                                                        pass
                                                if existing_tracker_name:
                                                    existing_runtimes = {existing_tracker_name: float(existing_tracker_runtime_str)}
                                                else:
                                                    existing_runtimes = {}
                                        elif isinstance(existing_tracker_runtime_str, dict):
                                            existing_runtimes = existing_tracker_runtime_str
                                        else:
                                            # Numeric value (backward compatibility)
                                            existing_tracker_name = None
                                            if "tracker_name" in existing_record:
                                                try:
                                                    existing_tn = existing_record.get("tracker_name")
                                                    if isinstance(existing_tn, str):
                                                        try:
                                                            existing_tn_list = json.loads(existing_tn)
                                                            if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                existing_tracker_name = existing_tn_list[-1]
                                                        except:
                                                            existing_tracker_name = existing_tn
                                                except:
                                                    pass
                                            if existing_tracker_name:
                                                existing_runtimes = {existing_tracker_name: float(existing_tracker_runtime_str)}
                                            else:
                                                existing_runtimes = {}
                                    
                                    # Merge: existing trackers preserved, new tracker updates/overwrites its entry
                                    merged_runtimes = existing_runtimes.copy()
                                    merged_runtimes[incoming_tracker_name] = new_runtime
                                    
                                    # Store merged tracker_runtime as JSON string for detailed tracking (per-tracker runtimes)
                                    record["tracker_runtimes"] = json.dumps(merged_runtimes)
                                    
                                    # Store the maximum (latest) runtime as a simple value in tracker_runtime for backward compatibility
                                    # This ensures staleness checks (now()-tracker_runtime) continue to work
                                    # The entity is considered "active" if ANY tracker has run recently
                                    if merged_runtimes:
                                        max_runtime = max(merged_runtimes.values())
                                        record["tracker_runtime"] = max_runtime
                                    else:
                                        record["tracker_runtime"] = new_runtime
                                except (ValueError, TypeError) as e:
                                    logging.error(
                                        f'instance_id="{self.instance_id}", failed to convert tracker_runtime for object="{record.get("object")}", '
                                        f'exception="{str(e)}"'
                                    )
                            elif new_tracker_runtime_value:
                                # We have runtime but no tracker_name, store as simple value (backward compatibility)
                                try:
                                    record["tracker_runtime"] = float(new_tracker_runtime_value)
                                except (ValueError, TypeError):
                                    pass
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge tracker_runtime for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "tracker_runtime" in existing_record:
                        # Field not in incoming record, preserve existing
                        record["tracker_runtime"] = existing_record.get("tracker_runtime")
                    
                    # Merge disruption_min_time_sec (take maximum value for concurrent trackers)
                    if "disruption_min_time_sec" in record:
                        try:
                            new_disruption_min_time_str = record.get("disruption_min_time_sec")
                            existing_disruption_min_time_str = existing_record.get("disruption_min_time_sec") if "disruption_min_time_sec" in existing_record else None
                            
                            # Get incoming tracker name to use as key
                            incoming_tracker_name = None
                            if "tracker_name" in record:
                                try:
                                    tracker_name_value = record.get("tracker_name")
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list) and tracker_names:
                                                incoming_tracker_name = tracker_names[-1]
                                        except (json.JSONDecodeError, TypeError):
                                            incoming_tracker_name = tracker_name_value
                                    elif isinstance(tracker_name_value, list) and tracker_name_value:
                                        incoming_tracker_name = tracker_name_value[-1]
                                except:
                                    pass
                            
                            # If we have a tracker name and disruption_min_time_sec value, convert to tracker-keyed JSON
                            if incoming_tracker_name and new_disruption_min_time_str:
                                try:
                                    new_disruption_min_time = None
                                    if isinstance(new_disruption_min_time_str, str):
                                        try:
                                            # Try parsing as tracker-keyed JSON
                                            parsed = json.loads(new_disruption_min_time_str)
                                            if isinstance(parsed, dict):
                                                # Already tracker-keyed format
                                                new_disruption_times = parsed
                                            else:
                                                # Simple numeric value, convert to tracker-keyed
                                                new_disruption_min_time = int(float(new_disruption_min_time_str))
                                                new_disruption_times = {incoming_tracker_name: new_disruption_min_time}
                                        except (json.JSONDecodeError, TypeError, ValueError):
                                            # Not JSON, treat as simple numeric value
                                            new_disruption_min_time = int(float(new_disruption_min_time_str))
                                            new_disruption_times = {incoming_tracker_name: new_disruption_min_time}
                                    elif isinstance(new_disruption_min_time_str, dict):
                                        new_disruption_times = new_disruption_min_time_str
                                    else:
                                        # Numeric value
                                        new_disruption_min_time = int(float(new_disruption_min_time_str))
                                        new_disruption_times = {incoming_tracker_name: new_disruption_min_time}
                                    
                                    # Parse existing disruption_min_time_sec (might be tracker-keyed JSON or simple value)
                                    existing_disruption_times = {}
                                    if existing_disruption_min_time_str:
                                        if isinstance(existing_disruption_min_time_str, str):
                                            try:
                                                existing_disruption_times = json.loads(existing_disruption_min_time_str)
                                                if not isinstance(existing_disruption_times, dict):
                                                    # If not a dict, treat as simple value (backward compatibility)
                                                    existing_tracker_name = None
                                                    if "tracker_name" in existing_record:
                                                        try:
                                                            existing_tn = existing_record.get("tracker_name")
                                                            if isinstance(existing_tn, str):
                                                                try:
                                                                    existing_tn_list = json.loads(existing_tn)
                                                                    if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                        existing_tracker_name = existing_tn_list[-1]
                                                                except:
                                                                    existing_tracker_name = existing_tn
                                                        except:
                                                            pass
                                                    if existing_tracker_name:
                                                        existing_disruption_times = {existing_tracker_name: int(float(existing_disruption_min_time_str))}
                                                    else:
                                                        existing_disruption_times = {}
                                            except (json.JSONDecodeError, TypeError, ValueError):
                                                # If parsing fails, might be simple numeric value (backward compatibility)
                                                existing_tracker_name = None
                                                if "tracker_name" in existing_record:
                                                    try:
                                                        existing_tn = existing_record.get("tracker_name")
                                                        if isinstance(existing_tn, str):
                                                            try:
                                                                existing_tn_list = json.loads(existing_tn)
                                                                if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                    existing_tracker_name = existing_tn_list[-1]
                                                            except:
                                                                existing_tracker_name = existing_tn
                                                    except:
                                                        pass
                                                if existing_tracker_name:
                                                    existing_disruption_times = {existing_tracker_name: int(float(existing_disruption_min_time_str))}
                                                else:
                                                    existing_disruption_times = {}
                                        elif isinstance(existing_disruption_min_time_str, dict):
                                            existing_disruption_times = existing_disruption_min_time_str
                                        else:
                                            # Numeric value (backward compatibility)
                                            existing_tracker_name = None
                                            if "tracker_name" in existing_record:
                                                try:
                                                    existing_tn = existing_record.get("tracker_name")
                                                    if isinstance(existing_tn, str):
                                                        try:
                                                            existing_tn_list = json.loads(existing_tn)
                                                            if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                existing_tracker_name = existing_tn_list[-1]
                                                        except:
                                                            existing_tracker_name = existing_tn
                                                except:
                                                    pass
                                            if existing_tracker_name:
                                                existing_disruption_times = {existing_tracker_name: int(float(existing_disruption_min_time_str))}
                                            else:
                                                existing_disruption_times = {}
                                    
                                    # Merge: existing trackers preserved, new tracker updates/overwrites its entry
                                    merged_disruption_times = existing_disruption_times.copy()
                                    merged_disruption_times.update(new_disruption_times)
                                    
                                    # Store merged disruption_min_time_sec as JSON string for detailed tracking (per-tracker values)
                                    record["disruption_min_time_sec"] = json.dumps(merged_disruption_times)
                                    
                                    # Store the maximum value as a simple numeric value for backward compatibility
                                    # This ensures disruption_queue_lookup receives the highest value across all trackers
                                    if merged_disruption_times:
                                        max_disruption_time = max(int(float(v)) for v in merged_disruption_times.values())
                                        # Store as simple value for disruption queue (but keep tracker-keyed JSON in record)
                                        # The disruption queue will use the aggregated maximum value from trackmedecisionmaker
                                    else:
                                        # Fallback to new value if merged is empty
                                        if new_disruption_min_time is not None:
                                            record["disruption_min_time_sec"] = new_disruption_min_time
                                except (ValueError, TypeError) as e:
                                    logging.error(
                                        f'instance_id="{self.instance_id}", failed to convert disruption_min_time_sec for object="{record.get("object")}", '
                                        f'exception="{str(e)}"'
                                    )
                            elif new_disruption_min_time_str:
                                # We have disruption_min_time_sec but no tracker_name, store as simple value (backward compatibility)
                                try:
                                    if isinstance(new_disruption_min_time_str, str):
                                        try:
                                            parsed = json.loads(new_disruption_min_time_str)
                                            if isinstance(parsed, dict):
                                                # Tracker-keyed format but no tracker_name to use as key, take maximum
                                                max_value = max(int(float(v)) for v in parsed.values())
                                                record["disruption_min_time_sec"] = max_value
                                            else:
                                                record["disruption_min_time_sec"] = int(float(new_disruption_min_time_str))
                                        except (json.JSONDecodeError, TypeError, ValueError):
                                            record["disruption_min_time_sec"] = int(float(new_disruption_min_time_str))
                                    else:
                                        record["disruption_min_time_sec"] = int(float(new_disruption_min_time_str))
                                except (ValueError, TypeError):
                                    pass
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge disruption_min_time_sec for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "disruption_min_time_sec" in existing_record:
                        # Field not in incoming record, preserve existing
                        record["disruption_min_time_sec"] = existing_record.get("disruption_min_time_sec")
                    
                    # Merge max_sec_inactive (take minimum value for concurrent trackers - most restrictive)
                    if "max_sec_inactive" in record:
                        try:
                            new_max_sec_inactive_str = record.get("max_sec_inactive")
                            existing_max_sec_inactive_str = existing_record.get("max_sec_inactive") if "max_sec_inactive" in existing_record else None
                            
                            # Get incoming tracker name to use as key
                            incoming_tracker_name = None
                            if "tracker_name" in record:
                                try:
                                    tracker_name_value = record.get("tracker_name")
                                    if isinstance(tracker_name_value, str):
                                        try:
                                            tracker_names = json.loads(tracker_name_value)
                                            if isinstance(tracker_names, list) and tracker_names:
                                                incoming_tracker_name = tracker_names[-1]
                                        except (json.JSONDecodeError, TypeError):
                                            incoming_tracker_name = tracker_name_value
                                    elif isinstance(tracker_name_value, list) and tracker_name_value:
                                        incoming_tracker_name = tracker_name_value[-1]
                                except:
                                    pass
                            
                            # If we have a tracker name and max_sec_inactive value, convert to tracker-keyed JSON
                            if incoming_tracker_name and new_max_sec_inactive_str:
                                try:
                                    new_max_sec_inactive = None
                                    if isinstance(new_max_sec_inactive_str, str):
                                        try:
                                            # Try parsing as tracker-keyed JSON
                                            parsed = json.loads(new_max_sec_inactive_str)
                                            if isinstance(parsed, dict):
                                                # Already tracker-keyed format
                                                new_max_sec_inactive_times = parsed
                                            else:
                                                # Simple numeric value, convert to tracker-keyed
                                                new_max_sec_inactive = int(float(new_max_sec_inactive_str))
                                                new_max_sec_inactive_times = {incoming_tracker_name: new_max_sec_inactive}
                                        except (json.JSONDecodeError, TypeError, ValueError):
                                            # Not JSON, treat as simple numeric value
                                            new_max_sec_inactive = int(float(new_max_sec_inactive_str))
                                            new_max_sec_inactive_times = {incoming_tracker_name: new_max_sec_inactive}
                                    elif isinstance(new_max_sec_inactive_str, dict):
                                        new_max_sec_inactive_times = new_max_sec_inactive_str
                                    else:
                                        # Numeric value
                                        new_max_sec_inactive = int(float(new_max_sec_inactive_str))
                                        new_max_sec_inactive_times = {incoming_tracker_name: new_max_sec_inactive}
                                    
                                    # Parse existing max_sec_inactive (might be tracker-keyed JSON or simple value)
                                    existing_max_sec_inactive_times = {}
                                    if existing_max_sec_inactive_str:
                                        if isinstance(existing_max_sec_inactive_str, str):
                                            try:
                                                existing_max_sec_inactive_times = json.loads(existing_max_sec_inactive_str)
                                                if not isinstance(existing_max_sec_inactive_times, dict):
                                                    # If not a dict, treat as simple value (backward compatibility)
                                                    existing_tracker_name = None
                                                    if "tracker_name" in existing_record:
                                                        try:
                                                            existing_tn = existing_record.get("tracker_name")
                                                            if isinstance(existing_tn, str):
                                                                try:
                                                                    existing_tn_list = json.loads(existing_tn)
                                                                    if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                        existing_tracker_name = existing_tn_list[-1]
                                                                except:
                                                                    existing_tracker_name = existing_tn
                                                        except:
                                                            pass
                                                    if existing_tracker_name:
                                                        existing_max_sec_inactive_times = {existing_tracker_name: int(float(existing_max_sec_inactive_str))}
                                                    else:
                                                        existing_max_sec_inactive_times = {}
                                            except (json.JSONDecodeError, TypeError, ValueError):
                                                # If parsing fails, might be simple numeric value (backward compatibility)
                                                existing_tracker_name = None
                                                if "tracker_name" in existing_record:
                                                    try:
                                                        existing_tn = existing_record.get("tracker_name")
                                                        if isinstance(existing_tn, str):
                                                            try:
                                                                existing_tn_list = json.loads(existing_tn)
                                                                if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                    existing_tracker_name = existing_tn_list[-1]
                                                            except:
                                                                existing_tracker_name = existing_tn
                                                    except:
                                                        pass
                                                if existing_tracker_name:
                                                    existing_max_sec_inactive_times = {existing_tracker_name: int(float(existing_max_sec_inactive_str))}
                                                else:
                                                    existing_max_sec_inactive_times = {}
                                        elif isinstance(existing_max_sec_inactive_str, dict):
                                            existing_max_sec_inactive_times = existing_max_sec_inactive_str
                                        else:
                                            # Numeric value (backward compatibility)
                                            existing_tracker_name = None
                                            if "tracker_name" in existing_record:
                                                try:
                                                    existing_tn = existing_record.get("tracker_name")
                                                    if isinstance(existing_tn, str):
                                                        try:
                                                            existing_tn_list = json.loads(existing_tn)
                                                            if isinstance(existing_tn_list, list) and existing_tn_list:
                                                                existing_tracker_name = existing_tn_list[-1]
                                                        except:
                                                            existing_tracker_name = existing_tn
                                                except:
                                                    pass
                                            if existing_tracker_name:
                                                existing_max_sec_inactive_times = {existing_tracker_name: int(float(existing_max_sec_inactive_str))}
                                            else:
                                                existing_max_sec_inactive_times = {}
                                    
                                    # Merge: existing trackers preserved, new tracker updates/overwrites its entry
                                    merged_max_sec_inactive_times = existing_max_sec_inactive_times.copy()
                                    merged_max_sec_inactive_times.update(new_max_sec_inactive_times)
                                    
                                    # Store the minimum value as a simple numeric value for backward compatibility
                                    # This ensures inactive entity detection uses the most restrictive (lowest) value
                                    # The entity is considered inactive if ANY tracker's threshold is exceeded
                                    # The inactive inspector reads max_sec_inactive directly from KVstore as a numeric value
                                    if merged_max_sec_inactive_times:
                                        # Filter out 0 values (which disable the feature) before taking minimum
                                        non_zero_values = [int(float(v)) for v in merged_max_sec_inactive_times.values() if int(float(v)) > 0]
                                        if non_zero_values:
                                            min_max_sec_inactive = min(non_zero_values)
                                            # Store minimum value as simple numeric for inactive inspector
                                            record["max_sec_inactive"] = min_max_sec_inactive
                                        else:
                                            # All values are 0, store 0 (disabled)
                                            record["max_sec_inactive"] = 0
                                    else:
                                        # Fallback to new value if merged is empty
                                        if new_max_sec_inactive is not None:
                                            record["max_sec_inactive"] = new_max_sec_inactive
                                except (ValueError, TypeError) as e:
                                    logging.error(
                                        f'instance_id="{self.instance_id}", failed to convert max_sec_inactive for object="{record.get("object")}", '
                                        f'exception="{str(e)}"'
                                    )
                            elif new_max_sec_inactive_str:
                                # We have max_sec_inactive but no tracker_name, store as simple value (backward compatibility)
                                try:
                                    if isinstance(new_max_sec_inactive_str, str):
                                        try:
                                            parsed = json.loads(new_max_sec_inactive_str)
                                            if isinstance(parsed, dict):
                                                # Tracker-keyed format but no tracker_name to use as key, take minimum
                                                non_zero_values = [int(float(v)) for v in parsed.values() if int(float(v)) > 0]
                                                if non_zero_values:
                                                    min_value = min(non_zero_values)
                                                    record["max_sec_inactive"] = min_value
                                                else:
                                                    record["max_sec_inactive"] = 0
                                            else:
                                                record["max_sec_inactive"] = int(float(new_max_sec_inactive_str))
                                        except (json.JSONDecodeError, TypeError, ValueError):
                                            record["max_sec_inactive"] = int(float(new_max_sec_inactive_str))
                                    else:
                                        record["max_sec_inactive"] = int(float(new_max_sec_inactive_str))
                                except (ValueError, TypeError):
                                    pass
                        except Exception as e:
                            logging.error(
                                f'instance_id="{self.instance_id}", failed to merge max_sec_inactive for object="{record.get("object")}", '
                                f'exception="{str(e)}"'
                            )
                    elif "max_sec_inactive" in existing_record:
                        # Field not in incoming record, preserve existing
                        record["max_sec_inactive"] = existing_record.get("max_sec_inactive")

                # Strip _existing_* fields before building summary_record (internal use only)
                if use_preloaded:
                    for existing_field in ("_existing_mtime", "_existing_ctime", "_existing_data_last_time_seen"):
                        record.pop(existing_field, None)

                # loop through the dict
                for k in record:
                    logging.debug(f'instance_id="{self.instance_id}", field="{k}", value="{record[k]}"')

                    # Exclude the event time, add existing fields
                    if k != "_time":
                        #
                        # handle persistent field
                        #

                        if not record_is_new:
                            # if field is in persistent list of fields
                            if k in persistent_fields:
                                # preserve persistent fields if conflict update is detected
                                if conflict_update and not use_preloaded:
                                    # In normal mode, recover from collection_dict
                                    kv_value = collection_dict[
                                        record.get(self.key)
                                    ].get(k)
                                    if kv_value is not None:
                                        record[k] = kv_value
                                        summary_record[k] = kv_value
                                    else:
                                        summary_record[k] = record[k]
                                else:
                                    # In preloaded mode with conflict, persistent fields
                                    # are already on the record from the upstream lookup
                                    summary_record[k] = record[k]

                            # normal field
                            else:
                                summary_record[k] = record[k]

                        else:
                            # record is new, no need to consider it
                            summary_record[k] = record[k]

                # Preserve persistent fields from KV store that are not in the search result.
                # This handles user-configured fields (e.g. impact_score_weights) that may not
                # be present in the tracker search output but must survive batch_save (full replace).
                # In preloaded mode, these fields were already fetched by the upstream lookup.
                if not record_is_new and not use_preloaded:
                    kv_key = record.get(self.key)
                    if kv_key and kv_key in collection_dict:
                        existing_kv_record = collection_dict[kv_key]
                        for field in persistent_fields:
                            if field not in record and field in existing_kv_record:
                                kv_val = existing_kv_record.get(field)
                                if kv_val is not None:
                                    record[field] = kv_val
                                    summary_record[field] = kv_val

                # Safeguard: ensure tenant_id is always set on the record.
                # The tracker search and macro normally set this via eval, but if the
                # field is missing or empty (edge case) we derive it from the collection
                # name so the UI grouping remains correct.  (refs #625)
                if collection_tenant_id and not record.get("tenant_id"):
                    record["tenant_id"] = collection_tenant_id
                    summary_record["tenant_id"] = collection_tenant_id
                    logging.warning(
                        f'instance_id="{self.instance_id}", object="{record.get("object")}", '
                        f'tenant_id was missing or empty, set to "{collection_tenant_id}" '
                        f'derived from collection name'
                    )

                # insert and update the collection if requested
                final_records.append(record)

        # Task timing: record processing loop complete
        record_processing_run_time = round(time.time() - record_processing_start, 3)

        if skipped_new_entities > 0:
            logging.info(
                f'instance_id="{self.instance_id}", collection="{self.collection}", license read-only mode: '
                f'skipped {skipped_new_entities} new entities'
            )

        # Sourcetype explosion safeguard: purge stale alerts when safeguard is disabled (cap=0)
        if sourcetype_cap_per_index == 0 and component == "dsm":
            try:
                cap_alert_collection = self.service.kvstore["kv_trackme_sourcetype_cap_alerts"]
                existing_alerts = cap_alert_collection.data.query()
                for alert in existing_alerts:
                    if alert.get("tenant_id") == collection_tenant_id and alert.get("collection_name") == self.collection:
                        try:
                            cap_alert_collection.data.delete(json.dumps({"_key": alert.get("_key")}))
                            logging.info(
                                f'instance_id="{self.instance_id}", sourcetype_cap_safeguard: '
                                f'cleared stale alert for index="{alert.get("data_index")}" (safeguard disabled)'
                            )
                        except Exception:
                            pass
            except Exception:
                pass

        # Sourcetype explosion safeguard: post-loop audit and KV alert management
        if sourcetype_cap_per_index > 0 and component == "dsm":
            try:
                cap_alert_collection = self.service.kvstore["kv_trackme_sourcetype_cap_alerts"]

                if skipped_capped_entities > 0:
                    logging.warning(
                        f'instance_id="{self.instance_id}", sourcetype_cap_safeguard: '
                        f'skipped {skipped_capped_entities} new entities across {len(capped_indexes)} indexes, '
                        f'cap={sourcetype_cap_per_index}, collection="{self.collection}", '
                        f'capped_indexes="{list(capped_indexes.keys())}"'
                    )

                    # Write audit event to trackme_audit index
                    try:
                        audit_idx_name = reqinfo["trackme_conf"].get("index_settings", {}).get(
                            "trackme_audit_idx", "trackme_audit"
                        )
                        audit_record = {
                            "action": "sourcetype_cap_safeguard",
                            "tenant_id": collection_tenant_id or "unknown",
                            "component": "dsm",
                            "skipped_entities": skipped_capped_entities,
                            "cap_value": sourcetype_cap_per_index,
                            "capped_indexes": list(capped_indexes.keys()),
                            "index_counts": {idx: count for idx, count in capped_indexes.items()},
                        }
                        audit_target = self.service.indexes[audit_idx_name]
                        audit_target.submit(
                            event=json.dumps(audit_record),
                            source="trackme_persistentfields",
                            sourcetype="trackme:audit:sourcetype_cap",
                        )
                    except Exception as e:
                        logging.error(
                            f'instance_id="{self.instance_id}", failed to write sourcetype cap audit event: {e}'
                        )

                    # Upsert KV alert records for capped indexes
                    for idx, count in capped_indexes.items():
                        try:
                            alert_key = hashlib.sha256(
                                f"{collection_tenant_id}:{idx}".encode("utf-8")
                            ).hexdigest()
                            alert_record = {
                                "_key": alert_key,
                                "tenant_id": collection_tenant_id or "unknown",
                                "data_index": idx,
                                "collection_name": self.collection,
                                "sourcetype_count": count,
                                "cap_value": sourcetype_cap_per_index,
                                "mtime": time.time(),
                            }
                            cap_alert_collection.data.insert(json.dumps(alert_record))
                        except Exception:
                            # Insert fails if _key already exists (HTTP 409), fall back to update
                            try:
                                cap_alert_collection.data.update(alert_key, json.dumps(alert_record))
                            except Exception as e:
                                logging.error(
                                    f'instance_id="{self.instance_id}", failed to upsert sourcetype cap alert '
                                    f'for index="{idx}": {e}'
                                )

                # Self-healing: clear KV alerts for indexes that are now under threshold
                # Skip in preloaded mode — index_sourcetype_counts only has new entities, not the full count
                if not use_preloaded:
                    try:
                        existing_alerts = cap_alert_collection.data.query()
                        for alert in existing_alerts:
                            alert_tenant = alert.get("tenant_id", "")
                            alert_index = alert.get("data_index", "")
                            alert_collection = alert.get("collection_name", "")
                            # Only clear alerts belonging to this tracker's tenant and collection
                            if alert_tenant == collection_tenant_id and alert_collection == self.collection:
                                if index_sourcetype_counts.get(alert_index, 0) < sourcetype_cap_per_index:
                                    try:
                                        cap_alert_collection.data.delete(json.dumps({"_key": alert.get("_key")}))
                                        logging.info(
                                            f'instance_id="{self.instance_id}", sourcetype_cap_safeguard: '
                                            f'cleared alert for index="{alert_index}" (now under threshold)'
                                        )
                                    except Exception as e:
                                        logging.error(
                                            f'instance_id="{self.instance_id}", failed to clear sourcetype cap alert '
                                            f'for index="{alert_index}": {e}'
                                        )
                    except Exception as e:
                        logging.error(
                            f'instance_id="{self.instance_id}", failed to query sourcetype cap alerts for cleanup: {e}'
                        )
                else:
                    logging.debug(
                        f'instance_id="{self.instance_id}", sourcetype_cap_safeguard: '
                        f'skipping self-healing in preloaded mode (counts are incomplete)'
                    )

            except Exception as e:
                logging.error(
                    f'instance_id="{self.instance_id}", sourcetype_cap_safeguard post-loop processing failed: {e}'
                )

        # log
        logging.debug(f'instance_id="{self.instance_id}", final_records={json.dumps(final_records, indent=2)}')

        # set task
        #
        task_start = time.time()
        task_instance_id = get_uuid()
        task_name = "kvstore_batch_update"

        # Execute batch update synchronously
        batch_update_worker(
            target_collection, collection, final_records, self.instance_id, task_instance_id, task_name=task_name, max_multi_thread_workers=max_multi_thread_workers
        )

        # end task
        #
        batch_update_run_time = round(time.time() - task_start, 3)
        logging.info(
            f'instance_id="{self.instance_id}", collection="{self.collection}", '
            f'task="{task_name}", task_run_time={batch_update_run_time}, '
            f'no_records={len(final_records)}'
        )

        # Yield records back to Splunk pipeline
        for record in final_records:
            yield record

        # Fire-and-forget: flush any pending variable delay records in a background thread
        # (single batch_save REST call, doesn't block the pipeline)
        if collection_tenant_id and component in ("dsm", "dhm"):
            self._flush_variable_delay_records(self.service, collection_tenant_id, component)

        # perf counter for the entire call with full task breakdown
        total_run_time = round(time.time() - start_time, 3)
        logging.info(
            f'instance_id="{self.instance_id}", trackmepersistentfields has terminated, '
            f'collection="{self.collection}", component="{component}", key="{self.key}", '
            f'preloaded_entity_fields="{self.preloaded_entity_fields}", '
            f'existing_entities={existing_entity_count}, new_entities={new_entity_count}, '
            f'total_records={len(final_records)}, '
            f'task_init={init_run_time}, '
            f'task_collection_read={round(collection_read_run_time, 3)}, '
            f'task_record_processing={record_processing_run_time}, '
            f'task_batch_update={batch_update_run_time}, '
            f'total_run_time={total_run_time}'
        )


dispatch(TrackMePersistentHandler, sys.argv, sys.stdin, sys.stdout, __name__)
