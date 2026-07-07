import threatquotient_app_declare # noqa F401
import os
import traceback
import re
import urllib.parse

from splunktaucclib.rest_handler.endpoint.validator import Validator
from splunktaucclib.rest_handler.endpoint import (
    validator
)
import splunk.admin as admin
import splunk.clilib.cli_common
import splunklib.client as client
from splunklib.binding import HTTPError
from threatquotient_setup_utils import get_conf_file, write_to_conf_file
import logger_manager as log
import savedsearches_queries_breakdown as savedsearch_queries
import threatq_utils as utility
import threatq_const as tq_const


logger = log.setup_logging("threatquotient_setup")

APP_NAME = __file__.split(os.sep)[-3]

splunkrc = {
    "host": splunk.getDefault("host"),
    "port": splunk.getDefault("port"),
    "app": APP_NAME,
    "owner": "nobody",
}

SETTINGS_CONF_FILE = "threatquotient_app_settings"
COLLECTIONS_CONF_FILE = "collections"
MASTER_LOOKUP_STANZA_NAME = "master_lookup"
MATCH_LOOKUP_STANZA_NAME = "threatq_matched_indicators"

CONSUME_SAVEDSEARCH_LIST = [
    "threatq_consume_indicators",
    "threatq_consume_indicators_new",
]
INDEXES_MACRO_NAME = "threatq_match_indices"
TRANSFORMS_CONF_FILE = "transforms"

MATCH_TYPE_LIST = ["raw", "datamodel", "tstats"]
MAX_DATAMODEL_ALLOWED = 5
DATAMODEL_LIST = [
    "network_traffic",
    "malware",
    "incident_management",
    "intrusion_detection",
    "authentication",
    "certificates",
    "endpoint",
    "email",
    "compute_inventory",
    "network_resolution",
    "updates",
    "web",
]
SAVEDSEARCH_LIST = {
    "_incident_management": [
        "notable_events",
        "suppressed_notable_events",
        "suppression_audit_expired",
        "suppression_audit",
    ],
    "_endpoint": ["filesystem", "services", "processes"],
}
SAVEDSEARCH_STANZA_NAME = "threatq_update_matched_indicators_on_master_lookup_change"

SAVEDSEARCH_CONF_FILE = "savedsearches"
ES_SAVEDSEARCH_LIST = [
    "threatq_update_threat_intelligence_lookup_email_address",
    "threatq_update_threat_intelligence_lookup_email_subject",
    "threatq_update_threat_intelligence_lookup_file_name",
    "threatq_update_threat_intelligence_lookup_fqdn",
    "threatq_update_threat_intelligence_lookup_hash",
    "threatq_update_threat_intelligence_lookup_ip",
    "threatq_update_threat_intelligence_lookup_registry",
    "threatq_update_threat_intelligence_lookup_service",
    "threatq_update_threat_intelligence_lookup_certificate_serial",
    "threatq_update_threat_intelligence_lookup_certificate_subject",
    "threatq_update_threat_intelligence_lookup_url",
    "threatq_update_threat_intelligence_lookup_user",
]
unsupported_attributes = ["attributes", "adversaries", "sources", ".", "$"]
MASTER_LOOKUP_FIELDS_STR = ("ioc_id, status, type, ioc_value, "
                            "_key, score, updated_at, sources, "
                            "adversaries, index_time, malware_family, port")
MATCH_LOOKUP_FIELDS_STR = ("ioc_id, status, type, ioc_value, "
                           "_key, score, updated_at, match_time, "
                           "first_seen, last_seen, match_count, "
                           "sources, adversaries, sid, last_run_first_seen, "
                           "last_run_last_seen, last_run_match_count, malware_family, datamodel_name, raw_event")


class GetSessionKey(admin.MConfigHandler):
    """To get Splunk session key."""

    def __init__(self):
        """Initialize."""
        self.session_key = self.getSessionKey()


def post_macro_definition(session_key, macro_name, definition):
    """Save macro definition."""
    try:
        service = utility.create_service(session_key)
        response = service.post(
            "properties/macros/{}".format(macro_name), definition=definition
        )

        if response["status"] != 200:
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )

    except Exception as err:
        ERR_MSG = "error occurred while saving '{}' macro definitaion".format(
            macro_name
        )
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def save_macro_definition(session_key, indexes):
    """Convert indexes list to macro definition and update macro definition."""
    if "*" in indexes:
        definition = '(index="*")'
    elif not indexes:
        definition = '()'
    else:
        indexes = ['"{}"'.format(item) for item in indexes]
        definition = "(index={})".format(" OR index=".join(indexes))

    post_macro_definition(session_key, INDEXES_MACRO_NAME, definition)

