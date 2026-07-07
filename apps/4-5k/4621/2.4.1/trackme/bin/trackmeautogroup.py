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
    os.path.join(splunkhome, "var", "log", "splunk", "trackme_trackmeautogroup.log"),
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
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeReplicatorHandler(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Specify the TrackMe target tenant_id.""",
        require=True,
        default="None",
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    purge_single_member_grp = Option(
        doc="""
        **Syntax:** **purge_single_member_grp=****
        **Description:** Purge any single member resulting group.""",
        require=False,
        default=True,
        validate=validators.Match("purge_single_member_grp", r"^(True|False)$"),
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

    def stream(self, records):
        # performance counter
        main_start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # connect to the source KVstore
        collection_name = f"kv_trackme_common_logical_group_tenant_{self.tenant_id}"
        collection = self.service.kvstore[collection_name]

        # get source and target collection records
        collection_records, collection_keys = self.get_kv_collection(
            collection, collection_name
        )

        logging.info(f"collection_records={json.dumps(collection_records, indent=2)}")

        # turn it into a dict for direct access
        collection_dict = {_["_key"]: _ for _ in collection_records}

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

        # upstream results
        records_count = 0
        for record in records:
            if "object_group_name" not in record:
                raise Exception("object_group_name field is missing from record")
            elif "object_group_members" not in record:
                raise Exception("object_group_members field is missing from record")

            # increment
            records_count += 1

            # get object_group_name
            object_group_name = record.get("object_group_name")

            # get object_group_members
            object_group_members = record.get("object_group_members")

            # set the key
            key = hashlib.sha256(
                record.get("object_group_name").encode("utf-8")
            ).hexdigest()

            # count the number of members
            if not isinstance(object_group_members, list):
                count_members = 1
            else:
                count_members = len(object_group_members)

            # define object_group_min_green_percent
            object_group_min_green_percent = round(100 / count_members, 2)

            # add flag
            add_flag = False

            # purge_group
            if self.purge_single_member_grp == "True" and count_members == 1:
                remove_flag = True
            else:
                remove_flag = False

            # if group is to be removed
            if key in collection_keys and remove_flag:
                try:
                    collection.data.delete(json.dumps({"_key": key}))
                    purged_count += 1
                    logging.debug(
                        f'group record with key="{key}", object_group_name="{object_group_name}" has only 1 active member left and was purged from the collection'
                    )
                except Exception as e:
                    failures_count += 1
                    msg = f'failure to purge target key="{key}", object_group_name="{object_group_name}", exception="{str(e)}"'
                    exceptions_list.append(msg)
                    logging.error(msg)

            # the group is already known in the collection - check it out
            elif key in collection_keys:
                current_record = collection_dict[key]
                current_members = current_record["object_group_members"]

                # add if the group definition differs and we have more than 1 member in the group
                if current_members != object_group_members and count_members > 1:
                    add_flag = True

            elif not (self.purge_single_member_grp == "True" and count_members == 1):
                add_flag = True

            # add as needed
            if add_flag:
                # add to final_records
                final_records.append(
                    {
                        "_key": key,
                        "object_group_name": object_group_name,
                        "object_group_members": object_group_members,
                        "object_group_min_green_percent": object_group_min_green_percent,
                        "object_group_mtime": time.time(),
                    }
                )

            else:
                logging.debug(
                    f"group={object_group_name} with members={object_group_members} is already defined and does not need to be updated"
                )

        # batch update KVstore
        failures_count, exceptions_list, run_time = self.batch_update_kvstore(
            final_records, collection, collection_name
        )

        collection_dict = {
            "tenant_id": self.tenant_id,
            "purge_single_member_grp": self.purge_single_member_grp,
            "total_records": records_count,
            "updated_records": len(final_records),
            "purged_records": purged_count,
            "failures_count": failures_count,
            "exceptions": exceptions_list,
            "run_time": run_time,
        }

        yield_record = {
            "action": "failure" if failures_count > 0 else "success",
            "collection": collection_name,
            "data": collection_dict,
        }
        yield yield_record

        # perf counter for the entire call
        total_run_time = round((time.time() - main_start), 3)
        logging.info(
            f'trackmeautogroup has terminated, tenant_id="{self.tenant_id}", run_time="{total_run_time}"'
        )


dispatch(TrackMeReplicatorHandler, sys.argv, sys.stdin, sys.stdout, __name__)
