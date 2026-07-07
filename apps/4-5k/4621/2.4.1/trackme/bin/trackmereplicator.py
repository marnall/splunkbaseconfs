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
    os.path.join(splunkhome, "var", "log", "splunk", "trackme_trackmereplicator.log"),
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
from trackme_libs import trackme_reqinfo, run_splunk_search


@Configuration(distributed=False)
class TrackMeReplicatorHandler(StreamingCommand):
    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** Specify the TrackMe component.""",
        require=True,
        default="None",
        validate=validators.Match("component", r"^.*$"),
    )

    source_tenant_id = Option(
        doc="""
        **Syntax:** **source_tenant_id=****
        **Description:** Specify the TrackMe source tenant_id.""",
        require=True,
        default="None",
        validate=validators.Match("source_tenant_id", r"^.*$"),
    )

    target_tenant_id = Option(
        doc="""
        **Syntax:** **target_tenant_id=****
        **Description:** Specify the TrackMe target tenant_id.""",
        require=True,
        default="None",
        validate=validators.Match("target_tenant_id", r"^.*$"),
    )

    key_field = Option(
        doc="""
        **Syntax:** **key_field=****
        **Description:** The name of the field containing the KVstore record key value.""",
        require=True,
        default="None",
        validate=validators.Match("key_field", r"^.*$"),
    )

    def get_kv_collection(self, collection, collection_name):
        # get all records
        start_time = time.time()
        collection_records = []
        collection_records_keys = set()

        try:
            end = False
            skip_tracker = 0
            while not end:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if len(process_collection_records) == 0:
                    end = True

                else:
                    for record in process_collection_records:
                        collection_records.append(record)
                        collection_records_keys.add(record["_key"])

                    skip_tracker += len(process_collection_records)

            logging.info(
                f'context="perf", KVstore select terminated, no_records="{len(collection_records)}", run_time="{round((time.time() - start_time), 3)}", collection="{collection_name}"'
            )

            return collection_records, collection_records_keys

        except Exception as e:
            logging.error(
                f"failed to call get_kv_collection, args={collection_name}, exception={str(e)}"
            )
            raise Exception(str(e))

    def batch_update_kvstore(
        self, final_records, target_collection, target_collection_name
    ):
        # batch update/insert
        start_time = time.time()
        failures_count = 0
        exceptions_list = []

        # process by chunk
        chunks = [final_records[i : i + 500] for i in range(0, len(final_records), 500)]
        for chunk in chunks:
            try:
                target_collection.data.batch_save(*chunk)
            except Exception as e:
                failures_count += 1
                msg = f'KVstore batch failed with exception="{str(e)}"'
                exceptions_list.append(msg)
                logging.error(msg)

        run_time = round((time.time() - start_time), 3)

        # perf counter for the batch operation
        logging.info(
            f'context="perf", batch KVstore update terminated, no_records="{len(final_records)}", run_time="{run_time}", collection="{target_collection_name}"'
        )

        return failures_count, exceptions_list, run_time

    def register_summary(self):
        search = f"| `register_tenant_component_summary({self.target_tenant_id}, {self.component})`"
        kwargs_oneshot = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "count": 0,
            "output_mode": "json",
        }
        logging.debug(f'search="{search}"')

        component_summary_results = []

        # run search
        try:
            reader = run_splunk_search(
                self.service,
                search,
                kwargs_oneshot,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    logging.debug(f'search_results="{item}"')
                    # append to the list of searches
                    component_summary_results.append(
                        {
                            "tenant_id": self.target_tenant_id,
                            "comppnent": self.component,
                            "entities_count": item,
                        }
                    )

        except Exception as e:
            msg = f'tenant_id="{self.target_tenant_id}", component="{self.component}", search failed with exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        return component_summary_results

    def stream(self, records):
        # performance counter
        main_start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # common collections
        collections_list = [
            f"kv_trackme_{self.component}_tenant",
            "kv_trackme_common_logical_group_tenant",
        ]

        # we will add here any additional collection to be synced
        if self.component in "dsm":
            collections_list.append(f"kv_trackme_{self.component}_data_sampling_tenant")
        elif self.component in "wlk":
            collections_list.append(
                f"kv_trackme_{self.component}_apps_enablement_tenant"
            )

        # loop and proceed
        for handle_collection in collections_list:
            # connect to the source KVstore
            source_collection_name = f"{handle_collection}_{self.source_tenant_id}"
            source_collection = self.service.kvstore[source_collection_name]

            # connect to the target KVstore
            target_collection_name = f"{handle_collection}_{self.target_tenant_id}"
            target_collection = self.service.kvstore[target_collection_name]

            # get source and target collection records
            source_collection_records, source_collection_keys = self.get_kv_collection(
                source_collection, source_collection_name
            )
            target_collection_records, target_collection_keys = self.get_kv_collection(
                target_collection, target_collection_name
            )

            #
            # Replica proceed
            #

            final_records = []

            # purged counter
            purged_count = 0

            # failures counter
            failures_count = 0

            # a list to store any exception encountered
            exceptions_list = []

            # purge records that wouldn't exist anymore in the source KVstore
            for record in target_collection_records:
                # get record key
                record_key = record.get("_key")

                # sync step1: if a record in target does not exist anymore in the source, purge the record
                if (
                    record_key not in source_collection_keys
                    and record.get("tenant_parent") == self.source_tenant_id
                ):
                    try:
                        target_collection.data.delete(json.dumps({"_key": record_key}))
                        purged_count += 1
                        logging.debug(
                            f'record with key="{record_key}" does not exist anymore in the source collection and was purged'
                        )
                    except Exception as e:
                        failures_count += 1
                        msg = f'failure to purge target key="{record_key}", exception="{str(e)}"'
                        exceptions_list.append(msg)
                        logging.error(msg)

            # sync input records from the upstream search, this allows the user to have SPL flexibility for filtering out
            # the wanted content for the main collection
            records_count = 0
            if handle_collection == f"kv_trackme_{self.component}_tenant":
                for record in records:
                    # increment
                    records_count += 1

                    # replace tenant_id
                    record["tenant_id"] = self.target_tenant_id

                    # add parent info
                    record["tenant_parent"] = self.source_tenant_id

                    # add _key
                    record["_key"] = record.get(self.key_field)

                    # add to final_records
                    final_records.append(record)

            # other collections do not filter on the object however
            else:
                for record in source_collection_records:
                    # increment
                    records_count += 1

                    # replace tenant_id
                    record["tenant_id"] = self.target_tenant_id

                    # add parent info
                    record["tenant_parent"] = self.source_tenant_id

                    # add _key
                    record["_key"] = record.get("_key")

                    # add to final_records
                    final_records.append(record)

            # batch update KVstore
            failures_count, exceptions_list, run_time = self.batch_update_kvstore(
                final_records, target_collection, target_collection_name
            )

            collection_dict = {
                "source_collection": f"{handle_collection}_{self.source_tenant_id}",
                "target_collection": f"{handle_collection}_{self.target_tenant_id}",
                "source_tenant_id": self.source_tenant_id,
                "target_tenant_id": self.target_tenant_id,
                "total_records": records_count,
                "purged_records": purged_count,
                "failures_count": failures_count,
                "exceptions": exceptions_list,
                "run_time": run_time,
            }

            yield_record = {
                "action": "failure" if failures_count > 0 else "success",
                "source_collection": f"{handle_collection}_{self.source_tenant_id}",
                "target_collection": f"{handle_collection}_{self.target_tenant_id}",
                "data": collection_dict,
            }
            yield yield_record

        #
        # Process register_tenant_component_summary
        #

        try:
            component_summary_results = self.register_summary()
            logging.info(
                f'register_tenant_component_summary successfully executed, results="{json.dumps(component_summary_results, indent=2)}"'
            )
        except Exception as e:
            logging.info(
                f"register_tenant_component_summary has failed, exception={str(e)}"
            )

        # perf counter for the entire call
        total_run_time = round((time.time() - main_start), 3)
        logging.info(
            f'trackmereplicator has terminated, component="{self.component}", source_tenant_id="{self.source_tenant_id}", target_tenant_id="{self.target_tenant_id}", run_time="{total_run_time}"'
        )


dispatch(TrackMeReplicatorHandler, sys.argv, sys.stdin, sys.stdout, __name__)
