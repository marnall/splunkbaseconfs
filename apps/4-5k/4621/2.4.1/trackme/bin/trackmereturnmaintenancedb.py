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

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_return_maintenance_kdb.log" % splunkhome,
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
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class TrackMeReturnMaintenanceKdb(GeneratingCommand):

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    def generate(self, **kwargs):
        if self:
            # performance counter
            start = time.time()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # get maintenance_kdb_exclusion_behaviour, returned value will be:
            # any - include either planned or unplanned maintenance records
            # planned - include only planned maintenance records
            # unplanned - include only unplanned maintenance records
            # the default in TrackMe matches planned records only
            maintenance_kdb_exclusion_behaviour = reqinfo["trackme_conf"][
                "maintenance"
            ]["maintenance_kdb_exclusion_behaviour"]

            # collection
            collection_name = "kv_trackme_maintenance_kdb"
            collection = self.service.kvstore[collection_name]

            # get all records
            get_collection_start = time.time()
            collection_records = []
            collection_records_planned = []
            collection_records_unplanned = []
            collection_records_keys = set()

            # counter
            maintenance_records_eligible = 0

            end = False
            skip_tracker = 0
            while end == False:
                process_collection_records = collection.data.query(skip=skip_tracker)
                if len(process_collection_records) != 0:
                    for item in process_collection_records:

                        # from item, get tenants_scope field, if any, if not available in the record add "*"
                        if "tenants_scope" in item:
                            tenants_scope = item.get("tenants_scope")
                            # check that tenants_scope is a list, if not convert to list from comma separated string
                            if not isinstance(tenants_scope, list):
                                tenants_scope = tenants_scope.split(",")
                        else:
                            tenants_scope = ["*"]

                        if (
                            item.get("_key") not in collection_records_keys
                            and int(item.get("is_disabled")) == 0
                        ):
                            collection_records.append(item)
                            collection_records_keys.add(item.get("_key"))
                            if maintenance_kdb_exclusion_behaviour == "any":
                                maintenance_records_eligible += 1

                            # Add to planned or unplanned list
                            if item.get("type") == "planned" and (
                                self.tenant_id in tenants_scope
                                or tenants_scope == ["*"]
                            ):
                                collection_records_planned.append(item)
                                if maintenance_kdb_exclusion_behaviour == "planned":
                                    maintenance_records_eligible += 1
                            elif item.get("type") == "unplanned" and (
                                self.tenant_id in tenants_scope
                                or tenants_scope == ["*"]
                            ):
                                collection_records_unplanned.append(item)
                                if maintenance_kdb_exclusion_behaviour == "unplanned":
                                    maintenance_records_eligible += 1

                    skip_tracker += len(process_collection_records)
                else:
                    end = True

            logging.info(
                f'context="perf", get collection records, no_records="{len(collection_records)}", no_records_planned="{len(collection_records_planned)}", no_records_unplanned="{len(collection_records_unplanned)}", run_time="{round((time.time() - get_collection_start), 3)}", collection="kv_trackme_maintenance_kdb"'
            )

            # return statement
            if maintenance_records_eligible != 0:
                # init list
                search_str_list = []

                if maintenance_kdb_exclusion_behaviour == "any":
                    for record in collection_records:
                        search_str_list.append(
                            f"(_time>={record['time_start']} AND _time<={record['time_end']})"
                        )

                    # generate the search_str fromn the list, join with AND NOT
                    search_str = " AND NOT ".join(search_str_list)

                elif maintenance_kdb_exclusion_behaviour == "planned":
                    for record in collection_records_planned:
                        search_str_list.append(
                            f"(_time>={record['time_start']} AND _time<={record['time_end']})"
                        )

                    # generate the search_str fromn the list, join with AND NOT
                    search_str = " AND NOT ".join(search_str_list)

                elif maintenance_kdb_exclusion_behaviour == "unplanned":
                    for record in collection_records_unplanned:
                        search_str_list.append(
                            f"(_time>={record['time_start']} AND _time<={record['time_end']})"
                        )

                    # generate the search_str fromn the list, join with AND NOT
                    search_str = " AND NOT ".join(search_str_list)

            else:
                search_str = "_time==0"

            # yield
            yield {
                "_time": time.time(),
                "_raw": search_str,
                "search_str": search_str,
            }

        logging.info(
            f'trackmereturnmaintenancedb has terminated, run_time={round(time.time() - start, 3)}, results="{search_str}"'
        )


dispatch(TrackMeReturnMaintenanceKdb, sys.argv, sys.stdin, sys.stdout, __name__)
