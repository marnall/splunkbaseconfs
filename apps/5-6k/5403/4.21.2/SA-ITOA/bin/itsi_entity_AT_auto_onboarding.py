# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import logging
import math
import sys

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib"]))
sys.path.append(make_splunkhome_path(["etc", "apps", "SA-ITOA", "lib", "SA_ITOA_app_common"]))

from ITOA.itoa_common import is_feature_enabled, modular_input_should_run, post_splunk_user_message, wait_for_job
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.splunklib import results
from SA_ITOA_app_common.splunklib.binding import HTTPError
from at_utils.utils import generate_ml_entity_at_scout_search, generate_ml_entity_at_search
from itsi.itsi_utils import ITOAInterfaceUtils, SplunkMessageHandler
from itsi.objects.itsi_entity import ItsiEntity
from itsi.objects.itsi_kpi_entity_threshold import ItsiKpiEntityThreshold
from itsi.objects.itsi_service import ItsiService
from itsi.searches import itsi_filter
import itsi_path


class ItsiEntityATAutoOnboarding(ModularInput):
    """
    Modular input that handles entity-level AT regular background processes
    """

    title = "IT Service Intelligence Entity-Level Adaptive Thresholding Auto-Onboarding"
    description = "Onboards new entities onto KPIs with entity-level AT enabled."
    handlers = None
    logger = None
    app = "SA-ITOA"
    name = "itsi_entity_AT_auto_onboarding"
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def extra_arguments(self):
        return [
            {
                "name": "log_level",
                "title": "Logging Level",
                "description": "This is the level at which the modular input will log data."
            }
        ]

    @staticmethod
    def _compute_required_days_from_window(window_str, default_days=7):
        """
        Compute the minimum whole days to require based on a relative earliest_time window string
        like '-7d'. Falls back to default_days if unparseable or missing.
        """
        if isinstance(window_str, str) and window_str.startswith("-") and window_str.endswith("d"):
            try:
                days = int(window_str[1:-1])
                return max(1, days)
            except (ValueError, TypeError):
                # Fallback to default if parsing fails
                pass
        return default_days

    def run_recommendation_search(self, search_service, kpi_object, entities):
        """
        Run search to generate recommendation for a KPI and a set of entities

        :param search_service: Search service to run searches with
        :type search_service: splunklib.client.Service

        :param kpi_object: KPI to generate recommendation from
        :type kpi_object: dict

        :param entities: Entities in a compressed format (key:title) for referencing
        :type entities: set of string
        """
        if not entities:
            return

        # Ensure data is present in the oldest day before running ML
        data_search = generate_ml_entity_at_scout_search([{
            "entity_key": entity_str.split(":", 1)[0],
            "entity_title": entity_str.split(":", 1)[1],
            "kpi_id": kpi_object["_key"],
        } for entity_str in entities])
        search_job = search_service.jobs.create(
            data_search, earliest_time=kpi_object.get("entity_recommendation_training_window"),
            latest_time=kpi_object.get("entity_recommendation_training_window") + "+1d",
        )
        wait_for_job(search_job)
        search_results = results.JSONResultsReader(search_job.results(output_mode="json"))
        found_entities = set()
        for search_result in search_results:
            if isinstance(search_result, dict) and "entity_key" in search_result and "entity_title" in search_result:
                found_entities.add("%s:%s" % (search_result["entity_key"], search_result["entity_title"]))

        # Notify which entities will not be used
        missing_entities = entities - found_entities
        for entity in missing_entities:
            self.logger.info("Skipping recommendation generation for KPI ({0}), entity ({1})".format(
                kpi_object["_key"], entity))

        # Skip retirable or retired entities
        entity_interface = ItsiEntity(self.session_key, "nobody")
        retiring_entities = entity_interface.get_bulk(
            "nobody", filter_data={"$or": [{"retirable": 1}, {"retired": 1}]}, fields=["_key", "title"],
        )
        retiring_entities_set = set()
        for entity in retiring_entities:
            retiring_entities_set.add("%s:%s" % (entity["_key"], entity["title"]))
        net_entities = found_entities - retiring_entities_set

        # Run ML search to generate recommendations
        at_search = generate_ml_entity_at_search([{
            "entity_key": entity_str.split(":", 1)[0],
            "entity_title": entity_str.split(":", 1)[1],
            "kpi_id": kpi_object["_key"],
        } for entity_str in net_entities], kpi_object)
        search_job = search_service.jobs.create(
            at_search, earliest_time=kpi_object.get("entity_recommendation_training_window"),
        )
        wait_for_job(search_job)
        results.JSONResultsReader(search_job.results(output_mode="json"))

    @skip_run_during_migration
    def do_run(self, stanzas):
        """
        This is the method called by splunkd when mod input is enabled.
        @param stanzas: config stanzas passed down by splunkd
        """
        self.logger = getLogger4ModInput(stanzas)
        if not is_feature_enabled("itsi-high-scale-at", self.session_key) or \
                not is_feature_enabled("itsi-entity-level-adaptive-thresholding", self.session_key):
            self.logger.info(f"Due to feature flags, modular input ({self.title}) will not run.")
            return

        if not modular_input_should_run(self.session_key, logger=self.logger):
            self.logger.info("Modular input will not run on this node.")
            return

        # Single instance mode for safety only, so we only want the first stanza
        stanza_config = next(iter(stanzas.values()))
        self.log_level = stanza_config.get("log_level", "INFO").upper()
        if self.log_level not in ["ERROR", "WARN", "WARNING", "INFO", "DEBUG"]:
            self.log_level = "INFO"

        self.logger.setLevel(logging.getLevelName(self.log_level))

        input_job = self.config_name.split("://")[1]
        try:
            if input_job == "auto_onboarding":
                self.run_onboarding()
            elif input_job == "auto_deboarding":
                self.run_deboarding()
            else:
                self.logger.error("Unknown input job type for itsi_entity_AT_auto_onboarding")
        except HTTPError as e:
            self.logger.error(e)
            raise Exception(f"Error when running modular input: {self.config_name}. Error: {e}")
        self.logger.debug("Exiting modular input.")

    def run_onboarding(self):
        """
        Run AT onboarding for KPIs on entities
        """

        search_connection = ITOAInterfaceUtils.service_connection(self.session_key, app_name="SA-ITOA")
        service_interface = ItsiService(self.session_key, "nobody")
        threshold_interface = ItsiKpiEntityThreshold(self.session_key, "nobody")

        onboarding_services = service_interface.get_bulk(
            "nobody", filter_data={"enabled": 1, "kpis.onboarding_new_entities_enabled": True},
        )

        for service in onboarding_services:
            # This only matters if a KPI has an entity split, but that information isn't at the service level (depth
            # 0)
            is_entity_filter_calculated = False
            for kpi in service["kpis"]:
                if kpi.get("onboarding_new_entities_enabled") and kpi["is_entity_breakdown"]:
                    # Entity split
                    if kpi["is_service_entity_filter"]:
                        if not is_entity_filter_calculated:
                            new_entity_filter_set = set()

                            service_entity_filter = service["entity_rules"]
                            entity_filter = itsi_filter.ItsiFilter(service_entity_filter)
                            entities = entity_filter.get_filtered_objects(self.session_key, "nobody")
                            for entity in entities:
                                new_entity_filter_set.add("%s:%s" % (entity["_key"], entity["title"]))
                            is_entity_filter_calculated = True

                        existing_thresholds = threshold_interface.get_bulk(
                            "nobody", filter_data={"service_id": service["_key"], "kpi_id": kpi["_key"]},
                        )
                        old_entity_set = set()
                        for threshold in existing_thresholds:
                            old_entity_set.add("%s:%s" % (threshold["entity_key"], threshold["entity_title"]))
                        unthresholded_entities = new_entity_filter_set - old_entity_set
                        self.run_recommendation_search(search_connection, kpi, unthresholded_entities)

                    # Pseudo-entity split (bounded to training window and requiring daily coverage)
                    training_window = kpi.get("entity_recommendation_training_window", "-7d")
                    required_days = self._compute_required_days_from_window(training_window, default_days=7)

                    # Build a daily-bucketed SPL that requires at least one datapoint per day
                    pseudo_entity_daily_spl = (
                        "| mstats count(alert_value) AS cnt WHERE `get_itsi_summary_metrics_index` "
                        "AND is_filled_gap_event!=1 AND is_null_alert_value=0 `metrics_entity_level_kpi_only` "
                        f"AND itsi_kpi_id={kpi['_key']} BY itsi_kpi_id, itsi_service_id, entity_key, entity_title span=1d "
                        "| where cnt > 0 "
                        "| stats count AS days_with_data by itsi_kpi_id, itsi_service_id, entity_key, entity_title "
                        f"| where days_with_data >= {required_days} "
                        "| sort 0 -days_with_data, entity_key, entity_title "
                        "| table itsi_kpi_id, itsi_service_id, entity_key, entity_title, days_with_data"
                    )

                    search_job = search_connection.jobs.create(
                        pseudo_entity_daily_spl,
                        earliest_time=training_window,
                        latest_time="now",
                    )
                    wait_for_job(search_job)
                    reader = results.JSONResultsReader(search_job.results(output_mode="json"))
                    new_entity_set = set()
                    for result in reader:
                        if isinstance(result, dict) and "entity_key" in result and "entity_title" in result:
                            new_entity_set.add("%s:%s" % (result["entity_key"], result["entity_title"]))
                    existing_thresholds = threshold_interface.get_bulk(
                        "nobody", filter_data={"service_id": service["_key"], "kpi_id": kpi["_key"]},
                    )
                    old_entity_set = set()
                    for threshold in existing_thresholds:
                        old_entity_set.add("%s:%s" % (threshold["entity_key"], threshold["entity_title"]))
                    unthresholded_entities = new_entity_set - old_entity_set
                    self.run_recommendation_search(search_connection, kpi, unthresholded_entities)

    def run_deboarding(self):
        """
        Remove defunct thresholds based on two conditions:
            * Pseudo-entity has not contributed data in 14 days
            * Real entity is retirable or retired
        """
        def threshold_to_id(threshold_obj):
            """
            Helper function for creating a reference-able ID from a threshold

            :param threshold_obj: ItsiKpiEntityThreshold object
            :type threshold_obj: dict

            :return: Colon-separated ID (note that KVStore keys won't have colons)
            :rtype: string
            """
            return "%s:%s:%s:%s" % (threshold_obj["service_id"], threshold_obj["kpi_id"], threshold_obj["entity_key"],
                                    threshold_obj["entity_title"])

        def result_to_id(result):
            """
            Helper function for creating a reference-able ID from a search result

            :param result: Splunk search result
            :type result: dict

            :return: Colon-separated ID (note that KVStore keys won't have colons)
            :rtype: string
            """
            return "%s:%s:%s:%s" % (result["itsi_service_id"], result["itsi_kpi_id"], result["entity_key"],
                                    result["entity_title"])

        entity_interface = ItsiEntity(self.session_key, "nobody")
        threshold_interface = ItsiKpiEntityThreshold(self.session_key, "nobody")
        search_connection = ITOAInterfaceUtils.service_connection(self.session_key, app_name="SA-ITOA")
        total_thresholds = set()
        thresholds_to_keep = set()

        # "Retired" pseudo-entities
        possible_thresholds = threshold_interface.get_bulk("nobody", filter_data={"entity_key": "N/A"})
        possible_thresholds_by_kpi = {}
        thresholds_by_id = {}
        for threshold in possible_thresholds:
            if not possible_thresholds_by_kpi.get(threshold["kpi_id"]):
                possible_thresholds_by_kpi[threshold["kpi_id"]] = []
            possible_thresholds_by_kpi[threshold["kpi_id"]].append(threshold)
            threshold_id = threshold_to_id(threshold)
            if not thresholds_by_id.get(threshold_id):
                thresholds_by_id[threshold_id] = []
            thresholds_by_id[threshold_id].append(threshold["_key"])
            total_thresholds.add(threshold_id)

        for kpi_key in possible_thresholds_by_kpi.keys():
            # Find pseudo-entities with any data points in the last 14 days to keep their thresholds
            active_pseudo_entity_spl = (
                "| mstats count(alert_value) AS event_cnt WHERE `get_itsi_summary_metrics_index` "
                "AND is_filled_gap_event!=1 AND is_null_alert_value=0 `metrics_entity_level_kpi_only` "
                f"AND itsi_kpi_id={kpi_key} AND entity_key=\"N/A\" BY itsi_kpi_id, itsi_service_id, entity_key, entity_title "
                "| where event_cnt > 0"
            )
            search_job = search_connection.jobs.create(active_pseudo_entity_spl, earliest_time="-14d", latest_time="now")
            wait_for_job(search_job)
            search_results = results.JSONResultsReader(search_job.results(output_mode="json"))

            for result in search_results:
                if isinstance(result, dict) and "itsi_service_id" in result and "itsi_kpi_id" in result and "entity_key" in result and "entity_title" in result:
                    thresholds_to_keep.add(result_to_id(result))

        thresholds_to_remove = total_thresholds - thresholds_to_keep
        keys_to_remove = []
        for threshold_id in thresholds_to_remove:
            keys_to_remove.extend(thresholds_by_id[threshold_id])

        # Retired entities
        possible_thresholds = threshold_interface.get_bulk("nobody", filter_data={"entity_key": {"$ne": "N/A"}})
        retired_entities = entity_interface.get_bulk("nobody", filter_data={"$or": [{"retirable": 1}, {"retired": 1}]},
                                                     fields=["_key"])
        retired_entities_set = set([entity["_key"] for entity in retired_entities])

        if retired_entities_set:
            for threshold in possible_thresholds:
                if threshold["entity_key"] in retired_entities_set:
                    keys_to_remove.append(threshold["_key"])

        # Delete thresholds
        for i in range(0, len(keys_to_remove), 100):
            batched_filter = {"$or": [{"_key": key} for key in keys_to_remove[i:i + 100]]}
            self.logger.info("Deleting thresholds: %s" % keys_to_remove[i:i + 100])
            threshold_interface.delete_bulk("nobody", filter_data=batched_filter)
            self.logger.info("Deleted thresholds: %s" % keys_to_remove[i:i + 100])

        messages = SplunkMessageHandler(self.session_key)
        message_text = "{0} deleted {1} unused entity adaptive threshold(s)".format(self.name,
                                                                                    len(keys_to_remove))
        self.logger.info(message_text)
        if len(keys_to_remove):
            messages.post_or_update_message(self.name, SplunkMessageHandler.INFO, message_text, role="itoa_admin")


if __name__ == "__main__":
    worker = ItsiEntityATAutoOnboarding()
    worker.execute()
    sys.exit(0)