def get_macro_definition(session_key, macro_name):
    """Fetch macro definition."""
    try:
        service = utility.create_service(session_key)

        response = service.get(
            "properties/macros/{}/definition".format(macro_name)
        )
        if response["status"] != 200:
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )
    except Exception as err:
        ERR_MSG = "error occurred while getting '{}' macro definitaion".format(
            macro_name
        )
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

    definitaion = str(response["body"].read().decode())

    return definitaion

def parse_indexes_from_macro(session_key):
    """
    Parse indexes names from the 'threatq_match_indices' macro definition.

    Ex. For macro definition = (index="main" or index=abc), parsed indexes
    are = ["main", "abc"]
    """
    ERR_MSG = (
        "error occurred while parsing indexes from the '{}' macro "
        "definition. Please check macro definition".format(INDEXES_MACRO_NAME)
    )

    definition = get_macro_definition(session_key, INDEXES_MACRO_NAME)

    indexes = {}
    definition = definition.strip()

    if (definition[0] == "(" and definition[-1] != ")") or (
        definition[-1] == ")" and definition[0] != "("
    ):
        raise Exception(ERR_MSG)

    if definition[0] == "(":
        definition = definition[1:-1].strip()

    if definition:
        for item in definition.lower().split(" or "):
            item = item.strip()
            match = re.search(
                r'^index\s*=\s*([0-9a-z][0-9a-z_-]*|"[0-9a-z][0-9a-z_-]*'
                r'"|\*|"\*")$',
                item,
            )
            if match:
                index_name = match.group(1).strip('"')
                indexes[index_name] = index_name
            else:
                logger.error(ERR_MSG)
                raise Exception(ERR_MSG)

    indexes_list = list(indexes)

    return indexes_list

def remove_duplicates_from_list(custom_fields):
    """Remove duplicate values from the list."""
    if custom_fields:
        custom_fields = custom_fields.split(", ")
        custom_fields = list(set(custom_fields))
        custom_fields = ", ".join(custom_fields)
    else:
        custom_fields = ""
    return custom_fields

def update_conf(suffix, action, postfix=""):
    """Update savedsearches.conf file to enable-disable savedsearches."""
    prefix = [
        "threatq_match_indicators{}",
        "threatq_update_matched_indicators{}",
    ]
    if suffix in SAVEDSEARCH_LIST.keys():
        for search in SAVEDSEARCH_LIST[suffix]:
            for i in prefix:
                stanza_name = i.format(suffix) + "_" + search + postfix
                data = {"disabled": action}
                write_to_conf_file(
                    SAVEDSEARCH_CONF_FILE, stanza_name, data
                )
    else:
        for i in prefix:
            stanza_name = i.format(suffix) + postfix
            data = {"disabled": action}
            write_to_conf_file(SAVEDSEARCH_CONF_FILE, stanza_name, data)

def update_conf_for_es_savedsearches(action):
    """Update savedsearches.conf file to enable-disable savedsearches."""
    for search in ES_SAVEDSEARCH_LIST:
        write_to_conf_file(
            SAVEDSEARCH_CONF_FILE, search, {"disabled": action}
        )

def update_conf_for_consume_savesearch(consume_savesearch):
    """Update savedsearches.conf file to enable-disable savedsearches."""
    index = CONSUME_SAVEDSEARCH_LIST.index(consume_savesearch)
    write_to_conf_file(
        SAVEDSEARCH_CONF_FILE, CONSUME_SAVEDSEARCH_LIST[index], {"disabled": 0}
    )
    write_to_conf_file(
        SAVEDSEARCH_CONF_FILE,
        CONSUME_SAVEDSEARCH_LIST[not index],
        {"disabled": 1},
    )

