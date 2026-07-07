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
import json

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_outliers_render.log" % splunkhome,
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
from trackme_libs import trackme_reqinfo, run_splunk_search

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# Import trackme libs mloutliers
from trackme_libs_mloutliers import return_lightsimulation_search


@Configuration(distributed=False)
class SplkOutliersRender(GeneratingCommand):
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
        validate=validators.Match("component", r"^(?:dsm|dhm|flx|fqm|wlk)$"),
    )

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** Optional, The value for object.""",
        require=False,
        default="*",
        validate=validators.Match("object", r"^.*$"),
    )

    object_id = Option(
        doc="""
        **Syntax:** **object_id=****
        **Description:** Optional, The value for object id.""",
        require=False,
        default="*",
        validate=validators.Match("object_id", r"^.*$"),
    )

    model_id = Option(
        doc="""
        **Syntax:** **model_id=****
        **Description:** The Machine Learning model ID to be rendered, optional and defaults to the first model defined for the entity.""",
        require=False,
        validate=validators.Match("model_id", r"^.*$"),
    )

    mode = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The rendering mode, live model retrieves the model definition from the KVstore, simulation from the model_def argument.""",
        require=False,
        default="live",
        validate=validators.Match("mode", r"^(live|simulation|lightsimulation)$"),
    )

    model_json_def = Option(
        doc="""
        **Syntax:** **model_json_def=****
        **Description:** If in simulation mode, the JSON definition for the ML model.""",
        require=False,
        validate=validators.Match("model_json_def", r"^.*$"),
    )

    earliest = Option(
        doc="""
        **Syntax:** **earliest=****
        **Description:** The earliest time for the search.""",
        require=False,
        default=None,
    )

    latest = Option(
        doc="""
        **Syntax:** **latest=****
        **Description:** The latest time for the search.""",
        require=False,
        default=None,
    )

    lowerbound_negative = Option(
        doc="""
        **Syntax:** **lowerbound_negative=****
        **Description:** Allow negative lowerBound.""",
        require=False,
        default=False,
        validate=validators.Match("mode", r"^(True|False)$"),
    )

    auto_correct = Option(
        doc="""
        **Syntax:** **auto_correct=****
        **Description:** Automatically correct lower bound and upper bound calculations notably using the min lower and upper deviation percentage.""",
        require=False,
        default=True,
        validate=validators.Match("mode", r"^(True|False)$"),
    )

    allow_auto_train = Option(
        doc="""
        **Syntax:** **allow_auto_train=****
        **Description:** Allows automated ML training if not trained since more than system wide parameter.""",
        require=False,
        default=False,
    )

    def _get_log_object_ref(self):
        """Helper function to get object reference for logging (includes object_id when available)."""
        object_id_ref = f'object_id="{self.object_id}"' if self.object_id != "*" else ""
        object_ref = f'object="{self.object}"' if self.object != "*" else ""
        if object_id_ref and object_ref:
            return f'{object_id_ref}, {object_ref}'
        elif object_id_ref:
            return object_id_ref
        elif object_ref:
            return object_ref
        else:
            return 'object="*"'

    def force_model_training(self, header, entity_outlier, entity_outlier_dict):

        # Attempt to update the ml lookup permissions
        rest_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_outliers_engine/write/outliers_train_entity_model"

        post_data = {
            "tenant_id": self.tenant_id,
            "component": self.component,
            "mode": "live",
            "entity_outlier": entity_outlier,
            "entity_outlier_dict": entity_outlier_dict,
        }
        # Prefer object_id if available, otherwise fall back to object
        if self.object_id != "*":
            post_data["object_id"] = self.object_id
        elif self.object != "*":
            post_data["object"] = self.object

        logging.debug(f'post_data="{json.dumps(post_data, indent=2)}"')

        try:
            response = requests.post(
                rest_url,
                headers=header,
                data=json.dumps(post_data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, failure to process ML model training, url="{rest_url}", data="{json.dumps(post_data, indent=0)}", response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(error_msg)
            else:
                return response

        except Exception as e:
            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, ML model training failed to process with exception: "{str(e)}"'
            raise Exception(error_msg)

    def get_entities_outliers(self, collection_rule):

        #
        # Get the Outliers rules
        #

        # Define the KV query
        # object_id takes precedence over object when both are provided
        if self.object == "*" and self.object_id == "*":
            query_string = {
                "object_category": f"splk-{self.component}",
            }
        else:
            if self.object_id != "*":
                # Use object_id first (preferred method)
                query_string_filter = {
                    "object_category": f"splk-{self.component}",
                    "_key": self.object_id,
                }
            elif self.object != "*":
                # Fall back to object if object_id is not provided
                query_string_filter = {
                    "object_category": f"splk-{self.component}",
                    "object": self.object,
                }

            query_string = {"$and": [query_string_filter]}

        # Get the current record
        # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

        key = None

        try:
            records_outliers_rules = collection_rule.data.query(
                query=json.dumps(query_string)
            )
            record_outliers_rules = records_outliers_rules[0]
            key = record_outliers_rules.get("_key")

        except Exception as e:
            key = None

        # if no records
        if not key:
            object_ref = self.object if self.object != "*" else f"object_id={self.object_id}"
            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {object_ref} outliers rules record cannot be found or are not yet available for this entity.'
            logging.error(msg)
            raise Exception(msg)

        # log debug
        logging.debug(f'record_outliers_rules="{record_outliers_rules}"')

        # If object_id was used, extract object from the record for use in subsequent code
        if self.object == "*" and self.object_id != "*":
            object_from_record = record_outliers_rules.get("object")
            if object_from_record:
                # Update self.object so it can be used throughout the code
                self.object = object_from_record
                logging.debug(f'Extracted object="{object_from_record}" from record using object_id="{self.object_id}"')

        # Get the JSON outliers rules object
        entities_outliers = record_outliers_rules.get("entities_outliers")

        # Load as a dict
        try:
            entities_outliers = json.loads(
                record_outliers_rules.get("entities_outliers")
            )
            return record_outliers_rules, entities_outliers

        except Exception as e:
            msg = f'Failed to load entities_outliers with exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

    def run_render_search(self, header, post_data):

        # Run the search and render outliers
        rest_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_outliers_engine/outliers_render_entity_model"

        try:
            response = requests.post(
                rest_url,
                headers=header,
                data=json.dumps(post_data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, failure to process ML model rendering, url="{rest_url}", data="{json.dumps(post_data, indent=0)}", response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, action="success", url="{rest_url}", ML model rendering processed successfully, response.status_code="{response.status_code}"'
                )
                return response.json().get("search_results")

        except Exception as e:
            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, ML model rendering failed to be processed with exception: "{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

    def check_model_existence(self, header, model_id, model_storage="file", tenant_id=None):

        # Check that the model exists: run a POST call to TrackMe endpoint /services/trackme/v2/splk_outliers_engine/outliers_check_model
        # with model_id as the payload, retrieve model_exists (boolean) from the response
        # if the model does not exist, do not run the search and returns a message instead

        check_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_outliers_engine/outliers_check_model"
        model_exists = False

        post_data = {"model_id": model_id}
        if model_storage:
            post_data["model_storage"] = model_storage
        if tenant_id:
            post_data["tenant_id"] = tenant_id

        try:
            response = requests.post(
                check_url,
                headers=header,
                data=json.dumps(post_data),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", failure to check model existence, url="{check_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)

            model_exists = response.json().get("model_exists")
            logging.debug(f'model_exists="{model_exists}"')

        except Exception as e:
            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", failure to check model existence with exception: "{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

        return model_exists

    def generate(self, **kwargs):
        # track run_time
        start = time.time()

        # Validate that at least one of object or object_id is provided
        if self.object == "*" and self.object_id == "*":
            msg = f'tenant_id="{self.tenant_id}", component="{self.component}", Either object or object_id must be provided.'
            logging.error(msg)
            raise Exception(msg)

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Retrieve the max time in days for a model to have been last trained from reqinfo
        splk_outliers_max_days_since_last_train_default = int(
            reqinfo["trackme_conf"]["splk_outliers_detection"][
                "splk_outliers_max_days_since_last_train_default"
            ]
        )

        # set earliest and latest
        if not self.earliest:
            earliest = self._metadata.searchinfo.earliest_time
        else:
            earliest = self.earliest

        if not self.latest:
            latest = self._metadata.searchinfo.latest_time
        else:
            latest = self.latest

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }

        # Outliers rules storage collection
        collection_rules_name = (
            f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id}"
        )
        collection_rule = self.service.kvstore[collection_rules_name]

        try:
            record_outliers_rules, entities_outliers = self.get_entities_outliers(
                collection_rule
            )
        except Exception as e:
            msg = f'Failed to get entities_outliers with exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        #
        # mode live
        #

        if self.mode == "live":
            # log debug
            logging.debug("mode is live")

            #
            # check model existence
            #

            # Determine model_storage from entity_outlier_dict for proper existence check
            # Default depends on algorithm: native algorithms default to kvstore, MLTK to file
            entity_model_storage = "file"
            if self.model_id and self.model_id in entities_outliers:
                entity_dict = entities_outliers[self.model_id]
                entity_algo = entity_dict.get("algorithm", "")
                is_native = entity_algo == "TrackMeNativeDensityFunction"
                default_storage = "kvstore" if is_native else "file"
                entity_model_storage = entity_dict.get("model_storage", default_storage)

            # Check model existence based on storage type
            if entity_model_storage == "kvstore" and self.tenant_id:
                # For KVstore-based models (native density function), check directly
                # using the service context — this is the same approach trackmeapply uses
                # and avoids REST handler indirection which has namespace issues with
                # dynamically-created per-tenant collections
                try:
                    collection_name = f"kv_trackme_native_ml_models_tenant_{self.tenant_id}"
                    collection = self.service.kvstore[collection_name]
                    records = collection.data.query(query=json.dumps({"_key": self.model_id}))
                    model_exists = bool(records and len(records) > 0)
                    if model_exists:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                            f'model_id="{self.model_id}", model found in KVstore collection "{collection_name}"'
                        )
                    else:
                        logging.warning(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                            f'model_id="{self.model_id}", model not found in KVstore collection "{collection_name}"'
                        )
                except Exception as e:
                    model_exists = False
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                        f'model_id="{self.model_id}", failed to check KVstore model existence with exception="{str(e)}"'
                    )
            else:
                # For file-based models (MLTK or native file storage), use the REST handler check
                model_exists = self.check_model_existence(header, self.model_id, model_storage=entity_model_storage, tenant_id=self.tenant_id)

            if not model_exists:

                # For KVstore-based native models with auto_train enabled, the model may not yet
                # exist because of a schema migration (e.g. 2315 migrating from file-based to KVstore).
                # In this case, instead of returning a "model not found" message, we trigger an
                # automatic training so the user sees results immediately after upgrade.
                if (
                    entity_model_storage == "kvstore"
                    and self.allow_auto_train == "True"
                    and self.model_id
                    and self.model_id in entities_outliers
                ):
                    entity_outlier_dict = entities_outliers[self.model_id]
                    entity_algo = entity_outlier_dict.get("algorithm", "")

                    if entity_algo == "TrackMeNativeDensityFunction":
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                            f'model_id="{self.model_id}", KVstore model does not exist yet but auto_train is enabled '
                            f'and algorithm is TrackMeNativeDensityFunction — triggering automatic training '
                            f'(likely post-migration scenario)'
                        )

                        try:
                            response = self.force_model_training(
                                header, self.model_id, entity_outlier_dict
                            )
                            logging.info(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                                f'model_id="{self.model_id}", action="success", auto-training for missing KVstore model '
                                f'processed successfully, response.status_code="{response.status_code}"'
                            )
                            # Training succeeded — the model now exists in KVstore,
                            # set model_exists to True so we proceed to rendering
                            model_exists = True

                            # Reload entities_outliers from KVstore since training has
                            # updated the entity rules (ml_model_render_search, etc.
                            # were "pending" before training and are now populated)
                            try:
                                record_outliers_rules, entities_outliers = self.get_entities_outliers(
                                    collection_rule
                                )
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                                    f'model_id="{self.model_id}", successfully reloaded entities_outliers after auto-training'
                                )
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                                    f'model_id="{self.model_id}", failed to reload entities_outliers after auto-training '
                                    f'with exception: "{str(e)}"'
                                )

                        except Exception as e:
                            error_msg = (
                                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, '
                                f'model_id="{self.model_id}", auto-training for missing KVstore model failed '
                                f'with exception: "{str(e)}"'
                            )
                            logging.error(error_msg)
                            # Training failed — fall through to the "model not found" message below

                if not model_exists:
                    # response_final
                    response_final = {
                        "_time": time.time(),
                        "_raw": f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{self.model_id}", The requested model {self.model_id} does not exist, or it has not been generated and trained yet, or your input is incorrect.',
                    }

                    logging.warning(json.dumps(response_final, indent=2))

                    # yield
                    yield {
                        "_time": response_final["_time"],
                        "_raw": response_final,
                    }

            if model_exists:

                # Load the account and the general enablement
                try:
                    ds_account = record_outliers_rules.get("ds_account")
                    outliers_is_disabled = int(record_outliers_rules.get("is_disabled"))
                    logging.debug(
                        f'ds_account="{ds_account}", is_disabled="{outliers_is_disabled}"'
                    )
                except Exception as e:
                    msg = f'Failed to extract one or more expected settings from the entity, is this record corrupted? Exception="{str(e)}"'
                    logging.error(msg)
                    raise Exception(msg)

                #
                # Start
                #

                # Only proceed is enabled

                # proceed
                if outliers_is_disabled == 1:
                    yield {
                        "_time": time.time(),
                        "_raw": "Outliers detection are disabled at the global level for this entity, nothing to do.",
                        "response": "Outliers detection are disabled at the global level for this entity, nothing to do.",
                    }

                elif outliers_is_disabled == 0:
                    # set a list for error reporting purposes of available modesl
                    entity_outliers_models = []

                    # Process render
                    process_render = False

                    # Loop through outliers entities
                    for entity_outlier in entities_outliers:
                        # check is_disabled
                        is_disabled = int(
                            entities_outliers[entity_outlier]["is_disabled"]
                        )

                        # log debug
                        logging.debug(
                            f'entity_outlier="{entity_outlier}", is_disabled="{is_disabled}"'
                        )

                        # Add to the list
                        if is_disabled == 0:
                            entity_outliers_models.append(entity_outlier)
                        else:
                            logging.debug(
                                f'entity_outlier="{entity_outlier}", entity is disabled, is_disabled="{is_disabled}"'
                            )

                    # if all models have been disabked
                    if not entity_outliers_models:
                        # bool
                        process_render = False

                        # yield
                        yield {
                            "_time": time.time(),
                            "_raw": "All models for this entity are currently disabled, nothing to do.",
                            "response": "All models for this entity are currently disabled, nothing to do.",
                        }

                    elif self.model_id:
                        # check is_disabled for this model
                        try:
                            is_disabled = int(
                                entities_outliers[self.model_id]["is_disabled"]
                            )
                        except Exception as e:
                            is_disabled = 0

                        # log debug
                        logging.debug(
                            f'model_id="{self.model_id}", is_disabled="{is_disabled}"'
                        )

                        if is_disabled != 0:
                            # bool
                            process_render = False

                            # yield
                            yield {
                                "_time": time.time(),
                                "_raw": "This model is currently disabled, nothing to do.",
                                "response": "This model is currently disabled, nothing to do.",
                            }

                        else:
                            # bool
                            process_render = True

                            # normalise
                            model_id = self.model_id

                    else:
                        # bool
                        process_render = True

                        # normalise, select first available model
                        model_id = entity_outliers_models[0]

                    # if process render
                    if process_render:
                        # Extract as a dict
                        entity_outlier_dict = entities_outliers[model_id]

                        # log debug
                        logging.debug(f'entity_outlier_dict="{entity_outlier_dict}"')

                        try:
                            # Extract the last_exec (epochtime)
                            ml_model_last_exec = float(entity_outlier_dict["last_exec"])

                            # Calculate the time since last execution as ml_model_time_since_last_train
                            ml_model_time_since_last_train = round(
                                time.time() - ml_model_last_exec, 0
                            )
                            ml_model_time_since_last_train = int(
                                ml_model_time_since_last_train
                            )

                        except Exception as e:
                            ml_model_time_since_last_train = 0

                        # if the time since last train is greater than the max days since last train
                        if self.allow_auto_train == "True":

                            # convert splk_outliers_max_days_since_last_train_default from days to seconds
                            splk_outliers_max_days_since_last_train_default = (
                                splk_outliers_max_days_since_last_train_default * 86400
                            )

                            if (
                                ml_model_time_since_last_train
                                > splk_outliers_max_days_since_last_train_default
                            ):
                                # force model training
                                try:
                                    response = self.force_model_training(
                                        header, entity_outlier, entity_outlier_dict
                                    )
                                    logging.info(
                                        f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", action="success", force model training processed successfully, response.status_code="{response.status_code}"'
                                    )
                                except Exception as e:
                                    error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", failure to process ML model training with exception: "{str(e)}"'
                                    logging.error(error_msg)
                            else:
                                # auto train is not required
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", action="success", force model training not required, ml_model_time_since_last_train="{ml_model_time_since_last_train}", splk_outliers_max_days_since_last_train_default="{splk_outliers_max_days_since_last_train_default}"'
                                )

                        else:
                            # only log in debug
                            logging.debug(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", action="success", force model training not allowed, allow_auto_train="{self.allow_auto_train}"'
                            )

                        # Extract the render search
                        ml_model_render_search = entity_outlier_dict[
                            "ml_model_render_search"
                        ]

                        # if the search is pending, rendering outliers is not ready yet
                        if ml_model_render_search == "pending":
                            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", The ML search is not yet available for rendering, please train this model first.'
                            logging.warning(error_msg)
                            raise Exception(error_msg)

                        # log debug
                        logging.debug(
                            f'ml_model_render_search="{ml_model_render_search}"'
                        )

                        # Get the perc_min_lowerbound_deviation
                        perc_min_lowerbound_deviation = float(
                            entity_outlier_dict["perc_min_lowerbound_deviation"]
                        )
                        logging.debug(
                            f'perc_min_lowerbound_deviation="{perc_min_lowerbound_deviation}"'
                        )

                        # Get the perc_min_upperbound_deviation
                        perc_min_upperbound_deviation = float(
                            entity_outlier_dict["perc_min_upperbound_deviation"]
                        )
                        logging.debug(
                            f'perc_min_upperbound_deviation="{perc_min_upperbound_deviation}"'
                        )

                        # Get min_value_for_lowerbound_breached/min_value_for_upperbound_breached, if not defined, set default value to 0
                        try:
                            min_value_for_lowerbound_breached = float(
                                entity_outlier_dict["min_value_for_lowerbound_breached"]
                            )
                        except Exception as e:
                            min_value_for_lowerbound_breached = 0

                        try:
                            min_value_for_upperbound_breached = float(
                                entity_outlier_dict["min_value_for_upperbound_breached"]
                            )
                        except Exception as e:
                            min_value_for_upperbound_breached = 0

                        # log debug
                        logging.debug(
                            f'min_value_for_lowerbound_breached="{min_value_for_lowerbound_breached}", min_value_for_upperbound_breached="{min_value_for_upperbound_breached}"'
                        )

                        # Get static_lower_threshold and static_upper_threshold, if not defined, set default value to None
                        try:
                            static_lower_threshold = float(
                                entity_outlier_dict["static_lower_threshold"]
                            )
                        except Exception as e:
                            static_lower_threshold = None

                        try:
                            static_upper_threshold = float(
                                entity_outlier_dict["static_upper_threshold"]
                            )
                        except Exception as e:
                            static_upper_threshold = None

                        # log debug
                        logging.debug(
                            f'static_lower_threshold="{static_lower_threshold}", static_upper_threshold="{static_upper_threshold}"'
                        )

                        # Run the search and render outliers
                        post_data = {
                            "tenant_id": self.tenant_id,
                            "object": self.object,
                            "component": self.component,
                            "mode": self.mode,
                            "model_id": model_id,
                            "earliest_time": self._metadata.searchinfo.earliest_time,
                            "latest_time": self._metadata.searchinfo.latest_time,
                        }

                        try:
                            search_results = self.run_render_search(
                                header,
                                post_data,
                            )
                        except Exception as e:
                            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", ML model rendering failed to be processed with exception: "{str(e)}"'
                            logging.error(error_msg)
                            raise Exception(error_msg)

                        # loop through the reader results
                        for item in search_results:
                            if isinstance(item, dict):
                                search_results = item

                                # raw results logged only in debug
                                logging.debug(f'search_results="{search_results}"')

                                # if a static_lower_threshold and static_upper_threshold are defined, use them instead of the generated ones
                                if static_lower_threshold:
                                    item["LowerBound"] = static_lower_threshold

                                if static_upper_threshold:
                                    item["UpperBound"] = static_upper_threshold

                                # yield_record
                                yield_record = {}

                                # auto correct parameter, can come as an option to the CLI or part of the model definition
                                auto_correct = True

                                try:
                                    model_auto_correct = int(
                                        entity_outlier_dict["auto_correct"]
                                    )
                                    if model_auto_correct == 0:
                                        auto_correct = False
                                    elif model_auto_correct == 1:
                                        auto_correct = True
                                except Exception as e:
                                    if self.auto_correct == "True":
                                        auto_correct = True
                                    elif self.auto_correct == "False":
                                        auto_correct = self.auto_correct

                                # log
                                logging.debug(f'auto_correct="{auto_correct}"')

                                # loop through the fields, and process outliers rendering
                                for k in search_results:
                                    # log if the lower and/or upper outliers were corrected
                                    LowerBoundWasCorrected = 0
                                    LowerBoundCorrectionReason = "N/A"
                                    UpperBoundWasCorrected = 0
                                    UpperBoundCorrectionReason = "N/A"

                                    # get the kpi metric name and value
                                    kpi_metric_name = entity_outlier_dict["kpi_metric"]
                                    kpi_metric_value = search_results[
                                        entity_outlier_dict["kpi_metric"]
                                    ]
                                    logging.debug(
                                        f'kpi_metric_name="{kpi_metric_name}", kpi_metric_value="{kpi_metric_value}"'
                                    )

                                    # calculate the perc_min_lowerbound_deviation value
                                    perc_min_lowerbound_deviation_value = (
                                        float(kpi_metric_value)
                                        * int(perc_min_lowerbound_deviation)
                                        / 100
                                    )
                                    logging.debug(
                                        f"kpi_metric_value={kpi_metric_value}, perc_min_lowerbound_deviation={perc_min_lowerbound_deviation}, perc_min_lowerbound_deviation_value={perc_min_lowerbound_deviation_value}"
                                    )

                                    # calculate the perc_min_upperbound_deviation value
                                    perc_min_upperbound_deviation_value = (
                                        float(kpi_metric_value)
                                        * int(perc_min_upperbound_deviation)
                                        / 100
                                    )
                                    logging.debug(
                                        f"kpi_metric_value={kpi_metric_value}, perc_min_upperbound_deviation={perc_min_upperbound_deviation}, perc_min_upperbound_deviation_value={perc_min_upperbound_deviation_value}"
                                    )

                                    # calculate the corrected candidates
                                    LowerBoundMin = float(kpi_metric_value) - float(
                                        perc_min_lowerbound_deviation_value
                                    )
                                    UpperBoundMin = float(kpi_metric_value) + float(
                                        perc_min_upperbound_deviation_value
                                    )
                                    logging.debug(
                                        f'LowerBoundMin="{LowerBoundMin}", UpperBoundMin="{UpperBoundMin}"'
                                    )

                                    # try to get the LowerBound and UpperBound, if we have no results (not enough historical data), apply corrected values instead
                                    try:
                                        LowerBound = search_results["LowerBound"]
                                    except Exception as e:
                                        LowerBoundWasCorrected = 1
                                        LowerBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                                        LowerBound = LowerBoundMin
                                        logging.warning(
                                            f'Could not retrieve a LowerBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{LowerBound}" instead'
                                        )

                                    try:
                                        UpperBound = search_results["UpperBound"]
                                    except Exception as e:
                                        UpperBoundWasCorrected = 1
                                        UpperBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                                        UpperBound = UpperBoundMin
                                        logging.warning(
                                            f'Could not retrieve a UpperBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{UpperBound}" instead'
                                        )

                                    # Degenerate-state guards (insufficient-data handling).
                                    # These run regardless of auto_correct because they handle a
                                    # degenerate native output (native_apply emits LowerBound=0,
                                    # UpperBound=0 when the model has status != "fitted", e.g. when
                                    # the training data volume was below the native fit minimum).
                                    # Without these guards, auto_correct=0 would propagate 0/0 bounds
                                    # downstream and the simulation would render N/A cells.
                                    # The statistical deviation-based corrections below remain gated
                                    # behind `if auto_correct:` where they belong.
                                    if (
                                        float(LowerBound) <= 0
                                        and not self.lowerbound_negative == "True"
                                    ):
                                        LowerBoundWasCorrected = 1
                                        LowerBoundCorrectionReason = f"Generated LowerBound {float(LowerBound)} is negative or equal to 0 (likely insufficient historical data)"
                                        LowerBoundOrig = LowerBound
                                        LowerBound = float(LowerBoundMin)

                                    if float(UpperBound) <= 0:
                                        UpperBoundWasCorrected = 1
                                        UpperBoundCorrectionReason = f"Generated UpperBound {float(UpperBound)} is negative or equal to 0 (likely insufficient historical data)"
                                        UpperBoundOrig = UpperBound
                                        UpperBound = float(UpperBoundMin)

                                    if float(LowerBound) == float(UpperBound):
                                        # bounds collapsed to the same value (e.g. both 0 from an
                                        # unfitted model) — substitute safety margins for both
                                        _collapsed_lower = LowerBound
                                        _collapsed_upper = UpperBound
                                        LowerBoundWasCorrected = 1
                                        LowerBoundCorrectionReason = f"LowerBound value {_collapsed_lower} and UpperBound value {_collapsed_upper} cannot be equal (likely insufficient historical data)"
                                        LowerBoundOrig = _collapsed_lower
                                        LowerBound = float(LowerBoundMin)

                                        UpperBoundWasCorrected = 1
                                        UpperBoundCorrectionReason = f"LowerBound value {_collapsed_lower} and UpperBound value {_collapsed_upper} cannot be equal (likely insufficient historical data)"
                                        UpperBoundOrig = _collapsed_upper
                                        UpperBound = float(UpperBoundMin)

                                    # apply
                                    if auto_correct:
                                        # condition for a lower outlier: generated lower threshold is greater than the kpi value
                                        # condition for an upper outlier: generated upper threshold is lower than the kpi value

                                        currentLowerBoundDeviationValue = float(
                                            LowerBound
                                        ) - float(kpi_metric_value)

                                        logging.debug(
                                            f"currentLowerBoundDeviationValue={currentLowerBoundDeviationValue}"
                                        )

                                        currentUpperBoundDeviationValue = float(
                                            kpi_metric_value
                                        ) - float(UpperBound)

                                        logging.debug(
                                            f"currentUpperBoundDeviationValue={currentUpperBoundDeviationValue}"
                                        )

                                        # for lowerBound, replace as well if equal or lower than 0 unless requested to allow this behavior
                                        if (
                                            float(LowerBound) <= 0
                                            and not self.lowerbound_negative == "True"
                                        ):
                                            LowerBoundWasCorrected = 1
                                            LowerBoundCorrectionReason = f"Generated LowerBound {float(LowerBound)} is negative or equal to 0"
                                            LowerBoundOrig = LowerBound
                                            LowerBound = float(LowerBoundMin)

                                        # for upperBound, replace as well if equal or lower than 0
                                        if float(UpperBound) <= 0:
                                            UpperBoundWasCorrected = 1
                                            UpperBoundCorrectionReason = f"Generated UpperBound {float(UpperBound)} is negative or equal to 0"
                                            UpperBoundOrig = UpperBound
                                            UpperBound = float(UpperBoundMin)

                                        #
                                        # lower
                                        #

                                        # if a lower outlier is said to be detected
                                        if float(LowerBound) > float(kpi_metric_value):
                                            # the generated lower bound should be not lower than the safety margin
                                            if not float(
                                                currentLowerBoundDeviationValue
                                            ) > float(
                                                perc_min_lowerbound_deviation_value
                                            ):
                                                # apply safeties instead of generated
                                                LowerBoundWasCorrected = 1
                                                LowerBoundCorrectionReason = f"Current LowerBound deviation value {round(currentLowerBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_lowerbound_deviation_value} using {perc_min_lowerbound_deviation} pct deviation"
                                                LowerBoundOrig = LowerBound
                                                LowerBound = float(LowerBoundMin)

                                            else:
                                                # else accept the outlier
                                                LowerBoundOrig = LowerBound

                                        else:
                                            LowerBoundOrig = LowerBound

                                        #
                                        # upper
                                        #

                                        # If an upper outlier is said to be detected
                                        if float(UpperBound) < float(kpi_metric_value):
                                            # the generated upper bound should be higher than the safety margin
                                            if not float(
                                                currentUpperBoundDeviationValue
                                            ) > float(
                                                perc_min_upperbound_deviation_value
                                            ):
                                                # apply safeties instead of generated
                                                UpperBoundWasCorrected = 1
                                                UpperBoundCorrectionReason = f"Current UpperBound deviation value {round(currentUpperBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_upperbound_deviation_value} using {perc_min_upperbound_deviation} pct deviation"
                                                UpperBoundOrig = UpperBound
                                                UpperBound = float(UpperBoundMin)

                                            # else accept the outlier
                                            else:
                                                UpperBoundOrig = UpperBound

                                        else:
                                            UpperBoundOrig = UpperBound

                                        # lower bound and upper bound cannot be equal
                                        if float(LowerBound) == float(UpperBound):
                                            # apply safeties instead of generated
                                            LowerBoundWasCorrected = 1
                                            LowerBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                                            LowerBoundOrig = LowerBound
                                            LowerBound = float(LowerBoundMin)

                                            # apply safeties instead of generated
                                            UpperBoundWasCorrected = 1
                                            UpperBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                                            UpperBoundOrig = UpperBound
                                            UpperBound = float(UpperBoundMin)

                                    # do not correct anything
                                    else:
                                        LowerBoundOrig = LowerBound
                                        UpperBoundOrig = UpperBound

                                    # handle min_value_for_lowerbound_breached / min_value_for_upperbound_breached
                                    rejectedLowerboundOutlier = 0
                                    rejectedUpperboundOutlier = 0
                                    rejectedLowerboundOutlierReason = "N/A"
                                    rejectedUpperboundOutlierReason = "N/A"

                                    if float(kpi_metric_value) < float(
                                        min_value_for_lowerbound_breached
                                    ):
                                        rejectedLowerboundOutlier = 1
                                        rejectedLowerboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"
                                    else:
                                        rejectedLowerboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"

                                    if float(kpi_metric_value) < float(
                                        min_value_for_upperbound_breached
                                    ):
                                        rejectedUpperboundOutlier = 1
                                        rejectedUpperboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"
                                    else:
                                        rejectedUpperboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"

                                    # finally, create isLowerBoundOutlier / isUpperBoundOutlier (0/1)
                                    if (
                                        float(kpi_metric_value) < float(LowerBound)
                                        and rejectedLowerboundOutlier == 0
                                    ):
                                        isLowerBoundOutlier = 1
                                        pct_decrease = (
                                            (
                                                float(LowerBound)
                                                - float(kpi_metric_value)
                                            )
                                            / float(LowerBound)
                                        ) * 100
                                        isLowerBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", LowerBound="{round(float(LowerBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{search_results["_time"]}", pct_decrease="{round(float(pct_decrease), 2)}"'

                                    else:
                                        isLowerBoundOutlier = 0
                                        isLowerBoundOutlierReason = "N/A"

                                    if (
                                        float(kpi_metric_value) > float(UpperBound)
                                        and rejectedUpperboundOutlier == 0
                                    ):
                                        isUpperBoundOutlier = 1
                                        pct_increase = (
                                            (
                                                float(kpi_metric_value)
                                                - float(UpperBound)
                                            )
                                            / float(UpperBound)
                                        ) * 100
                                        isUpperBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", model_id="{model_id}", UpperBound="{round(float(UpperBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{search_results["_time"]}", pct_increase="{round(float(pct_increase), 2)}"'

                                    else:
                                        isUpperBoundOutlier = 0
                                        isUpperBoundOutlierReason = "N/A"

                                    # Add to the dict
                                    yield_record["_time"] = search_results["_time"]
                                    yield_record["LowerBound"] = LowerBound
                                    yield_record["UpperBound"] = UpperBound
                                    yield_record["isLowerBoundOutlier"] = (
                                        isLowerBoundOutlier
                                    )
                                    yield_record["isLowerBoundOutlierReason"] = (
                                        isLowerBoundOutlierReason
                                    )
                                    yield_record["isUpperBoundOutlier"] = (
                                        isUpperBoundOutlier
                                    )
                                    yield_record["isUpperBoundOutlierReason"] = (
                                        isLowerBoundOutlierReason
                                    )
                                    yield_record["isOutlier"] = 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                                    yield_record[kpi_metric_name] = kpi_metric_value
                                    yield_record["kpi_metric_name"] = kpi_metric_name
                                    yield_record["kpi_metric_value"] = kpi_metric_value
                                    yield_record["LowerBoundMin"] = LowerBoundMin
                                    yield_record["LowerBoundOrig"] = LowerBoundOrig
                                    yield_record["LowerBoundWasCorrected"] = (
                                        LowerBoundWasCorrected
                                    )
                                    yield_record["LowerBoundCorrectionReason"] = (
                                        LowerBoundCorrectionReason
                                    )
                                    yield_record["UpperBoundMin"] = UpperBoundMin
                                    yield_record["UpperBoundOrig"] = UpperBoundOrig
                                    yield_record["UpperBoundWasCorrected"] = (
                                        UpperBoundWasCorrected
                                    )
                                    yield_record["UpperBoundCorrectionReason"] = (
                                        UpperBoundCorrectionReason
                                    )
                                    yield_record[
                                        "min_value_for_lowerbound_breached"
                                    ] = min_value_for_lowerbound_breached
                                    yield_record[
                                        "min_value_for_upperbound_breached"
                                    ] = min_value_for_upperbound_breached
                                    yield_record["rejectedLowerboundOutlier"] = (
                                        rejectedLowerboundOutlier
                                    )
                                    yield_record["rejectedUpperboundOutlier"] = (
                                        rejectedUpperboundOutlier
                                    )
                                    yield_record["rejectedLowerboundOutlierReason"] = (
                                        rejectedLowerboundOutlierReason
                                    )
                                    yield_record["rejectedUpperboundOutlierReason"] = (
                                        rejectedUpperboundOutlierReason
                                    )

                                    # Add _raw
                                    yield_record["_raw"] = {
                                        "_time": search_results["_time"],
                                        "kpi_metric_name": kpi_metric_name,
                                        "kpi_metric_value": kpi_metric_value,
                                        "LowerBoundMin": LowerBoundMin,
                                        "LowerBoundOrig": LowerBoundOrig,
                                        "LowerBound": LowerBound,
                                        "UpperBoundMin": UpperBoundMin,
                                        "UpperBoundOrig": UpperBoundOrig,
                                        "UpperBound": UpperBound,
                                        "isLowerBoundOutlier": isLowerBoundOutlier,
                                        "isLowerBoundOutlierReason": isLowerBoundOutlierReason,
                                        "isUpperBoundOutlier": isUpperBoundOutlier,
                                        "isUpperBoundOutlierReason": isUpperBoundOutlierReason,
                                        "isOutlier": 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                                        "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                                        "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                                        "LowerBoundWasCorrected": LowerBoundWasCorrected,
                                        "LowerBoundCorrectionReason": LowerBoundCorrectionReason,
                                        "UpperBoundWasCorrected": UpperBoundWasCorrected,
                                        "UpperBoundCorrectionReason": UpperBoundCorrectionReason,
                                        "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                                        "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                                        "rejectedLowerboundOutlier": rejectedLowerboundOutlier,
                                        "rejectedUpperboundOutlier": rejectedUpperboundOutlier,
                                        "rejectedLowerboundOutlierReason": rejectedLowerboundOutlierReason,
                                        "rejectedUpperboundOutlierReason": rejectedUpperboundOutlierReason,
                                        "search_results": search_results,
                                    }

                                # yield
                                yield yield_record

                        # log
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", search was terminated successfully, duration={time.time() - start}, search="{ml_model_render_search}"'
                        )

        elif self.mode == "simulation":
            # log debug
            logging.debug("mode is simulation")

            # set model_id
            model_id = self.model_id

            # log debug
            logging.debug(f"model_json_def={self.model_json_def}")

            # load the model definition as a dict
            try:
                model_json_def = json.loads(self.model_json_def)
                # log debug
                logging.debug(
                    f'successfully loaded model_json_def="{json.dumps(model_json_def, indent=4)}"'
                )
            except Exception as e:
                msg = f'failed to load the submitted model_json_def="{self.model_json_def}" with exception="{e}"'
                logging.error(msg)
                raise Exception(msg)

            # auto correct parameter, can come as an option to the CLI or part of the model definition
            auto_correct = True

            try:
                model_auto_correct = int(model_json_def.get("auto_correct"))
                if model_auto_correct == 0:
                    auto_correct = False
                elif model_auto_correct == 1:
                    auto_correct = True
            except Exception as e:
                if self.auto_correct == "True":
                    auto_correct = True
                elif self.auto_correct == "False":
                    auto_correct = self.auto_correct

            # log
            logging.debug(f'auto_correct="{auto_correct}"')

            #
            # pre-train the model
            #

            # set kwargs
            pretrain_kwargs = {
                "earliest_time": model_json_def.get("period_calculation"),
                "latest_time": model_json_def.get("period_calculation_latest", "now"),
                "search_mode": "normal",
                "preview": False,
                "time_format": "%s",
                "count": 0,
                "output_mode": "json",
            }

            # set the search

            # set model_json_def_str from model_json_def with double quotes replaced
            model_json_def_str = json.dumps(model_json_def).replace('"', '\\"')

            ml_model_pretrain_search = remove_leading_spaces(
                f"""\
                    | trackmesplkoutlierstrain tenant_id="{self.tenant_id}" component="{self.component}" object="{self.object}" model_id="{self.model_id}" mode="simulation" model_json_def="{model_json_def_str}"
                """
            )
            logging.debug(f"ml_model_pretrain_search {ml_model_pretrain_search}")

            # run search
            start_time_pretrain = time.time()
            try:
                reader = run_splunk_search(
                    self.service,
                    ml_model_pretrain_search,
                    pretrain_kwargs,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        # log
                        logging.debug(
                            f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, results="{json.dumps(item, indent=2)}"'
                        )

                # log info
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", search has been processed successfully, duration={round(time.time() - start_time_pretrain, 3)}, search="{ml_model_pretrain_search}"'
                )

            except Exception as e:
                msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", search has failed with the following exception="{str(e)}", search="{ml_model_pretrain_search}"'
                logging.error(msg)
                raise Exception(msg)

            #
            # process
            #

            # refresh from KV
            try:
                record_outliers_rules, entities_outliers = self.get_entities_outliers(
                    collection_rule
                )
            except Exception as e:
                msg = f'Failed to get entities_outliers with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            # Extract as a dict
            entity_outlier_dict = entities_outliers[model_id]

            # log debug
            logging.debug(f'entity_outlier_dict="{entity_outlier_dict}"')

            # Extract the render search
            ml_model_render_search = entity_outlier_dict[
                "ml_model_simulation_render_search"
            ]
            logging.debug(
                f'ml_model_simulation_render_search="{ml_model_render_search}"'
            )

            # if the search is pending, rendering outliers is not ready yet
            if ml_model_render_search == "pending":
                error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", The ML search is not yet available for rendering, please train this model first.'
                logging.warning(error_msg)
                raise Exception(error_msg)

            # Get the perc_min_lowerbound_deviation
            perc_min_lowerbound_deviation = float(
                model_json_def.get("perc_min_lowerbound_deviation")
            )
            logging.debug(
                f'perc_min_lowerbound_deviation="{perc_min_lowerbound_deviation}"'
            )

            # Get the perc_min_upperbound_deviation
            perc_min_upperbound_deviation = float(
                model_json_def.get("perc_min_upperbound_deviation")
            )
            logging.debug(
                f'perc_min_upperbound_deviation="{perc_min_upperbound_deviation}"'
            )

            # Get min_value_for_lowerbound_breached/min_value_for_upperbound_breached, if not defined, set default value to 0
            try:
                min_value_for_lowerbound_breached = float(
                    model_json_def["min_value_for_lowerbound_breached"]
                )
            except Exception as e:
                min_value_for_lowerbound_breached = 0

            try:
                min_value_for_upperbound_breached = float(
                    model_json_def["min_value_for_upperbound_breached"]
                )
            except Exception as e:
                min_value_for_upperbound_breached = 0

            # Get static_lower_threshold and static_upper_threshold, if not defined, set default value to None
            try:
                static_lower_threshold = float(model_json_def["static_lower_threshold"])
            except Exception as e:
                static_lower_threshold = None

            try:
                static_upper_threshold = float(model_json_def["static_upper_threshold"])
            except Exception as e:
                static_upper_threshold = None

            # Run the search and render outliers
            post_data = {
                "tenant_id": self.tenant_id,
                "object": self.object,
                "component": self.component,
                "mode": self.mode,
                "model_id": model_id,
                "earliest_time": self._metadata.searchinfo.earliest_time,
                "latest_time": self._metadata.searchinfo.latest_time,
            }

            try:
                search_results = self.run_render_search(
                    header,
                    post_data,
                )
            except Exception as e:
                error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, model_id="{model_id}", ML model rendering failed to be processed with exception: "{str(e)}"'
                logging.error(error_msg)
                raise Exception(error_msg)

            # loop through the reader results
            for item in search_results:
                if isinstance(item, dict):
                    search_results = item

                    # raw results logged only in debug
                    logging.debug(f'search_results="{search_results}"')

                    # if a static_lower_threshold and static_upper_threshold are defined, use them instead of the generated ones
                    if static_lower_threshold:
                        item["LowerBound"] = static_lower_threshold

                    if static_upper_threshold:
                        item["UpperBound"] = static_upper_threshold

                    # yield_record
                    yield_record = {}

                    # loop through the fields, and process outliers rendering
                    for k in search_results:
                        # log if the lower and/or upper outliers were corrected
                        LowerBoundWasCorrected = 0
                        LowerBoundCorrectionReason = "N/A"
                        UpperBoundWasCorrected = 0
                        UpperBoundCorrectionReason = "N/A"

                        # get the kpi metric name and value
                        kpi_metric_name = model_json_def.get("kpi_metric")
                        kpi_metric_value = search_results[
                            model_json_def.get("kpi_metric")
                        ]
                        logging.debug(
                            f'kpi_metric_name="{kpi_metric_name}", kpi_metric_value="{kpi_metric_value}"'
                        )

                        # calculate the perc_min_lowerbound_deviation value
                        perc_min_lowerbound_deviation_value = (
                            float(kpi_metric_value)
                            * int(perc_min_lowerbound_deviation)
                            / 100
                        )
                        logging.debug(
                            f"kpi_metric_value={kpi_metric_value}, perc_min_lowerbound_deviation={perc_min_lowerbound_deviation}, perc_min_lowerbound_deviation_value={perc_min_lowerbound_deviation_value}"
                        )

                        # calculate the perc_min_upperbound_deviation value
                        perc_min_upperbound_deviation_value = (
                            float(kpi_metric_value)
                            * int(perc_min_upperbound_deviation)
                            / 100
                        )
                        logging.debug(
                            f"kpi_metric_value={kpi_metric_value}, perc_min_upperbound_deviation={perc_min_upperbound_deviation}, perc_min_upperbound_deviation_value={perc_min_upperbound_deviation_value}"
                        )

                        # calculate the corrected candidates
                        LowerBoundMin = float(kpi_metric_value) - float(
                            perc_min_lowerbound_deviation_value
                        )
                        UpperBoundMin = float(kpi_metric_value) + float(
                            perc_min_upperbound_deviation_value
                        )
                        logging.debug(
                            f'LowerBoundMin="{LowerBoundMin}", UpperBoundMin="{UpperBoundMin}"'
                        )

                        # try to get the LowerBound and UpperBound, if we have no results (not enough historical data), apply corrected values instead
                        try:
                            LowerBound = search_results["LowerBound"]
                        except Exception as e:
                            LowerBoundWasCorrected = 1
                            LowerBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                            LowerBound = LowerBoundMin
                            logging.warning(
                                f'Could not retrieve a LowerBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{LowerBound}" instead'
                            )

                        try:
                            UpperBound = search_results["UpperBound"]
                        except Exception as e:
                            UpperBoundWasCorrected = 1
                            UpperBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                            UpperBound = UpperBoundMin
                            logging.warning(
                                f'Could not retrieve a UpperBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{UpperBound}" instead'
                            )

                        # apply
                        if auto_correct:
                            # condition for a lower outlier: generated lower threshold is greater than the kpi value
                            # condition for an upper outlier: generated upper threshold is lower than the kpi value

                            currentLowerBoundDeviationValue = float(LowerBound) - float(
                                kpi_metric_value
                            )

                            logging.debug(
                                f"currentLowerBoundDeviationValue={currentLowerBoundDeviationValue}"
                            )

                            currentUpperBoundDeviationValue = float(
                                kpi_metric_value
                            ) - float(UpperBound)

                            logging.debug(
                                f"currentUpperBoundDeviationValue={currentUpperBoundDeviationValue}"
                            )

                            # for lowerBound, replace as well if equal or lower than 0 unless requested to allow this behavior
                            if (
                                float(LowerBound) <= 0
                                and not self.lowerbound_negative == "True"
                            ):
                                LowerBoundWasCorrected = 1
                                LowerBoundCorrectionReason = f"Generated LowerBound {float(LowerBound)} is negative or equal to 0"
                                LowerBoundOrig = LowerBound
                                LowerBound = float(LowerBoundMin)

                            # for upperBound, replace as well if equal or lower than 0
                            if float(UpperBound) <= 0:
                                UpperBoundWasCorrected = 1
                                UpperBoundCorrectionReason = f"Generated UpperBound {float(UpperBound)} is negative or equal to 0"
                                UpperBoundOrig = UpperBound
                                UpperBound = float(UpperBoundMin)

                            #
                            # lower
                            #

                            # if a lower outlier is said to be detected
                            if float(LowerBound) > float(kpi_metric_value):
                                # the generated lower bound should be not lower than the safety margin
                                if not float(currentLowerBoundDeviationValue) > float(
                                    perc_min_lowerbound_deviation_value
                                ):
                                    # apply safeties instead of generated
                                    LowerBoundWasCorrected = 1
                                    LowerBoundCorrectionReason = f"Current LowerBound deviation value {round(currentLowerBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_lowerbound_deviation_value} using {perc_min_lowerbound_deviation} pct deviation"
                                    LowerBoundOrig = LowerBound
                                    LowerBound = float(LowerBoundMin)

                                else:
                                    # else accept the outlier
                                    LowerBoundOrig = LowerBound

                            else:
                                LowerBoundOrig = LowerBound

                            #
                            # upper
                            #

                            # If an upper outlier is said to be detected
                            if float(UpperBound) < float(kpi_metric_value):
                                # the generated upper bound should be higher than the safety margin

                                if not float(currentUpperBoundDeviationValue) > float(
                                    perc_min_upperbound_deviation_value
                                ):
                                    # apply safeties instead of generated
                                    UpperBoundWasCorrected = 1
                                    UpperBoundCorrectionReason = f"Current UpperBound deviation value {round(currentUpperBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_upperbound_deviation_value} using {perc_min_upperbound_deviation} pct deviation"
                                    UpperBoundOrig = UpperBound
                                    UpperBound = float(UpperBoundMin)

                                # else accept the outlier
                                else:
                                    UpperBoundOrig = UpperBound

                            else:
                                UpperBoundOrig = UpperBound

                            # lower bound and upper bound cannot be equal
                            if float(LowerBound) == float(UpperBound):
                                # apply safeties instead of generated
                                LowerBoundWasCorrected = 1
                                LowerBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                                LowerBoundOrig = LowerBound
                                LowerBound = float(LowerBoundMin)

                                # apply safeties instead of generated
                                UpperBoundWasCorrected = 1
                                UpperBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                                UpperBoundOrig = UpperBound
                                UpperBound = float(UpperBoundMin)

                        # do not correct anything
                        else:
                            LowerBoundOrig = LowerBound
                            UpperBoundOrig = UpperBound

                        # handle min_value_for_lowerbound_breached / min_value_for_upperbound_breached
                        rejectedLowerboundOutlier = 0
                        rejectedUpperboundOutlier = 0
                        rejectedLowerboundOutlierReason = "N/A"
                        rejectedUpperboundOutlierReason = "N/A"

                        if float(kpi_metric_value) < float(
                            min_value_for_lowerbound_breached
                        ):
                            rejectedLowerboundOutlier = 1
                            rejectedLowerboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"
                        else:
                            rejectedLowerboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"

                        if float(kpi_metric_value) < float(
                            min_value_for_upperbound_breached
                        ):
                            rejectedUpperboundOutlier = 1
                            rejectedUpperboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"
                        else:
                            rejectedUpperboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"

                        # finally, create isLowerBoundOutlier / isUpperBoundOutlier (0/1)
                        if (
                            float(kpi_metric_value) < float(LowerBound)
                            and rejectedLowerboundOutlier == 0
                        ):
                            isLowerBoundOutlier = 1
                            pct_decrease = (
                                (float(LowerBound) - float(kpi_metric_value))
                                / float(LowerBound)
                            ) * 100
                            isLowerBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", LowerBound="{round(float(LowerBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{search_results["_time"]}", pct_decrease="{round(float(pct_decrease), 2)}"'

                        else:
                            isLowerBoundOutlier = 0
                            isLowerBoundOutlierReason = "N/A"

                        if (
                            float(kpi_metric_value) > float(UpperBound)
                            and rejectedUpperboundOutlier == 0
                        ):
                            isUpperBoundOutlier = 1
                            pct_increase = (
                                (float(kpi_metric_value) - float(UpperBound))
                                / float(UpperBound)
                            ) * 100
                            isUpperBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", UpperBound="{round(float(UpperBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{search_results["_time"]}", pct_increase="{round(float(pct_increase), 2)}"'
                        else:
                            isUpperBoundOutlier = 0
                            isUpperBoundOutlierReason = "N/A"

                        # Add to the dict
                        yield_record["_time"] = search_results["_time"]
                        yield_record["LowerBound"] = LowerBound
                        yield_record["UpperBound"] = UpperBound
                        yield_record["isLowerBoundOutlier"] = isLowerBoundOutlier
                        yield_record["isLowerBoundOutlierReason"] = (
                            isLowerBoundOutlierReason
                        )
                        yield_record["isUpperBoundOutlier"] = isUpperBoundOutlier
                        yield_record["isUpperBoundOutlierReason"] = (
                            isLowerBoundOutlierReason
                        )
                        yield_record["isOutlier"] = 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                        yield_record[kpi_metric_name] = kpi_metric_value
                        yield_record["kpi_metric_name"] = kpi_metric_name
                        yield_record["kpi_metric_value"] = kpi_metric_value
                        yield_record["LowerBoundMin"] = LowerBoundMin
                        yield_record["LowerBoundOrig"] = LowerBoundOrig
                        yield_record["UpperBoundMin"] = UpperBoundMin
                        yield_record["UpperBoundOrig"] = UpperBoundOrig
                        yield_record["perc_min_lowerbound_deviation"] = (
                            perc_min_lowerbound_deviation
                        )
                        yield_record["perc_min_upperbound_deviation"] = (
                            perc_min_upperbound_deviation
                        )
                        yield_record["LowerBoundWasCorrected"] = LowerBoundWasCorrected
                        yield_record["LowerBoundCorrectionReason"] = (
                            LowerBoundCorrectionReason
                        )
                        yield_record["UpperBoundWasCorrected"] = UpperBoundWasCorrected
                        yield_record["UpperBoundCorrectionReason"] = (
                            UpperBoundCorrectionReason
                        )
                        yield_record["min_value_for_lowerbound_breached"] = (
                            min_value_for_lowerbound_breached
                        )
                        yield_record["min_value_for_upperbound_breached"] = (
                            min_value_for_upperbound_breached
                        )
                        yield_record["rejectedLowerboundOutlier"] = (
                            rejectedLowerboundOutlier
                        )
                        yield_record["rejectedUpperboundOutlier"] = (
                            rejectedUpperboundOutlier
                        )
                        yield_record["rejectedLowerboundOutlierReason"] = (
                            rejectedLowerboundOutlierReason
                        )
                        yield_record["rejectedUpperboundOutlierReason"] = (
                            rejectedUpperboundOutlierReason
                        )

                        # Add _raw
                        yield_record["_raw"] = {
                            "_time": search_results["_time"],
                            "kpi_metric_name": kpi_metric_name,
                            "kpi_metric_value": kpi_metric_value,
                            "isLowerBoundOutlier": isLowerBoundOutlier,
                            "isLowerBoundOutlierReason": isLowerBoundOutlierReason,
                            "isUpperBoundOutlier": isUpperBoundOutlier,
                            "isUpperBoundOutlierReason": isUpperBoundOutlierReason,
                            "isOutlier": 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                            "LowerBoundMin": LowerBoundMin,
                            "LowerBoundOrig": LowerBoundOrig,
                            "LowerBound": LowerBound,
                            "UpperBoundMin": UpperBoundMin,
                            "UpperBoundOrig": UpperBoundOrig,
                            "UpperBound": UpperBound,
                            "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                            "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                            "LowerBoundWasCorrected": LowerBoundWasCorrected,
                            "LowerBoundCorrectionReason": LowerBoundCorrectionReason,
                            "UpperBoundWasCorrected": UpperBoundWasCorrected,
                            "UpperBoundCorrectionReason": UpperBoundCorrectionReason,
                            "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                            "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                            "rejectedLowerboundOutlier": rejectedLowerboundOutlier,
                            "rejectedUpperboundOutlier": rejectedUpperboundOutlier,
                            "rejectedLowerboundOutlierReason": rejectedLowerboundOutlierReason,
                            "rejectedUpperboundOutlierReason": rejectedUpperboundOutlierReason,
                            "search_results": search_results,
                        }

                    # yield
                    yield yield_record

                # log
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", trackmesplkoutliersrender has terminated successfully, {self._get_log_object_ref()}, model_id="{self.model_id}", duration={time.time() - start}'
                )

        elif self.mode == "lightsimulation":
            # log debug
            logging.debug("mode is lightsimulation")

            # log debug
            logging.debug(f"model_json_def={self.model_json_def}")

            # load the model definition as a dict
            try:
                model_json_def = json.loads(self.model_json_def)
                # log debug
                logging.debug(
                    f'successfully loaded model_json_def="{json.dumps(model_json_def, indent=4)}"'
                )
            except Exception as e:
                msg = f'failed to load the submitted model_json_def="{self.model_json_def}" with exception="{e}"'
                logging.error(msg)
                raise Exception(msg)

            # auto correct parameter, can come as an option to the CLI or part of the model definition
            auto_correct = True

            try:
                model_auto_correct = int(model_json_def.get("auto_correct"))
                if model_auto_correct == 0:
                    auto_correct = False
                elif model_auto_correct == 1:
                    auto_correct = True
            except Exception as e:
                if self.auto_correct == "True":
                    auto_correct = True
                elif self.auto_correct == "False":
                    auto_correct = self.auto_correct

            # log
            logging.debug(f'auto_correct="{auto_correct}"')

            # Get the perc_min_lowerbound_deviation
            perc_min_lowerbound_deviation = float(
                model_json_def.get("perc_min_lowerbound_deviation")
            )
            logging.debug(
                f'perc_min_lowerbound_deviation="{perc_min_lowerbound_deviation}"'
            )

            # Get the perc_min_upperbound_deviation
            perc_min_upperbound_deviation = float(
                model_json_def.get("perc_min_upperbound_deviation")
            )
            logging.debug(
                f'perc_min_upperbound_deviation="{perc_min_upperbound_deviation}"'
            )

            # Get min_value_for_lowerbound_breached/min_value_for_upperbound_breached, if not defined, set default value to 0
            try:
                min_value_for_lowerbound_breached = float(
                    model_json_def["min_value_for_lowerbound_breached"]
                )
            except Exception as e:
                min_value_for_lowerbound_breached = 0

            try:
                min_value_for_upperbound_breached = float(
                    model_json_def["min_value_for_upperbound_breached"]
                )
            except Exception as e:
                min_value_for_upperbound_breached = 0

            # set the tenant_trackme_metric_idx
            metric_idx = None

            # get the index conf for this tenant
            url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/vtenants/tenant_idx_settings"
            data = {"tenant_id": self.tenant_id, "idx_stanza": "trackme_metric_idx"}

            # Retrieve and set the tenant idx, if any failure, logs and use the global index
            try:
                response = requests.post(
                    url,
                    headers=header,
                    data=json.dumps(data, indent=1),
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (200, 201, 204):
                    error_msg = f'failed to retrieve the tenant index, response="{response.text}"'
                    logging.error(error_msg)
                    raise Exception(error_msg)
                else:
                    metric_idx = response.json().get("trackme_metric_idx")

            except Exception as e:
                error_msg = f'failed to retrieve the tenant index, exception="{str(e)}"'
                logging.error(error_msg)
                raise Exception(error_msg)

            # define the simulation search
            ml_model_render_search = return_lightsimulation_search(
                self.tenant_id, self.component, self.object, metric_idx, model_json_def
            )

            # Get the perc_min_lowerbound_deviation
            perc_min_lowerbound_deviation = float(
                model_json_def.get("perc_min_lowerbound_deviation")
            )
            logging.debug(
                f'perc_min_lowerbound_deviation="{perc_min_lowerbound_deviation}"'
            )

            # Get the perc_min_upperbound_deviation
            perc_min_upperbound_deviation = float(
                model_json_def.get("perc_min_upperbound_deviation")
            )
            logging.debug(
                f'perc_min_upperbound_deviation="{perc_min_upperbound_deviation}"'
            )

            # set kwargs
            kwargs_oneshot = {
                "earliest_time": earliest,
                "latest_time": latest,
                "search_mode": "normal",
                "preview": False,
                "time_format": "%s",
                "count": 0,
                "output_mode": "json",
            }

            # proceed
            try:
                reader = run_splunk_search(
                    self.service,
                    ml_model_render_search,
                    kwargs_oneshot,
                    24,
                    5,
                )

            except Exception as e:
                msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, Machine Learning simulation failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
                logging.error(msg)
                raise Exception(msg)

            # loop through the reader results
            for item in reader:

                # yield_record
                yield_record = {}

                # loop through the fields, and process outliers rendering
                for k in item:
                    # log if the lower and/or upper outliers were corrected
                    LowerBoundWasCorrected = 0
                    LowerBoundCorrectionReason = "N/A"
                    UpperBoundWasCorrected = 0
                    UpperBoundCorrectionReason = "N/A"

                    # get the kpi metric name and value
                    kpi_metric_name = model_json_def["kpi_metric"]
                    kpi_metric_value = item[model_json_def["kpi_metric"]]
                    logging.debug(
                        f'kpi_metric_name="{kpi_metric_name}", kpi_metric_value="{kpi_metric_value}"'
                    )

                    # calculate the perc_min_lowerbound_deviation value
                    perc_min_lowerbound_deviation_value = (
                        float(kpi_metric_value)
                        * int(perc_min_lowerbound_deviation)
                        / 100
                    )
                    logging.debug(
                        f"kpi_metric_value={kpi_metric_value}, perc_min_lowerbound_deviation={perc_min_lowerbound_deviation}, perc_min_lowerbound_deviation_value={perc_min_lowerbound_deviation_value}"
                    )

                    # calculate the perc_min_upperbound_deviation value
                    perc_min_upperbound_deviation_value = (
                        float(kpi_metric_value)
                        * int(perc_min_upperbound_deviation)
                        / 100
                    )
                    logging.debug(
                        f"kpi_metric_value={kpi_metric_value}, perc_min_upperbound_deviation={perc_min_upperbound_deviation}, perc_min_upperbound_deviation_value={perc_min_upperbound_deviation_value}"
                    )

                    # calculate the corrected candidates
                    LowerBoundMin = float(kpi_metric_value) - float(
                        perc_min_lowerbound_deviation_value
                    )
                    UpperBoundMin = float(kpi_metric_value) + float(
                        perc_min_upperbound_deviation_value
                    )
                    logging.debug(
                        f'LowerBoundMin="{LowerBoundMin}", UpperBoundMin="{UpperBoundMin}"'
                    )

                    # try to get the LowerBound and UpperBound, if we have no results (not enough historical data), apply corrected values instead
                    try:
                        LowerBound = item["LowerBound"]
                    except Exception as e:
                        LowerBoundWasCorrected = 1
                        LowerBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                        LowerBound = LowerBoundMin
                        logging.warning(
                            f'Could not retrieve a LowerBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{LowerBound}" instead'
                        )

                    try:
                        UpperBound = item["UpperBound"]
                    except Exception as e:
                        UpperBoundWasCorrected = 1
                        UpperBoundCorrectionReason = "No value was generated, likely due to lack of historical data"
                        UpperBound = UpperBoundMin
                        logging.warning(
                            f'Could not retrieve a UpperBound value from item="{item}", likely we have not enough historical data yet, applying corrected value="{UpperBound}" instead'
                        )

                    # apply
                    if auto_correct:
                        # condition for a lower outlier: generated lower threshold is greater than the kpi value
                        # condition for an upper outlier: generated upper threshold is lower than the kpi value

                        currentLowerBoundDeviationValue = float(LowerBound) - float(
                            kpi_metric_value
                        )

                        logging.debug(
                            f"currentLowerBoundDeviationValue={currentLowerBoundDeviationValue}"
                        )

                        currentUpperBoundDeviationValue = float(
                            kpi_metric_value
                        ) - float(UpperBound)

                        logging.debug(
                            f"currentUpperBoundDeviationValue={currentUpperBoundDeviationValue}"
                        )

                        # for lowerBound, replace as well if equal or lower than 0 unless requested to allow this behavior
                        if (
                            float(LowerBound) <= 0
                            and not self.lowerbound_negative == "True"
                        ):
                            LowerBoundWasCorrected = 1
                            LowerBoundCorrectionReason = f"Generated LowerBound {float(LowerBound)} is negative or equal to 0"
                            LowerBoundOrig = LowerBound
                            LowerBound = float(LowerBoundMin)

                        # for upperBound, replace as well if equal or lower than 0
                        if float(UpperBound) <= 0:
                            UpperBoundWasCorrected = 1
                            UpperBoundCorrectionReason = f"Generated UpperBound {float(UpperBound)} is negative or equal to 0"
                            UpperBoundOrig = UpperBound
                            UpperBound = float(UpperBoundMin)

                        #
                        # lower
                        #

                        # if a lower outlier is said to be detected
                        if float(LowerBound) > float(kpi_metric_value):
                            # the generated lower bound should be not lower than the safety margin
                            if not float(currentLowerBoundDeviationValue) > float(
                                perc_min_lowerbound_deviation_value
                            ):
                                # apply safeties instead of generated
                                LowerBoundWasCorrected = 1
                                LowerBoundCorrectionReason = f"Current LowerBound deviation value {round(currentLowerBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_lowerbound_deviation_value} using {perc_min_lowerbound_deviation} pct deviation"
                                LowerBoundOrig = LowerBound
                                LowerBound = float(LowerBoundMin)

                            else:
                                # else accept the outlier
                                LowerBoundOrig = LowerBound

                        else:
                            LowerBoundOrig = LowerBound

                        #
                        # upper
                        #

                        # If an upper outlier is said to be detected
                        if float(UpperBound) < float(kpi_metric_value):
                            # the generated upper bound should be higher than the safety margin
                            if not float(currentUpperBoundDeviationValue) > float(
                                perc_min_upperbound_deviation_value
                            ):
                                # apply safeties instead of generated
                                UpperBoundWasCorrected = 1
                                UpperBoundCorrectionReason = f"Current UpperBound deviation value {round(currentUpperBoundDeviationValue, 3)} is not higher than minimal deviation value {perc_min_upperbound_deviation_value} using {perc_min_upperbound_deviation} pct deviation"
                                UpperBoundOrig = UpperBound
                                UpperBound = float(UpperBoundMin)

                            # else accept the outlier
                            else:
                                UpperBoundOrig = UpperBound

                        else:
                            UpperBoundOrig = UpperBound

                        # lower bound and upper bound cannot be equal
                        if float(LowerBound) == float(UpperBound):
                            # apply safeties instead of generated
                            LowerBoundWasCorrected = 1
                            LowerBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                            LowerBoundOrig = LowerBound
                            LowerBound = float(LowerBoundMin)

                            # apply safeties instead of generated
                            UpperBoundWasCorrected = 1
                            UpperBoundCorrectionReason = f"LowerBound value {LowerBoundOrig} and UpperBound value {UpperBoundOrig} cannot be equal"
                            UpperBoundOrig = UpperBound
                            UpperBound = float(UpperBoundMin)

                    # do not correct anything
                    else:
                        LowerBoundOrig = LowerBound
                        UpperBoundOrig = UpperBound

                    # handle min_value_for_lowerbound_breached / min_value_for_upperbound_breached
                    rejectedLowerboundOutlier = 0
                    rejectedUpperboundOutlier = 0
                    rejectedLowerboundOutlierReason = "N/A"
                    rejectedUpperboundOutlierReason = "N/A"

                    if float(kpi_metric_value) < float(
                        min_value_for_lowerbound_breached
                    ):
                        rejectedLowerboundOutlier = 1
                        rejectedLowerboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"
                    else:
                        rejectedLowerboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_lowerbound_breached {min_value_for_lowerbound_breached}"

                    if float(kpi_metric_value) < float(
                        min_value_for_upperbound_breached
                    ):
                        rejectedUpperboundOutlier = 1
                        rejectedUpperboundOutlierReason = f"Outlier if any will be rejected, KPI value {kpi_metric_value} is lower than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"
                    else:
                        rejectedUpperboundOutlierReason = f"Outlier if any will be accepted, KPI value {kpi_metric_value} is higher than min_value_for_upperbound_breached {min_value_for_upperbound_breached}"

                    # finally, create isLowerBoundOutlier / isUpperBoundOutlier (0/1)
                    if (
                        float(kpi_metric_value) < float(LowerBound)
                        and rejectedLowerboundOutlier == 0
                    ):
                        isLowerBoundOutlier = 1
                        pct_decrease = (
                            (float(LowerBound) - float(kpi_metric_value))
                            / float(LowerBound)
                        ) * 100
                        isLowerBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", LowerBound="{round(float(LowerBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{item["_time"]}", pct_decrease="{round(float(pct_decrease), 2)}"'

                    else:
                        isLowerBoundOutlier = 0
                        isLowerBoundOutlierReason = "N/A"

                    if (
                        float(kpi_metric_value) > float(UpperBound)
                        and rejectedUpperboundOutlier == 0
                    ):
                        isUpperBoundOutlier = 1
                        pct_increase = (
                            (float(kpi_metric_value) - float(UpperBound))
                            / float(UpperBound)
                        ) * 100
                        isUpperBoundOutlierReason = f'Outliers ML for kpi="{kpi_metric_name}", UpperBound="{round(float(UpperBound), 3)}" breached with kpi_metric_value="{round(float(kpi_metric_value), 3)}" at time="{item["_time"]}", pct_increase="{round(float(pct_increase), 2)}"'

                    else:
                        isUpperBoundOutlier = 0
                        isUpperBoundOutlierReason = "N/A"

                    # Add to the dict
                    yield_record["_time"] = item["_time"]
                    yield_record["LowerBound"] = LowerBound
                    yield_record["UpperBound"] = UpperBound
                    yield_record["isLowerBoundOutlier"] = isLowerBoundOutlier
                    yield_record["isLowerBoundOutlierReason"] = (
                        isLowerBoundOutlierReason
                    )
                    yield_record["isUpperBoundOutlier"] = isUpperBoundOutlier
                    yield_record["isUpperBoundOutlierReason"] = (
                        isLowerBoundOutlierReason
                    )
                    yield_record["isOutlier"] = 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                    yield_record[kpi_metric_name] = kpi_metric_value
                    yield_record["kpi_metric_name"] = kpi_metric_name
                    yield_record["kpi_metric_value"] = kpi_metric_value
                    yield_record["LowerBoundMin"] = LowerBoundMin
                    yield_record["LowerBoundOrig"] = LowerBoundOrig
                    yield_record["LowerBoundWasCorrected"] = LowerBoundWasCorrected
                    yield_record["LowerBoundCorrectionReason"] = (
                        LowerBoundCorrectionReason
                    )
                    yield_record["UpperBoundMin"] = UpperBoundMin
                    yield_record["UpperBoundOrig"] = UpperBoundOrig
                    yield_record["UpperBoundWasCorrected"] = UpperBoundWasCorrected
                    yield_record["UpperBoundCorrectionReason"] = (
                        UpperBoundCorrectionReason
                    )
                    yield_record["min_value_for_lowerbound_breached"] = (
                        min_value_for_lowerbound_breached
                    )
                    yield_record["min_value_for_upperbound_breached"] = (
                        min_value_for_upperbound_breached
                    )
                    yield_record["rejectedLowerboundOutlier"] = (
                        rejectedLowerboundOutlier
                    )
                    yield_record["rejectedUpperboundOutlier"] = (
                        rejectedUpperboundOutlier
                    )
                    yield_record["rejectedLowerboundOutlierReason"] = (
                        rejectedLowerboundOutlierReason
                    )
                    yield_record["rejectedUpperboundOutlierReason"] = (
                        rejectedUpperboundOutlierReason
                    )

                    # Add _raw
                    yield_record["_raw"] = {
                        "_time": item["_time"],
                        "kpi_metric_name": kpi_metric_name,
                        "kpi_metric_value": kpi_metric_value,
                        "LowerBoundMin": LowerBoundMin,
                        "LowerBoundOrig": LowerBoundOrig,
                        "LowerBound": LowerBound,
                        "UpperBoundMin": UpperBoundMin,
                        "UpperBoundOrig": UpperBoundOrig,
                        "UpperBound": UpperBound,
                        "isLowerBoundOutlier": isLowerBoundOutlier,
                        "isLowerBoundOutlierReason": isLowerBoundOutlierReason,
                        "isUpperBoundOutlier": isUpperBoundOutlier,
                        "isUpperBoundOutlierReason": isUpperBoundOutlierReason,
                        "isOutlier": 1 if (isLowerBoundOutlier or isUpperBoundOutlier) else 0,
                        "perc_min_lowerbound_deviation": perc_min_lowerbound_deviation,
                        "perc_min_upperbound_deviation": perc_min_upperbound_deviation,
                        "LowerBoundWasCorrected": LowerBoundWasCorrected,
                        "LowerBoundCorrectionReason": LowerBoundCorrectionReason,
                        "UpperBoundWasCorrected": UpperBoundWasCorrected,
                        "UpperBoundCorrectionReason": UpperBoundCorrectionReason,
                        "min_value_for_lowerbound_breached": min_value_for_lowerbound_breached,
                        "min_value_for_upperbound_breached": min_value_for_upperbound_breached,
                        "rejectedLowerboundOutlier": rejectedLowerboundOutlier,
                        "rejectedUpperboundOutlier": rejectedUpperboundOutlier,
                        "rejectedLowerboundOutlierReason": rejectedLowerboundOutlierReason,
                        "rejectedUpperboundOutlierReason": rejectedUpperboundOutlierReason,
                        "item": item,
                    }

                # yield
                yield yield_record

            # log
            logging.info(
                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, simulation search was terminated successfully, duration={time.time() - start}, search="{ml_model_render_search}"'
            )


dispatch(SplkOutliersRender, sys.argv, sys.stdin, sys.stdout, __name__)
