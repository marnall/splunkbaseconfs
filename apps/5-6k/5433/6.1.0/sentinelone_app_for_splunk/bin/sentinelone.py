"""
sentinelone.py ;; 2023-05-1
Written by ksmith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import logging as logger
import sys
import os
import time
import json
import re
import multiprocessing.dummy as mp
import uuid

from Utilities import KennyLoggins, Utilities
from s1_client import S1ModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.util import normalizeBoolean
from s1_app_properties import __app_name__
from datetime import datetime, timezone
import s1_paths
# These libraries require _paths import
from flatten_json import flatten, unflatten_list

__author__ = 'ksmith'
_MI__app_name__ = 'SentinelOne Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
kl = KennyLoggins()
log = kl.get_logger(__app_name__, "sentinelone-core-modularinput", logger.INFO)
force_log_creation = kl.get_logger(__app_name__, "mgmt_sdk", logger.INFO)
force_log_creation.info("action=forcing_line_due_to_mgmt_sdk")
run_id = '{}'.format(str(uuid.uuid4()))
last_reload_chkpnt_name = "sentinelone-input-health-check-last-reload.json"
reload_time_difference_in_hrs = 25


# This line is only here to make it exist since the s1 sdk doesn't do that. It makes the assumption it exists.


class S1BaseModularInput(S1ModularInput):
    def __init__(self, **kwargs):
        S1ModularInput.__init__(self, **kwargs)

    def _get_threats(self, start, next_page):
        self.log.debug("start={}, next_page={}".format(start, next_page))
        try:
            return self._paginate(
                self.s1_mgmt.threats.get,
                next_page=next_page,
                time_field="threats",
                updatedAt__gte=start,
            )
        except Exception as e:
            self._catch_error(e)

    def _get_groups(self):
        try:
            return self._paginate(self.s1_mgmt.groups.get, time_field="updatedAt")
        except Exception as e:
            self._catch_error(e)

    def _get_applications(self, start):
        try:
            if self.enabled_features.get("appManagement", False):
                self.log.debug(
                    f"action=upgraded_applications_routine appManagement=true start={start}"
                )
                # Uncomment the following line if enabling the "inventory" call below
                # self.sourcetype("sentinelone:channel:application_management:inventory")
                # Call Sleep is in Seconds to wait between calls to the endpoint.
                return self._paginate(
                    self.s1_mgmt.applications.get, time_field="updatedAt",
                    # This is *all* the applications, but not by agent.
                    # self.s1_mgmt.application_management.inventory, time_field="timestamp",
                    call_sleep=1,
                )
            else:
                self.log.warning(
                    "action=legacy_applications_routine appManagement=false "
                    'message="Please contact SentinelOne Support to be migrated"'
                )
                return self._paginate(
                    self.s1_mgmt.applications.get, time_field="updatedAt"
                )
        except Exception as e:
            self._catch_error(e)

    def _get_application_risks(self, start):
        try:
            if self.enabled_features.get("appManagement", False):
                self.log.debug(
                    f"action=upgraded_applications_routine appManagement=true start={start}"
                )
                self.sourcetype("sentinelone:channel:application_management:risks")
                # Call Sleep is in Seconds to wait between calls to the endpoint.
                return self._paginate(
                    self.s1_mgmt.application_management.get,
                    time_field="riskUpdatedAt",
                    call_sleep=1,
                    riskUpdatedDate__gte=start,
                    includeRemovals=True,
                )
            else:
                self.log.warning(
                    "action=legacy_applications_routine appManagement=false "
                    'message="Please use the Applications input, and check the CVE box."'
                )
                return 0, None
        except Exception as e:
            self._catch_error(e)

    def _get_agents(self):
        try:
            return self._paginate(self.s1_mgmt.agents.get, time_field="updatedAt")
        except Exception as e:
            self._catch_error(e)

    def _get_activities(self, start, next_page):
        try:
            return self._paginate(
                self.s1_mgmt.activities.get,
                next_page=next_page,
                time_field="updatedAt",
                createdAt__gte=start,
            )
        except Exception as e:
            self._catch_error(e)

    def _create_result_field_dict(self, event):
        #
        # Create a dictionary with fields that need to be added to the final event
        #
        flattened_result = []
        # REMOVE / COMMENT /  DELETE THIS TWO LINES BEFORE PRODUCTION
        # if "network_interfaces" not in v[1]:
        #     v[1]["network_interfaces"] = [{"physical": "PHYSICALLYFIT","somethingelse": "first"}, {"somethingelse": "darkside"}]
        field_map_dict = flatten(event, self.flatten_sep)
        self.log.debug(
            "action=process_field_options field_map_dict={} k={}".format(
                field_map_dict, event
            )
        )
        flattened_result_tuple = (event, field_map_dict)
        flattened_result.append(flattened_result_tuple)
        return flattened_result
    
    def _get_uam_alerts(self, start, next_page):
        self.log.debug(f"action=get_uam_alerts start={start} next_page={next_page}")
        try:
            view_type = self.get_config('view_types', '')
            
            return self._paginate(
                self.s1_mgmt.uam_alerts.get,
                next_page=next_page,
                time_field="updatedAt",
                updatedAt__gte=start,
                view_type=view_type,
                logger=self.log,
            )
        except Exception as e:
            self._catch_error(e)
            return 0, None

    def _process_field_options(self, result, num, channel):
        try:
            field_options = self.utils.get_field_options(channel)
            field_list = field_options["field_list"].split(",")
            field_action = field_options["field_option"]
        except Exception as e:
            field_list = []
            field_options = None
            field_action = "include"

        try:
            if (
                    field_list is None
                    or field_list == ""
                    or field_options is None
                    or len(field_list) < 1
            ):
                self.log.debug(
                    f"action=process_field_options status=no_field_list result=include_all result_number={num}"
                )
                include_all_fields = "1"
            else:
                include_all_fields = "0"
            self.log.debug(
                f"action=process_field_options, field options={field_options}, field_list={field_list}, field_action={field_action} result_number={num}"
            )
            final_result = {}
            if include_all_fields == "1":
                self.log.debug(
                    f"action=process_field_options include_all_fields=true result_number={num}"
                )
                final_result = result
            else:
                self.log.debug(
                    f"action=process_field_options option=flatten_dict result_number={num}"
                )
                flattened_fields_list = self._create_result_field_dict(result)
                self.log.debug(
                    f"action=process_field_options  result_number={num} flattened_list_length={len(flattened_fields_list)}"
                )
                regex_filter_fields = [
                    re.compile(x.replace("*", ".*")) for x in field_list if "*" in x
                ]
                for k, v in enumerate(flattened_fields_list):
                    updated_result = {}
                    self.log.debug(
                        f"action=enumerated_tuples k={k} v={v}  result_number={num}"
                    )
                    for key, val in v[1].items():
                        # Basically, through a series of comprehensions, if the key of an object matches a field that has "*" in it, pull the matching string, and add to the filter list.
                        matches = [
                            z
                            for z in [
                                y.group(0)
                                for y in [x.match(key) for x in regex_filter_fields]
                                if y is not None
                            ]
                        ]
                        throw_away = [
                            field_list.append(z) for z in matches if z not in field_list
                        ]
                        self.log.debug(
                            "action=process_field_options key={} value={} "
                            "field_list={} type_field_list={} matches={} throw={}".format(
                                key,
                                val,
                                field_list,
                                type(field_list),
                                matches,
                                throw_away,
                            )
                        )
                        clean_key = key
                        if re.match(r"[a-zA-Z\-_\d]+\.\d+\.[a-zA-Z\-_\d]+", key):
                            clean_key = str.replace(".", ".", key)
                            self.log.debug(
                                "action=process_field_options cleaning_key keys={} key={}".format(
                                    clean_key, key
                                )
                            )
                        if field_action == "exclude" and key not in field_list:
                            self.log.debug(
                                "action=process_field_options field_action={} method=test test={}".format(
                                    field_action, key not in field_list
                                )
                            )
                            updated_result[clean_key] = val
                        elif field_action == "include" and key in field_list:
                            self.log.debug(
                                "action=process_field_options field_action={} method=test test={}".format(
                                    field_action, key in field_list
                                )
                            )
                            updated_result[clean_key] = val
                        else:
                            self.log.debug(
                                "action=passing_if_then_block tuple_count={}".format(k)
                            )
                        self.log.debug(
                            "action=process_field_options key={} clean_key={} val={}".format(
                                key, clean_key, val
                            )
                        )
                    final_result = unflatten_list(updated_result, self.flatten_sep)
            self.log.debug(
                "action=final_result_count final_result={} count={}".format(
                    final_result.keys(), len(final_result)
                )
            )
            return final_result
        except Exception as e:
            self._catch_error(e)

    def _map_severity_to_id(self, severity):
        """
        Map severity string to severity_id numeric value
        Based on OCSF severity_id mapping
        """
        severity_mapping = {
            "OTHER": 99,
            "FATAL": 6,
            "CRITICAL": 5,
            "HIGH": 4,
            "MEDIUM": 3,
            "LOW": 2,
            "INFORMATIONAL": 1,
            "UNKNOWN": 0
        }
        
        if severity is None:
            return 0
        
        severity_upper = str(severity).upper()
        return severity_mapping.get(severity_upper, 0)

    def _process_data_threaded(self, num, x, time_field="timestamp"):
        # self.log.debug("action=found_data function=threaded id={} num={}".format(x, num))
        try:
            channel = self.get_config("channel")
            separate_indicators_enabled = normalizeBoolean(
                self.get_config("separate_indicators")
            )
            separate_star_details_enabled = normalizeBoolean(
                self.get_config("separate_star_details")
            )
            indicator_event = None
            star_details_event = None
            indicator_original_count = 0
            indicator_deduped_count = 0
            star_details_count = 0
            self.log.debug(
                "action=before_field_process time_field={} channel={}  keys={} result_number={}".format(
                    time_field, channel, x.keys(), num
                )
            )
            if channel != "uam_alerts":
                x = self._process_field_options(x, num, channel)
            self.log.debug(
                "action=after_field_process channel={} keys={} result_number={}".format(
                    channel, x.keys(), num
                )
            )
            check_value = x.get("threatInfo", {}).get("initiatedBy", "")
            self.log.debug(
                f'action=process_star_detail channel={channel} result_number=={num} check_value="{check_value}"'
            )
            if check_value == "star_active" and self.enabled_features.get(
                    "starAlerts", False
            ):
                storyline = x.get("threatInfo", {}).get(
                    "storyline", "REQUIRED_NOT_FOUND"
                )
                self.log.debug(
                    "action=process_star_detail channel={} result_number={} storyline={} status=passed_check".format(
                        channel, num, storyline
                    )
                )
                star_details = self._get_threats_star_details(storyline)
                star_details_data = star_details.get("data", [])
                if not isinstance(star_details_data, list):
                    star_details_data = []
                x["star_details"] = star_details_data
                x_field = "threat_id"
                x_id = x.get(x_field)
                if x_id is None:
                    x_id = x.get("id", "NO_X_ID")
                    x_field = "id"
                pagination = " ".join(
                    [
                        f'pagination.{k}="{star_details.get("pagination", {}).get(k, "")}"'
                        for k, v in star_details.get("pagination", {}).items()
                    ]
                )
                self.log.debug(
                    f"action=process_star_detail x_id={x_id} x_field={x_field} storyline={storyline} "
                    f'ret_keys={list(star_details.keys())} res_data_length={len(star_details.get("data", []))} '
                    f"{pagination}"
                )
            if time_field == "threats" and "threatInfo" in x:
                self.log.info(
                    "action=update_timestamp type=threat result_num={}".format(num)
                )
                x["updatedAt"] = x["threatInfo"].get("updatedAt")
                time_field = "updatedAt"
                get_events = self.get_config("threat_events")
                self.log.info("action=get_threat_events config={}".format(get_events))
                if get_events == "1":
                    # Extract all unique alert titles from star_details
                    alert_title = None
                    if "star_details" in x and len(x.get("star_details", [])) > 0:
                        alert_titles = []
                        for alert in x.get("star_details", []):
                            if not isinstance(alert, dict):
                                continue
                            title = alert.get("ruleInfo", {}).get("name")
                            if title and title not in alert_titles:
                                alert_titles.append(title)
                        alert_title = " | ".join(alert_titles) if alert_titles else None
                    self._get_threat_events(x, alert_title=alert_title)
            self.log.debug(
                "action=get_cves_for_applications channel={} add_cves={} appManagement={}".format(
                    channel,
                    normalizeBoolean(self.get_config("add_cves")),
                    self.enabled_features.get("appManagement", False),
                )
            )
            if (
                    channel == "applications"
                    and normalizeBoolean(self.get_config("add_cves"))
                    and not self.enabled_features.get("appManagement", False)
            ):
                app_id = x.get("id", None)
                if app_id is not None:
                    totals, cves = self._get_application_cves(x)
                    self.log.info(
                        "totals={} cves={} subspace=cve action=get_cves_for_application application_id={}".format(
                            totals, type(cves), app_id
                        )
                    )
                    x["cves"] = cves
                    self.log.debug(
                        "x={} subspace=cve action=full_event application_id={}".format(
                            x, app_id
                        )
                    )
                else:
                    self.log.warning(
                        "subspace=cve action=get_cves_for_application msg='Failed to find App ID'"
                    )
            
            # UAM Alerts: Add severity_id mapping
            if channel == "uam_alerts":
                if "severity" in x:
                    x["severity_id"] = self._map_severity_to_id(x.get("severity"))
                    self.log.debug(
                        f"action=map_severity_id severity={x.get('severity')} severity_id={x.get('severity_id')} result_number={num}"
                    )


            if (
                    separate_indicators_enabled
                    and "indicators" in x
                    and isinstance(x["indicators"], list)
                    and len(x["indicators"]) > 0
            ):
                # Extract flat indicator IDs into main event before popping
                flat_ids = set()
                for ind in x["indicators"]:
                    if not isinstance(ind, dict):
                        continue
                    ids = ind.get("ids", [])
                    if not isinstance(ids, list):
                        continue
                    for id_val in ids:
                        flat_ids.add(id_val)
                x["indicator_ids"] = sorted(list(flat_ids))

                indicators = x.pop("indicators")
                indicator_original_count = len(indicators)

                # Deduplicate by category+description, merge ids AND tactics
                merged = {}
                for indicator in indicators:
                    if isinstance(indicator, dict):
                        indicator_ids = indicator.get("ids", [])
                        if not isinstance(indicator_ids, list):
                            indicator_ids = []
                        indicator_tactics = indicator.get("tactics", [])
                        if not isinstance(indicator_tactics, list):
                            indicator_tactics = []
                        key = "{}||{}".format(
                            indicator.get("category", ""),
                            indicator.get("description", "")
                        )
                        if key in merged:
                            # Merge ids (no duplicates)
                            for id_val in indicator_ids:
                                merged[key]["ids"].add(id_val)
                            # Merge tactics (dedup by tactic name, merge techniques inside)
                            for tactic in indicator_tactics:
                                if not isinstance(tactic, dict):
                                    continue
                                techniques = tactic.get("techniques", [])
                                if not isinstance(techniques, list):
                                    techniques = []
                                tname = tactic.get("name")
                                if tname and tname in merged[key]["_tactics_map"]:
                                    # Tactic exists — merge techniques
                                    existing = merged[key]["_tactics_map"][tname]
                                    for tech in techniques:
                                        if not isinstance(tech, dict):
                                            continue
                                        tech_key = tech.get("name", "")
                                        if tech_key not in existing["_tech_names"]:
                                            existing["_tech_names"].add(tech_key)
                                            existing["techniques"].append(tech)
                                elif tname:
                                    # New tactic — add it
                                    tech_names = set(
                                        t.get("name", "") for t in techniques if isinstance(t, dict)
                                    )
                                    merged[key]["_tactics_map"][tname] = {
                                        "name": tname,
                                        "source": tactic.get("source"),
                                        "techniques": list(techniques),
                                        "_tech_names": tech_names
                                    }
                        else:
                            # First time seeing this category+description
                            tactics_map = {}
                            for tactic in indicator_tactics:
                                if not isinstance(tactic, dict):
                                    continue
                                techniques = tactic.get("techniques", [])
                                if not isinstance(techniques, list):
                                    techniques = []
                                tname = tactic.get("name")
                                if tname:
                                    tech_names = set(
                                        t.get("name", "") for t in techniques if isinstance(t, dict)
                                    )
                                    tactics_map[tname] = {
                                        "name": tname,
                                        "source": tactic.get("source"),
                                        "techniques": list(techniques),
                                        "_tech_names": tech_names
                                    }
                            merged[key] = {
                                "category": indicator.get("category"),
                                "description": indicator.get("description"),
                                "ids": set(indicator_ids),
                                "_tactics_map": tactics_map
                            }

                # Build clean deduped indicators list
                deduped_indicators = []
                for v in merged.values():
                    clean_tactics = []
                    for tac in v["_tactics_map"].values():
                        clean_tactics.append({
                            "name": tac["name"],
                            "source": tac["source"],
                            "techniques": tac["techniques"]
                        })
                    deduped_indicators.append({
                        "category": v["category"],
                        "description": v["description"],
                        "ids": sorted(list(v["ids"])),
                        "tactics": clean_tactics
                    })
                indicator_deduped_count = len(deduped_indicators)

                indicator_event = {
                    "id": x.get("id"),
                    "indicators": deduped_indicators,
                    "timestamp": x.get("updatedAt") or x.get("timestamp"),
                }

            # --- Separate star_details into dedicated sourcetype ---
            if (
                    separate_star_details_enabled
                    and "star_details" in x
                    and isinstance(x["star_details"], list)
                    and len(x["star_details"]) > 0
            ):
                # Extract alert IDs into main event before popping
                star_alert_ids = set()
                for alert in x["star_details"]:
                    if not isinstance(alert, dict):
                        continue
                    alert_id = alert.get("alertInfo", {}).get("alertId")
                    if alert_id:
                        star_alert_ids.add(alert_id)
                x["star_alert_ids"] = sorted(list(star_alert_ids))

                star_details = x.pop("star_details")
                star_details_count = len(star_details)

                star_details_event = {
                    "id": x.get("id"),
                    "star_details": star_details,
                    "timestamp": x.get("updatedAt") or x.get("timestamp"),
                }

            self.print_event(json.dumps(x), time_field=time_field)

            if indicator_event is not None:
                self.print_event(
                    json.dumps(indicator_event),
                    time_field="timestamp",
                    sourcetype="{}:indicators".format(self.sourcetype()),
                )
                self.log.info(
                    "action=separated_deduped_indicators threat_id={} original_count={} deduped_count={} result_number={}".format(
                        x.get("id"), indicator_original_count, indicator_deduped_count, num
                    )
                )

            if star_details_event is not None:
                self.print_event(
                    json.dumps(star_details_event),
                    time_field="timestamp",
                    sourcetype="{}:star_details".format(self.sourcetype()),
                )
                self.log.info(
                    "action=separated_star_details threat_id={} star_details_count={} result_number={}".format(
                        x.get("id"), star_details_count, num
                    )
                )

        except Exception as e:
            self._catch_error(e)

    def _process_data_threaded_events(
            self, num, x, threat_id, updatedat, sec_st="event", alert_title=None
    ):
        self.log.debug(
            "action=found_data function=threaded id={} num={}".format(x, num)
        )
        x = self._process_field_options(x, num, self.get_config("channel"))
        x["updatedAt"] = updatedat
        x["id"] = x.get("id", threat_id)
        
        # Add alert title to the event if available
        if alert_title:
            x["alertTitle"] = alert_title
        
        self.print_event(
            json.dumps(x),
            time_field="updatedAt",
            sourcetype="{}:{}".format(self.sourcetype(), sec_st),
        )

    def _process_data_threaded_cves(self, num, x, app):
        x = self._process_field_options(x, num, self.get_config("channel"))
        app_id = app.get("id", None)
        self.log.debug(
            "application_id={} subspace=cve action=found_data function=threaded id={} num={}".format(
                app_id, x, num
            )
        )
        x["application_id"] = app_id
        x["endpointId"] = app.get("agentId", None)
        self.print_event(
            json.dumps(x),
            time_field="updatedAt",
            sourcetype="{}:cve".format(self.sourcetype()),
        )

    def _get_threats_star_details(self, storyline=None):
        channel = self.get_config("channel")
        self.log.debug(f"action=gathering_star_details storyline={storyline}")
        if storyline is None:
            self.log.warning(f"action='No Threat Id' storyline={storyline}")
            return {}
        self.log.debug(f"action=calling_management storyline={storyline}")
        try:
            self.log.debug(
                f"action=enabledFeatures storyline={storyline} mgmt={self.s1_mgmt}"
            )
            resp = self.s1_mgmt.star_alerts.get(sourceProcessStoryline=storyline)
            self.log.debug(f"action=calling_complete storyline={storyline} resp={resp}")
            results = resp.json
            self.log.info(
                "application_id={} subspace=star_alerts channel={} status_code={} length_results_data={}".format(
                    storyline, channel, resp.status_code, len(results["data"])
                )
            )
            return results
        except Exception as e:
            self._catch_error(e)
            self.log.error(f"storyline={storyline} error={e} error_type={type(e)}")
            return {}

    def _get_application_cves(self, app):
        try:
            channel = "{}:cve".format(self.get_config("channel"))
            app_id = app.get("id", None)
            total_items = 0
            complete_set = []
            resp = self.s1_mgmt.applications.get_cves(applicationIds=app_id)
            results = resp.json
            self.log.info(
                "application_id={} subspace=cve action=paginate channel={} status_code={} length_results_data={}".format(
                    app_id, channel, resp.status_code, len(results["data"])
                )
            )
            while total_items < int(self.get_config("bulk_import_limit")):
                next_cursor = results["pagination"].get("next_cursor")
                [complete_set.append(x) for x in results["data"]]
                self.log.info(
                    "application_id={} subspace=cve action=paginate channel={} data_length={}".format(
                        app_id, channel, len(complete_set)
                    )
                )
                self.log.info(
                    "application_id={} subspace=cve action=paginate cursor={} channel={}".format(
                        app_id, next_cursor, channel
                    )
                )
                p = mp.Pool(10)
                if len(results["data"]) > 0:
                    matrix = [
                        (num, result, app) for num, result in enumerate(results["data"])
                    ]
                    self.log.info(
                        "application_id={} subspace=cve action=paginate matrix_length={} channel={}".format(
                            app_id, len(matrix), channel
                        )
                    )
                    self.log.debug("_get_application_cves, matrix: {}".format(matrix))
                    p.starmap(self._process_data_threaded_cves, matrix)
                else:
                    self.log.debug("_get_application_cves, results[data] is empty")

                p.close()
                p.join()
                total_items += len(results["data"])
                self.log.info(
                    "application_id={} subspace=cve action=paginate total_items={} channel={}".format(
                        app_id, total_items, channel
                    )
                )
                if next_cursor is None:
                    break
                resp = self.s1_mgmt.applications.get_cves(
                    applicationIds=[app_id], cursor=next_cursor
                )
                results = resp.json
                self.log.info(
                    "application_id={} subspace=cve action=paginate channel={} status_code={}".format(
                        app_id, channel, resp.status_code
                    )
                )
            return total_items, complete_set
        except Exception as e:
            self._catch_error(e)

    def _get_threat_events(self, x, alert_title=None):
        try:
            threat_id = x["id"]
            limit = 1000
            channel = "{}:event".format(self.get_config("channel"))
            self.log.info(
                "action=paginate channel={} threat_id={}".format(channel, threat_id)
            )
            total_items = 0
            resp = self.s1_mgmt.threat_explore.get_events(threat_id, limit=limit)
            results = resp.json
            self.log.debug(
                "action=paginate channel={}  threat_id={} status_code={} pagination={}".format(
                    channel, threat_id, resp.status_code, results.get("pagination", [])
                )
            )
            p = mp.Pool(10)
            if len(results["data"]) > 0:
                matrix = [
                    (num, result, threat_id, x["updatedAt"], "event", alert_title)
                    for num, result in enumerate(results["data"])
                ]
                self.log.debug(
                    "action=paginate matrix_length={} channel={}  threat_id={}".format(
                        len(matrix), channel, threat_id
                    )
                )
                p.starmap(self._process_data_threaded_events, matrix)
            else:
                self.log.debug(
                    "action=paginate matrix_length=0  threat_id={} msg='results[data] is empty'".format(
                        threat_id
                    ))
            p.close()
            p.join()
            total_items += len(results["data"])
            self.log.info(
                "action=paginate total_items={}  threat_id={} channel={}".format(
                    total_items, threat_id, channel
                )
            )
            return total_items
        except Exception as e:
            self._catch_error(e)

    def _reload_inputs(self, utils):
        """
        This method will reload the inputs of the application
        """
        reload_uri = utils._build_endpoint_uri(["data", "inputs", "sentinelone", "_reload"])
        self.info("Reloading the input for the current changes affect")
        utils._make_get_request(uri=reload_uri, args={'output_mode': 'json'})



    def _is_epoch_behind_reload_limit(self, epoch_time):
        """
        This method will check is the epoch is behind reload time difference
        """
        current_time = int(time.time())
        self.info(f"The current time: {current_time} and epoch time: {epoch_time}")
        # Calculate the epoch time for reload time difference

        time_checkpoint = current_time - (reload_time_difference_in_hrs * 60 * 60)
        self.info(f"The current tim: {current_time}; epoch time: {epoch_time} and {str(reload_time_difference_in_hrs)} hours ago time: {time_checkpoint}")
        # Compare the given epoch time with the current time
        if epoch_time < time_checkpoint:
            return True
        return False
    
    def _get_all_enabled_valid_data_inputs(self, all_data_inputs_content):
        """
        This method filters all enabled inputs and those with the "Inputs Check" enabled.
        """
        enabled_content = []
        for each_content in all_data_inputs_content:
            if not each_content.get("disabled") and normalizeBoolean(each_content.get("is_auto_inputs_check", "0")):
                self.info(f"The input with GUID: {each_content.get('guid', '')} is enabled and valid.")
                enabled_content.append(each_content)
        return enabled_content

    def _get_all_data_inputs_content(self, utils):
        """
        This method fetches the SentinelOne data inputs from the Splunk server.
        """
        self.info("Fetching data inputs from Splunk.")
        get_input_config_uri = utils._build_endpoint_uri(["configs", "conf-inputs"])

        entries = []
        all_inputs_content = []
        per_page = 1000
        offset = 0
        while True:
            args = {
                "output_mode": "json",
                "count": per_page,
                "offset": offset
            }
            try:
                # Make the API request
                self.info("Making an API call to fetch the inputs.")
                data = {}
                data_tuple = utils._make_get_request(uri=get_input_config_uri, args=args)
                if len(data_tuple) >= 2:
                    data = json.loads(data_tuple[1].decode('utf-8'))
            except Exception as e:
                self.warn(f"Got exception while fetching the data inputs config. Exception: {str(e)}")
                break
            self.info("Fetch inputs API call successful.")

            # Filter the entries with 'sentinelone://' in the 'name'
            filtered_entries = [entry for entry in data.get('entry', []) if 'sentinelone://' in entry['name']]
            entries.extend(filtered_entries)
            # Check if we have fetched all entries by checking the total count
            total_entries = data.get('paging', {}).get('total', 0)
            offset += per_page
            
            if offset >= total_entries or not data:
                break
        self.info("Fetching the content of each entry in SentinelOne.")
        for entry in entries:
            if entry["content"]:
                all_inputs_content.append(entry["content"])
        self.info("Fetched the content of each entry in SentinelOne.")
        return all_inputs_content
    
    def _get_current_execution_time(self):
        """
        This method generates the current UTC time and returns it in a dictionary.
        The time is represented as a string formatted as a timestamp.
        """
        current_execution_time = str(int(datetime.now(timezone.utc).timestamp()))
        return {"last_execution": current_execution_time}


    def _validate_the_last_reload_expiration(self):
        """
        This method will validate the last reload check which is happen, this also validates with last reload_time_difference_in_hrs
        """
        last_reload_chkpnt_obj = self.get_checkpoint(last_reload_chkpnt_name, isObject=True, isReloadCheck=True)
        if isinstance(last_reload_chkpnt_obj, bool) and not last_reload_chkpnt_obj:
            last_reload_chkpnt_obj = self._get_current_execution_time()
            self.info(f"The reload checkpoint file does not exist, so setting the checkpoint with the following value: {str(last_reload_chkpnt_obj['last_execution'])}")
            self._set_checkpoint(chkpnt_name=last_reload_chkpnt_name, checkpoint_time=last_reload_chkpnt_obj["last_execution"])
        else:
            try:
                if isinstance(last_reload_chkpnt_obj, str):
                    last_reload_chkpnt_obj = json.loads(last_reload_chkpnt_obj)
                self.info(f"Successfully fetched the last reload checkpoint object. {str(last_reload_chkpnt_obj)}")
            except Exception as e:
                last_reload_chkpnt_obj = self._get_current_execution_time()
                self.info(f"There is an issue parsing the return value of the reload checkpoint, so the checkpoint is being set with the following value: {str(last_reload_chkpnt_obj['last_execution'])}")
                self._set_checkpoint(chkpnt_name=last_reload_chkpnt_name, checkpoint_time=last_reload_chkpnt_obj["last_execution"])
                self.warn(
                    f"message=when fetching the reload checkpoint EXCEPTION={e} OBJECT={last_reload_chkpnt_obj}"
                )
        reload_chkpnt = "{}".format(last_reload_chkpnt_obj["last_execution"])
        self.info(f"Validating the last reload expiration time: {str(reload_chkpnt)}")
        return self._is_epoch_behind_reload_limit(int(float(reload_chkpnt)))


    def auto_restart_of_inputs(self):
        """
        This method checks whether the inputs are behind the last reload_time_difference_in_hrs. If an input is outdated (i.e., running behind), it will be automatically re-enabled. 
        This check will apply to all inputs when the "Inputs Check" checkbox is selected.
        """
        try:
            self.info("Starting the process of re enable of data inputs and creating the Utils object.")
            utils = Utilities(app_name=__app_name__, session_key=self.get_config("session_key"))
            all_data_inputs_content = self._get_all_data_inputs_content(utils)
            enabled_valid_data_inputs = self._get_all_enabled_valid_data_inputs(all_data_inputs_content)
            self.info(f"The enabled and valid data inputs: {str(enabled_valid_data_inputs)}")
            # Creating the reload checkpoint object

            is_last_reload_time_expired = self._validate_the_last_reload_expiration()
            is_reload_required = False
            if is_last_reload_time_expired:
                self.info(f"The last reload time has expired, so starting to validate the inputs to check if they have been stuck for more than {str(reload_time_difference_in_hrs)} hours.")
                inputs_running_behind = []
                for each_enabled_input in enabled_valid_data_inputs:
                    channel = each_enabled_input.get("channel", "")
                    input_guid = each_enabled_input.get("guid", "")
                    chkpnt_name = "sentinelone-input-{}-channel-{}.json".format(input_guid, channel)
                    input_chkpnt_obj = self.get_checkpoint(chkpnt_name, isObject=True)
                    try:
                        if isinstance(input_chkpnt_obj, str):
                            input_chkpnt_obj = json.loads(input_chkpnt_obj)
                        self.info("Successfully fetched the checkpoint object.")
                    except Exception as e:
                        input_chkpnt_obj = {
                            "next_page": None,
                            "last_execution": str(int(datetime.now(timezone.utc).timestamp())),
                        }
                        self.warn(
                            f"channel={channel} EXCEPTION={e} OBJECT={input_chkpnt_obj}"
                        )
                    input_chkpnt = "{}".format(input_chkpnt_obj["last_execution"])
                    self.info(f"The check point value of input guid: {input_guid}, input name: {each_enabled_input.get('input_name', '')}, checkpoint: {input_chkpnt}")
                    is_epoch_behind_accepted_limit = self._is_epoch_behind_reload_limit(int(float(input_chkpnt)))
                    if is_epoch_behind_accepted_limit:
                        inputs_running_behind.append(input_guid)
                        is_reload_required = True
                if is_reload_required:
                    self.info(f"The input(s) with GUID: {str(inputs_running_behind)} are running behind last {str(reload_time_difference_in_hrs)} hours")
                    current_time = str(int(datetime.now(timezone.utc).timestamp()))
                    self.info(f"Setting up the checkpoint for the last reload. current_time: {str(current_time)}")
                    self._set_checkpoint(chkpnt_name=last_reload_chkpnt_name, checkpoint_time=current_time)
                    self.info("Performing the reload of the inputs")
                    # Reload the Input once all inputs updated
                    self._reload_inputs(utils)
            else:
                self.info(f"The last reload has not expired; will perform the reload once it has expired.")
            self.info("Completed the process of re enable of data inputs.")
        except Exception as e:
            self._catch_error(e)

    def get_channel(self, func_run_id=""):
        try:
            self.info("Fetching the channel information")
            channel = self.get_config("channel")
            if normalizeBoolean(self.get_config("lockfile", "1")):
                time_to_force_unlock = int(self.get_config("lockfile_duration", 3600))  # Default force unlock after 1 hour of being locked.
                self.info(f"The lock file mechanism was enabled, for channel: {channel} and time to force unlock: {str(time_to_force_unlock)} secs")
                if not self._set_lock(func_run_id):
                    lockfile = self._get_lockfile()
                    self.fatal(action="setting_lockfile",
                               category="lockfile",
                               msg="lockfile exists",
                               lockfile=lockfile)
                    now = time.time()
                    with open(lockfile, "r") as lf:
                        cnts = lf.read().split(";;")
                    lock_time = float(cnts[0])
                    last_run_id = cnts[1]
                    time_since_lock = float(f"{now}") - lock_time
                    self.inform(action="reading_lockfile",
                                category="lockfile",
                                lock_time=lock_time,
                                now=now,
                                time_since_lock=time_since_lock,
                                last_run_id=last_run_id,
                                lockfile=lockfile)
                    if time_since_lock > time_to_force_unlock:
                        self.warn(action="forcing_lock_removal",
                                  category="lockfile",
                                  lockfile=lockfile,
                                  time_since_lock=time_since_lock,
                                  time_to_force_unlock=time_to_force_unlock,
                                  time_until_unlock=(time_to_force_unlock - time_since_lock))
                        if self._remove_lock():
                            self._set_lock(func_run_id)
                    else:
                        self.warn(action="waiting_to_remove_lock",
                                  category="lockfile",
                                  lockfile=lockfile,
                                  time_since_lock=time_since_lock,
                                  time_to_force_unlock=time_to_force_unlock,
                                  time_until_unlock=(time_to_force_unlock - time_since_lock))
                        return
                else:
                    self.inform(action="setting_lockfile",
                                msg="lockfile set",
                                category="lockfile",
                                lockfile=self._get_lockfile())
            else:
                self.info(f"The lock file mechanism was not enabled, for channel: {channel}")
            if self.s1_mgmt is None:
                self.fatal(action="fatal_error",
                           category="init",
                           message="S1 Client not Instantiated. Please review error logs.",
                           channel=channel,
                           input=self.get_config("guid"))
                return
            chkpnt_name = "sentinelone-input-{}-channel-{}.json".format(
                self.get_config("guid"), channel
            )
            lb = self.get_config("lookback")
            self.sourcetype("sentinelone:channel:{}".format(channel))
            self.log.debug(
                f"action=evaluating_lookback channel={channel} lookback={lb} lookback_type={type(lb)} run_id={func_run_id}"
            )
            if int(lb) > 0:
                self.log.debug(
                    f"run_id={func_run_id} action=evaluating_lookback channel={channel} new_lookback={(int(lb) * 1440)}"
                )
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            chkpnt_obj = self.get_checkpoint(chkpnt_name, isObject=True)
            try:
                self.log.debug(
                    f"run_id={func_run_id} action=evaluating_checkpoint  channel={channel} type={type(chkpnt_obj)} checkpoint='{chkpnt_obj}'"
                )
                try:
                    if isinstance(chkpnt_obj, str):
                        chkpnt_obj = json.loads(chkpnt_obj)
                except Exception as e:
                    chkpnt_obj = {
                        "next_page": None,
                        "last_execution": "{}".format(datetime.now(timezone.utc).strftime("%s")),
                    }
                    self.log.critical(
                        f"run_id={func_run_id} action=FORCING_CHECKPOINT channel={channel} EXCEPTION={e} OBJECT={chkpnt_obj}"
                    )
            except Exception as e:
                self._catch_error(e)
            self.log.warning(
                f"run_id={func_run_id} action=got_checkpoint checkpoint={chkpnt_obj} channel={channel} type={type(chkpnt_obj)}"
            )
            np = None
            try:
                np = chkpnt_obj.get("next_page", None)
            except Exception as e:
                self.log.critical(
                    f'run_id={func_run_id} action=FAILURE_TO_GET_ATTRIBUTE channel={channel} attr=next_page OBJECT="{chkpnt_obj}" TYPE="{type(chkpnt_obj)}" EXCEPTION={e}'
                )
            next_page = None
            if np is not None and np != "None":
                next_page = np
            chkpnt = "{}".format(chkpnt_obj["last_execution"])
            self.log.warning(
                f"run_id={func_run_id} action=got_checkpoint checkpoint={chkpnt_obj} channel={channel} last_execution={chkpnt}"
            )
            # 1608240066072
            chkpnt_end = str(int(time.time()))
            start = "{}000".format(chkpnt.split(".")[0])
            end = "{}000".format(chkpnt_end)
            self.log.warning(
                "run_id={} action=calling_{}_channel status=start "
                "start={} start_length={} start_type={} end={} end_length={} end_type={} "
                "checkpoint={} channel={}".format(func_run_id,
                                                  channel,
                                                  start,
                                                  len(start),
                                                  type(start),
                                                  end,
                                                  len(end),
                                                  type(end),
                                                  chkpnt,
                                                  channel,
                                                  )
            )
            results_resp = None
            page = None
            if channel == "threats":
                results_resp, page = self._get_threats(start, next_page)
            if channel == "uam_alerts":
                results_resp, page = self._get_uam_alerts(start, next_page)
            if channel == "activities":
                results_resp, page = self._get_activities(start, next_page)
            if channel == "groups":
                results_resp, page = self._get_groups()
            if channel == "applications":
                results_resp, page = self._get_applications(start)
            if channel == "agents":
                results_resp, page = self._get_agents()
            if channel == "risks":
                results_resp, page = self._get_application_risks(start)
            if results_resp is None:
                raise Exception(f"run_id={func_run_id} action=results_not_found channel={channel}")
            self.log.info(
                "run_id={} action=completed_run checkpoint={} items_found={} page={} channel={}".format(
                    func_run_id, chkpnt, results_resp, page, channel
                )
            )
            if results_resp > 0:
                self.log.warning(
                    "run_id={} action=saving_checkpoint checkpoint={} items_found={} page={} channel={}, chkpnt_end={}".format(
                        func_run_id, chkpnt, results_resp, page, channel, chkpnt_end
                    )
                )
                self._set_checkpoint(
                    chkpnt_name, next_page=page, checkpoint_time=chkpnt_end
                )
            else:
                self.log.warning(
                    "run_id={} action=saving_checkpoint "
                    "msg='not saving checkpoint in case there was a communication error' "
                    "start={} items_found={} channel={}".format(
                        func_run_id, start, results_resp, channel
                    )
                )
            if normalizeBoolean(self.get_config("lockfile", "1")):
                self.info("Removing the lock file at the end of the ingestion.")
                self._remove_lock()
            self.log.info(
                "run_id={} action=calling_{}_channel status=end channel={}".format(func_run_id, channel, channel))
        except Exception as e:
            self._catch_error(e)


modular_input = S1BaseModularInput(app_name=__app_name__,
                                   tracking_uuid=run_id,
                                   scheme={
                                       "title": "SentinelOne",
                                       "description": "Provides a view into SentinelOne",
                                       "args": [
                                           {"name": "guid",
                                            "description": "distinct guid",
                                            "title": "GUID",
                                            "required": True
                                            },
                                           {"name": "input_name",
                                            "description": "descriptive name",
                                            "title": "Input Name",
                                            "required": True
                                            },
                                           {"name": "lookback",
                                            "description": "how many days to lookback on initial ingest",
                                            "title": "Lookback",
                                            "required": True
                                            },
                                           {"name": "channel",
                                            "description": "The single channel to query",
                                            "title": "Channel",
                                            "required": True
                                            },
                                           {"name": "api_config",
                                            "description": "The api_config guid for authentication.",
                                            "title": "API Config Guid",
                                            "required": True
                                            },
                                           {"name": "bulk_import_limit",
                                            "description": "Bulk import limit",
                                            "title": "Bulk Import Limit",
                                            "required": True
                                            }
                                       ]
                                   })

# These are the channels that require use of the mgmtsdk_v2_1_apl that is custom developed.
APL_SPECIFIC_MGMT_CHANNELS = ["applications"]


def run():
    log.warning(f"action=start_modular_input name=sentinelone-alerts run_id={run_id}")
    modular_input.start()
    try:
        log.info("Starting the modular input")
        channel = modular_input.get_config("channel")
        input_guid = modular_input.get_config("guid")
        log.warning(f"run_id={run_id} action=DECLARE_START channel={channel} input_guid={input_guid}")
        modular_input.set_logger(
            kl.get_logger(__app_name__, f"sentinelone-modularinput-{channel}", logger.INFO))
        modular_input.setup(apl=channel in APL_SPECIFIC_MGMT_CHANNELS)
        modular_input.sourcetype("sentinelone:informational")
        modular_input.source("sentinelone:input:{}".format(input_guid))
        log.warning(f"action=start_get_channel name=sentinelone-alerts run_id={run_id}")
        modular_input.get_channel(run_id)
        modular_input.auto_restart_of_inputs()
        log.warning(f"action=end_get_channel name=sentinelone-alerts run_id={run_id}")
        log.warning(f"run_id={run_id} action=DECLARE_END channel={channel} input_guid={input_guid}")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, modular_input.get_config("guid"),
                    modular_input.get_config("input_name"))
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()
        log.warning(f"action=stop_modular_input name=sentinelone-alerts run_id={run_id}")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
