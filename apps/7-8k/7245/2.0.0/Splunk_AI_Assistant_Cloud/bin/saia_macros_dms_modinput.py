# Copyright 2026 Cisco, Inc.
import json
import logging
import os
import re
import sys
import time
import uuid
from collections import OrderedDict, namedtuple
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union, cast

import splunk
from splunk import ResourceNotFound, SplunkdConnectionException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from spl_gen.remote.factory import SaiaApiFactory
from spl_gen.saia_data_models_collection import SaiaDataModelsCollection
from spl_gen.saia_lookups_collection import SaiaLookupsCollection
from spl_gen.saia_macros_collection import SaiaMacrosCollection
from spl_gen.utils import get_app_version, log_kwargs
from spl_gen.utils.log import add_log_extra_metadata, setup_logger
from spl_gen.utils.modinput.fields import BooleanField
from spl_gen.utils.modinput.json_modinput import JsonModularInput
from spl_gen.utils.requests import OutputMode, send_request
from spl_gen.utils.splunk_search import create_search_job, get_search_results
from splunklib.binding import handler
from splunklib.client import connect
from splunklib.searchcommands import environment

DEFAULT_MAX_CHUNK_RANGE_SECONDS = 86400

SA_CONF_URL = f"{splunk.rest.makeSplunkdUri()}servicesNS/nobody/Splunk_AI_Assistant_Cloud/configs/conf-saiamacrossummary"

logger = setup_logger("saia_macros_summary_modinput")
LOGGER_METADATA_TAG = "saia_macros_summary_modinput"