def post_custom_fields_collections(conf_name, stanza_name, data):
    """Save custom fields to collection definition."""
    try:
        write_to_conf_file(
            conf_name, stanza_name, data
        )
    except Exception as err:
        ERR_MSG = "error occurred while saving '{}' collection definitaion".format(
            stanza_name
        )
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def create_tstats_savedsearch(session_key, name, search, datamodel_name):
    """
    Create a tstats-based savedsearch stanza in savedsearches.conf
    named `name`, with the given search and fixed schedule,
    and disable other custom_tstats_* savedsearches.
    """
    try:
        service = utility.create_service(session_key)
        payload = {
            "name": name,
            "search": search,
            "cron_schedule": "*/30 * * * *",
            "dispatch.earliest_time": "-35m",
            "dispatch.latest_time": "now",
            "enableSched": "1",
            "realtime_schedule": "0",
            "disabled": "0",
            "request.ui_dispatch_app": "threatqappforsplunk",
            "request.ui_dispatch_view": "search",
            "allow_skew": "50%",
            "description": (
                "Match indicators from the master_lookup which are not in the "
                "threatq_matched_indicators against {} events (tstats)"
            ).format(datamodel_name),
        }

        # Create / overwrite current custom tstats savedsearch
        response = service.post("configs/conf-savedsearches", **payload)
        if response["status"] not in (200, 201):
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )

        # Disable all other custom_tstats_* and custom_datamodel_* savedsearches
        prefixes = ["custom_tstats_", "custom_datamodel_"]

        for ss in service.saved_searches:
            ss_name = ss.name
            if not any(ss_name.startswith(pfx) for pfx in prefixes):
                continue
            if ss_name == name:
                continue  # keep the one we just created enabled

            encoded_name = urllib.parse.quote(ss_name, safe="")
            disable_resp = service.post(
                f"properties/savedsearches/{encoded_name}",
                disabled="1",
            )
            if disable_resp["status"] not in (200, 201):
                raise Exception(
                    "Failed to disable savedsearch '{}', status={}, response={}".format(
                        ss_name, disable_resp["status"], str(disable_resp)
                    )
                )

    except Exception as err:
        ERR_MSG = "Error occurred while updating savedsearches for custom tstats datamodels."
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def create_datamodel_savedsearch(session_key, name, search, datamodel_name):
    """
    Create a savedsearch stanza in savedsearches.conf
    named `name`, with the given search and fixed schedule,
    and disable other custom_datamodel_* and custom_tstats_* savedsearches.
    """
    try:
        service = utility.create_service(session_key)
        payload = {
            "name": name,
            "search": search,
            "cron_schedule": "*/30 * * * *",
            "dispatch.earliest_time": "-35m",
            "dispatch.latest_time": "now",
            "enableSched": "1",
            "realtime_schedule": "0",
            "disabled": "0",
            "request.ui_dispatch_app": "threatqappforsplunk",
            "request.ui_dispatch_view": "search",
            "allow_skew": "50%",
            "description": (
                "Match indicators from the master_lookup which are not in the "
                "threatq_matched_indicators against {} events"
            ).format(datamodel_name),
        }
        # Create / overwrite current custom savedsearch
        response = service.post("configs/conf-savedsearches", **payload)
        if response["status"] not in (200, 201):
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )
        # Disable all other custom_datamodel_* and custom_tstats_* savedsearches
        prefixes = ["custom_datamodel_", "custom_tstats_"]

        for ss in service.saved_searches:
            ss_name = ss.name
            if not any(ss_name.startswith(pfx) for pfx in prefixes):
                continue
            if ss_name == name:
                continue  # keep the one we just created enabled

            encoded_name = urllib.parse.quote(ss_name, safe="")
            disable_resp = service.post(
                f"properties/savedsearches/{encoded_name}",
                disabled="1",
            )

            if disable_resp["status"] not in (200, 201):
                raise Exception(
                    "Failed to disable savedsearch '{}', status={}, response={}".format(
                        ss_name, disable_resp["status"], str(disable_resp)
                    )
                )

    except Exception as err:
        ERR_MSG = "Error occurred while updating savedsearches for custom datamodels."
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def add_fields_to_collections(custom_fields_list, master_lookup_data, match_lookup_data, skip_master=False):
    """Add key value pairs to the collections."""
    if custom_fields_list:
        custom_fields_list = custom_fields_list.split(",")
        for custom_field in custom_fields_list:
            custom_field = custom_field.replace(" ", "_")
            if not skip_master:
                master_lookup_data['field.' + custom_field] = 'string'
            match_lookup_data['field.' + custom_field] = 'string'
    return [master_lookup_data, match_lookup_data]

def update_custom_fields_collections(args):
    """Update collections.conf definiton with the custom fields."""
    master_lookup_data = {}
    match_lookup_data = {}
    custom_attributes_list = ",".join([value.strip() for value in args.get("custom_attributes").split(",")])
    custom_fields_list = ",".join([value.strip().lower() for value in args.get("custom_fields").split(",")])

    [master_lookup_data, match_lookup_data] = add_fields_to_collections(custom_attributes_list, master_lookup_data,
                                                                        match_lookup_data)
    [master_lookup_data, match_lookup_data] = add_fields_to_collections(custom_fields_list, master_lookup_data,
                                                                        match_lookup_data)
    post_custom_fields_collections(COLLECTIONS_CONF_FILE, MASTER_LOOKUP_STANZA_NAME, master_lookup_data)
    post_custom_fields_collections(COLLECTIONS_CONF_FILE, MATCH_LOOKUP_STANZA_NAME, match_lookup_data)

