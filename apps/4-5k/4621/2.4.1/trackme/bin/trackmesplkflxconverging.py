#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.2.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party library imports
import requests
import urllib3
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_flx_converging.log" % splunkhome,
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
from trackme_libs import trackme_reqinfo, get_splunkd_timeout, SPLUNKD_TIMEOUT_DEFAULT
from trackme_filter_engine import apply_filter

# Maximum number of concurrent REST calls for multi-tenant fetches
MAX_PARALLEL_WORKERS = 4


@Configuration(distributed=False)
class TrackMeFlxConverging(GeneratingCommand):

    tenants_scope = Option(
        doc="""
        **Syntax:** **tenants_scope=****
        **Description:** Comma separated list of tenants id where to source entities from.""",
        require=True,
        default=None,
    )

    group = Option(
        doc="""
        **Syntax:** **group=****
        **Description:** The group this entity belongs to.""",
        require=True,
        default=None,
    )

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** The entity object name.""",
        require=True,
        default=None,
    )

    object_description = Option(
        doc="""
        **Syntax:** **object_description=****
        **Description:** The entity object description.""",
        require=True,
        default=None,
    )

    root_constraint = Option(
        doc="""
        **Syntax:** **root_constraint=****
        **Description:** Filter expression using field=value DSL with glob wildcards, AND/OR logic, and parentheses. Example: priority=high OR priority=critical""",
        require=False,
        default=None,
    )

    consider_orange_as_up = Option(
        doc="""
        **Syntax:** **consider_orange_as_up=****
        **Description:** Consider orange as up""",
        require=False,
        default=True,
        validate=validators.Boolean(),
    )

    remove_extra_attributes = Option(
        doc="""
        **Syntax:** **remove_extra_attributes=****
        **Description:** Remove the extra_attributes field from the results.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    min_pct_for_green = Option(
        doc="""
        **Syntax:** **min_pct_for_green=****
        **Description:** Minimum percentage of availability required for the status to be green (1). Default is 100.""",
        require=False,
        default=100,
        validate=validators.Integer(0, 100),
    )

    # Component key to tenant field mapping for enabled-status checks
    COMPONENT_ENABLED_FIELD_MAP = {
        "flx": "tenant_flx_enabled",
        "dsm": "tenant_dsm_enabled",
        "dhm": "tenant_dhm_enabled",
        "mhm": "tenant_mhm_enabled",
        "cim": "tenant_cim_enabled",
        "fqm": "tenant_fqm_enabled",
        "wlk": "tenant_wlk_enabled",
    }

    def _load_valid_tenants(self, session_key, splunkd_uri, splunkd_timeout=SPLUNKD_TIMEOUT_DEFAULT):
        """
        Call the trackmeload endpoint to retrieve the list of valid tenants
        and their enabled components. Returns a dict mapping tenant_id to a
        set of enabled component keys (e.g. {"my-tenant": {"flx", "dsm"}}).
        """

        if not splunkd_uri.startswith("https://"):
            splunkd_uri = f"https://{splunkd_uri}"

        url = f"{splunkd_uri}/services/trackme/v2/vtenants/trackmeload"
        headers = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps({"mode": "full"}),
                verify=False,
                timeout=splunkd_timeout,
            )
            response.raise_for_status()
            data = response.json()

            valid_tenants = {}
            tenants_json = data.get("tenants_json")
            if not isinstance(tenants_json, dict):
                logging.warning(
                    "trackmeload response has unexpected structure, skipping tenant validation"
                )
                return None

            tenants_list = tenants_json.get("tenants", [])

            for tenant in tenants_list:
                tenant_id = tenant.get("tenant_id")
                if not tenant_id:
                    continue

                enabled_components = set()
                for comp_key, field_name in self.COMPONENT_ENABLED_FIELD_MAP.items():
                    value = tenant.get(field_name)
                    if value not in (None, "null", 0, "0"):
                        enabled_components.add(comp_key)

                valid_tenants[tenant_id] = enabled_components

            return valid_tenants

        except Exception as e:
            logging.error(
                f'Failed to load tenants from trackmeload endpoint, exception="{str(e)}"'
            )
            return None

    def _fetch_tenant_entities(self, session_key, splunkd_uri, tenant_id, component, splunkd_timeout):
        """
        Fetch entity records for a tenant/component pair via direct REST call
        to the load_component_data endpoint, bypassing SPL dispatch overhead.

        Returns a list of entity dicts, already filtered for non-converging
        and enabled entities.
        """

        if not splunkd_uri.startswith("https://"):
            splunkd_uri = f"https://{splunkd_uri}"

        url = f"{splunkd_uri}/services/trackme/v2/component/load_component_data"
        headers = {
            "Authorization": f"Splunk {session_key}",
            "Content-Type": "application/json",
        }
        params = {
            "tenant_id": tenant_id,
            "component": component,
            "page": 1,
            "size": 0,
        }

        fetch_start = time.time()

        try:
            response = requests.get(
                url,
                headers=headers,
                params=params,
                verify=False,
                timeout=splunkd_timeout,
            )
            response.raise_for_status()
            data = response.json().get("data", [])

            # Apply static filters in Python (previously done via SPL where/search)
            # 1. Exclude converging flx_type entities
            # 2. Exclude disabled entities
            filtered = [
                record for record in data
                if record.get("flx_type") != "converging"
                and record.get("monitored_state") != "disabled"
            ]

            fetch_duration = round(time.time() - fetch_start, 3)
            logging.info(
                f'_fetch_tenant_entities completed, tenant_id="{tenant_id}", '
                f'component="{component}", total_records={len(data)}, '
                f'after_filter={len(filtered)}, duration={fetch_duration}s'
            )

            return filtered

        except Exception as e:
            logging.error(
                f'_fetch_tenant_entities failed, tenant_id="{tenant_id}", '
                f'component="{component}", exception="{str(e)}"'
            )
            raise

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get configurable splunkd timeout
        splunkd_timeout = get_splunkd_timeout(reqinfo=reqinfo)

        # Session credentials
        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri

        # Load valid tenants/components for pre-validation
        valid_tenants = self._load_valid_tenants(
            session_key,
            splunkd_uri,
            splunkd_timeout=splunkd_timeout,
        )

        # Get tenants_scope and turn into a list
        tenants_scope = self.tenants_scope.split(",")

        # Build validated list of (tenant_id, component) pairs
        validated_pairs = []
        for tenant_item in tenants_scope:

            # we accept <tenant_id>:<component> as a key pair in the list
            # if not, we set the component to flx
            if ":" in tenant_item:
                tenant_id, component = tenant_item.split(":")
            else:
                tenant_id = tenant_item
                component = "flx"

            # Validate that the tenant/component combination exists
            if valid_tenants is not None:
                if tenant_id not in valid_tenants:
                    logging.warning(
                        f'tenant_id="{tenant_id}" does not exist, '
                        f'skipping this tenant/component pair from the converging tracker scope'
                    )
                    continue

                if component not in valid_tenants[tenant_id]:
                    logging.warning(
                        f'tenant_id="{tenant_id}" component="{component}" is not enabled for this tenant, '
                        f'skipping this tenant/component pair from the converging tracker scope'
                    )
                    continue

            validated_pairs.append((tenant_id, component))

        # initialise search_results
        results_dict = {}
        results_summary_dict = {}
        results_light_list_up = []
        results_light_list_down = []

        # counters
        count_entities = 0
        count_entities_list = []
        count_entities_up = 0
        count_entities_up_list = []
        count_entities_down = 0
        count_entities_down_list = []

        # percentage of availability
        pct_availability = 0

        # Resolve the root_constraint filter expression
        root_constraint = self.root_constraint or ""

        # Strip wrapping parentheses if the entire expression is wrapped
        # (backward compatibility with legacy SPL-style constraints like "(object=* priority=*)")
        stripped = root_constraint.strip()
        if stripped.startswith("(") and stripped.endswith(")"):
            # Only strip if the parens are balanced outer wrapper
            depth = 0
            is_outer_wrap = True
            for i, ch in enumerate(stripped):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if depth == 0 and i < len(stripped) - 1:
                    is_outer_wrap = False
                    break
            if is_outer_wrap:
                root_constraint = stripped[1:-1].strip()

        # Normalize legacy SPL catch-all wildcards to empty (match everything).
        # Before v2.3.18, root_constraint was an SPL expression (| search <expr>),
        # so "*" / "(*)" meant "match all". Treat these as no filter.
        if root_constraint == "*":
            root_constraint = ""

        logging.info(
            f'trackmesplkflxconverging starting, tenants_scope="{self.tenants_scope}", '
            f'validated_pairs={len(validated_pairs)}, root_constraint="{root_constraint}"'
        )

        # Fetch entity data — parallel REST calls for multi-tenant, direct call for single
        fetch_errors = []

        if len(validated_pairs) == 0:
            logging.warning("No valid tenant/component pairs to process")

        elif len(validated_pairs) == 1:
            # Single tenant — direct call, no thread overhead
            tenant_id, component = validated_pairs[0]
            try:
                data = self._fetch_tenant_entities(
                    session_key, splunkd_uri, tenant_id, component, splunkd_timeout
                )
                # Apply root_constraint filter
                data = apply_filter(data, root_constraint)
                for record in data:
                    key = record.get("_key")
                    if key:
                        # stamp the source component (load_component_data does not
                        # return it) so the converging breakdown can group members
                        # by tenant:component downstream (e.g. the topology graph)
                        record["component"] = component
                        results_dict[key] = record
            except Exception as e:
                fetch_errors.append((tenant_id, component, str(e)))

        else:
            # Multi-tenant — parallel REST calls
            max_workers = min(MAX_PARALLEL_WORKERS, len(validated_pairs))
            logging.info(
                f'Fetching entities in parallel, pairs={len(validated_pairs)}, workers={max_workers}'
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_pair = {
                    executor.submit(
                        self._fetch_tenant_entities,
                        session_key, splunkd_uri, tid, comp, splunkd_timeout
                    ): (tid, comp)
                    for tid, comp in validated_pairs
                }

                for future in as_completed(future_to_pair):
                    tid, comp = future_to_pair[future]
                    try:
                        data = future.result()
                        # Apply root_constraint filter
                        data = apply_filter(data, root_constraint)
                        for record in data:
                            key = record.get("_key")
                            if key:
                                # stamp the source component (see single-tenant branch)
                                record["component"] = comp
                                results_dict[key] = record
                    except Exception as e:
                        logging.error(
                            f'Parallel fetch failed, tenant_id="{tid}", '
                            f'component="{comp}", exception="{str(e)}"'
                        )
                        fetch_errors.append((tid, comp, str(e)))

        # Log a warning when some (but not all) fetches failed — the tracker
        # proceeds with partial data by design, but we surface the gap for
        # troubleshooting.
        if fetch_errors and len(fetch_errors) < len(validated_pairs):
            failed_scopes = ", ".join(
                f"{tid}:{comp}" for tid, comp, _ in fetch_errors
            )
            logging.warning(
                f"trackmesplkflxconverging proceeding with partial data, "
                f"failed_scopes=[{failed_scopes}], "
                f"succeeded={len(validated_pairs) - len(fetch_errors)}/{len(validated_pairs)}"
            )

        # If ALL fetches failed (not just some), yield a failure record
        if len(fetch_errors) == len(validated_pairs) and validated_pairs:
            error_details = "; ".join(
                f'{tid}:{comp} -> {err}' for tid, comp, err in fetch_errors
            )
            yield_record = {
                "_time": time.time(),
                "action": "failure",
                "response": "All entity fetches failed",
                "_raw": {
                    "action": "failure",
                    "response": "All entity fetches failed",
                    "errors": error_details,
                },
            }
            yield yield_record
            logging.error(
                f'trackmesplkflxconverging failed, all fetches errored, '
                f'run_time={round(time.time() - start, 3)}'
            )
            return

        #
        # main processing
        #

        # for entity in results_dict, get the status (object_state), if green or orange, count as up, if red, count as down and add to the associated lists
        for entity in results_dict:

            entity_record = results_dict[entity]

            # get the alias
            entity_alias = entity_record.get("alias")

            # set the summary dict
            entity_summary_dict = {}

            # for fields: object, alias, priority, object_state, status_message_json, status_description, status_description_short, tracker_name
            # if available in the entity record, add to the entity_summary_dict
            for field in [
                "tenant_id",
                "component",
                "object",
                "keyid",
                "priority",
                "object_state",
                # tags surfaced so the topology graph search can match on them
                # (self-heals on the next tracker run for pre-enrichment records)
                "tags",
                "status_message_json",
                "status_description",
                "status_description_short",
                "tracker_name",
            ]:
                if field in entity_record:
                    entity_summary_dict[field] = entity_record[field]

            # add to our summary — key by the unique _key (the loop var), NOT
            # the object name. A converging tracker aggregates across
            # tenant:component scopes where the same object name can recur;
            # keying by object alone lets one scope's entity overwrite
            # another's, silently dropping members from all_entities (and from
            # the topology graph grouped by tenant:component). Every consumer
            # reads the object off the value (e.object), so the key is free to
            # be the _key.
            results_summary_dict[entity] = entity_summary_dict

            count_entities += 1
            count_entities_list.append(entity_summary_dict)

            if self.consider_orange_as_up:
                if results_dict[entity]["object_state"] in ["green", "blue", "orange"]:
                    count_entities_up += 1
                    count_entities_up_list.append(entity_summary_dict)
                    results_light_list_up.append(entity_alias)
                    entity_summary_dict["converging_status"] = "up"
                elif results_dict[entity]["object_state"] == "red":
                    count_entities_down += 1
                    count_entities_down_list.append(entity_summary_dict)
                    results_light_list_down.append(entity_alias)
                    entity_summary_dict["converging_status"] = "down"
            else:
                if results_dict[entity]["object_state"] in ["green", "blue"]:
                    count_entities_up += 1
                    count_entities_up_list.append(entity_summary_dict)
                    results_light_list_up.append(entity_alias)
                    entity_summary_dict["converging_status"] = "up"
                elif results_dict[entity]["object_state"] in ["orange", "red"]:
                    count_entities_down += 1
                    count_entities_down_list.append(entity_summary_dict)
                    results_light_list_down.append(entity_alias)
                    entity_summary_dict["converging_status"] = "down"

        # Sort the lists by tenant_id and object
        def sort_key(entity):
            return (entity.get("tenant_id", ""), entity.get("object", ""))

        count_entities_down_list.sort(key=sort_key)
        count_entities_list.sort(key=sort_key)

        # Sort the results_summary_dict by tenant_id and object
        sorted_results = {}
        for key in sorted(
            results_summary_dict.keys(),
            key=lambda k: (
                results_summary_dict[k].get("tenant_id", ""),
                results_summary_dict[k].get("object", ""),
            ),
        ):
            sorted_results[key] = results_summary_dict[key]

        # Reorganize results_summary_dict with down_entities and all_entities sections
        new_results_summary_dict = {"all_entities": sorted_results}
        if count_entities_down > 0:
            new_results_summary_dict = {
                "down_entities": count_entities_down_list,
                **new_results_summary_dict,
            }
        results_summary_dict = new_results_summary_dict

        # calculate the percentage of availability
        if count_entities > 0:
            pct_availability = round((count_entities_up / count_entities) * 100, 2)

        # status (1 / 2 / 3)
        if pct_availability >= self.min_pct_for_green:
            status = 1
        elif pct_availability >= 0:
            status = 2
        else:
            status = 3

        # set the value of metrics
        metrics = {
            "pct_availability": pct_availability,
            "count_entities": count_entities,
            "count_entities_up": count_entities_up,
            "count_entities_down": count_entities_down,
        }

        # set status_description_short
        status_description_short = f"Availability={pct_availability}%, up={count_entities_up}, down={count_entities_down}"

        # set status_description
        if pct_availability == 100:
            status_description = f"The availability percentage is {pct_availability}, all {count_entities} entities are up"
        elif pct_availability > 0:
            status_description = f"The availability percentage is {pct_availability}, {count_entities_up} entities are up and {count_entities_down} entities are down: {results_light_list_down}"
        else:
            status_description = f"The availability percentage is {pct_availability}, all {count_entities} entities are down: {results_light_list_down}"

        # final results records
        if count_entities > 0:
            final_results_records = {
                "group": self.group,
                "object": self.object,
                "object_description": self.object_description,
                "status": status,
                "status_description": status_description,
                "status_description_short": status_description_short,
                "extra_attributes": results_summary_dict,
                "metrics": metrics,
            }
        else:  # no entities found
            final_results_records = {
                "group": self.group,
                "object": self.object,
                "object_description": self.object_description,
                "status": 3,
                "status_description": "No entities found",
                "status_description_short": "No entities found",
                "extra_attributes": {},
                "metrics": {
                    "pct_availability": 0,
                    "count_entities": 0,
                    "count_entities_up": 0,
                    "count_entities_down": 0,
                },
            }

        # remove extra_attributes if requested
        if self.remove_extra_attributes:
            results_summary_dict = {}
            final_results_records["extra_attributes"] = {}

        yield_record = {
            "_time": time.time(),
            "action": "success",
            "group": self.group,
            "object": self.object,
            "object_description": self.object_description,
            "status": status,
            "status_description": status_description,
            "status_description_short": status_description_short,
            "extra_attributes": results_summary_dict,
            "metrics": metrics,
            "_raw": final_results_records,
        }

        # yield
        yield yield_record

        # Log the run time
        run_time = round(time.time() - start, 3)
        logging.info(
            f'trackmesplkflxconverging has terminated, run_time={run_time}, '
            f'tenants_scope="{self.tenants_scope}", root_constraint="{root_constraint}", '
            f'entities={count_entities}, up={count_entities_up}, down={count_entities_down}'
        )


dispatch(TrackMeFlxConverging, sys.argv, sys.stdin, sys.stdout, __name__)
