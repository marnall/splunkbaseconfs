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
import json
import logging
import os
import sys
import time
import requests
from collections import defaultdict

# Third-party library imports
import urllib3
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_feeds_delayed_inspector.log" % splunkhome,
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

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    run_splunk_search,
    trackme_vtenant_component_info,
    trackme_register_tenant_object_summary,
    trackme_idx_for_tenant,
    trackme_handler_events,
)

# import splk-feeds
from trackme_libs_splk_feeds import (
    generate_dsm_report_search,
    generate_dhm_report_search,
)

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds

# Maximum number of entities to batch into a single search.
# Entities sharing the same (account, search_mode, breakby_key, range_category) are batched together.
MAX_BATCH_SIZE = 50


@Configuration(distributed=False)
class TrackMeFeedsDelayedInspector(GeneratingCommand):

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The value for tenant_id.""",
        require=True,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The component category.""",
        require=True,
        default=None,
        validate=validators.Match("component", r"^(?:dsm|dhm|flx|wlk)$"),
    )

    max_runtime = Option(
        doc="""
        **Syntax:** **max_runtime=****
        **Description:** Optional, The max value in seconds for the total runtime of the job, defaults to 900 (15 min) which is subtracted by 120 sec of margin. Once the job reaches this, it gets terminated""",
        require=False,
        default="900",
        validate=validators.Match("max_runtime", r"^\d*$"),
    )

    max_errors_count_per_entity_search = Option(
        doc="""
        **Syntax:** **max_errors_count_per_entity_search=****
        **Description:** Optional, The maximum number of errors allowed per entity search, defaults to 3.
        """,
        require=False,
        default="3",
        validate=validators.Match("max_errors_count_per_entity_search", r"^\d*$"),
    )

    object_name = Option(
        doc="""
        **Syntax:** **object_name=****
        **Description:** Optional, The object name.""",
        require=False,
        default=None,
    )

    """
    Function to check if we have a record in the delayed inspector KV collection based
    on the _key field, and return the record if found, otherwise return empty dict
    """

    def get_delayed_inspector_record(
        self, delayed_inspector_collection, _key
    ):

        # check if we have a KVrecord already for this object
        query_string = {
            "$and": [
                {
                    "_key": _key,
                }
            ]
        }

        # record from the component
        try:
            kvrecord = delayed_inspector_collection.data.query(
                query=(json.dumps(query_string))
            )[0]
        except Exception as e:
            kvrecord = {}

        return kvrecord

    """
    Function to return the range category appartenance based on the data_last_lag_seen value and the delayed inspector configuration

    data_last_lag_seen: int
    splk_feeds_auto_disablement_period: str

    # behavior:
    - if the data_last_lag_seen is less than 24 hours, we return "24h"
    - if the data_last_lag_seen is between 24 hours and 7 days, we return "7d"
    - if the data_last_lag_seen is between 7 days and the auto disablement period, we return "until_disabled"
    - if the data_last_lag_seen is greater than the auto disablement period, we return "do_not_proceed"

    # returns:
    - str: The range category
    - str: The entity search earliest time
    - str: The span value, the longer the period of the search, the less granular the search
    """

    def get_range_category(
        self,
        data_last_lag_seen,
        splk_feeds_auto_disablement_period,
    ):
        # extract the number of days from splk_feeds_auto_disablement_period (format ex: 30d)
        splk_feeds_auto_disablement_period_days = int(
            splk_feeds_auto_disablement_period.split("d")[0]
        )

        if data_last_lag_seen < 3600 * 24:
            return "24h", "-24h", "1m"
        elif data_last_lag_seen >= 3600 * 24 and data_last_lag_seen < 3600 * 24 * 7:
            return "7d", "-7d", "5m"
        elif (
            data_last_lag_seen >= 3600 * 24 * 7
            and data_last_lag_seen < 3600 * 24 * splk_feeds_auto_disablement_period_days
        ) and splk_feeds_auto_disablement_period != "0d":
            return (
                "until_disabled",
                f"-{splk_feeds_auto_disablement_period_days}d",
                "1d",
            )
        else:
            return "do_not_proceed", None, None

    """
    Function to define the proceed entity boolean depending on the range category and the last inspection time

    range_category: str
    last_inspection_time: int
    splk_feeds_delayed_inspector_24hours_range_min_sec: int
    splk_feeds_delayed_inspector_7days_range_min_sec: int
    splk_feeds_delayed_inspector_until_disabled_range_min_sec: int
    backoff_multiplier: int (default 1, multiplied against the base threshold)

    # behavior:
    - if the range category is "24h" and the last inspection time is greater than the effective threshold, we proceed
    - if the range category is "7d" and the last inspection time is greater than the effective threshold, we proceed
    - if the range category is "until_disabled" and the last inspection time is greater than the effective threshold, we proceed
    - if the range category is "do_not_proceed", we do not proceed

    # returns:
    - bool: True if the entity should be proceeded, False otherwise
    - reason: A string message explaining the reason for the proceed_entity_bool value
    """

    def define_proceed_entity_bool(
        self,
        range_category,
        last_inspection_time,
        splk_feeds_delayed_inspector_24hours_range_min_sec,
        splk_feeds_delayed_inspector_7days_range_min_sec,
        splk_feeds_delayed_inspector_until_disabled_range_min_sec,
        backoff_multiplier=1,
    ):
        reason = ""
        proceed_entity_bool = False

        # Guard against invalid backoff multiplier values
        if backoff_multiplier < 1:
            backoff_multiplier = 1

        # If any of the range minimum seconds values are 0, do not proceed (feature disabled)
        if (
            range_category == "24h"
            and splk_feeds_delayed_inspector_24hours_range_min_sec == 0
        ):
            reason = "The delayed inspector is disabled for the 24h range category (splk_feeds_delayed_inspector_24hours_range_min_sec is set to 0)"
            return proceed_entity_bool, reason
        elif (
            range_category == "7d"
            and splk_feeds_delayed_inspector_7days_range_min_sec == 0
        ):
            reason = "The delayed inspector is disabled for the 7d range category (splk_feeds_delayed_inspector_7days_range_min_sec is set to 0)"
            return proceed_entity_bool, reason
        elif (
            range_category == "until_disabled"
            and splk_feeds_delayed_inspector_until_disabled_range_min_sec == 0
        ):
            reason = "The delayed inspector is disabled for the until_disabled range category (splk_feeds_delayed_inspector_until_disabled_range_min_sec is set to 0)"
            return proceed_entity_bool, reason

        # Compute effective thresholds by applying the backoff multiplier
        effective_24h = splk_feeds_delayed_inspector_24hours_range_min_sec * backoff_multiplier
        effective_7d = splk_feeds_delayed_inspector_7days_range_min_sec * backoff_multiplier
        effective_until_disabled = splk_feeds_delayed_inspector_until_disabled_range_min_sec * backoff_multiplier

        if range_category == "24h":

            if last_inspection_time == 0:
                proceed_entity_bool = True
                reason = f"The entity is within the 24h range category and the last inspection time {last_inspection_time} is 0"
            elif last_inspection_time > effective_24h:
                proceed_entity_bool = True
                reason = f"The entity is within the 24h range category and the last inspection time {last_inspection_time} is greater than the effective threshold {effective_24h} (base={splk_feeds_delayed_inspector_24hours_range_min_sec}, backoff_multiplier={backoff_multiplier})"
            else:
                reason = f"The entity is within the 24h range category but the last inspection time {last_inspection_time} is less than the effective threshold {effective_24h} (base={splk_feeds_delayed_inspector_24hours_range_min_sec}, backoff_multiplier={backoff_multiplier})"

        elif range_category == "7d":

            if last_inspection_time == 0:
                proceed_entity_bool = True
                reason = f"The entity is within the 7d range category and the last inspection time {last_inspection_time} is 0"
            elif last_inspection_time > effective_7d:
                proceed_entity_bool = True
                reason = f"The entity is within the 7d range category and the last inspection time {last_inspection_time} is greater than the effective threshold {effective_7d} (base={splk_feeds_delayed_inspector_7days_range_min_sec}, backoff_multiplier={backoff_multiplier})"
            else:
                reason = f"The entity is within the 7d range category but the last inspection time {last_inspection_time} is less than the effective threshold {effective_7d} (base={splk_feeds_delayed_inspector_7days_range_min_sec}, backoff_multiplier={backoff_multiplier})"

        elif range_category == "until_disabled":

            if last_inspection_time == 0:
                proceed_entity_bool = True
                reason = f"The entity is within the until_disabled range category and the last inspection time {last_inspection_time} is 0"
            elif last_inspection_time > effective_until_disabled:
                proceed_entity_bool = True
                reason = f"The entity is within the until_disabled range category and the last inspection time {last_inspection_time} is greater than the effective threshold {effective_until_disabled} (base={splk_feeds_delayed_inspector_until_disabled_range_min_sec}, backoff_multiplier={backoff_multiplier})"
            else:
                reason = f"The entity is within the until_disabled range category but the last inspection time {last_inspection_time} is less than the effective threshold {effective_until_disabled} (base={splk_feeds_delayed_inspector_until_disabled_range_min_sec}, backoff_multiplier={backoff_multiplier})"

        else:
            reason = f"The entity is not within any range category, the range category is {range_category}"

        return proceed_entity_bool, reason

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # get vtenant component info
        vtenant_component_info = trackme_vtenant_component_info(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )
        logging.debug(
            f'tenant_id="{self.tenant_id}", component="{self.component}", vtenant_component_info="{json.dumps(vtenant_component_info, indent=2)}"'
        )

        # get configuration values for the delayed inspector
        splk_feeds_delayed_inspector_24hours_range_min_sec = int(
            vtenant_component_info["splk_feeds_delayed_inspector_24hours_range_min_sec"]
        )
        splk_feeds_delayed_inspector_7days_range_min_sec = int(
            vtenant_component_info["splk_feeds_delayed_inspector_7days_range_min_sec"]
        )
        splk_feeds_delayed_inspector_until_disabled_range_min_sec = int(
            vtenant_component_info[
                "splk_feeds_delayed_inspector_until_disabled_range_min_sec"
            ]
        )
        splk_feeds_auto_disablement_period = str(
            vtenant_component_info["splk_feeds_auto_disablement_period"]
        )

        # get max backoff multiplier from config (system-wide setting)
        max_backoff_multiplier = max(
            1,
            int(
                vtenant_component_info.get(
                    "splk_feeds_delayed_inspector_max_backoff_multiplier", 4
                )
            ),
        )

        # check schema version migration state
        try:
            schema_version = int(vtenant_component_info["schema_version"])
            schema_version_upgrade_in_progress = bool(
                int(vtenant_component_info["schema_version_upgrade_in_progress"])
            )
            logging.debug(
                f'schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"'
            )
        except Exception as e:
            schema_version = 0
            schema_version_upgrade_in_progress = False
            logging.error(
                f'failed to retrieve schema_version_upgrade_in_progress=, exception="{str(e)}"'
            )

        # Do not proceed if the schema version upgrade is in progress
        if schema_version_upgrade_in_progress:
            yield_json = {
                "_time": time.time(),
                "tenant_id": self.tenant_id,
                "component": self.component,
                "response": f'tenant_id="{self.tenant_id}", schema upgrade is currently in progress, we will wait until the process is completed before proceeding, the schema upgrade is handled by the health_tracker of the tenant and is completed once the schema_version field of the Virtual Tenants KVstore (trackme_virtual_tenants) matches TrackMe\'s version, schema_version="{schema_version}", schema_version_upgrade_in_progress="{schema_version_upgrade_in_progress}"',
                "schema_version": schema_version,
                "schema_version_upgrade_in_progress": schema_version_upgrade_in_progress,
            }
            logging.info(json.dumps(yield_json, indent=2))
            yield {
                "_time": yield_json["_time"],
                "_raw": yield_json,
            }

        # log start
        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", starting delayed entities inspector, max_backoff_multiplier={max_backoff_multiplier}'
        )

        # get the target index
        tenant_indexes = trackme_idx_for_tenant(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # initialise search_results
        search_results = []

        # initialise results_dict
        results_dict = {}

        # initialise yield_record
        yield_record = {}

        # range category dict (by entity key)
        range_category_dict = {}
        # counters
        count_entities_processed = 0
        count_entities_failed = 0

        # delayed_inspector_search
        delayed_inspector_search = f"""
            | trackmegetcoll tenant_id={self.tenant_id} component={self.component}
            ``` root constraints: filter on enabled entities, and entities that have been managed by the health tracker within at least the 15 minutes ```
            | where monitored_state=="enabled" AND tracker_health_runtime>=(now()-900)
            ``` filter on positive data_last_lag_seen ```
            | where data_last_lag_seen > 0
            ``` lookup against the delayed inspector KV collection ```
            | lookup trackme_{self.component}_delayed_entities_inspector_tenant_{self.tenant_id} _key as _key OUTPUT mtime as inspector_mtime, inspector_error_counters, inspector_backoff_multiplier
            | eval inspector_mtime=if(isnull(inspector_mtime), 0, inspector_mtime), inspector_error_counters=if(isnull(inspector_error_counters), 0, inspector_error_counters), inspector_backoff_multiplier=if(isnull(inspector_backoff_multiplier), 1, inspector_backoff_multiplier)
            ``` calculate the time spent since the last inspection ```
            | eval time_since_last_inspection=if(inspector_mtime == 0, 0, now()-inspector_mtime)
            ``` round time_since_last_inspection ```
            | eval time_since_last_inspection=round(time_since_last_inspection, 0)
            ``` do not proceed if the inspector_error_counters is greater than {self.max_errors_count_per_entity_search}, this means we allow up to {self.max_errors_count_per_entity_search} attempts to run the search ```
            | where inspector_error_counters <= {self.max_errors_count_per_entity_search}
            ``` round data_last_lag_seen ```
            | eval data_last_lag_seen=round(data_last_lag_seen, 0)
            ``` table fields needed for the delayed inspector ```
            | table _key, object, alias, inspector_mtime, inspector_error_counters, inspector_backoff_multiplier, time_since_last_inspection, data_last_lag_seen
            ``` sort by the older inspector_mtime ```
            | sort - inspector_mtime
        """

        # if object_name is set, add a constraint to the search
        if self.object_name:
            delayed_inspector_search += f"""
                | search object="{self.object_name}"
            """

        # delayed inspector KV collection
        delayed_inspector_collection_name = f"kv_trackme_{self.component}_delayed_entities_inspector_tenant_{self.tenant_id}"

        # connect to the delayed inspector KV collection
        delayed_inspector_collection = self.service.kvstore[
            delayed_inspector_collection_name
        ]

        # report name for logging purposes
        report_name = f"trackme_{self.component}_delayed_entities_inspector_tracker_tenant_{self.tenant_id}"

        # max runtime
        max_runtime = int(self.max_runtime)

        # Retrieve the search cron schedule
        savedsearch = self.service.saved_searches[report_name]
        savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

        # get the cron_exec_sequence_sec
        try:
            cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
        except Exception as e:
            logging.error(
                f'tenant_id="{self.tenant_id}", component="{self.component}", failed to convert the cron schedule to seconds, error="{str(e)}"'
            )
            cron_exec_sequence_sec = max_runtime

        # the max_runtime cannot be bigger than the cron_exec_sequence_sec
        if max_runtime > cron_exec_sequence_sec:
            max_runtime = cron_exec_sequence_sec

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime="{max_runtime}",  savedsearch_name="{report_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
        )

        #
        # main processing
        #

        try:
            reader = run_splunk_search(
                self.service,
                delayed_inspector_search,
                {
                    "earliest_time": "-5m",
                    "latest_time": "now",
                    "count": 0,
                    "output_mode": "json",
                },
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    logging.debug(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", search_results="{item}"'
                    )
                    # append to the list of searches
                    search_results.append(item)

                    # get entity_key
                    entity_key = item["_key"]

                    # add to the dict by _key
                    results_dict[entity_key] = item

                    # get range category
                    range_category, entity_search_earliest_time, span_value = (
                        self.get_range_category(
                            int(item["data_last_lag_seen"]),
                            str(splk_feeds_auto_disablement_period),
                        )
                    )

                    # add to the range category dict
                    range_category_dict[entity_key] = {
                        "range_category": range_category,
                        "entity_search_earliest_time": entity_search_earliest_time,
                        "span_value": span_value,
                    }

        except Exception as e:
            logging.error(
                f'tenant_id="{self.tenant_id}", component="{self.component}", An exception was encountered, exception="{str(e)}"'
            )
            yield_record = {
                "_time": time.time(),
                "action": "failure",
                "search": delayed_inspector_search,
                "response": f'The entity providing delayed inspector search failed to be executed, exception="{str(e)}"',
                "_raw": {
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "action": "failure",
                    "response": "The entity providing delayed inspector search failed to be executed",
                    "exception": str(e),
                },
            }

            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                report_name,
                "failure",
                time.time(),
                str(time.time() - start),
                f'The entity providing delayed inspector search failed to be executed, exception="{str(e)}"',
                "-5m",
                "now",
            )

            # yield the record
            yield yield_record

            # raise an exception
            raise Exception(
                f'The entity providing delayed inspector search failed to be executed, exception="{str(e)}"'
            )

        #
        # Step 1: Collect eligible entities
        #

        eligible_entities = {}

        for key, value in results_dict.items():

            object_value = results_dict[key]["object"]

            # get the range category for this particular entity
            range_category = range_category_dict[key]["range_category"]

            # get the backoff multiplier for this entity, clamped to [1, max_backoff_multiplier]
            entity_backoff_multiplier = max(
                1,
                min(
                    int(float(results_dict[key].get("inspector_backoff_multiplier", 1))),
                    max_backoff_multiplier,
                ),
            )

            # set the boolean depending on the range category and the last inspection time
            proceed_entity_bool, proceed_entity_reason = (
                self.define_proceed_entity_bool(
                    range_category,
                    int(results_dict[key]["time_since_last_inspection"]),
                    splk_feeds_delayed_inspector_24hours_range_min_sec,
                    splk_feeds_delayed_inspector_7days_range_min_sec,
                    splk_feeds_delayed_inspector_until_disabled_range_min_sec,
                    backoff_multiplier=entity_backoff_multiplier,
                )
            )

            if not proceed_entity_bool:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", proceed_entity_bool="{proceed_entity_bool}", proceed_entity_reason="{proceed_entity_reason}", range_category="{range_category}", backoff_multiplier={entity_backoff_multiplier}, the conditions for this entity to be proceeded were not met'
                )
                continue

            eligible_entities[key] = {
                "object": object_value,
                "range_category": range_category,
                "entity_search_earliest_time": range_category_dict[key]["entity_search_earliest_time"],
                "span_value": range_category_dict[key]["span_value"],
                "backoff_multiplier": entity_backoff_multiplier,
            }

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", eligible_entities_count={len(eligible_entities)}, total_entities_count={len(results_dict)}'
        )

        if not eligible_entities:
            run_time = round(time.time() - start, 3)
            yield {
                "_time": time.time(),
                "_raw": {
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "search": delayed_inspector_search,
                    "result": "there were no entities to process at this time.",
                    "count_entities_processed": 0,
                    "count_entities_failed": 0,
                    "run_time": run_time,
                },
                "run_time": run_time,
            }
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", there were no entities to process at this time'
            )

            trackme_register_tenant_object_summary(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
                self.tenant_id,
                f"splk-{self.component}",
                report_name,
                "success",
                time.time(),
                str(time.time() - start),
                "The report was executed successfully",
                "-5m",
                "now",
            )

            # Log the run time
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", trackmesplkfeedsdelayedinspector has terminated, run_time={round(time.time() - start, 3)}, count_entities_processed="0", count_entities_failed="0"'
            )
            return

        #
        # Step 2: Fetch entity_info for all eligible entities
        #

        entity_info_dict = {}
        component_url = {
            "dsm": "/services/trackme/v2/splk_dsm/ds_entity_info",
            "dhm": "/services/trackme/v2/splk_dhm/dh_entity_info",
        }

        for key in list(eligible_entities.keys()):
            # timeout guard
            if (time.time() - start) >= max_runtime - 30:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime approaching during entity_info fetch, stopping'
                )
                break

            object_value = eligible_entities[key]["object"]

            try:
                json_data = {
                    "tenant_id": self.tenant_id,
                    "object": object_value,
                }

                target_url = f"{self._metadata.searchinfo.splunkd_uri}{component_url[self.component]}"
                response = requests.post(
                    target_url,
                    headers={
                        "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                        "Content-Type": "application/json",
                    },
                    verify=False,
                    timeout=600,
                    data=json.dumps(json_data),
                )

                entity_info = json.loads(response.text)
                logging.debug(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", entity_info retrieved'
                )

                # DSM: skip elastic sources
                if self.component == "dsm" and entity_info.get("is_elastic") == 1:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", is_elastic=1, skipping'
                    )
                    del eligible_entities[key]
                    continue

                entity_info_dict[key] = entity_info

            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", could not retrieve entity info, exception="{str(e)}"'
                )
                # remove from eligible since we can't generate a search without entity_info
                del eligible_entities[key]

        #
        # Step 3: Group entities for batching by (account, search_mode, breakby_key, range_category)
        #

        batch_groups = defaultdict(list)
        for key in eligible_entities:
            if key not in entity_info_dict:
                continue

            info = entity_info_dict[key]
            group_key = (
                info.get("account", "local"),
                info.get("search_mode", "tstats"),
                info.get("breakby_key", "none") or "none",
                eligible_entities[key]["range_category"],
            )
            batch_groups[group_key].append(key)

        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", batch_groups_count={len(batch_groups)}, groups={[(k, len(v)) for k, v in batch_groups.items()]}'
        )

        #
        # Step 4: Process each batch group
        #

        for group_key, group_entity_keys in batch_groups.items():
            account, search_mode, breakby_key, range_category = group_key

            # timeout guard
            if (time.time() - start) >= max_runtime - 30:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime approaching, stopping batch processing'
                )
                break

            # Get range params from the first entity (all share the same range_category)
            first_key = group_entity_keys[0]
            entity_search_earliest_time = eligible_entities[first_key]["entity_search_earliest_time"]
            span_value = eligible_entities[first_key]["span_value"]

            # Split into sub-batches of MAX_BATCH_SIZE
            for batch_start in range(0, len(group_entity_keys), MAX_BATCH_SIZE):
                batch_keys = group_entity_keys[batch_start:batch_start + MAX_BATCH_SIZE]

                # timeout guard
                if (time.time() - start) >= max_runtime - 30:
                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", max_runtime approaching, stopping sub-batch processing'
                    )
                    break

                batch_start_time = time.time()

                # Combine root_constraints with OR, wrapped in outer parentheses
                # to prevent Splunk AND precedence from applying host/other filters
                # only to the first constraint
                combined_constraint = "( " + " OR ".join(
                    f"( {entity_info_dict[key]['search_constraint']} )"
                    for key in batch_keys
                ) + " )"

                # Use the first entity's info as template (all share account, search_mode, breakby_key)
                template_info = entity_info_dict[batch_keys[0]]

                # Generate the batched search
                batched_search = None
                if self.component == "dsm":
                    batched_search = generate_dsm_report_search(
                        entity_info=template_info,
                        search_mode=search_mode,
                        tenant_id=self.tenant_id,
                        root_constraint=combined_constraint,
                        index_earliest_time=entity_search_earliest_time,
                        index_latest_time="now",
                        dsm_tstats_root_time_span=span_value,
                        breakby_field=breakby_key,
                        account=account,
                        earliest_time=entity_search_earliest_time,
                        latest_time="now",
                        dsm_tstats_root_breakby_include_splunk_server=False,
                        dsm_tstats_root_breakby_include_host=False,
                    )
                elif self.component == "dhm":
                    batched_search = generate_dhm_report_search(
                        entity_info=template_info,
                        search_mode=search_mode,
                        tenant_id=self.tenant_id,
                        root_constraint=combined_constraint,
                        index_earliest_time=entity_search_earliest_time,
                        index_latest_time="now",
                        dhm_tstats_root_time_span=span_value,
                        breakby_field=breakby_key,
                        account=account,
                        earliest_time=entity_search_earliest_time,
                        latest_time="now",
                        dhm_tstats_root_breakby_include_splunk_server=False,
                    )

                if not batched_search:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", could not generate batched search for group={group_key}'
                    )
                    continue

                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", executing batched search for {len(batch_keys)} entities, group={group_key}'
                )

                # Execute the batched search
                batch_search_results = []
                batch_search_failed = False
                batch_search_failed_reason = None

                try:
                    reader = run_splunk_search(
                        self.service,
                        batched_search,
                        {
                            "earliest_time": entity_search_earliest_time,
                            "latest_time": "now",
                            "count": 0,
                            "output_mode": "json",
                        },
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            logging.debug(f'batched_search_result="{item}"')
                            batch_search_results.append(item)

                    logging.info(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", batched search executed in {round(time.time() - batch_start_time, 3)} seconds, result_count={len(batch_search_results)}'
                    )

                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", batched search failed, exception="{str(e)}"'
                    )
                    batch_search_failed = True
                    batch_search_failed_reason = str(e)

                # Extract entity keys that appeared in search results
                # The search results contain the entity key field which is constructed by the abstract macro
                entity_keys_with_data = set()
                if not batch_search_failed:
                    for result in batch_search_results:
                        # The result contains a "key" field (entity key) set by the tracker pipeline
                        result_key = result.get("key")
                        if result_key:
                            entity_keys_with_data.add(result_key)

                # Process each entity in the batch
                for key in batch_keys:
                    object_value = eligible_entities[key]["object"]

                    # get the delayed inspector record
                    delayed_inspector_record = self.get_delayed_inspector_record(
                        delayed_inspector_collection, key
                    )

                    # get exec and error counters
                    exec_counters = int(
                        delayed_inspector_record.get("inspector_exec_counters", 0)
                    )
                    error_counters = int(
                        delayed_inspector_record.get("inspector_error_counters", 0)
                    )

                    # Read previous backoff state
                    prev_consecutive_no_data = int(
                        float(
                            delayed_inspector_record.get(
                                "inspector_consecutive_no_data_count", 0
                            )
                        )
                    ) if delayed_inspector_record else 0

                    if batch_search_failed:
                        # On batch failure, increment error counters, preserve backoff state
                        error_counters += 1
                        count_entities_failed += 1
                        new_consecutive_no_data = prev_consecutive_no_data
                        new_backoff_multiplier = max(
                            1,
                            min(
                                int(float(delayed_inspector_record.get("inspector_backoff_multiplier", 1))) if delayed_inspector_record else 1,
                                max_backoff_multiplier,
                            ),
                        )
                        entity_has_data = False

                        entity_search_summary_record = {
                            "_key": key,
                            "mtime": time.time(),
                            "object": object_value,
                            "inspector_exec_counters": exec_counters,
                            "inspector_error_counters": error_counters,
                            "inspector_last_error": batch_search_failed_reason,
                            "inspector_last_status": "failed",
                            "inspector_consecutive_no_data_count": new_consecutive_no_data,
                            "inspector_last_data_found": int(
                                float(
                                    delayed_inspector_record.get("inspector_last_data_found", 1)
                                )
                            ) if delayed_inspector_record else 1,
                            "inspector_backoff_multiplier": new_backoff_multiplier,
                        }

                    else:
                        # Determine if this entity had data
                        entity_has_data = key in entity_keys_with_data

                        # Update backoff state
                        if entity_has_data:
                            new_consecutive_no_data = 0
                            new_backoff_multiplier = 1
                        else:
                            new_consecutive_no_data = prev_consecutive_no_data + 1
                            new_backoff_multiplier = min(
                                new_consecutive_no_data + 1, max_backoff_multiplier
                            )

                        exec_counters += 1

                        entity_search_summary_record = {
                            "_key": key,
                            "mtime": time.time(),
                            "object": object_value,
                            "inspector_exec_counters": exec_counters,
                            "inspector_error_counters": error_counters,
                            "inspector_last_error": None,
                            "inspector_last_status": "success",
                            "inspector_consecutive_no_data_count": new_consecutive_no_data,
                            "inspector_last_data_found": 1 if entity_has_data else 0,
                            "inspector_backoff_multiplier": new_backoff_multiplier,
                        }

                    count_entities_processed += 1

                    # KVstore insert/update
                    if not delayed_inspector_record:
                        try:
                            delayed_inspector_collection.data.insert(
                                json.dumps(entity_search_summary_record),
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", could not insert delayed inspector record, exception="{e}"'
                            )
                    else:
                        try:
                            delayed_inspector_collection.data.update(
                                key,
                                json.dumps(entity_search_summary_record),
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", could not update delayed inspector record, exception="{e}"'
                            )

                    # notification event
                    try:
                        trackme_handler_events(
                            session_key=self._metadata.searchinfo.session_key,
                            splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                            tenant_id=self.tenant_id,
                            sourcetype="trackme:handler",
                            source=f"trackme:handler:{self.tenant_id}",
                            handler_events=[
                                {
                                    "object": object_value,
                                    "object_id": key,
                                    "object_category": f"splk-{self.component}",
                                    "handler": "delayed_inspector",
                                    "key": key,
                                    "handler_message": f"Entity was inspected by the delayed inspector (range={range_category}, has_data={entity_has_data}, consecutive_no_data={new_consecutive_no_data}, backoff_multiplier={new_backoff_multiplier}, batch_size={len(batch_keys)}). It is out of the scope of any hybrid tracker due to high delay and/or latency. The delay inspector performs regular backward searches to refresh the entity status and up to date knowledge.",
                                    "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackme:custom_commands:trackmesplkfeedsdelayedinspector tenant_id={self.tenant_id} component={self.component} object={object_value}",
                                    "handler_time": time.time(),
                                }
                            ],
                        )
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", object="{object_value}", key="{key}", could not send notification event, exception="{e}"'
                        )

                    # yield record for each entity
                    yield {
                        "_time": time.time(),
                        "_raw": results_dict[key],
                        "entity_has_delayed_record": bool(delayed_inspector_record),
                        "keyid": key,
                        "object": results_dict[key]["object"],
                        "alias": results_dict[key]["alias"],
                        "entity_has_data": entity_has_data,
                        "inspector_consecutive_no_data_count": new_consecutive_no_data,
                        "inspector_backoff_multiplier": new_backoff_multiplier,
                        "entity_search_failed": batch_search_failed,
                        "entity_search_failed_reason": batch_search_failed_reason,
                        "proceed_entity_bool": True,
                        "range_category": range_category,
                        "batch_size": len(batch_keys),
                        "last_inspection_time": int(
                            results_dict[key]["time_since_last_inspection"]
                        ),
                        "delayed_inspector_message": f"The entity was inspected as part of a batch of {len(batch_keys)} entities.",
                    }

        # if no entities were processed, yield a record
        if count_entities_processed == 0:
            run_time = round(time.time() - start, 3)
            yield {
                "_time": time.time(),
                "_raw": {
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "search": delayed_inspector_search,
                    "result": "there were no entities to process at this time.",
                    "count_entities_processed": count_entities_processed,
                    "count_entities_failed": count_entities_failed,
                    "run_time": run_time,
                },
                "run_time": run_time,
            }
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", there were no entities to process at this time, count_entities_processed="{count_entities_processed}", count_entities_failed="{count_entities_failed}"'
            )

        # yield a final summary record with run_time when entities were processed
        if count_entities_processed > 0:
            run_time = round(time.time() - start, 3)
            yield {
                "_time": time.time(),
                "_raw": {
                    "tenant_id": self.tenant_id,
                    "component": self.component,
                    "search": delayed_inspector_search,
                    "result": "delayed inspector processing completed.",
                    "count_entities_processed": count_entities_processed,
                    "count_entities_failed": count_entities_failed,
                    "run_time": run_time,
                },
                "run_time": run_time,
            }

        trackme_register_tenant_object_summary(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
            f"splk-{self.component}",
            report_name,
            "success",
            time.time(),
            str(time.time() - start),
            "The report was executed successfully",
            "-5m",
            "now",
        )

        #
        # End processing
        #

        # Log the run time
        logging.info(
            f'tenant_id="{self.tenant_id}", component="{self.component}", trackmesplkfeedsdelayedinspector has terminated, run_time={round(time.time() - start, 3)}, count_entities_processed="{count_entities_processed}", count_entities_failed="{count_entities_failed}"'
        )


dispatch(TrackMeFeedsDelayedInspector, sys.argv, sys.stdin, sys.stdout, __name__)