def replace_space_with_underscore(custom_list, is_field=False):
    """Replace space with underscore."""
    custom_list = [value.strip().lower() if is_field else value.strip() for value in custom_list.split(",")]
    custom_new_list = []
    for value in custom_list:
        value = value.replace(" ", "_")
        custom_new_list.append(value)
    custom_str = ","
    custom_str = custom_str.join(custom_new_list)
    return custom_str

def post_custom_fields_transforms(session_key, conf_name, stanza_name, data):
    """Save custom fields to transforms.conf."""
    try:
        service = utility.create_service(session_key)
        response = service.post(
            "properties/{}/{}".format(conf_name, stanza_name), fields_list=data
        )
        if response["status"] != 200:
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )
    except Exception as err:
        ERR_MSG = "error occurred while saving '{}' transforms fields_list".format(
            stanza_name
        )
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def update_custom_fields_transforms(args, session_key):
    """Update transforms.conf to add the custom fields."""
    custom_attributes_list = args.get("custom_attributes")  
    if custom_attributes_list is not None:
        custom_attributes_list = replace_space_with_underscore(custom_attributes_list)
    custom_fields_list = args.get("custom_fields")  
    if custom_fields_list is not None:
        custom_fields_list = replace_space_with_underscore(custom_fields_list, is_field=True)

    transform_file = utility.get_conf_file(session_key, APP_NAME, "transforms")
    data_master_lookup = MASTER_LOOKUP_FIELDS_STR
    updated_data_match_lookup = ''
    existing_fields = set()
    if transform_file["threatq_matched_indicators"]["fields_list"]:
        fields_transforms = transform_file["threatq_matched_indicators"]["fields_list"]
    else:
        fields_transforms = MATCH_LOOKUP_FIELDS_STR
    existing_fields.update([field.strip() for field in fields_transforms.split(',')])

    # Add raw_event and datamodel_name if they are not present
    if 'raw_event' not in existing_fields:
        existing_fields.add('raw_event')
    if 'datamodel_name' not in existing_fields:
        existing_fields.add('datamodel_name')

    if custom_attributes_list:
        data_master_lookup = data_master_lookup + ", " + custom_attributes_list
        custom_attr = ','.join([field.strip().rsplit('.', 1)[-1] for field in custom_attributes_list.strip().split(',')])
        existing_fields.update([field.strip() for field in custom_attr.split(',')])

    if custom_fields_list:
        data_master_lookup = data_master_lookup + ", " + custom_fields_list
        custom_tq_fields = ','.join([field.strip().rsplit('.', 1)[-1] for field in custom_fields_list.strip().split(',')])
        existing_fields.update([field.strip() for field in custom_tq_fields.split(',')])

    updated_data_match_lookup = ', '.join(existing_fields)
    post_custom_fields_transforms(session_key, TRANSFORMS_CONF_FILE, MASTER_LOOKUP_STANZA_NAME, data_master_lookup)
    post_custom_fields_transforms(session_key, TRANSFORMS_CONF_FILE, MATCH_LOOKUP_STANZA_NAME, updated_data_match_lookup)

def post_custom_fields_savedsearches(session_key, conf_name, stanza_name, query):
    """Save custom fields to threatq_update_matched_indicators_on_master_lookup_change savedsearch."""
    try:
        service = utility.create_service(session_key)
        response = service.post(
            "properties/{}/{}".format(conf_name, stanza_name), search=query
        )
        if response["status"] != 200:
            raise Exception(
                "Got response with status_code={}, response={}".format(
                    response["status"], str(response)
                )
            )
    except Exception as err:
        ERR_MSG = "error occurred while saving '{}' savedsearch query".format(
            stanza_name
        )
        logger.error(ERR_MSG)
        logger.exception(err)
        raise admin.ArgValidationException(ERR_MSG)

