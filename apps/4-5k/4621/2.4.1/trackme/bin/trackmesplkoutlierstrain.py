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
    "%s/var/log/splunk/trackme_splk_outliers_train.log" % splunkhome,
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

# import trackme libs
from trackme_libs import trackme_reqinfo, run_splunk_search

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces, escape_backslash


@Configuration(distributed=False)
class SplkOutliersTrain(GeneratingCommand):
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
        **Description:** The Machine Learning model ID to be trained, optional and defaults to all models defined for the entity.""",
        require=False,
        validate=validators.Match("object", r"^.*$"),
    )

    mode = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The training mode, live means complete and normal training of model(s), simulation is called by the render in simulation mode.""",
        require=False,
        default="live",
        validate=validators.Match("component", r"^(?:live|simulation)$"),
    )

    model_json_def = Option(
        doc="""
        **Syntax:** **model_json_def=****
        **Description:** If in simulation mode, the JSON definition for the ML model.""",
        require=False,
        default={},
        validate=validators.Match("model_json_def", r"^.*$"),
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

    def update_kvrecord(
        self,
        collection_rule,
        key,
        entities_outliers,
        record_outliers_rules,
        last_exec,
        ml_confidence,
        ml_confidence_reason,
        splk_outliers_min_days_history=None,
    ):
        """
        Update the KV store record with new data.

        :param collection_rule: The KV store collection rule object.
        :param key: The key of the record to update.
        :param entities_outliers: Updated entities outliers data.
        :param record_outliers_rules: The original record from outliers rules.
        :param last_exec: The timestamp of the last execution.
        :param ml_confidence: The machine learning confidence level.
        :param ml_confidence_reason: The reason for the ML confidence level.
        :param splk_outliers_min_days_history: The min days history config value used for this training.
        """
        try:
            collection_rule.data.update(
                str(key),
                json.dumps(
                    {
                        "entities_outliers": json.dumps(entities_outliers, indent=4),
                        "is_disabled": record_outliers_rules.get("is_disabled"),
                        "mtime": record_outliers_rules.get("mtime"),
                        "object": record_outliers_rules.get("object"),
                        "object_category": record_outliers_rules.get("object_category"),
                        "last_exec": last_exec,
                        "confidence": ml_confidence,
                        "confidence_reason": ml_confidence_reason,
                        "splk_outliers_min_days_history": splk_outliers_min_days_history,
                    }
                ),
            )
            return True

        except Exception as e:
            error_msg = f'Failure while trying to update the KV store record, exception="{str(e)}"'
            raise Exception(error_msg)

    def generate(self, **kwargs):
        # track run_time
        global_start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }

        # Get global index conf
        trackme_metric_idx = reqinfo["trackme_conf"]["index_settings"][
            "trackme_metric_idx"
        ]

        # Get the value for splk_outliers_min_days_history
        splk_outliers_min_days_history = reqinfo["trackme_conf"][
            "splk_outliers_detection"
        ]["splk_outliers_min_days_history"]

        # set the tenant_trackme_metric_idx
        tenant_trackme_metric_idx = None

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
                tenant_trackme_metric_idx = trackme_metric_idx
            else:
                try:
                    response_data = json.loads(json.dumps(response.json(), indent=1))
                    tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
                except Exception as e:
                    tenant_trackme_metric_idx = response_data["trackme_metric_idx"]

        except Exception as e:
            tenant_trackme_metric_idx = trackme_metric_idx

        # Component collection
        collection_name = f"kv_trackme_{self.component}_tenant_{str(self.tenant_id)}"
        collection = self.service.kvstore[collection_name]

        # Outliers rules storage collection
        collection_rules_name = (
            f"kv_trackme_{self.component}_outliers_entity_rules_tenant_{self.tenant_id}"
        )
        collection_rule = self.service.kvstore[collection_rules_name]

        # Vtenants storage collection
        vtenants_collection_name = "kv_trackme_virtual_tenants"
        vtenants_collection = self.service.kvstore[vtenants_collection_name]

        #
        # First, get the full vtenant definition
        #

        # Define the KV query search string
        query_string = {
            "tenant_id": self.tenant_id,
        }

        # get
        try:
            vtenant_record = vtenants_collection.data.query(
                query=json.dumps(query_string)
            )
        except Exception as e:
            error_msg = f'tenant_id="{self.tenant_id}", Could not retrieve the virtual tenant definition in the KVstore storage="{vtenants_collection_name}", exception="{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

        #
        # Get the Outliers rules
        #

        # Validate that at least one of object or object_id is provided
        if self.object == "*" and self.object_id == "*":
            error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", At least one of "object" or "object_id" must be provided.'
            logging.error(error_msg)
            raise Exception(error_msg)

        # Define the KV query
        # object_id takes precedence over object when both are provided
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
            object_ref = f'object="{self.object}"' if self.object != "*" else f'object_id="{self.object_id}"'
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
        except Exception as e:
            msg = f'Failed to load entities_outliers with exception="{str(e)}"'

        # log debug
        logging.debug(f'entities_outliers="{entities_outliers}"')

        # Load the general enablement
        try:
            outliers_is_disabled = int(record_outliers_rules.get("is_disabled"))
            logging.debug(f'is_disabled="{outliers_is_disabled}"')

        except Exception as e:
            msg = f'Failed to extract one or more expected settings from the entity, is this record corrupted? Exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        # Only proceed is enabled

        # proceed
        if outliers_is_disabled == 1:
            yield {
                "_time": time.time(),
                "_raw": "Outliers detection are disabled at the global level for this entity, nothing to do.",
                "response": "Outliers detection are disabled at the global level for this entity, nothing to do.",
            }

        elif outliers_is_disabled == 0:
            #
            # Establish confidence level
            #

            # Establish low as the basis level
            ml_confidence = "low"
            ml_confidence_reason = (
                "ML has insufficient historical metrics to proceed (pending)"
            )
            ml_metrics_duration = "unknown"

            # set kwargs
            kwargs_confidence = {
                "earliest_time": "-90d",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # define the gen search
            metric_root = None
            if self.component in ("dsm", "dhm"):
                metric_root = f"trackme.splk.feeds"
            else:
                metric_root = f"trackme.splk.{self.component}"

            ml_confidence_search = remove_leading_spaces(
                f"""\
                | mstats latest({metric_root}.*) as * where index={tenant_trackme_metric_idx} tenant_id="{self.tenant_id}" object_category="splk-{self.component}" object="{escape_backslash(self.object)}" by object span=1d
                | stats min(_time) as first_time by object
                | eval metrics_duration=now()-first_time
                | eval confidence=if(metrics_duration<({splk_outliers_min_days_history}*86400), "low", "normal")
                | eval metrics_duration=tostring(metrics_duration, "duration")
                | head 1
                """
            )
            logging.info(
                f"tenant_id={self.tenant_id}, component={self.component}, {self._get_log_object_ref()}, ML confidence inspection"
            )

            # run search

            # track the search runtime
            start = time.time()

            # proceed
            try:
                reader = run_splunk_search(
                    self.service,
                    ml_confidence_search,
                    kwargs_confidence,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        # log
                        logging.info(
                            f'tenant_id={self.tenant_id}, {self._get_log_object_ref()}, ML confidence inspection, ml_confidence={item.get("confidence")}, metrics_duration={item.get("metrics_duration")}, ml_confidence_search={ml_confidence_search}'
                        )
                        ml_confidence = item.get("confidence", "low")
                        ml_metrics_duration = item.get("metrics_duration", "unknown")

            except Exception as e:
                msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, Machine Learning model training search failed with exception="{str(e)}", run_time="{str(time.time() - start)}"'
                logging.error(msg)
                raise Exception(msg)

            # set the ml_confidence_reason
            if ml_confidence == "low":
                ml_confidence_reason = f"ML has insufficient historical metrics to proceed (metrics_duration={ml_metrics_duration}, required={splk_outliers_min_days_history}days)"
            elif ml_confidence == "normal":
                ml_confidence_reason = f"ML has sufficient historical metrics to proceed (metrics_duration={ml_metrics_duration}, required={splk_outliers_min_days_history}days)"

            #
            # ML model evaluation
            #

            # use a counter to condition final actions
            process_counter = 0

            # set a list for error reporting purposes of available modesl
            entity_outliers_models = []

            # Loop through outliers entities
            for entity_outlier in entities_outliers:
                # Add to the list
                entity_outliers_models.append(entity_outlier)

                # Extract as a dict
                entity_outlier_dict = entities_outliers[entity_outlier]
                logging.debug(f'entity_outlier_dict="{entity_outlier_dict}"')

                # Define if entity is enabled
                process_entity = False

                try:
                    is_disabed = int(entity_outlier_dict["is_disabled"])
                    if is_disabed == 0:
                        process_entity = True
                    else:
                        process_entity = False

                except Exception as e:
                    msg = f'tenant_id="{self.tenant_id}", component="{self.component}", object="{entity_outlier}", Failed to extract the entity enablement status, is this record corrupted? Exception="{str(e)}"'
                    logging.error(msg)
                    raise Exception(msg)

                # Extract the outliers entity settings
                if process_entity:
                    # Process all outliers entities, unless filtering is set at the custom command level
                    process_entity_outliers = False

                    # decide
                    if self.model_id:
                        if self.model_id == entity_outlier:
                            process_entity_outliers = True
                        else:
                            process_entity_outliers = False
                    else:
                        process_entity_outliers = True

                    # log debug
                    logging.debug(
                        f'process_entity_outliers="{process_entity_outliers}"'
                    )

                    # if process
                    if process_entity_outliers:
                        # increment counter
                        process_counter += 1

                        # Attempt to update the ml lookup permissions
                        rest_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_outliers_engine/write/outliers_train_entity_model"

                        post_data = {
                            "tenant_id": self.tenant_id,
                            "component": self.component,
                            "mode": self.mode,
                            "entity_outlier": entity_outlier,
                            "entity_outlier_dict": entity_outlier_dict,
                            "model_json_def": self.model_json_def,
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
                                logging.error(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, failure to process ML model training, url="{rest_url}", data="{json.dumps(post_data, indent=0)}", response.status_code="{response.status_code}", response.text="{response.text}"'
                                )
                            else:
                                logging.info(
                                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, action="success", url="{rest_url}", ML model training processed successfully, response.status_code="{response.status_code}", response="{json.dumps(response.json(), indent=2)}"'
                                )
                                response_json = response.json()

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, ML model training failed to process with exception: "{str(e)}"'
                            )

                        logging.debug(
                            f'response_json="{json.dumps(response_json, indent=2)}"'
                        )

                        # Update the main dict
                        entities_outliers = response_json.get("entities_outliers")
                        entity_outlier = response_json.get("entity_outlier")
                        entity_outlier_dict = entities_outliers.get(entity_outlier)

                        last_exec = time.time()
                        final_dict = {
                            "_key": key,
                            "entities_outliers": entities_outliers,
                            "is_disabled": record_outliers_rules.get("is_disabled"),
                            "mtime": record_outliers_rules.get("mtime"),
                            "object": record_outliers_rules.get("object"),
                            "object_category": record_outliers_rules.get(
                                "object_category"
                            ),
                            "last_exec": last_exec,
                        }

                        # Update the KVrecord
                        try:
                            self.update_kvrecord(
                                collection_rule,
                                key,
                                entities_outliers,
                                record_outliers_rules,
                                last_exec,
                                ml_confidence,
                                ml_confidence_reason,
                                splk_outliers_min_days_history,
                            )
                        except Exception as e:
                            logging.error(str(e))

            if process_counter > 0:

                final_dict = {
                    "_key": key,
                    "entities_outliers": entities_outliers,
                    "is_disabled": record_outliers_rules.get("is_disabled"),
                    "mtime": time.time(),
                    "object": record_outliers_rules.get("object"),
                    "object_category": record_outliers_rules.get("object_category"),
                    "last_exec": time.time(),
                }

                # Update the component KVrecord
                try:
                    kvrecord = collection.data.query(
                        query=json.dumps(
                            {"object": record_outliers_rules.get("object")}
                        )
                    )[0]
                    kvrecordkey = kvrecord.get("_key")

                except Exception as e:
                    logging.error(
                        f'Could not retrieve the component KVstore record with key="{record_outliers_rules.get("object")}", this installation seems to be corrupted!'
                    )
                    kvrecordkey = None

                # proceed
                if kvrecordkey:
                    kvrecord["outliers_readiness"] = "True"
                    try:
                        collection.data.update(str(kvrecordkey), json.dumps(kvrecord))
                        logging.debug(
                            f'outliers_readiness status was updated successfully for object="{record_outliers_rules.get("object")}"'
                        )
                    except Exception as e:
                        logging.error(
                            f'Failed to update the component Kvstore record with key="{record_outliers_rules.get("object")}", exception="{str(e)}"'
                        )

                # yield
                yield {"_time": time.time(), "_raw": final_dict}

                # log final
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, Machine Learning model training search terminated, run_time="{round(time.time() - global_start, 3)}"'
                )

            else:
                if self.model_id:
                    error_msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, The model_id="{self.model_id}" was not found for this object, available models="{json.dumps(entity_outliers_models)}"'
                    logging.error(error_msg)
                    raise Exception(error_msg)
                else:
                    msg = f'tenant_id="{self.tenant_id}", component="{self.component}", {self._get_log_object_ref()}, there are no models yet to be trained for this object.'
                    logging.info(msg)
                    yield {
                        "_time": time.time(),
                        "_raw": {
                            "response": "There are no models to be trained for this object yet."
                        },
                        "tenant_id": self.tenant_id,
                        "component": self.component,
                        "object": self.object,
                    }


dispatch(SplkOutliersTrain, sys.argv, sys.stdin, sys.stdout, __name__)
