# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import copy

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path

from itsi.searches import itsi_filter
from itsi.objects.itsi_entity import ItsiEntity
from ITOA.setup_logging import getLogger
from ITOA.controller_utils import ITOAError, handle_json_in_splunkd, load_validate_json, block_during_migration
from base_splunkd_rest import BaseSplunkdRest
from itsi.objects.itsi_service import ItsiService
from itsi.objects.itsi_deep_dive import ItsiDeepDive

logger = getLogger()
logger.debug("Initialized deep dive services log...")


# Set default as empty string as state store does not handle None value very well.
# Note focus_id has to be defined before creating it.
# Otherwise state store will save "None" value as "{ $undefined : true }"
NEW_DEEP_DIVE = {"mod_time": "",
                 "focus_id": None,
                 "title": "",
                 "description": "",
                 "is_named": False,
                 "latest_time": None,
                 "earliest_time": None,
                 "lane_settings_collection": [],
                 "acl": {"can_write": True, "can_share_global": True, "can_change_perms": True, "can_share_user": True,
                         "can_share_app": True, "owner": "nobody", "sharing": "app", "perms": {"write": [], "read": []},
                         "modifiable": True}
                 }


def handle_path_terms(f):
    def wrapper(self, *args, **kwargs):
        """
        path must be either
        deep_dive_services/entity_drilldown/retrieve
        """
        len_ = len(self.pathParts)
        if len_ < 3:
            raise ITOAError(status="404", message="Insufficient arguments provided.")
        return f(self, *args, **kwargs)
    return wrapper