def update_custom_fields_savedsearches(args, session_key):
    """Update savedsearches.conf to add the custom fields."""
    custom_attributes_list = args.get("custom_attributes")
    if custom_attributes_list is not None:
        custom_attributes_list = replace_space_with_underscore(custom_attributes_list)
    custom_fields_list = args.get("custom_fields")  
    if custom_fields_list is not None:
        custom_fields_list = replace_space_with_underscore(custom_fields_list, is_field=True)
    savedsearch_part_1 = "| inputlookup threatq_matched_indicators" +\
        "| lookup master_lookup ioc_value output ioc_id, status, type, score, updated_at, sources, adversaries, malware_family" +\
        "| where isnotnull(match_count) | eval key_datamodel_name=if(isnotnull(raw_event) AND (isnull(datamodel_name) OR datamodel_name=\"\"), \"Raw\", coalesce(datamodel_name, \"Unknown\")) | eval key_dm_safe=replace(key_datamodel_name, \"[^A-Za-z0-9_-]\", \"_\") | eval value=ioc_value + \"_\" + key_dm_safe " +\
        "| table ioc_id, ioc_value, value, match_time, first_seen, last_seen, match_count, " +\
        "score, status, type, updated_at, sources, adversaries, sid, last_run_first_seen, " +\
        "last_run_last_seen, last_run_match_count, malware_family, port, datamodel_name, raw_event, `splunk_custom_fields_macro2`"
    savedsearch_part_2 = "| outputlookup threatq_matched_indicators key_field=value"
    savedsearch = savedsearch_part_1
    if custom_attributes_list:
        savedsearch = savedsearch + ", " + custom_attributes_list
    if custom_fields_list:
        savedsearch = savedsearch + ", " + custom_fields_list
    savedsearch = savedsearch + savedsearch_part_2
    post_custom_fields_savedsearches(session_key, SAVEDSEARCH_CONF_FILE, SAVEDSEARCH_STANZA_NAME, savedsearch)

class MacroConfiguration(Validator):
    """Class provides methods for handling Macros Configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(MacroConfiguration, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)

    def validate(self, value, data):
        try:
            indexes = data.get("indexes",None)
            indexes = [
                item.strip()
                for item in (indexes or "").strip().lower().split(",")
                if item.strip()
            ]
            index = []
            for item in indexes:
                match = re.match(r"(^[0-9a-z][0-9a-z_-]*$|^\*$)", item)
                if not match:
                    logger.error( "Index Names may contain only letters, numbers, underscores, "
                        "or hyphens. They must begin with a letter or number")
                    self.put_msg(
                        "Index Names may contain only letters, numbers, underscores, "
                        "or hyphens. They must begin with a letter or number"
                    )
                    return False
                index.append(item.lower())
            save_macro_definition(GetSessionKey().session_key, index)
            data['indexes'] = ",".join(index) if len(index)>0 else index
            
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True

        
class SightingEventConfiguration(Validator):
    """Class provides methods for handling Sighting Event Configuration."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(SightingEventConfiguration, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            consume_savesearch = data.get("sighting_event_configuration",None)
            if consume_savesearch not in CONSUME_SAVEDSEARCH_LIST:
                msg = "Invalid value of Sighting Event field"
                logger.error(msg)
                self.put_msg(msg)
                return False
            # Update collections.conf based on custom fields
            update_custom_fields_collections(data)

            # Update transforms.conf based on custom fields
            update_custom_fields_transforms(data, GetSessionKey().session_key)

            # Update savedsearches.conf based on custom fields
            update_custom_fields_savedsearches(data, GetSessionKey().session_key)
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True


class EnableSavedSearch(Validator):
    """Class provides methods for handling Enable Splunk ES savedsearches."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(EnableSavedSearch, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            # Reading values from conf file
            enable_es_savedsearches = data.get("enable_es_savedsearches",None)
            if enable_es_savedsearches not in ["0","1"]:
                msg = "Invalid value of Enable Splunk ES savedsearches field"
                logger.error(msg)
                self.put_msg(msg)
                return False
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True


class MatchType(Validator):
    """Class provides methods for handling Search Matching Algorithm."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(MatchType, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            match_type = data.get("match_type")
            indexes = data.get("indexes",None)
            enable_es_savedsearches = data.get("enable_es_savedsearches",None)
            sighting_event_configuration = data.get("sighting_event_configuration",None)
            datamodel_list = data.get("datamodel_list",None)
            if not indexes and match_type == MATCH_TYPE_LIST[0]:
                logger.error("Please enter at least one Index Name")
                self.put_msg("Please enter at least one Index Name")
                return False
            if not match_type and enable_es_savedsearches != "1":
                logger.error("Please select at least one option")
                self.put_msg("Please select at least one option")
                return False
            if match_type and match_type not in MATCH_TYPE_LIST:
                msg = "Invalid value of Search Matching Algorithm field"
                logger.error(msg)
                self.put_msg(msg)
                return False
            if match_type == MATCH_TYPE_LIST[0] and datamodel_list:
                data["datamodel_list"] = ""
            if match_type == MATCH_TYPE_LIST[0]:
                update_conf( "", "0")
                for dm in DATAMODEL_LIST:
                    update_conf( "_" + dm, "1")
                    update_conf( "_" + dm, "1", "_tstats")
            elif match_type == "":
                update_conf("", "1")
                for dm in DATAMODEL_LIST:
                    update_conf("_" + dm, "1")
                    update_conf("_" + dm, "1", "_tstats")
            action = 0 if enable_es_savedsearches == "1" else 1
            update_conf_for_es_savedsearches(action)
            update_conf_for_consume_savesearch(sighting_event_configuration)
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True


