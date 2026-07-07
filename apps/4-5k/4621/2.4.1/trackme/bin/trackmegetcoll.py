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

# Built-in modules
import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

# Third-party modules
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_get_collection.log" % splunkhome,
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

# Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, get_splunkd_timeout


@Configuration(distributed=False)
class TrackMeGetCollection(GeneratingCommand):

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
        validate=validators.Match("tenant_id", r".+"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The tracker component name to be executed.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm|mhm|flx|wlk|fqm)$"),
    )

    mode = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The mode of the command, set to "stats" to get the stats only. Default is "records".""",
        require=False,
        default="records",
        validate=validators.Match("mode", r"^(?:records|stats|cachedstats)$"),
    )

    mode_view = Option(
        doc="""
        **Syntax:** **mode_view=****
        **Description:** The mode_view, when applicable. Default is "minimal", valid options: minimal, full.""",
        require=False,
        default=None,
        validate=validators.Match("mode", r"^(?:minimal|compact|full)$"),
    )

    filter_key = Option(
        doc="""
        **Syntax:** **filter_key=****
        **Description:** Filter on a key, filter for a specific record by using its unique key.""",
        require=False,
        default=None,
        validate=validators.Match("filter_key", r".*"),
    )

    filter_object = Option(
        doc="""
        **Syntax:** **filter_object=****
        **Description:** Filter on a given object, filter for a specific record by using its object value.""",
        require=False,
        default=None,
        validate=validators.Match("filter_object", r".*"),
    )

    def generate_fields(self, records):
        """
        this function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
        if a given result does not have a given field, it will be added to the record as an empty value
        """

        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            record["_time"] = time.time()
            record["_raw"] = json.dumps(record)
            yield record

    def count_records(self, record, stats):
        """
        Update the stats based on the properties of the record.

        :param record: A dictionary representing a single record.
        :param stats: A dictionary holding the count of various statistics.
        """
        stats["count_total"] += 1
        if record.get("monitored_state") == "disabled":
            stats["count_total_disabled"] += 1
        if (
            record.get("object_state") == "red"
            and record.get("monitored_state") == "enabled"
        ):
            stats["count_total_in_alert"] += 1
        if (
            record.get("object_state") == "red"
            and record.get("priority") == "high"
            and record.get("monitored_state") == "enabled"
        ):
            stats["count_total_high_priority_red"] += 1
        if (
            record.get("object_state") == "red"
            and record.get("priority") == "critical"
            and record.get("monitored_state") == "enabled"
        ):
            stats["count_total_critical_priority_red"] += 1
        if record.get("monitored_state") == "enabled":
            if record.get("priority") == "low":
                stats["count_low_enabled"] += 1
            if record.get("priority") == "medium":
                stats["count_medium_enabled"] += 1
            if record.get("priority") == "high":
                stats["count_high_enabled"] += 1
            if record.get("priority") == "critical":
                stats["count_critical_enabled"] += 1
            if record.get("priority") == "pending":
                stats["count_pending_enabled"] += 1
            if record.get("object_state") == "green":
                stats["count_green_enabled"] += 1
            if record.get("object_state") == "blue":
                stats["count_blue_enabled"] += 1
            if record.get("object_state") == "orange":
                stats["count_orange_enabled"] += 1
            if record.get("object_state") == "red" and record.get("priority") == "high":
                stats["count_red_high_priority_enabled"] += 1
            if (
                record.get("object_state") == "red"
                and record.get("priority") == "critical"
            ):
                stats["count_red_critical_priority_enabled"] += 1
            if (
                record.get("object_state") == "red"
                and record.get("priority") != "high"
                and record.get("priority") != "critical"
            ):
                stats["count_red_other_priority_enabled"] += 1

    def ensure_record_tenant_id(self, record):
        """
        Ensure a record has a valid tenant_id field set to the command's tenant_id argument.
        If the record's tenant_id is missing, empty, or invalid, set it to self.tenant_id.
        
        :param record: A dictionary representing a single record.
        """
        record_tenant_id = record.get("tenant_id")
        
        # Check if tenant_id is missing, empty, or invalid
        if not record_tenant_id or not str(record_tenant_id).strip():
            record["tenant_id"] = self.tenant_id
            logging.debug(
                f'Record missing or empty tenant_id, set to command argument value, tenant_id="{self.tenant_id}"'
            )

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Log the run time
        logging.info(f"trackmegetcomponent is starting")

        # Validate tenant_id argument is not None or empty
        if not self.tenant_id or not self.tenant_id.strip():
            msg = f'tenant_id is required and cannot be empty, tenant_id="{self.tenant_id}"'
            logging.error(msg)
            raise Exception(msg)

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # if filtering, this cannot be on both
        if self.filter_key and self.filter_object:
            msg = f'filter_key and filter_object cannot be used together, filter_key="{self.filter_key}", filter_object="{self.filter_object}"'
            logging.error(msg)
            raise Exception(msg)

        # summary KVstore collection
        summary_collection_name = f"kv_trackme_virtual_tenants_entities_summary"
        summary_collection = self.service.kvstore[summary_collection_name]

        # Get the summary record
        try:
            vtenant_record = summary_collection.data.query(
                query=json.dumps({"tenant_id": self.tenant_id})
            )[0]
            vtenant_key = vtenant_record.get("_key")
            logging.debug(
                f'tenant_id="{self.tenant_id}", vtenant_key="{vtenant_key}", vtenant_report="{json.dumps(vtenant_record)}"'
            )
        except Exception as e:
            vtenant_record = {}
            vtenant_key = None

        # if vtenant_key is found, get the cached stats ({component}_extended_stats)
        cached_extended_stats = {}
        if vtenant_key and self.mode == "cachedstats":
            try:
                cached_extended_stats = json.loads(
                    vtenant_record.get(f"{self.component}_extended_stats")
                )
            except Exception as e:
                cached_extended_stats = {}

        # data_records
        data_records = []

        # counter for stats
        stats = {
            "count_total": 0,
            "count_total_disabled": 0,
            "count_total_in_alert": 0,
            "count_total_high_priority_red": 0,
            "count_total_critical_priority_red": 0,
            "count_low_enabled": 0,
            "count_medium_enabled": 0,
            "count_high_enabled": 0,
            "count_critical_enabled": 0,
            "count_pending_enabled": 0,
            "count_blue_enabled": 0,
            "count_orange_enabled": 0,
            "count_green_enabled": 0,
            "count_red_critical_priority_enabled": 0,
            "count_red_high_priority_enabled": 0,
            "count_red_other_priority_enabled": 0,
        }

        params = {
            "tenant_id": self.tenant_id,
            "component": self.component,
            "page": 1,
            "size": 0,
        }

        if self.filter_key and self.filter_key != "*":
            params["filter_key"] = self.filter_key

        if self.filter_object and self.filter_object != "*":
            params["filter_object"] = self.filter_object

        if self.mode_view:
            params["mode_view"] = self.mode_view

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
            "Content-Type": "application/json",
        }

        # Set url
        url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/component/load_component_data"

        #
        # cache information

        # cache_is_outed boolean, False by default, True if not updated since more than 5 minutes
        cache_is_outed = False

        # if cached_extended_stats is an empty dict, set cache_is_outed to True
        if not cached_extended_stats:
            cache_is_outed = True
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", cache_is_outed="{cache_is_outed}", cached_extended_stats is not available yet, will proceed to query stats.'
            )

        # count_total_entities, for logging reporting only
        count_total_entities = 0

        if self.mode == "cachedstats" and cached_extended_stats:

            # get in cached_extended_stats the mtime value (epoch) and calculate the time in seconds since the last update
            mtime = cached_extended_stats.get("mtime")
            time_since_last_update = time.time() - mtime

            # if the time since last update is more than 15 minutes, set cache_is_outed to True
            if time_since_last_update > 900:
                cache_is_outed = True
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", cache_is_outed="{cache_is_outed}", time_since_last_update="{round(time_since_last_update, 3)}", will proceed to query stats.'
                )

        # Proceed
        if self.mode == "cachedstats" and not cache_is_outed:

            if not cache_is_outed:
                # yield the stats

                # add a field _raw which contains all fields in stats
                cached_extended_stats["_raw"] = json.dumps(cached_extended_stats)

                # add _time field
                cached_extended_stats["_time"] = time.time()

                # count total
                count_total_entities = cached_extended_stats.get("count_total")

                yield cached_extended_stats

        elif (
            self.mode == "stats"
            or self.mode == "records"
            or (self.mode == "cachedstats" and cache_is_outed)
        ):

            try:
                response = requests.get(
                    url,
                    headers=header,
                    params=params,
                    verify=False,
                    timeout=splunkd_timeout,
                )

                if response.status_code not in (200, 201, 204):
                    msg = f'get component has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                    raise Exception(msg)

                else:
                    response_json = response.json()
                    data = response_json.get("data", [])

                    # add the data to the data_records
                    for record in data:
                        # Ensure record has valid tenant_id set to command argument
                        self.ensure_record_tenant_id(record)

                        if self.mode == "records":

                            # the field anomaly_reason is a pipe separated string, turn it into a list
                            try:
                                anomaly_reason_list = record.get(
                                    "anomaly_reason"
                                ).split("|")
                                record["anomaly_reason"] = anomaly_reason_list
                                # count the number of anomalies, and add as the field anomaly_reason_count
                                record["anomaly_reason_count"] = len(
                                    anomaly_reason_list
                                )
                            except Exception as e:
                                record["anomaly_reason_count"] = 1

                            data_records.append(record)
                        # count the records
                        self.count_records(record, stats)

            except Exception as e:
                msg = f'get component has failed, exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            if self.mode == "records":
                for yield_record in self.generate_fields(data_records):
                    yield yield_record

            elif self.mode == "stats" or (
                self.mode == "cachedstats" and cache_is_outed
            ):
                # yield the stats

                # add a field _raw which contains all fields in stats
                stats["_raw"] = json.dumps(stats)

                # add _time field
                stats["_time"] = time.time()

                yield stats

                # count total
                count_total_entities = stats.get("count_total")

        # Log the run time
        logging.info(
            f'context="perf", trackmegetcomponent has terminated, no_records="{count_total_entities}", run_time="{round((time.time() - start), 3)}", tenant_id="{self.tenant_id}", component="{self.component}"'
        )


dispatch(TrackMeGetCollection, sys.argv, sys.stdin, sys.stdout, __name__)