def time_modifier_from_timestamp(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


Macro = namedtuple("Macro", ["name", "use_time_range"])
TimeModifiers = namedtuple("TimeModifiers", ["earliest", "latest"])
Index_Sourcetype_Size = namedtuple(
    "Index_Sourcetype_Size", ["index", "sourcetype", "size"]
)
Stack_Server = namedtuple("Stack_Server", ["stack", "server"])


class SAIAMacrosSummaryModularInputConfig:
    """
    A class responsible for managing the Security Assistant mod_input configuration.
    """

    def __init__(self, session_key: str, this_logger: logging.Logger = logger):
        self.session_key = session_key
        self.logger = this_logger
        config_data = self._retrieve_sa_config_data()
        config = self._parse_sa_config_data(config_data)
        self.settings = config["settings"]
        self.status = config["status"]
        # self.search_params = config["search_params"]

    def _retrieve_sa_config_data(self) -> Dict:
        """
        Sends an authenticated GET request to the SA configuration endpoint
        and returns the parsed JSON response.
        """
        self.logger.debug(f"Fetching SA configuration data from {SA_CONF_URL}")
        return send_request(
            url=SA_CONF_URL,
            method="get",
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _update_sa_config_data(self) -> Dict:
        """
        Sends an authenticated POST request to the SA configuration status
        endpoint with the latest context update timestamp and returns the
        parsed JSON response.
        """
        self.logger.debug(f"Updating SA configuration data at {SA_CONF_URL}/status")
        return send_request(
            url=f"{SA_CONF_URL}/status",
            method="post",
            data={
                "last_context_update_timestamp": self.status[
                    "last_context_update_timestamp"
                ],
            },
            headers={
                "Authorization": f"Splunk {self.session_key}",
                "Accept": "application/json",
            },
            output_mode=OutputMode.PARSE_JSON,
        )

    def _parse_sa_config_data(self, config_data: Dict) -> Dict:
        """
        Parse raw SA configuration response into structured settings and status.

        Transforms the configuration response payload into a normalized dictionary
        containing `settings` and `status` sections with properly typed values.
        """
        self.logger.debug(
            "Parsing configuration entries into structured settings and status"
        )
        config = {}
        for entry in config_data["entry"]:
            content = entry["content"]
            if entry["name"] == "settings":
                config["settings"] = {
                    "context_update_interval_seconds": int(
                        content["context_update_interval_seconds"].strip() or 0
                    ),
                    "max_chunk_range_seconds": int(
                        content["max_chunk_range_seconds"].strip()
                        or DEFAULT_MAX_CHUNK_RANGE_SECONDS
                    )
                    or DEFAULT_MAX_CHUNK_RANGE_SECONDS,
                }
            elif entry["name"] == "status":
                config["status"] = {
                    "last_context_update_timestamp": int(
                        content["last_context_update_timestamp"].strip() or 0
                    ),
                }

        return config

    def update(
        self,
        *,
        last_context_update_timestamp: Optional[int] = None,
    ) -> None:
        """
        Update SA configuration status.

        Optionally updates the `last_context_update_timestamp` in the local status
        state and persists the changes to the SA configuration endpoint.
        """
        if last_context_update_timestamp is not None:
            self.status["last_context_update_timestamp"] = last_context_update_timestamp
        try:
            self._update_sa_config_data()
        except Exception as e:
            self.logger.exception("Failed to update SA configuration data: %s", e)

    def is_context_update_due(self) -> bool:
        """
        Determine whether a context update is due.

        Compares the current Unix timestamp with the last recorded context update
        timestamp and evaluates whether the configured update interval has elapsed.
        """
        return (
            int(time.time()) - self.status["last_context_update_timestamp"]
            >= self.settings["context_update_interval_seconds"]
        )

    def __str__(self):
        return f"settings={self.settings}, status={self.status}, search_params={{}}"


class SAIAMacrosSummaryModularInput(JsonModularInput):
    def __init__(self, this_logger: logging.Logger = logger):
        environment.app_root = os.path.join(os.path.dirname(__file__), "..")
        scheme_args = {
            "title": "Splunk AI Assistant for SPL Macros Summary Modular Input",
            "description": "Collects macros summary context for personalized SPL generation",
            "use_external_validation": "true",
            "streaming_mode": "json",
            "use_single_instance": "true",
            "supported_on_cloud": "true",
            "supported_on_onprem": "true",
            "supported_on_fedramp": "false",
        }
        self._chunk_count = 0
        args = [
            BooleanField(
                "debug",
                "Debug",
                "If true, debug logging is enabled.",
                required_on_create=False,
            )
        ]
        super().__init__(scheme_args, args, this_logger)

    def create_search(
        self,
        spl: str,
        time_modifiers: TimeModifiers,
        spl_name: str,
        sample_ratio=None,
        max_time=None,
    ) -> str:
        """
        creates a splunk search and returns the sid of the search
        :param spl: str -> spl string to generate a search fo
        :param time_modifiers: TimeModifers -> TimeModifiers tuple which contains earliest and latest times for the search
        :param spl_name: str -> name of the spl to log
        :param sample_ratio: int -> species how many samples should we sample
        :return sid: str -> a list of search results
        """

        self.logger.debug(f"Creating search job for '{spl_name}'")
        try:
            sid = create_search_job(
                search=spl,
                earliest=time_modifiers.earliest,
                latest=time_modifiers.latest,
                sample_ratio=sample_ratio,
                max_time=max_time,
                session_key=self._input_config.session_key,
                logger=self.logger,
            )
            if not sid:
                raise Exception(
                    f"Failed to create search job for '{spl_name}' SPL context"
                )
            return sid
        except SplunkdConnectionException as e:
            raise Exception(
                f"Failed to create search job for '{spl_name}' SPL context"
            ) from e

    def create_search_and_get_results(
        self,
        spl: str,
        time_modifiers: TimeModifiers,
        spl_name: str,
        sample_ratio=None,
        max_time=None,
    ) -> list:
        """
        creates a splunk search and returns the results of the search
        :param spl: str -> spl string to generate a search fo
        :param time_modifiers: TimeModifers -> TimeModifiers tuple which contains earliest and latest times for the search
        :param spl_name: str -> name of the spl to log
        :param sample_ratio: int -> species how many samples should we sample
        :return content: List[Dict[str, str]] -> a list of search results
        """

        try:
            sid = self.create_search(
                spl=spl,
                time_modifiers=time_modifiers,
                spl_name=spl_name,
                sample_ratio=sample_ratio,
                max_time=None,
            )
            self.logger.debug(f"Fetching search result for '{spl_name}' SPL context")

            content = get_search_results(
                sid=sid,
                session_key=self._input_config.session_key,
                logger=self.logger,
                strict_unicode=False,
            )
            if content is None:
                self.logger.warning(
                    f"Failed to fetch search result for '{spl_name}' SPL context"
                )
                return []
            return content
        except (SplunkdConnectionException, ResourceNotFound) as e:
            raise Exception(
                f"Failed to fetch search result for '{spl_name}' SPL context"
            ) from e

    def _connect_service(self, user: str):
        """
        Establish a connection to the SAIA service.

        Creates and returns a service connection using the current session token
        and predefined connection parameters.
        """
        self.logger.info("Connecting to SAIA service")
        return connect(
            token=self._input_config.session_key,
            handler=handler(timeout=1),
            host="127.0.0.1",
            app="-",
            owner="-",
            retries=2,
        )

    def _get_macros_dms_lookups_metadata(
        self,
        *,
        earliest: int,
        latest: int,
        macros=False,
        lookups=False,
        data_models=False,
    ) -> Any:
        """
        Retrieve metadata for macros, lookups, or data models within a time range.

        Executes a REST-based SPL query to collect metadata for the selected object
        type (macros, lookups, or data models) using the provided time boundaries.

        Args:
            earliest (int): Earliest time boundary as a Unix timestamp.
            latest (int): Latest time boundary as a Unix timestamp.
            macros (bool, optional): If True, retrieves macros metadata.
            lookups (bool, optional): If True, retrieves lookups metadata.
            data_models (bool, optional): If True, retrieves data models metadata.

        Returns:
            Any: Search results returned from `create_search_and_get_results`,
            typically containing metadata records for the selected object type.
        """

        macros_spl_query = "| rest /services/configs/conf-macros| fields title definition args eai:acl.app eai:acl.perms.read"
        lookups_spl_query = "| rest /services/data/transforms/lookups | fields title,type, filename, match_type, min_matches, max_matches, eai:acl.app, fields_list, eai:acl.perms.read"
        datamodels_spl_query = (
            "| rest /services/datamodel/model | table title, acceleration, description"
        )

        time_modifiers = TimeModifiers(
            earliest=time_modifier_from_timestamp(earliest),
            latest=time_modifier_from_timestamp(latest),
        )
        if macros:
            spl_query = macros_spl_query
            spl_name = "getting_macros"
            self.logger.info("Obtain data for MACROS")
        elif lookups:
            spl_query = lookups_spl_query
            spl_name = "getting_lookups"
            self.logger.info("Obtain data for LOOKUPS")
        elif data_models:
            spl_query = datamodels_spl_query
            spl_name = "getting_datamodels"
            self.logger.info("Obtain data for DATAMODELS")
        content = self.create_search_and_get_results(
            spl=f"{spl_query}",
            time_modifiers=time_modifiers,
            spl_name=spl_name,
            max_time=120,
        )
        self.logger.info("Obtained data")
        self.logger.info(content)
        return content

    def _get_enriched_macros_metadata(self, *, earliest: int, latest: int) -> List[Any]:
        """
        Fetch enriched macros metadata for the given time range.

        Runs an SPL pipeline that reads macros from `saia_macros`, expands referenced
        lookups and data models, joins against `saia_lookups` and `saia_datamodels`,
        and aggregates the enriched fields into a per-macro result set.

        Args:
            earliest (int): Earliest time boundary as a Unix timestamp.
            latest (int): Latest time boundary as a Unix timestamp.

        Returns:
            List[Any]: Enriched macros metadata results. Returns an empty list if the
            search fails or an exception is raised.
        """

        try:
            spl_query = """| inputlookup saia_macros
| streamstats count AS row_id
| mvexpand lookups_used
| eval lookup_app_name = mvindex(split(lookups_used, "."), 0),
       lookup_title_in  = mvindex(split(lookups_used, "."), 1)
| lookup saia_lookups app_name AS lookup_app_name title AS lookup_title_in
    OUTPUTNEW fields_list AS lookup_fields_list,
             title       AS lookup_title,
             type        AS lookup_type
| eval lookup_key = "{'title':'".lookup_title."','fields_list':'".lookup_fields_list."','type':'".lookup_type."'}"
| mvexpand datamodels_used
| eval datamodel_title = mvindex(split(datamodels_used, "."), 0),
       dataset_title   = mvindex(split(datamodels_used, "."), 1)
| lookup saia_datamodels data_model AS datamodel_title name AS dataset_title
    OUTPUTNEW updated_spl_query
| eval datamodel_key = "{'datamodel_name':'".datamodel_title."','dataset_name':'".dataset_title."','spl_used':'".updated_spl_query."'}"
| stats values(lookup_key)    AS lookup_key
        values(datamodel_key) AS datamodel_key
        first(title)          AS title
        first(definition)     AS definition
        first(updated_spl)    AS updated_spl
        first(macros_used)    AS macros_used
        first(app_name)       AS app_name
        first(args)           AS args
        first(user_id)        AS user_id
        first(datamodels_used) AS datamodels_used
    BY row_id
| fields title definition updated_spl macros_used app_name args lookup_key datamodels_used datamodel_key user_id
            """
            time_modifiers = TimeModifiers(
                earliest=time_modifier_from_timestamp(earliest),
                latest=time_modifier_from_timestamp(latest),
            )
            self.logger.info("Obtain data for enriching MACROS")
            content = self.create_search_and_get_results(
                spl=f"{spl_query}",
                time_modifiers=time_modifiers,
                spl_name="enriching_macros",
                max_time=120,
            )
            self.logger.info("Obtained data for enriching MACROS")
            self.logger.info(
                f"Length of content: {len(content)} and content is: {content}"
            )
            self.logger.info(f"type of content: {type(content)}")

            return content
        except Exception as e:
            self.logger.exception("Error fetching enriched macros metadata: %s", e)
            return []

    def _get_enriched_datamodels_metadata(
        self, *, earliest: int, latest: int
    ) -> List[Any]:
        """
        Fetch enriched data model metadata for the given time range.

        Runs an SPL pipeline that reads data models from `saia_datamodels`, expands
        referenced lookups, macros, and related data models, joins against
        `saia_lookups`, `saia_macros`, and `saia_datamodels`, and aggregates the
        enriched fields into a per-row result set.

        Args:
            earliest (int): Earliest time boundary as a Unix timestamp.
            latest (int): Latest time boundary as a Unix timestamp.

        Returns:
            List[Any]: Enriched data model metadata results. Returns an empty list if
            the search fails or an exception is raised.
        """

        try:
            spl_query = """
| inputlookup saia_datamodels
| streamstats count AS row_id
| mvexpand lookups_used
| eval lookup_app_name = mvindex(split(lookups_used, "."), 0),
       lookup_title_in  = mvindex(split(lookups_used, "."), 1)
| lookup saia_lookups app_name AS lookup_app_name title AS lookup_title_in
    OUTPUTNEW fields_list AS lookup_fields_list,
             title       AS lookup_title,
             type        AS lookup_type
| eval lookup_key = "{'title':'".lookup_title."','fields_list':'".lookup_fields_list."','type':'".lookup_type."'}"
| mvexpand macros_used
| eval macro_app_name = mvindex(split(macros_used, "."), 0),
       macro_title_in  = mvindex(split(macros_used, "."), 1)
| lookup saia_macros app_name AS macro_app_name title AS macro_title_in
    OUTPUTNEW content AS macro_content,
              title   AS macro_title
| eval macro_key = "{'title':'".macro_title."','content':'".macro_content."'}"
| mvexpand datamodels_used
| eval datamodel_title = mvindex(split(datamodels_used, "."), 0),
       dataset_title   = mvindex(split(datamodels_used, "."), 1)
| lookup saia_datamodels data_model AS datamodel_title name AS dataset_title
    OUTPUTNEW updated_spl_query
| eval datamodel_key = "{'datamodel_name':'".datamodel_title."','dataset_name':'".dataset_title."','spl_used':'".updated_spl_query."'}"
| stats values(macro_key)      AS macro_key
        values(lookup_key)     AS lookup_key
        values(datamodel_key)  AS datamodel_key
        first(name)            AS name
        first(type)            AS type
        first(fields)          AS fields
        first(updated_spl_query) AS updated_spl_query
        first(data_model)      AS data_model
        first(user_id)         AS user_id
        first(acceleration)    AS acceleration
        first(app_name)        AS app_name
        first(macros_used)     AS macros_used
        first(datamodels_used) AS datamodels_used
        first(lookups_used)    AS lookups_used
    BY row_id
| fields name type fields updated_spl_query macros_used macro_key lookup_key lookups_used datamodels_used datamodel_key data_model user_id acceleration app_name
"""
            time_modifiers = TimeModifiers(
                earliest=time_modifier_from_timestamp(earliest),
                latest=time_modifier_from_timestamp(latest),
            )
            self.logger.info("Obtaining enriched data for DATA MODELS")
            content = self.create_search_and_get_results(
                spl=spl_query,
                time_modifiers=time_modifiers,
                spl_name="enriching_datamodels",
                max_time=120,
            )
            self.logger.info("Obtained enriched data for DATA MODELS")
            self.logger.info(
                f"Length of enriched datamodel content: {len(content)} and content is: {content}"
            )
            return content
        except Exception as e:
            self.logger.exception("Error fetching enriched datamodels metadata: %s", e)
            return []

    def _get_datamodels_metadata(
        self, *, earliest: int, latest: int
    ) -> List[Dict[str, Any]]:
        """
        Retrieve data model metadata within a given time range.

        Executes a REST-based SPL query to collect data model metadata, including
        acceleration and description fields. Attempts to parse JSON-encoded fields
        into dictionaries, logging warnings if parsing fails.

        Args:
            earliest (int): Earliest time boundary as a Unix timestamp.
            latest (int): Latest time boundary as a Unix timestamp.

        Returns:
            List[Dict[str, Any]]: A list of data model metadata records with
            parsed `acceleration` and `description` fields where applicable.
        """

        spl_query = "| rest /services/datamodel/model | table title, acceleration, description, eai:acl.app, eai:acl.perms.read"
        time_modifiers = TimeModifiers(
            earliest=time_modifier_from_timestamp(earliest),
            latest=time_modifier_from_timestamp(latest),
        )
        # Create search and get results for data models
        self.logger.info("Obtain data for Data models")
        content = self.create_search_and_get_results(
            spl=f"{spl_query}",
            time_modifiers=time_modifiers,
            spl_name="getting_datamodels",
            max_time=120,
        )
        self.logger.info("Obtained data for Data models")
        self.logger.info("len content" + str(len(content)))
        for row in content:
            for field in ("acceleration", "description"):
                json_blob = row.get(field)
                if isinstance(json_blob, str):
                    try:
                        row[field] = json.loads(json_blob)
                    except json.JSONDecodeError as e:
                        self.logger.warning(
                            f"Failed to parse JSON for datamodel field '{field}': {e}"
                        )
        self.logger.info("len content" + str(len(content)))
        for row in content:
            for field in ("acceleration", "description"):
                json_blob = row.get(field)
                if isinstance(json_blob, str):
                    try:
                        row[field] = json.loads(json_blob)
                    except json.JSONDecodeError as e:
                        self.logger.warning(
                            f"Failed to parse JSON for datamodel field '{field}': {e}"
                        )
        return content

    @staticmethod
    def _to_bool(value: Any) -> bool:
        """
        Convert a value to a boolean.

        Interprets common string, numeric, and boolean representations and
        returns their boolean equivalent. Unrecognized or unsupported values
        default to False.

        Args:
            value (Any): The value to convert.

        Returns:
            bool: The boolean interpretation of the provided value.
        """

        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "t", "yes", "y"}:
                return True
            if lowered in {"0", "false", "f", "no", "n"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return False

    def _parse_macros_payload(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parse raw macros payload into a normalized list of macro dictionaries.

        Extracts macro entries from various possible response structures
        (e.g., `entry`, `results`, or a direct list), filters out incomplete
        records, and returns a standardized list of macro metadata.

        Args:
            raw_data (Any): Raw response payload containing macro data.

        Returns:
            List[Dict[str, Any]]: A list of parsed macro dictionaries including
            title, definition, content, and optional metadata such as args,
            app_name, and user_id.
        """

        entries: List[Dict[str, Any]] = []
        if isinstance(raw_data, dict):
            if isinstance(raw_data.get("entry"), list):
                entries = cast(List[Dict[str, Any]], raw_data.get("entry"))
            elif isinstance(raw_data.get("results"), list):
                entries = cast(List[Dict[str, Any]], raw_data.get("results"))
        elif isinstance(raw_data, list):
            entries = cast(List[Dict[str, Any]], raw_data)

        macros: List[Dict[str, Any]] = []
        self.logger.info(f"Length of macros payload: {len(entries)}")
        for entry in entries:
            content = entry.get("content", entry)
            title = entry.get("name") or content.get("title")
            definition = content.get("definition")
            args = content.get("args")
            app_name = content.get("eai:acl.app")
            user_id = content.get("eai:acl.perms.read")
            if not title or not definition:
                continue
            macro_payload: Dict[str, Any] = {
                "title": title,
                "definition": definition,
                "content": content,
            }
            if args:
                macro_payload["args"] = args
            if app_name:
                macro_payload["app_name"] = app_name
            if user_id:
                macro_payload["user_id"] = user_id
            macros.append(macro_payload)
        return macros

    def _parse_datamodel_fields(self, fields_section: Any) -> List[Dict[str, Any]]:
        """
        Parse and normalize a data model fields section.

        Accepts a JSON string, dictionary, or list representing data model fields,
        normalizes the structure, and extracts relevant field metadata.

        Args:
            fields_section (Any): The fields section of a data model, which may be
                a JSON string, dictionary, or list.

        Returns:
            List[Dict[str, Any]]: A list of parsed field dictionaries containing
            `fieldName`, `type`, and `displayName`. Returns an empty list if the
            input cannot be parsed or is invalid.
        """

        if isinstance(fields_section, str):
            try:
                fields_section = json.loads(fields_section)
            except json.JSONDecodeError:
                return []

        if isinstance(fields_section, dict):
            iterable = fields_section.values()
        elif isinstance(fields_section, list):
            iterable = fields_section
        else:
            return []

        parsed_fields: List[Dict[str, Any]] = []
        for field in iterable:
            if not isinstance(field, dict):
                continue
            field_name = field.get("fieldName") or field.get("name")
            if not field_name:
                continue
            parsed_fields.append(
                {
                    "fieldName": field_name,
                    "type": field.get("type") or field.get("fieldType") or "",
                    "displayName": field.get("displayName") or field_name,
                }
            )
        return parsed_fields

    def _parse_datamodel_objects(self, objects_section: Any) -> List[Dict[str, Any]]:
        """
        Parse and normalize a data model objects section.

        Accepts a JSON string, dictionary, or list representing data model objects,
        extracts object metadata, and parses associated fields using
        `_parse_datamodel_fields`.

        Args:
            objects_section (Any): The objects section of a data model, which may be
                a JSON string, dictionary, or list.

        Returns:
            List[Dict[str, Any]]: A list of parsed object dictionaries containing
            `objectName`, `displayName`, and a list of parsed `fields`. Returns an
            empty list if the input cannot be parsed or is invalid.
        """

        if isinstance(objects_section, str):
            try:
                objects_section = json.loads(objects_section)
            except json.JSONDecodeError:
                return []

        objects: List[Dict[str, Any]] = []
        if isinstance(objects_section, dict):
            iterable = ((name, data) for name, data in objects_section.items())
        elif isinstance(objects_section, list):
            iterable = (
                (obj.get("objectName") or obj.get("name"), obj)
                for obj in objects_section
                if isinstance(obj, dict)
            )
        else:
            return objects

        for object_name, object_data in iterable:
            if not isinstance(object_data, dict):
                continue
            resolved_name = object_name or object_data.get("objectName")
            if not resolved_name:
                continue
            fields = self._parse_datamodel_fields(object_data.get("fields"))
            objects.append(
                {
                    "objectName": resolved_name,
                    "displayName": object_data.get("displayName") or resolved_name,
                    "fields": fields,
                }
            )
        return objects

    def _parse_lookup_payload(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Parse and filter lookup payload data.

        Extracts a predefined subset of fields from each lookup entry in the
        provided raw payload.

        Args:
            raw_data (Any): Iterable containing lookup metadata records.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing only the
            selected lookup fields (`title`, `type`, `fields_list`,
            `eai:acl.app`, and `eai:acl.perms.read`).
        """

        parsed_list = []
        fields_to_extract = [
            "title",
            "type",
            "fields_list",
            "eai:acl.app",
            "eai:acl.perms.read",
        ]
        for item in raw_data:
            if isinstance(item, dict):
                filtered = {
                    key: item.get(key) for key in fields_to_extract if key in item
                }
                parsed_list.append(filtered)
        return parsed_list

    def retain_simple_macro_queries(self, data) -> List[Dict[str, Any]]:
        """
        Filter and retain simple macro queries.

        Keeps only macro entries whose SPL definitions do not reference
        other macros (i.e., contain no nested macro usage). Queries that
        include lookups or data model references are retained as long as
        they do not reference additional macros.

        Args:
            data (List[Dict[str, Any]]): List of macro metadata dictionaries,
                each expected to contain a `definition` field.

        Returns:
            List[Dict[str, Any]]: Filtered list containing only simple,
            non-nested macro queries.
        """

        final_macros = []
        for query in data:
            # macro = await self.extract_single_macro(query.get('definition'))
            macro = self.extract_macros_datamodels_lookups(
                query.get("definition"), return_only_macros=True
            )
            if not macro:
                final_macros.append(query)
        return final_macros

    def _split_app_qualifier(self, value: str, default_app: str) -> Tuple[str, str]:
        """
        Split an app-qualified identifier into its components.

        Parses values in the format "app:object" and returns a tuple of
        (app, object). If no app prefix is present, the provided
        `default_app` is used. Only the first ':' is treated as the delimiter.

        Args:
            value (str): The app-qualified value to split.
            default_app (str): The default app name to use if no prefix is present.

        Returns:
            Tuple[str, str]: A tuple containing (app, object).
        """

        if ":" in value:
            app, obj = value.split(":", 1)
            return app or default_app, obj or value
        return default_app, value

    def extract_macros_datamodels_lookups(
        self,
        spl_query: str,
        return_only_macros: bool = False,
        default_app: str = "search",
    ) -> Union[List[str], Tuple[List[str], List[str], List[str]]]:
        """
        Extract referenced macros, data models, and lookups from an SPL query.

        Parses the provided SPL query string to identify:
        - Macros wrapped in backticks, returned as app-qualified names (app.macro).
        - Data model references from `datamodel` and `from datamodel=...` syntax,
          returned as `datamodel.dataset` where applicable.
        - Lookup references from `lookup` and `inputlookup`, returned as
          app-qualified names (app.lookup).

        If `return_only_macros` is True, only the list of macro references is returned.

        Args:
            spl_query (str): The SPL query text to parse.
            return_only_macros (bool, optional): If True, return only macro references.
                Defaults to False.
            default_app (str, optional): Default app name used when references are not
                explicitly app-qualified (no "app:object" prefix). Defaults to "search".

        Returns:
            Union[List[str], Tuple[List[str], List[str], List[str]]]:
                If `return_only_macros` is True, returns `List[str]` of macro references
                formatted as "app.macro". Otherwise returns a tuple:
                (macro_dotted, data_model_names, lookup_dotted).
        """

        # ---------- MACROS ----------
        macro_pattern = re.compile(r"`([A-Za-z0-9_:-]+(?:\([^`]*?\))?)`")
        macro_ordered = OrderedDict()
        for match in macro_pattern.finditer(spl_query):
            raw = match.group(1)
            app, macro = self._split_app_qualifier(raw, default_app)
            macro_ordered.setdefault((app, macro), None)

        macro_tuples = list(macro_ordered.keys())
        macro_dotted = [f"{app}.{macro}" for app, macro in macro_tuples]

        if return_only_macros:
            return macro_dotted

        # ---------- DATA MODELS ----------
        datamodel_pipe_pattern = re.compile(
            r"\bdatamodel\s+([A-Za-z0-9_]+)(?:\s+([A-Za-z0-9_]+))?",
            re.IGNORECASE,
        )

        datamodel_from_pattern = re.compile(
            r"\bfrom\s+datamodel\s*=\s*([A-Za-z0-9_]+)(?:\.([A-Za-z0-9_]+))?",
            re.IGNORECASE,
        )

        data_model_map = OrderedDict()

        for match in datamodel_pipe_pattern.finditer(spl_query):
            model = match.group(1)
            dataset = match.group(2)
            data_model_map.setdefault(model, set())
            if dataset:
                data_model_map[model].add(dataset)

        for match in datamodel_from_pattern.finditer(spl_query):
            model = match.group(1)
            dataset = match.group(2)
            data_model_map.setdefault(model, set())
            if dataset:
                data_model_map[model].add(dataset)

        data_model_names = []
        for model, datasets in data_model_map.items():
            if datasets:
                for ds in sorted(datasets):
                    data_model_names.append(f"{model}.{ds}")
            else:
                data_model_names.append(model)

        # ---------- LOOKUPS ----------
        lookup_pattern = re.compile(
            r"\b(?:lookup|inputlookup)\s+([A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?)",
            re.IGNORECASE,
        )

        lookup_ordered = OrderedDict()
        for match in lookup_pattern.finditer(spl_query):
            raw = match.group(1)
            app, lookup = self._split_app_qualifier(raw, default_app)
            lookup_ordered.setdefault((app, lookup), None)

        lookup_tuples = list(lookup_ordered.keys())
        lookup_dotted = [f"{app}.{lookup}" for app, lookup in lookup_tuples]

        return (
            macro_dotted,
            data_model_names,
            lookup_dotted,
        )

    def _parse_dotted(self, dotted: str, default_app: str):
        """Parse 'app.name' -> (app, name). If no '.', treat as default_app."""
        if "." in dotted:
            app, name = dotted.split(".", 1)
            return app or default_app, name or dotted
        return default_app, dotted

    def _macro_token_to_dotted(self, raw: str, default_app: str) -> str:
        """
        Convert a raw macro token (inside backticks, WITHOUT backticks) into dotted form.
        raw examples:
          - macro
          - macro(args)
          - some_app:macro
          - some_app:macro(args)
        """
        app, macro = self._split_app_qualifier(raw, default_app)
        return f"{app}.{macro}"

    def sync_replace_macro(
        self,
        macro_name: str,  # dotted "app.macro" preferred; non-dotted still supported
        original_text: str,
        lookup: dict,
        app_name: Optional[str] = None,  # default context if macro_name is not dotted
        seen: Optional[set] = None,
        collected_args: Optional[list] = None,
        default_app: str = "search",
    ) -> str:
        """
        Async macro replacement that supports nested macros.

        - Expands macro_name using its 'definition' (not updated_spl)
        - Recursively expands nested macros
        - Does NOT wrap expansions in parentheses
        - Optionally collects args for each expanded macro in collected_args
        """

        if seen is None:
            seen = set()

        if "." in macro_name:
            macro_app, macro_key = self._parse_dotted(macro_name, default_app)
        else:
            macro_app = app_name or default_app
            macro_key = macro_name

        seen_key = (macro_app, macro_key)
        if seen_key in seen:
            return original_text
        seen.add(seen_key)

        if collected_args is None:
            collected_args = []

        macro_info = lookup.get(macro_app, {}).get(macro_key, {})
        expanded = macro_info.get("definition")
        if not expanded:
            return original_text

        macro_args = macro_info.get("args")
        if macro_args:
            for arg in macro_args:
                if arg not in collected_args:
                    collected_args.append(arg)

        macro_call_pattern = re.compile(r"`([A-Za-z0-9_:-]+(?:\([^`]*?\))?)`")

        updated_parts = []
        last_end = 0

        for match in macro_call_pattern.finditer(expanded):
            updated_parts.append(expanded[last_end : match.start()])

            raw_inner = match.group(1)  # no backticks
            inner_dotted = self._macro_token_to_dotted(raw_inner, default_app=macro_app)

            replacement_text = self.sync_replace_macro(
                inner_dotted,
                match.group(0),  # includes backticks, used as fallback if not found
                lookup,
                app_name=macro_app,  # nested unqualified macros inherit current macro_app
                seen=seen,
                collected_args=collected_args,
                default_app=default_app,
            )

            updated_parts.append(replacement_text)
            last_end = match.end()

        updated_parts.append(expanded[last_end:])
        return "".join(updated_parts)

    def retain_already_present_macros(
        self, data: list, lookup: dict, default_app: str = "search"
    ) -> List[Dict[str, Any]]:
        """
        Retain macros whose referenced macros are already present and expand them in-place.

        Filters the provided macro metadata list to include only entries whose SPL
        `definition` references macros that all exist in the supplied `lookup` map.
        For retained entries, replaces each macro invocation with its synchronized
        representation via `sync_replace_macro`, builds an `updated_spl_query`, and
        merges any collected arguments into the macro's `args` list.

        Args:
            data (list): List of macro metadata dictionaries. Each element is expected
                to include `definition` and `app_name`, and may include `args`.
            lookup (dict): Nested mapping of available macros by app, used to validate
                that all referenced macros exist (e.g., `{app: {macro: ...}}`).
            default_app (str, optional): Default app name used when a macro reference
                is not explicitly app-qualified. Defaults to "search".

        Returns:
            List[Dict[str, Any]]: List of retained macro metadata dictionaries with
            `updated_spl_query` populated and `args` updated to include any newly
            collected arguments.
        """

        self.logger.info("In retain_already_present_macros")
        retained_list = []

        macro_call_pattern = re.compile(r"`([A-Za-z0-9_:-]+(?:\([^`]*?\))?)`")

        for element in data:
            definition = element.get("definition")
            if not definition:
                continue

            element_app = element.get("app_name")
            if not element_app:
                continue

            macro_dotted, _, _ = self.extract_macros_datamodels_lookups(
                definition, default_app=element_app
            )
            if not macro_dotted:
                continue

            # Validate: every referenced macro exists in lookup under its app
            missing = False
            for dotted in macro_dotted:
                app, macro = self._parse_dotted(dotted, element_app)
                if app not in lookup or macro not in lookup.get(app, {}):
                    missing = True
                    break
            if missing:
                continue

            updated_parts = []
            last_end = 0
            collected_args = []

            for match in macro_call_pattern.finditer(definition):
                updated_parts.append(definition[last_end : match.start()])

                raw_macro = match.group(1)
                dotted_name = self._macro_token_to_dotted(
                    raw_macro, default_app=element_app
                )

                replacement_text = self.sync_replace_macro(
                    dotted_name,
                    match.group(0),
                    lookup,
                    app_name=element_app,
                    collected_args=collected_args,
                    default_app=default_app,
                )

                updated_parts.append(replacement_text)
                last_end = match.end()

            updated_parts.append(definition[last_end:])
            updated_definition = "".join(updated_parts)

            element["updated_spl_query"] = updated_definition

            base_args = element.get("args") or []
            expanded_args = list(base_args)
            for arg in collected_args:
                if arg not in expanded_args:
                    expanded_args.append(arg)
            element["args"] = expanded_args

            retained_list.append(element)

        return retained_list

    def remove_items(self, main_list, items_to_remove) -> List[Any]:
        """
        Remove specified items from a list.

        Creates and returns a new list containing only the elements from
        `main_list` that are not present in `items_to_remove`.

        Args:
            main_list (List[Any]): The original list of items.
            items_to_remove (List[Any]): Items that should be excluded
                from the resulting list.

        Returns:
            List[Any]: A new list with the specified items removed.
        """

        return [item for item in main_list if item not in items_to_remove]

    def augment_macro_data(
        self, data, existing_macros_dict, level=0
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Dict[str, Any]]]]:
        """
        Augment macro metadata with dependency and bookkeeping information.

        Enriches each macro entry with detected macro, lookup, and data model
        dependencies, usage flags, update timestamp, hierarchy level, and ensures
        `updated_spl_query` is populated. Also indexes macros into
        `existing_macros_dict` by app name and title.

        Args:
            data (List[Dict[str, Any]]): List of macro metadata dictionaries.
            existing_macros_dict (Dict[str, Dict[str, Dict[str, Any]]]): Nested
                dictionary keyed by app name, then macro title, used to store and
                reference macros.
            level (int, optional): Hierarchy or recursion level indicator.
                Defaults to 0.

        Returns:
            Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Dict[str, Any]]]]:
                - Updated list of macro metadata entries.
                - Updated nested dictionary indexed by app and macro title.
        """

        now_iso = datetime.now(timezone.utc).isoformat()

        for element in data:
            macro_names, datamodel_names, lookup_names = (
                self.extract_macros_datamodels_lookups(
                    element.get("definition"), default_app=element.get("app_name")
                )
            )
            element["uses_lookup"] = bool(lookup_names)
            element["uses_dataset"] = bool(datamodel_names)
            element["uses_macros"] = bool(macro_names)
            element["lookups_used"] = lookup_names
            element["datasets_used"] = datamodel_names
            element["macros_used"] = macro_names
            element["last_updated"] = now_iso
            element["level"] = level

            # Ensure updated_spl_query exists (default to definition)
            element.setdefault("updated_spl_query", element.get("definition"))

            # Index in existing_macros_dict by title
            title = element.get("title")
            if element.get("app_name") not in existing_macros_dict:
                existing_macros_dict[element.get("app_name")] = {}
            if title is not None:
                existing_macros_dict[element.get("app_name")][title] = element

        return data, existing_macros_dict

    def macros_data_transformation(
        self,
        data: list,
        nested_level=4,
    ) -> List[Dict[str, Any]]:
        """
        Transform macro data across nested dependency levels.

        Iteratively processes macro definitions to resolve dependencies up to
        the specified `nested_level`. At level 0, retains simple (non-nested)
        macros. At subsequent levels, retains macros whose referenced macros
        are already present. Each retained level is augmented with dependency
        metadata and accumulated into the final transformed result.

        Args:
            data (list): List of macro metadata dictionaries to process.
            nested_level (int, optional): Maximum number of dependency resolution
                levels to traverse. Defaults to 4.

        Returns:
            List[Dict[str, Any]]: Fully transformed list of macro metadata entries
            enriched with dependency information and ordered by resolution level.
        """

        final_transformed_data = []
        existing_macros_dict = {}
        for i in range(nested_level):
            if i == 0:
                filtered_level_data = self.retain_simple_macro_queries(data)
            else:
                filtered_level_data = self.retain_already_present_macros(
                    data, existing_macros_dict
                )
            self.logger.info(f"len of data before filtering: {len(data)}")
            data = self.remove_items(data, filtered_level_data)
            self.logger.info(f"len of data after filtering: {len(data)}")
            filtered_level_data, existing_macros_dict = self.augment_macro_data(
                filtered_level_data, existing_macros_dict, level=i
            )
            self.logger.info(
                f"Filtered data at level {i} and length of data {len(filtered_level_data)}: {filtered_level_data}"
            )
            final_transformed_data.extend(filtered_level_data)
            if not data:
                break
        return final_transformed_data

    def write_macros_data_to_kv_store(self, data) -> bool:
        """
        Write transformed macro metadata to the KV store.

        Establishes a service connection, clears the existing
        `SaiaMacrosCollection`, and caches the provided macro data
        into the KV store.

        Args:
            data (List[Dict[str, Any]]): List of transformed macro
                metadata entries to be stored.

        Returns:
            bool: True if the operation completes successfully.
        """

        user = "splunk-system-user"
        service = connect(
            token=self._input_config.session_key,
            handler=handler(timeout=1),
            host="127.0.0.1",
            app="Splunk_AI_Assistant_Cloud",
            owner=user,
            retries=2,
        )

        collection = SaiaMacrosCollection(service)
        self.logger.info("Caching MACROS metadata to KV store")
        collection.all_clear()
        self.logger.info("Cleared MACROS metadata from KV store")
        self.cache_results_to_kvstore(data, collection)

        self.logger.info("Cached MACROS metadata to KV store as below")
        return True

    def write_lookups_data_to_kv_store(self, data) -> bool:
        """
        Write lookup metadata to the KV store.

        Establishes a service connection, clears the existing
        `SaiaLookupsCollection`, and caches the provided lookup data
        into the KV store.

        Args:
            data (List[Dict[str, Any]]): List of lookup metadata
                entries to be stored.

        Returns:
            bool: True if the operation completes successfully.
        """

        user = "splunk-system-user"
        service = connect(
            token=self._input_config.session_key,
            handler=handler(timeout=1),
            host="127.0.0.1",
            app="Splunk_AI_Assistant_Cloud",
            owner=user,
            retries=2,
        )

        collection = SaiaLookupsCollection(service)
        self.logger.info("Caching Lookups metadata to KV store")
        collection.all_clear()
        self.logger.info("Cleared Lookups metadata from KV store")
        self.cache_results_to_kvstore(data, collection, macros=False, lookups=True)

        self.logger.info("Cached Lookups metadata to KV store as below")
        return True

    def write_data_models_data_to_kv_store(self, data) -> bool:
        """
        Write data model metadata to the KV store.

        Establishes a service connection, clears the existing
        `SaiaDataModelsCollection`, and caches the provided data model
        metadata into the KV store.

        Args:
            data (List[Dict[str, Any]]): List of data model metadata
                entries to be stored.

        Returns:
            bool: True if the operation completes successfully.
        """

        user = "splunk-system-user"
        service = connect(
            token=self._input_config.session_key,
            handler=handler(timeout=1),
            host="127.0.0.1",
            app="Splunk_AI_Assistant_Cloud",
            owner=user,
            retries=2,
        )

        collection = SaiaDataModelsCollection(service)
        self.logger.info("Caching DATA MODELS metadata to KV store")
        collection.all_clear()
        self.logger.info("Cleared DATA MODELS metadata from KV store")
        self.cache_results_to_kvstore(data, collection, macros=False, datamodels=True)

        self.logger.info("Cached DATA MODELS metadata to KV store as below")
        return True

    def get_full_dataset_query(self, ds, dataset_query_map) -> str:
        """
        Construct the full SPL query for a given dataset.

        Builds the dataset-specific SPL query based on its parent type and
        constraints. Handles special parent types such as `BaseSearch`,
        `BaseTransaction`, and `BaseEvent`, and optionally concatenates
        parent queries from `dataset_query_map`.

        Args:
            ds (Dict[str, Any]): Dataset definition containing fields such as
                `parentName`, `baseSearch`, `constraints`, and `lineage`.
            dataset_query_map (Dict[str, str]): Mapping of dataset names to
                their resolved SPL queries for parent lookup.

        Returns:
            str: The constructed SPL query for the specified dataset.
        """

        parent = ds.get("parentName", "")
        if parent == "BaseSearch":
            return ds.get("baseSearch", "")
        if parent == "BaseTransaction":
            return ""
        if (
            len(ds.get("constraints", [])) <= len(ds.get("lineage").split("."))
            and not parent == "BaseEvent"
        ):
            return dataset_query_map[ds.get("parentName")] + " ".join(
                c["search"] for c in ds.get("constraints", []) if c.get("search")
            )
        return " ".join(
            c["search"] for c in ds.get("constraints", []) if c.get("search")
        )

    def merge_data_model_fields(self, ds) -> List[Dict[str, Any]]:
        """
        Merge simple and calculated fields for a data model dataset.

        Combines standard dataset fields with calculated fields into a single
        normalized list. Calculated fields include metadata such as calculation
        type, expression, and optional lookup name.

        Args:
            ds (Dict[str, Any]): Dataset definition containing `fields`
                and optionally `calculations`.

        Returns:
            List[Dict[str, Any]]: A unified list of field dictionaries, each
            annotated with `field_type` ("simple" or "calculated") and, for
            calculated fields, associated calculation metadata.
        """

        fields = [{"field_type": "simple", **f} for f in ds.get("fields", [])]
        for calc in ds.get("calculations", []):
            calc_meta = {
                "calc_type": calc.get("calculationType"),
                "expression": calc.get("expression", ""),
            }
            if calc.get("lookupName"):
                calc_meta["lookup_name"] = calc.get("lookupName")
            for f in calc.get("outputFields", []):
                fields.append({"field_type": "calculated", "calc": calc_meta, **f})
        return fields

    def process_datamodels(self, data) -> List[Dict[str, Any]]:
        """
        Process data model definitions into a flattened list of datasets.

        Iterates through provided data model metadata, extracts dataset objects,
        determines dataset types (EVENT, SEARCH, TRANSACTION), resolves full SPL
        queries, detects macro/data model/lookup dependencies, merges field
        definitions, and returns a normalized dataset list.

        Args:
            data (List[Dict[str, Any]]): List of raw data model metadata entries,
                each containing description, acceleration, ACL, and related fields.

        Returns:
            List[Dict[str, Any]]: A flattened list of dataset dictionaries with
            resolved queries, dependency metadata, field definitions, and
            contextual attributes such as type, lineage, app name, and acceleration.
        """

        BASE_TYPES = {
            "BaseEvent": "EVENT",
            "BaseSearch": "SEARCH",
            "BaseTransaction": "TRANSACTION",
        }

        """Process all datamodels and return flat list of datasets."""
        datasets = []
        dataset_query_map = {}

        for item in data:
            # Parse description
            desc = item.get("description", {})
            dm_name = desc.get("modelName", "")
            app_name = item.get("eai:acl.app", "search")
            type_map = {}

            for ds in desc.get("objects", []):
                name = ds.get("objectName", "")
                parent = ds.get("parentName", "")
                lineage = ds.get("lineage", "")

                # Determine type
                if parent in BASE_TYPES:
                    ds_type, is_child = BASE_TYPES[parent], False
                elif parent in type_map:
                    ds_type, is_child = type_map[parent], True
                else:
                    ds_type, is_child = None, False

                if ds_type:
                    type_map[name] = ds_type

                updated_spl_query = self.get_full_dataset_query(ds, dataset_query_map)
                macros, dms, lookups = self.extract_macros_datamodels_lookups(
                    updated_spl_query, default_app=app_name
                )
                dataset = {
                    "data_model": dm_name,
                    "name": name,
                    "display_name": ds.get("displayName", ""),
                    "parent": parent,
                    "lineage": lineage,
                    "type": ds_type,
                    "is_child": is_child,
                    "updated_spl_query": updated_spl_query,
                    "fields": self.merge_data_model_fields(ds),
                    "macros_used": macros,
                    "datamodels_used": dms,
                    "lookups_used": lookups,
                    "app_name": app_name,
                    "user_id": item.get("eai:acl.perms.read", ""),
                    "acceleration": item.get("acceleration", {}),
                }
                dataset_query_map[name] = updated_spl_query

                if parent == "BaseTransaction":
                    dataset["group_by"] = ds.get("groupByFields", [])
                    dataset["objects_to_group"] = ds.get("objectsToGroup", [])

                datasets.append(dataset)

        return datasets

    def get_macros_datamodel_data(
        self, *, earliest: int = -1, latest: int = -1
    ) -> None:
        """
        Fetch, process, cache, and publish macros, lookups, and data model metadata.

        Retrieves lookup, macro, and data model metadata for the given time range,
        parses and transforms the results, caches them into KV store collections,
        and submits the enriched metadata to the SAIA API for context updates.

        Args:
            earliest (int, optional): Earliest time boundary as a Unix timestamp.
                Defaults to -1.
            latest (int, optional): Latest time boundary as a Unix timestamp.
                Defaults to -1.

        Returns:
            None
        """

        request_id = str(uuid.uuid4())
        user = "splunk-system-user"
        hashed_user = hash(user)
        service = self._connect_service(user)
        api = SaiaApiFactory.from_agent_mode_setting(
            service,
            service,
            user,
            None,
            hashed_user,
        )
        app_version = get_app_version(service)
        raw_lookup = self._get_macros_dms_lookups_metadata(
            earliest=earliest, latest=latest, lookups=True
        )
        self.logger.info(f"Raw_data for lookups is - {raw_lookup}")
        self.logger.info(f"length of lookups is - {len(raw_lookup)}")
        processed_lookup_data = self._parse_lookup_payload(raw_lookup)
        self.write_lookups_data_to_kv_store(processed_lookup_data)
        self.logger.info("Updating SPL Lookups context")
        self.logger.info(  # pyright: ignore
            log_kwargs(
                request_id=request_id,
                anticipated_entry_count=len(processed_lookup_data),
                saia_app_version=app_version,
            )
        )

        try:
            api.submit_lookups_metadata(
                field_data=processed_lookup_data, request_id=request_id
            )
        except Exception as e:
            self.logger.exception("Error in updating lookups context: %s", e)
        self.logger.info("Updating SPL LOOKUPS context")
        raw_data = self._get_macros_dms_lookups_metadata(
            earliest=earliest, latest=latest, macros=True
        )
        self.logger.info(f"Raw_data for macros is - {raw_data}")
        # process or transform data here by a method
        processed_data = self._parse_macros_payload(raw_data)
        self.logger.info(
            f"length of processed data for macros is - {len(processed_data)}"
        )
        transformed_data = self.macros_data_transformation(processed_data)
        _ = self.write_macros_data_to_kv_store(transformed_data)
        self.logger.info(
            f"length of transformed data for macros is - {len(transformed_data)}"
        )
        self.logger.info(f"Transformed data for macros is - {transformed_data}")

        raw_data_data_models = self._get_datamodels_metadata(
            earliest=earliest, latest=latest
        )
        self.logger.info("Updating SPL Data models context")

        datasets_list = self.process_datamodels(raw_data_data_models)
        self.write_data_models_data_to_kv_store(datasets_list)
        enriched_data = self._get_enriched_macros_metadata(
            earliest=earliest, latest=latest
        )
        self.logger.info("Updating SPL MACROS context")
        self.logger.info(
            log_kwargs(
                request_id=request_id,
                anticipated_entry_count=len(enriched_data),
                saia_app_version=app_version,
            )
        )
        # Upload macros metadata
        try:
            api.submit_macros_metadata(field_data=enriched_data, request_id=request_id)
        except Exception as e:
            self.logger.exception("Error in updating macros context: %s", e)

        self.logger.info("Updating SPL DATA MODELS context")
        enriched_datamodels = self._get_enriched_datamodels_metadata(
            earliest=earliest, latest=latest
        )
        datamodel_payload = enriched_datamodels or datasets_list
        self.logger.info(
            log_kwargs(
                request_id=request_id,
                anticipated_entry_count=len(datamodel_payload),
                saia_app_version=app_version,
            )
        )
        try:
            api.submit_datamodels_metadata(
                field_data=datamodel_payload, request_id=request_id
            )
        except Exception as e:
            self.logger.exception("Error in updating data models context: %s", e)

    def run(self, stanza: Sequence[Dict[str, Any]]):
        self.logger.info("Starting Macros Summary Modular Input")

        self.logger.setLevel(self.get_log_level(stanza))
        self.logger.debug(
            f"Input configuration: {self._input_config}, stanza: {stanza}"
        )
        config = SAIAMacrosSummaryModularInputConfig(
            self._input_config.session_key, self.logger
        )

        if config.is_context_update_due():
            now = int(time.time())
            earliest = max(
                config.status["last_context_update_timestamp"],
                now - config.settings["max_chunk_range_seconds"],
            )
            latest = int(time.time())

            try:
                self.logger.info("updating macros objects metadata")
                self.get_macros_datamodel_data(earliest=earliest, latest=latest)

            except Exception as e:
                self.logger.exception("Error in updating field summary context: %s", e)

            config.update(last_context_update_timestamp=latest)
            earliest = latest
            self._chunk_count += 1

    def cache_results_to_kvstore(
        self, results, collection, macros=True, lookups=False, datamodels=False
    ) -> None:
        """
        Cache processed results into the appropriate KV store collection.

        Transforms macro, lookup, or data model metadata into the expected KV store
        schema and performs a batch save operation on the provided collection.

        Args:
            results (List[Dict[str, Any]]): Processed metadata entries to cache.
            collection (Any): KV store collection instance supporting `batch_save`.
            macros (bool, optional): If True, treat results as macro metadata.
                Defaults to True.
            lookups (bool, optional): If True, treat results as lookup metadata.
                Defaults to False.
            datamodels (bool, optional): If True, treat results as data model metadata.
                Defaults to False.

        Returns:
            None
        """

        self.logger.info("Caching results to KV store started")
        entries_to_save = []
        if macros:
            for result in results:
                entries_to_save.append(
                    {
                        "title": result.get("title", ""),
                        "definition": result.get("definition", ""),
                        "content": json.dumps(result.get("content", "")),
                        "macros_used": result.get("macros_used", []),
                        "updated_spl": result.get("updated_spl_query", ""),
                        "datamodels_used": result.get("datasets_used", []),
                        "lookups_used": result.get("lookups_used", []),
                        "app_name": result.get("app_name", ""),
                        "args": result.get("args", []),
                        "user_id": result.get("user_id", ""),
                    }
                )
        elif lookups:
            for result in results:
                entries_to_save.append(
                    {
                        "title": result.get("title", ""),
                        "type": result.get("type", ""),
                        "fields_list": result.get("fields_list", ""),
                        "app_name": result.get("eai:acl.app", ""),
                        "user_id": result.get("eai:acl.perms.read", ""),
                    }
                )
        elif datamodels:
            for result in results:
                entries_to_save.append(
                    {
                        "data_model": result.get("data_model", ""),
                        "name": result.get("name", ""),
                        "display_name": result.get("display_name", ""),
                        "parent": result.get("parent", ""),
                        "lineage": result.get("lineage", ""),
                        "type": result.get("type", ""),
                        "is_child": result.get("is_child", False),
                        "updated_spl_query": result.get("updated_spl_query", ""),
                        "fields": result.get("fields", []),
                        "macros_used": result.get("macros_used", []),
                        "datamodels_used": result.get("datamodels_used", []),
                        "lookups_used": result.get("lookups_used", []),
                        "group_by": result.get("group_by", []),
                        "objects_to_group": result.get("objects_to_group", []),
                        "app_name": result.get("app_name", ""),
                        "user_id": result.get("user_id", ""),
                        "acceleration": result.get("acceleration", {}),
                    }
                )
        if entries_to_save:
            collection.batch_save(entries_to_save)

        self.logger.info(
            "Caching results to KV store completed, wrote %d entries",
            len(entries_to_save),
        )


if __name__ == "__main__":
    add_log_extra_metadata("tag", LOGGER_METADATA_TAG)
    add_log_extra_metadata("context", "modinput")
    mod_input = SAIAMacrosSummaryModularInput()
    mod_input.execute()