class DataModel(Validator):
    """Class provides methods for handling Datamodels."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(DataModel, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            datamodel_list = data.get("datamodel_list",None)
            match_type = data.get("match_type")      
            enable_es_savedsearches = data.get("enable_es_savedsearches",None)
            sighting_event_configuration = data.get("sighting_event_configuration",None)   
            if match_type and match_type != MATCH_TYPE_LIST[0]:
                if (
                        (match_type == MATCH_TYPE_LIST[1] or match_type == MATCH_TYPE_LIST[2])
                        and datamodel_list
                        and set(map(str.strip, datamodel_list.split(","))).issubset(
                            DATAMODEL_LIST
                        )
                    ):
                        datamodel_list = ", ".join(map(str.strip, datamodel_list.split(",")))
                        update_conf("", "1")

                        savedsearches_to_enable = list(set(data.get("datamodel_list").split(",")))
                        savedsearches_to_disable = list(set(DATAMODEL_LIST).difference(
                            savedsearches_to_enable
                        ))
                        if match_type == MATCH_TYPE_LIST[1]:
                            for dm in savedsearches_to_enable:                          
                                update_conf("_" + dm, "0")
                                update_conf("_" + dm, "1", "_tstats")
                        elif match_type == MATCH_TYPE_LIST[2]:
                            for dm in savedsearches_to_enable:
                                update_conf("_" + dm, "0", "_tstats")
                                update_conf("_" + dm, "1")
                        for dm in savedsearches_to_disable:
                            update_conf("_" + dm, "1")
                            update_conf("_" + dm, "1", "_tstats")
                else:
                    msg = "Invalid value of Datamodels field"
                    logger.error(msg)
                    self.put_msg(msg)
                    return False
            elif match_type == "":
                update_conf( "", "1")
                for dm in DATAMODEL_LIST:
                    update_conf( "_" + dm, "1")
                    update_conf( "_" + dm, "1", "_tstats")   
            action = 0 if enable_es_savedsearches == "1" else 1
            update_conf_for_es_savedsearches(action)
            update_conf_for_consume_savesearch(sighting_event_configuration)
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True


class ConsumeAttributes(Validator):
    """Class provides methods for handling Consume Attributes."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(ConsumeAttributes, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            # Reading values from conf file
            custom_attributes = data.get("custom_attributes",None)
            custom_attributes = remove_duplicates_from_list(custom_attributes)
            custom_attribute_list = custom_attributes.lower()
            if any(attribute in custom_attribute_list for attribute in unsupported_attributes):
                msg = "Invalid word entered (\"attributes, sources, adversaries, ., $\") in custom attributes."
                logger.error(msg)
                self.put_msg(msg)
                return False
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True


