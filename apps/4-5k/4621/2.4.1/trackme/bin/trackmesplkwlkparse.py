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
import re
import time
import hashlib
import ast
import json

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Third-party library imports
import urllib3
import requests

# Disable InsecureRequestWarning for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# Set up logging
log_file = os.path.join(
    splunkhome, "var", "log", "splunk", "trackme_splk_wlk_parse.log"
)
filehandler = RotatingFileHandler(log_file, mode="a", maxBytes=10000000, backupCount=1)
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

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import TrackMe libs
from trackme_libs_splk_wlk import trackme_wlk_gen_metrics
from trackme_libs import trackme_reqinfo
from trackme_libs_utils import decode_unicode


@Configuration(distributed=False)
class TrackMeSplkWlkParse(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    context = Option(
        doc="""
        **Syntax:** **context=****
        **Description:** The context is used for simulation purposes, defaults to live.""",
        require=False,
        default="live",
        validate=validators.Match("context", r"^(live|simulation)$"),
    )

    overgroup = Option(
        doc="""
        **Syntax:** **overgroup=****
        **Description:** The overgroup argument can be used to override the grouping per application name space, defaults to None.""",
        require=False,
        default=None,
        validate=validators.Match("context", r"^.*$"),
    )

    check_last_seen = Option(
        doc="""
        **Syntax:** **check_last_seen=****
        **Description:** Check last seen record, for deduplication and overlap purposes.""",
        require=False,
        default=False,
    )

    check_last_seen_field = Option(
        doc="""
        **Syntax:** **check_last_seen_field=****
        **Description:** Check last seen field in the KVstore collection.""",
        require=False,
        default=None,
        validate=validators.Match(
            "context",
            r"^(last_seen_scheduler|last_seen_introspection|last_seen_notable|last_seen_splunkcloud_svc)$",
        ),
    )

    def get_tenant_metric_idx(self):
        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % self._metadata.searchinfo.session_key,
            "Content-Type": "application/json",
        }

        # get the index conf for this tenant
        url = "%s/services/trackme/v2/vtenants/tenant_idx_settings" % (
            self._metadata.searchinfo.splunkd_uri
        )
        data = {"tenant_id": self.tenant_id, "idx_stanza": "trackme_metric_idx"}

        # Retrieve and set the tenant idx, if any failure, logs and use the global index
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'failed to retrieve the tenant metric index, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = (
                f'failed to retrieve the tenant metric index, exception="{str(e)}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    def process_record(self, reqinfo, record, metric_index):
        wlk_time = record.get("_time", time.time())
        wlk_object = decode_unicode(record.get("object"))
        wlk_tracker_type = record.get("tracker_type")
        wlk_overgroup = record.get("overgroup")
        wlk_group = record.get("group", wlk_tracker_type)
        wlk_app = record.get("app")
        wlk_user = record.get("user")
        wlk_savedsearch_name = record.get("savedsearch_name")
        wlk_account = record.get("account")
        wlk_status = int(record.get("status", 0))
        wlk_status_description = record.get("status_description")
        wlk_object_description = record.get("object_description")
        wlk_last_seen = record.get("last_seen")
        wlk_metrics = record.get("metrics")
        wlk_version_id = record.get("version_id")

        if wlk_object is None:
            log.error(
                f"The field 'object' is mandatory and should be part of the search results. The 'object' field could not be found in result: {json.dumps(record, indent=2)}"
            )
            raise ValueError(
                "The field 'object' is mandatory and should be part of the search results. The 'object' field could not be found in search results"
            )

        if not re.match(f"^{wlk_group}:", wlk_object):
            wlk_object = f"{wlk_group}:{wlk_object}"

        wlk_sha256 = hashlib.sha256(wlk_object.encode("utf-8")).hexdigest()

        # process
        wlk_metrics_parsed, wlk_metrics_parsed_msg = self.process_metrics(
            wlk_metrics, wlk_status
        )

        if self.context == "live":
            try:
                trackme_wlk_gen_metrics(
                    self.tenant_id,
                    wlk_overgroup,
                    wlk_group,
                    wlk_app,
                    wlk_user,
                    wlk_account,
                    wlk_savedsearch_name,
                    wlk_object,
                    wlk_sha256,
                    wlk_version_id,
                    metric_index,
                    wlk_metrics,
                )
            except Exception as e:
                log.error(
                    f'tenant_id="{self.tenant_id}", object="{wlk_object}", object_id="{wlk_sha256}", failed to stream events to metrics with exception="{e}"'
                )
                raise Exception(
                    f'tenant_id="{self.tenant_id}", object="{wlk_object}", object_id="{wlk_sha256}", failed to stream events to metrics with exception="{e}"'
                )

        raw = record.get("_raw", {k: v for k, v in record.items()})

        wlk_record = {
            "_time": wlk_time,
            "_raw": raw,
            "group": wlk_group,
            "object": wlk_object,
            "tracker_type": wlk_tracker_type,
            "object_description": wlk_object_description,
            "status": wlk_status,
            "status_description": wlk_status_description,
            "metrics": wlk_metrics,
            "last_seen": wlk_last_seen,
        }

        if self.context == "simulation":
            wlk_record["metrics_message"] = wlk_metrics_parsed_msg

        return wlk_record

    def process_metrics(self, wlk_metrics, wlk_status):
        wlk_metrics_parsed = False
        wlk_metrics_parsed_msg = None

        if wlk_metrics:
            try:
                wlk_metrics = json.loads(wlk_metrics)
                wlk_metrics_parsed = True
                wlk_metrics_parsed_msg = (
                    "Metrics JSON were submitted and successfully parsed"
                )
            except ValueError:
                try:
                    wlk_metrics = ast.literal_eval(wlk_metrics)
                    wlk_metrics_parsed = True
                    wlk_metrics_parsed_msg = (
                        "Metrics JSON were submitted and successfully parsed"
                    )
                except ValueError as e:
                    wlk_metrics_parsed_msg = f'Metrics JSON were submitted but could not be parsed properly, verify the JSON syntax, properties should be enquoted with single or double quotes, exception="{e}"'
                    log.error(wlk_metrics_parsed_msg)
                    raise

            if wlk_metrics and not wlk_metrics_parsed:
                wlk_metrics_parsed_msg = f"Metrics JSON were submitted but could not be parsed properly, verify the JSON syntax, properties should be enquoted with single or double quotes"
                logging.error(wlk_metrics_parsed_msg)
                raise ValueError(wlk_metrics_parsed_msg)

            else:
                if wlk_status:
                    wlk_metrics["status"] = wlk_status

        else:
            wlk_metrics = {
                "status": wlk_status,
            }
            wlk_metrics_parsed_msg = (
                "There were no metrics provided, will include the status only"
            )

        return wlk_metrics_parsed, wlk_metrics_parsed_msg

    def manage_kvstore_apps(self, apps_list):
        # connect to the apps enablement collection
        apps_collection_name = "kv_trackme_wlk_apps_enablement_tenant_%s" % (
            self.tenant_id
        )
        apps_collection = self.service.kvstore[apps_collection_name]

        # Pre-load the set of already-known apps in a single query, then batch
        # insert the missing ones. Replaces a per-app query + insert loop that
        # scaled linearly with the discovered app count on the WLK tracker's
        # first execution. If this query fails we must NOT fall back to an empty
        # set: every app would then be (re-)written via batch_save with
        # `enabled: "True"`, overwriting any user-disabled apps. Abort the seed
        # for this cycle - the next cycle will retry naturally.
        try:
            existing_records = apps_collection.data.query(query=json.dumps({}))
        except Exception as e:
            logging.error(
                f'tenant_id="{self.tenant_id}", failed to pre-load existing apps enablement records, aborting wlk_apps_enablement_seed for this cycle to avoid clobbering disabled apps, exception="{e}"'
            )
            return

        existing_apps = {
            r.get("app") for r in existing_records if r.get("app") is not None
        }

        new_records = []
        for app in apps_list:
            if app in existing_apps:
                continue
            new_records.append(
                {
                    "_key": hashlib.sha256(app.encode("utf-8")).hexdigest(),
                    "app": app,
                    "enabled": "True",
                    "mtime": time.time(),
                }
            )

        if not new_records:
            return

        # Chunk to 500 records per batch_save call (matches Splunk's
        # _kvstore/batch_save endpoint limit and the surrounding WLK
        # batch_kvstore_update idiom). Track actual successful chunk inserts
        # so the seed log reflects partial failures.
        chunks = [new_records[i : i + 500] for i in range(0, len(new_records), 500)]
        inserted_count = 0
        failed_count = 0
        for chunk in chunks:
            try:
                apps_collection.data.batch_save(*chunk)
                inserted_count += len(chunk)
            except Exception as e:
                failed_count += len(chunk)
                logging.error(
                    f'tenant_id="{self.tenant_id}", batch_save of apps enablement records failed, exception="{e}", chunk_size={len(chunk)}'
                )

        logging.info(
            f'tenant_id="{self.tenant_id}", wlk_apps_enablement_seed, inserted_count={inserted_count}, failed_count={failed_count}, candidate_count={len(new_records)}, total_apps_in_payload={len(apps_list)}'
        )

    def get_last_seen_collection(self):
        # connect to the KVstore
        collection_name = f"kv_trackme_wlk_last_seen_activity_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get all records
        get_collection_start = time.time()
        collection_records = []
        collection_records_keys = set()
        collection_records_dict = {}

        end = False
        skip_tracker = 0
        while end == False:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if len(process_collection_records) != 0:
                for item in process_collection_records:
                    if item.get("_key") not in collection_records_keys:
                        collection_records.append(item)
                        collection_records_keys.add(item.get("_key"))
                        collection_records_dict[item.get("_key")] = {
                            "_key": item.get("_key"),
                            "account": item.get("account"),
                            "object": item.get("object"),
                            "last_seen_scheduler": item.get("last_seen_scheduler"),
                            "last_seen_introspection": item.get(
                                "last_seen_introspection"
                            ),
                            "last_seen_notable": item.get("last_seen_notable"),
                            "last_seen_splunkcloud_svc": item.get(
                                "last_seen_splunkcloud_svc"
                            ),
                        }
                skip_tracker += len(process_collection_records)
            else:
                end = True

        logging.info(
            f'context="perf", get collection records, no_records="{len(collection_records)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="{collection_name}"'
        )

        return collection_records_dict

    # batch KVstore update
    def batch_kvstore_update(self, collection_dict):
        logging.debug(
            f"calling batch_kvstore_update, collection_dict={json.dumps(collection_dict, indent=2)}"
        )
        # connect to the KVstore
        collection_name = f"kv_trackme_wlk_last_seen_activity_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # batch update/insert
        batch_update_collection_start = time.time()

        final_records = []
        # loop through the collection dict and add to the list
        for key, value in collection_dict.items():
            final_records.append(
                {
                    "_key": key,
                    "account": value.get("account"),
                    "object": value.get("object"),
                    "last_seen_scheduler": value.get("last_seen_scheduler"),
                    "last_seen_introspection": value.get("last_seen_introspection"),
                    "last_seen_notable": value.get("last_seen_notable"),
                    "last_seen_splunkcloud_svc": value.get("last_seen_splunkcloud_svc"),
                }
            )

        # process by chunk
        chunks = [final_records[i : i + 500] for i in range(0, len(final_records), 500)]
        for chunk in chunks:
            try:
                collection.data.batch_save(*chunk)
            except Exception as e:
                logging.error(f'KVstore batch failed with exception="{str(e)}"')

        # perf counter for the batch operation
        logging.info(
            f'context="perf", batch KVstore update terminated, no_records="{len(final_records)}", run_time="{round((time.time() - batch_update_collection_start), 3)}", collection="{collection_name}"'
        )

        return True

    def stream(self, records):
        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        log.info(
            f'tenant_id="{self.tenant_id}", context="{self.context}", TrackMeSplkWlkParse is starting'
        )

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        # if check_last_seen is enabled, get the last seen collection
        if self.check_last_seen and self.check_last_seen_field:
            last_seen_collection = self.get_last_seen_collection()

        # list of apps
        apps_list = []

        # counters
        count = 0
        count_processed = 0

        for record in records:
            count += 1

            # first decode object
            record["object"] = decode_unicode(record.get("object"))

            # get and add app to the list
            app = record["app"]
            if not app in apps_list:
                apps_list.append(app)

            # overgroup
            if not self.overgroup:
                overgroup = app
            else:
                overgroup = self.overgroup
            record["overgroup"] = overgroup

            # if check_last_seen is enabled, check the last seen record from the dict
            record_to_be_processed = False

            if self.check_last_seen and self.check_last_seen_field:
                # define the sha256 key as: account + ":" + object
                if self.check_last_seen and self.check_last_seen_field:
                    # define the sha256 key as: account + ":" + object
                    record_key_str = f"{record['account']}:{record['object']}"
                    record_key = hashlib.sha256(
                        record_key_str.encode("utf-8")
                    ).hexdigest()

                    # get record from the last seen collection, if any
                    last_seen_collection_record = last_seen_collection.get(
                        record_key, {}
                    )
                    last_seen_epoch = last_seen_collection_record.get(
                        self.check_last_seen_field
                    )
                    if last_seen_epoch:
                        last_seen_epoch = round(float(last_seen_epoch), 0)

                    # get record epoch
                    record_epoch = round(float(record.get("_time")), 0)

                    # Logic to decide if the record should be processed
                    if not last_seen_collection_record:
                        # Create a new record with all required fields
                        last_seen_collection_record = {
                            "_key": record_key,
                            "account": record["account"],
                            "object": record["object"],
                            self.check_last_seen_field: record["_time"],
                        }
                        last_seen_collection[record_key] = last_seen_collection_record
                        logging.info(
                            f'tenant_id="{self.tenant_id}", account="{record.get("account")}", key="{record_key}", object="{record.get("object")}", action="granted", last_seen_collection_record is empty, granting record="{json.dumps(record, indent=2)}"'
                        )
                        record_to_be_processed = True

                    elif (
                        last_seen_epoch and record_epoch > last_seen_epoch
                    ) or not last_seen_epoch:
                        # Update only the relevant last_seen field in the existing record
                        last_seen_collection_record[self.check_last_seen_field] = (
                            record["_time"]
                        )
                        last_seen_collection[record_key] = last_seen_collection_record

                        logging.info(
                            f'tenant_id="{self.tenant_id}", account="{record.get("account")}", key="{record_key}", object="{record.get("object")}", action="granted", epoch condition is met, last_seen_epoch="{last_seen_epoch}" is bigger than record_epoch="{record_epoch}", granting record="{json.dumps(record, indent=2)}"'
                        )
                        record_to_be_processed = True

                    else:
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", account="{record.get("account")}", key="{record_key}", object="{record.get("object")}", action="skipped", epoch condition not met, last_seen_epoch="{last_seen_epoch}" is not bigger than record_epoch="{record_epoch}", skipping record="{json.dumps(record, indent=2)}"'
                        )
                        continue

            else:
                # grant process
                record_to_be_processed = True

            # process record
            if record_to_be_processed:
                count_processed += 1
                wlk_record = self.process_record(reqinfo, record, metric_index)

                # results
                result = {
                    "_time": wlk_record["_time"],
                    "_raw": wlk_record,
                    "overgroup": overgroup,
                    "group": wlk_record["group"],
                    "object": wlk_record["object"],
                    "object_category": "splk-wlk",
                    "object_description": wlk_record["object_description"],
                    "status": wlk_record["status"],
                    "status_description": wlk_record["status_description"],
                    "metrics": wlk_record["metrics"],
                    "last_seen": wlk_record["last_seen"],
                }

                if self.context == "simulation":
                    result["metrics_message"] = wlk_record["metrics_message"]

                yield result

                logging.debug(
                    f'tenant_id="{self.tenant_id}", context="{self.context}", processed result="{json.dumps(wlk_record, indent=2)}"'
                )

        # if check_last_seen is enabled, process to the KVstore batch update
        if self.check_last_seen and self.check_last_seen_field:
            # batch update the KVstore
            logging.debug(
                f'tenant_id="{self.tenant_id}", batch update the KVstore, last_seen_collection={json.dumps(last_seen_collection, indent=2)}'
            )
            self.batch_kvstore_update(last_seen_collection)

        # Call the new function to manage apps in KVstore
        if self.context == "live":
            self.manage_kvstore_apps(apps_list)

        if count_processed == 0:
            result = {
                "_time": time.time(),
                "result": f"no records to process, {count} record were skipped and already processed.",
            }
            yield result

        logging.info(
            f'tenant_id="{self.tenant_id}", context="{self.context}", TrackMeSplkWlkParse has terminated successfully, turn debug mode on for more details, results_count="{count}"'
        )


dispatch(TrackMeSplkWlkParse, sys.argv, sys.stdin, sys.stdout, __name__)