class deep_dive_services(BaseSplunkdRest):
    """
    Provides splunkd endpoints for deep dive operations
    """
    owner = 'nobody'

    def _get_kpi_lane_settings(self, context_id, local_session_key):
        """
            Get kpis associated with service id and return lane settings for kpis
            @param context_id: string service id
            @param local_session_key: splunk session key

            @return: list of kpis lane settings
        """
        kpis_settings = []
        service_object = ItsiService(local_session_key, self.owner)
        service = service_object.get(self.owner, context_id)
        service_name = service["title"]
        logger.debug("service=%s for service_id=%s", service, context_id)
        kpis = service.get("kpis", [])
        if len(kpis) == 0:
            logger.warning("service=%s has no kpis", service_name)
        for kpi in kpis:
            kpis_settings.append(
                {"searchSource": "kpi", "laneType": "kpi", "kpiServiceId": context_id, "kpiId": kpi["_key"],
                 "title": kpi["title"], "subtitle": service_name, "thresholdIndicationEnabled": "enabled",
                 "thresholdIndicationType": "stateIndication"})
        return kpis_settings

    def _check_duplicate_adhoc_search(self, existing_lane_settings, new_adhoc_lane_settings):
        """
            Check if search already existed
            @param existing_lane_settings: list of existing lane settings of deep dive
            @param new_adhoc_lane_settings: list of new search settings

            @return: list of adhoc lane setting which does not exist in deep dive
        """
        uni_adhoc_lane_settings = []
        for new in new_adhoc_lane_settings:
            is_existed = False
            for old in existing_lane_settings:
                # Note, do not check based upon title or subtitle
                if old.get("search", None) == new.get("search", ""):
                    logger.debug("adhoc search already existed, search_lane_settings=%s", new)
                    is_existed = True
                    break
            if not is_existed:
                uni_adhoc_lane_settings.append(new)
        return uni_adhoc_lane_settings

    def _check_duplicate_based_upon_kpi(self, existing_lane_settings, new_kpis_lane_settings):
        """
            Check if new kpis are already existed in lane settings
            @param existing_lane_settings: list of existing lane settings of deep dive
            @param new_kpis_lane_settings: list list of kpis which need to be checked

            @return: list - list of kpis lane setting which does not exist in deep dive
        """
        uni_kpi_lane_settings = []
        for kpi in new_kpis_lane_settings:
            is_existed = False
            for existing in existing_lane_settings:
                # Note we do not check for title and subtitle
                if existing.get("searchSource", None) == "kpi" and existing.get("laneType",
                                                                                None) == "kpi" and existing.get("kpiId",
                                                                                                                None) == kpi.get(
                        "kpiId", "") and existing.get("kpiServiceId", None) == kpi.get("kpiServiceId", ""):
                    logger.debug("kpis already existed in kpi_lane_settings=%s", kpi)
                    is_existed = True
                    break
            if not is_existed:
                uni_kpi_lane_settings.append(kpi)
        return uni_kpi_lane_settings

    def _merge_duplicate_lane_settings(self, existing_lane_settings, new_adhoc_lane_settings, new_kpis_lane_settings):
        """
            Check and merge duplicate lane settings
            @param existing_lane_settings:  list    already existed lane settings of deep dive
            @param new_adhoc_lane_settings: list    new parameterized lane settings
            @param new_kpis_lane_settings:  list    kpi based lane settings

            @return: list - merged value of old and new lane settings
        """
        return (existing_lane_settings + self._check_duplicate_adhoc_search(existing_lane_settings, new_adhoc_lane_settings)
                + self._check_duplicate_based_upon_kpi(existing_lane_settings, new_kpis_lane_settings))

    def get_deep_dive_id(self, local_session_key, args):
        """
        Compute a deep dive ID if none exists and return it to caller.
        @param self: The self reference
        @param local_session_key: splunkd sessionKey
        @param args: Key word arguments extracted from the POST body
            Generally expected args are:
                _key: the deep dive to redirect to
                context_id: <service id>
                lane_settings_collection: array of <lane settings>
                include_all_kpi: boolean, if true any KPIs associated with the context_id will be added as lanes
        @return: deep dive id
        @rval: json string
        """
        LOG_PREFIX = '[get_deep_dive_id] '  # noqa F841
        context_id = args.get("context_id", None)

        response = {}

        if context_id is not None:
            kpis_lane_settings = []
            if args.get("include_all_kpi", False):
                kpis_lane_settings = self._get_kpi_lane_settings(context_id, local_session_key)
            # Try to load some old context
            filter_data = {"focus_id": context_id, "is_named": False}
            deep_dive_object = ItsiDeepDive(local_session_key, 'unknown')
            all_objects = deep_dive_object.get_bulk(owner=self.owner, filter_data=filter_data)
            logger.debug("all objects %s", all_objects)
            if len(all_objects) == 0:
                service_object = ItsiService(local_session_key, self.owner)
                context = service_object.get(self.owner, context_id)
                # Create a new unnamed deep_dive for this context
                unnamed = copy.deepcopy(NEW_DEEP_DIVE)
                unnamed["lane_settings_collection"] = load_validate_json(
                    args.get("lane_settings_collection", "[]")) + kpis_lane_settings
                unnamed["focus_id"] = context_id
                if context is None:
                    unnamed["focus_title"] = "UNNAMED_CONTEXT"
                else:
                    unnamed["focus_title"] = context.get("title", "UNNAMED_CONTEXT")
                response = deep_dive_object.create(self.owner, unnamed)
                logger.debug("create response=%s", response)
            else:
                # Pull it, enhance it and send it along
                response = all_objects[0]
                if args.get("earliest", None) is not None:
                    response["earliest_time"] = args.get("earliest")
                if args.get("latest", None) is not None:
                    response["latest_time"] = args.get("latest")
                request_args_lane_settings = load_validate_json(args.get("lane_settings_collection", "[]"))
                # Check duplicate
                response["lane_settings_collection"] = self._merge_duplicate_lane_settings(
                    response.get("lane_settings_collection", []), request_args_lane_settings, kpis_lane_settings)
                # Must remove the ID property from the edit request or it will 404 (it should 400, but whatever)
                obj_id = response.get("_key")
                del response["_key"]
                response = deep_dive_object.update(
                    self.owner,
                    obj_id,
                    response,
                    is_partial_data=args.get('is_partial_data', False)
                )
                logger.debug("edit response=%s", response)
        else:
            response["lane_settings_collection"] = args.get("lane_settings_collection", [])
        logger.debug("post response=%s", response)

        return response

    @block_during_migration
    @handle_json_in_splunkd
    @handle_path_terms
    def handle_POST(self):
        """
        Get an entity rule specification and a list of entity titles and return the entities with those titles that
        match the entity rule. The return comes as an array with objects holding the drilldown_name and array of
        entities.

        parsed args key word arguments extracted from the POST body
        'drilldowns': JSON list of with fields drilldown_name, (unique name of the drilldown)
                    entities (list of entity titles)
        'rule': entity rule specification
        """
        if self.pathParts[2] == 'entity_drilldown':
            LOG_PREFIX = '[entity_drilldown] '
            drilldowns = self.args.get("drilldowns", None)
            if drilldowns is None:
                raise ITOAError(status="400", message="Required parameter drilldowns missing.")
            drilldowns = load_validate_json(drilldowns)
            processed_drilldowns = []

            for drilldown in drilldowns:
                logger.debug("drilldown is %s", drilldown)
                drilldown_name = drilldown.get("drilldown_name")
                entityTitles = drilldown.get("entities", [])
                entityKeys = drilldown.get("entity_keys", [])
                rule = drilldown.get("rule", "all")

                processed_drilldown = {"drilldown_name": drilldown_name, "entities": []}

                if len(entityTitles) == 0 and len(entityKeys) == 0:
                    logger.debug("someone tried to see if a drilldown would work on no entities, it doesn't.")
                    processed_drilldowns.append(processed_drilldown)
                    continue
                else:
                    entity_title_filter = [{"title": entity_title} for entity_title in entityTitles]
                    entity_key_filter = [{"_key": entity_key} for entity_key in entityKeys]
                    entity_filter_combined_or = {"$or": entity_title_filter + entity_key_filter}

                entity_object = ItsiEntity(self.sessionKey, self.owner)
                if rule == "all":
                    logger.debug("All entities are valid for this drilldown, simply retrieve the entities")
                    entity_filter = entity_filter_combined_or
                elif rule == "kpi_title_match":
                    logger.debug("Custom drilldown set up via conf for matching KPI names, skipping")
                    continue
                else:
                    # PARSE ENTITY RULE
                    rule_filter = itsi_filter.ItsiFilter(rule).generate_kvstore_filter(self.sessionKey, self.owner)
                    if rule_filter is not None:
                        entity_filter = {"$and": [entity_filter_combined_or, rule_filter]}
                    else:
                        logger.error("Rule configured for entity drilldown is invalid, returning no entities as a result.")
                        processed_drilldowns.append(processed_drilldown)
                        continue

                logger.debug("entity filter is %s", entity_filter)
                valid_entities = entity_object.get_bulk(self.owner, filter_data=entity_filter)
                logger.debug("retrieved entities: %s", valid_entities)
                processed_drilldown["entities"] = valid_entities
                if len(valid_entities) > 0:
                    processed_drilldowns.append(processed_drilldown)

            self.response.setHeader('content-type', 'application/json')
            self.response.write(self.render_json(processed_drilldowns))

        if self.pathParts[2] == 'redirect':
            LOG_PREFIX = '[redirect] '  # noqa F841
            response = self.get_deep_dive_id(self.sessionKey, self.args)
            self.response.setHeader('content-type', 'application/json')
            self.response.write(self.render_json(response))

    @block_during_migration
    @handle_json_in_splunkd
    @handle_path_terms
    def handle_GET(self):
        '''
        Function only exists to test pointing a browser at the endpoint
        '''
        self.response.write('')