class ConsumeFields(Validator):
    """Class provides methods for handling Consume Fields."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(ConsumeFields, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            # Reading values from conf file
            custom_fields = data.get("custom_fields",None)
            custom_fields = remove_duplicates_from_list(custom_fields)
            custom_fields_list = custom_fields.lower()
            if any(attribute in custom_fields_list for attribute in unsupported_attributes):
                msg = "Invalid word entered (\"attributes, sources, adversaries, ., $\") in custom fields."
                logger.error(msg)
                self.put_msg(msg)
                return False
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True

class ConsumeSplunkFields(Validator):
    """Class provides methods for handling Consume Fields."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(ConsumeSplunkFields, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            macro_custom_fields = data.get("splunk_additional_fields", "")
            if len(macro_custom_fields.split(",")) > 10:
                self.put_msg("Maximum of 10 fields can be selected.")
                return False
            settings_conf_file = utility.get_conf_file(GetSessionKey().session_key, APP_NAME, "threatquotient_app_settings")
            type_of_matching = settings_conf_file.get("match_algo_detail").get("match_type")
            custom_fields_set = set(field.strip() for field in macro_custom_fields.split(','))
            if type_of_matching in ['datamodel', 'tstats'] and data.get("selected_datamodel") and macro_custom_fields.strip():
                datamodel_list = data.get("selected_datamodel").strip()
                datamodel_list = datamodel_list.split(",")
                for datamodel in datamodel_list:
                    savedsearch_stanza = savedsearch_queries.DATAMODEL_TO_SAVEDSEARCH_MAPPING[datamodel]
                    for savedsearch in savedsearch_stanza:
                        if type_of_matching == "tstats" and "tstats" in savedsearch:
                            default_by = tq_const.DEFAULT_GROUP_BY_FIELDS_OF_DATAMODEL[savedsearch[:-7]]
                            default_by_set = set(field.strip() for field in default_by.split(','))
                            custom_fields_set -= default_by_set
                        elif type_of_matching == "datamodel" and "tstats" not in savedsearch:
                            default_by = tq_const.DEFAULT_GROUP_BY_FIELDS_OF_DATAMODEL[savedsearch]
                            default_by_set = set(field.strip() for field in default_by.split(','))
                            custom_fields_set -= default_by_set
                macro_custom_fields = ','.join(custom_fields_set)
            macro_def = macro_custom_fields.strip()
            if not macro_def:
                macro_def = '.'
            post_macro_definition(GetSessionKey().session_key, "splunk_custom_fields_macro", macro_def)

            transform_file = utility.get_conf_file(GetSessionKey().session_key, APP_NAME, "transforms")            
            splunk_custom_fields_list = data.get("splunk_additional_fields").strip()
            
            data_match_lookup = ''
            if splunk_custom_fields_list is not None:
                if type_of_matching == "raw":
                    splunk_custom_fields_list = ','.join(set([field.strip().replace('.', '_') for field in splunk_custom_fields_list.split(',')]))
                elif type_of_matching in ["datamodel", "tstats"]:
                    splunk_custom_fields_list = ','.join(set([field.strip().rsplit('.', 1)[-1] for field in splunk_custom_fields_list.split(',')]))
                post_macro_definition(GetSessionKey().session_key, "splunk_custom_fields_macro2", splunk_custom_fields_list)
                if transform_file["threatq_matched_indicators"]["fields_list"]:
                    fields_transforms = transform_file["threatq_matched_indicators"]["fields_list"]
                else:
                    fields_transforms = MATCH_LOOKUP_FIELDS_STR
                existing_fields = set([field.strip() for field in fields_transforms.split(',')])
                # Add raw_event and datamodel_name if they are not present
                if 'raw_event' not in existing_fields:
                    existing_fields.add('raw_event')
                if 'datamodel_name' not in existing_fields:
                    existing_fields.add('datamodel_name')
                new_fields = set([field.strip() for field in splunk_custom_fields_list.split(',')])
                data_match_lookup = ', '.join(existing_fields.union(new_fields))
                post_custom_fields_transforms(GetSessionKey().session_key, TRANSFORMS_CONF_FILE, MATCH_LOOKUP_STANZA_NAME, data_match_lookup)

                master_lookup_data = {}
                match_lookup_data = {}
                [master_lookup_data, match_lookup_data] = add_fields_to_collections(splunk_custom_fields_list, master_lookup_data, match_lookup_data, skip_master=True)
                post_custom_fields_collections(COLLECTIONS_CONF_FILE, MATCH_LOOKUP_STANZA_NAME, match_lookup_data)

            splunk_cust_fields = data.get("splunk_additional_fields")
            if type_of_matching in ['datamodel', 'tstats']:
                if splunk_cust_fields.strip() and data.get("selected_datamodel"):
                    datamodel_list = data.get("selected_datamodel").strip()
                    datamodel_list = datamodel_list.split(",")
                    for datamodel in datamodel_list:
                        savedsearch_stanza = savedsearch_queries.DATAMODEL_TO_SAVEDSEARCH_MAPPING[datamodel]
                        for savedsearch in savedsearch_stanza:
                            if type_of_matching == "datamodel" and "tstats" not in savedsearch:
                                ss_part1 = savedsearch_queries.SAVEDSEARCHES_BREAKDOWN[savedsearch]["ss_1"]
                                ss_part2 = savedsearch_queries.SAVEDSEARCHES_BREAKDOWN[savedsearch]["ss_11"]
                                ss_part3 = savedsearch_queries.SAVEDSEARCHES_BREAKDOWN[savedsearch]["ss_2"]
                                final_ss_query = ss_part1 + ', `splunk_custom_fields_macro`' + ss_part2 + ', `splunk_custom_fields_macro`' + ss_part3
                                post_custom_fields_savedsearches(GetSessionKey().session_key, SAVEDSEARCH_CONF_FILE, savedsearch, final_ss_query)
                            elif type_of_matching == "tstats" and "tstats" in savedsearch:
                                ss_part1 = savedsearch_queries.SAVEDSEARCHES_BREAKDOWN[savedsearch]["ss_1"]
                                ss_part2 = savedsearch_queries.SAVEDSEARCHES_BREAKDOWN[savedsearch]["ss_2"]
                                final_ss_query = ss_part1 + ', `splunk_custom_fields_macro` fillnull_value="-"' + ss_part2
                                post_custom_fields_savedsearches(GetSessionKey().session_key, SAVEDSEARCH_CONF_FILE, savedsearch, final_ss_query)
            else:
                ss_part1 = savedsearch_queries.RAW_EVENTS_SAVEDSEARCH["threatq_match_indicators"]["ss_1"]
                ss_part2 = savedsearch_queries.RAW_EVENTS_SAVEDSEARCH["threatq_match_indicators"]["ss_2"]
                final_ss_query = ss_part1 + " | table _raw `splunk_custom_fields_macro` _time " + ss_part2
                post_custom_fields_savedsearches(GetSessionKey().session_key, SAVEDSEARCH_CONF_FILE, "threatq_match_indicators", final_ss_query)
                ss_part1 = savedsearch_queries.RAW_EVENTS_SAVEDSEARCH_WITH_IS_TRUE["threatq_update_matched_indicators"]["ss_1"]
                ss_part2 = savedsearch_queries.RAW_EVENTS_SAVEDSEARCH_WITH_IS_TRUE["threatq_update_matched_indicators"]["ss_2"]
                final_ss_query = ss_part1 + " | table _raw `splunk_custom_fields_macro` _time " + ss_part2
                post_custom_fields_savedsearches(GetSessionKey().session_key, SAVEDSEARCH_CONF_FILE, "threatq_update_matched_indicators", final_ss_query)
            return True
        except Exception as e:
            msg = "Unrecognized error: {}".format(str(e))
            logger.error(msg)
            self.put_msg(msg)
            logger.error(traceback.format_exc())
            return False


class CustomDataModel(Validator):
    """Class provides methods for handling Datamodels."""

    def __init__(self, *args, **kwargs):
        """Initialize the parameters."""
        super(CustomDataModel, self).__init__(*args, **kwargs)
        self._validator = validator
        self._args = args
        self._kwargs = kwargs
        self.path = os.path.abspath(__file__)
    
    def validate(self, value, data):
        try:
            dm_combo = data.get("custom_datamodels", None)
            fields_selected = data.get("custom_dm_match_fields", None)
            custom_dm_chkbx = str(data.get("custom_dm_matching", "0")).lower() in ["1", "true", "yes"]
            if custom_dm_chkbx:
                if not dm_combo:
                    self.put_msg("Please select a custom datamodel.")
                    return False
                if not fields_selected:
                    self.put_msg("Please select Fields for Matching.")
                    return False

            datamodel_selected = None
            object_selected = None

            if dm_combo:
                parts = dm_combo.split(" - ", 1)
                datamodel_selected = parts[0].strip()
                if len(parts) > 1:
                    object_selected = parts[1].strip()

            match_type = data.get("match_type")
            if datamodel_selected and object_selected and fields_selected and custom_dm_chkbx:
                if match_type == "datamodel":
                    savedsearch_search = (
                        '| datamodel {dm} {obj} search '
                        '| fillnull value="" {fields} '
                        '| stats count by {fields} '
                        '| threatqfieldsmatchiocs '
                        'match_fields={fields} datamodel_name={dm}'
                    ).format(
                        dm=datamodel_selected,
                        obj=object_selected,
                        fields=fields_selected,
                    )

                    create_datamodel_savedsearch(
                        session_key=GetSessionKey().session_key,
                        name=f"custom_datamodel_{datamodel_selected}_{object_selected}_savedsearch",
                        search=savedsearch_search,
                        datamodel_name=datamodel_selected,
                    )

                elif match_type == "tstats":
                    savedsearch_search = (
                        '| tstats `threatq_summariesonly` count '
                        'from datamodel={dm}.{obj} by {fields} '
                        'fillnull_value="-" '
                        '| threatqfieldsmatchiocs '
                        'match_fields="{fields}" datamodel_name="{dm}"'
                    ).format(
                        dm=datamodel_selected,
                        obj=object_selected,
                        fields=fields_selected,
                    )

                    create_tstats_savedsearch(
                        session_key=GetSessionKey().session_key,
                        name=f"custom_tstats_{datamodel_selected}_{object_selected}_savedsearch",
                        search=savedsearch_search,
                        datamodel_name=datamodel_selected,
                    )
        except Exception as e:
            msg = "Error while creating/updating custom datamodel savedsearch: {}".format(str(e))
            ui_msg = "Error while creating/updating custom datamodel savedsearch. Please Check logs."
            logger.error(msg)
            self.put_msg(ui_msg)
            logger.error(traceback.format_exc())
            return False
        else:
            return True