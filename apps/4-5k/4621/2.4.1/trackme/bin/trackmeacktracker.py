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

# Built-in libraries
import json
import logging
import os
import sys
import time

# Third-party libraries
import urllib3

# Logging handlers
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_ack_tracker.log" % splunkhome,
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

# import trackme libs
from trackme_libs import (
    trackme_audit_event,
    trackme_reqinfo,
    run_splunk_search,
)
from trackme_libs_utils import normalize_anomaly_reason


@Configuration(distributed=False)
class TrackMeAckTracker(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Optional, the tenant identifier""",
        require=False,
        default=None,
    )

    action = Option(
        doc="""
        **Syntax:** **action=****
        **Description:** Optional, the action to be performed, valid options are: ack_expired | force_expire_all_ack""",
        require=False,
        default="ack_expired",
        validate=validators.Match("action", r"^(ack_expired|force_expire_all_ack)$"),
    )

    # Ensure that the elements in the lists are hashable
    def ensure_hashable(self, items):
        hashable_items = []
        for item in items:
            if isinstance(item, list):
                hashable_items.append(tuple(item))  # Convert inner lists to tuples
            else:
                hashable_items.append(item)
        return hashable_items

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # retrieve options

        trackme_ack_remove_on_reason_change = bool(
            int(
                reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_ack_remove_on_reason_change"
                ]
            )
        )

        logging.debug(
            f'trackme_ack_remove_on_reason_change="{trackme_ack_remove_on_reason_change}"'
        )

        trackme_ack_remove_on_reason_change_min_time_sec = int(
            reqinfo["trackme_conf"]["trackme_general"][
                "trackme_ack_remove_on_reason_change_min_time_sec"
            ]
        )

        logging.debug(
            f'trackme_ack_remove_on_reason_change_min_time_sec="{trackme_ack_remove_on_reason_change_min_time_sec}"'
        )

        trackme_ack_remove_on_reason_change_auto_ack_only = bool(
            int(
                reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_ack_remove_on_reason_change_auto_ack_only"
                ]
            )
        )

        logging.debug(
            f'trackme_ack_remove_on_reason_change_auto_ack_only="{trackme_ack_remove_on_reason_change_auto_ack_only}"'
        )

        trackme_ack_remove_when_green = bool(
            int(
                reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_ack_remove_when_green"
                ]
            )
        )

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # get current user
        username = self._metadata.searchinfo.username

        # get user info
        users = self.service.users

        # Get roles for the current user
        username_roles = []
        for user in users:
            if user.name == username:
                username_roles = user.roles
        logging.info(f'username="{username}", roles="{username_roles}"')

        # Data collection
        collection_name = "kv_trackme_virtual_tenants"
        collection = self.service.kvstore[collection_name]

        # Define the KV query search string
        query_string = {"tenant_status": "enabled"}

        if self.tenant_id and self.tenant_id != "*":
            query_string = {
                "$and": [
                    {
                        "tenant_id": self.tenant_id,
                        "tenant_status": "enabled",
                    }
                ]
            }

        # A dict to store the list of components enabled for each tenant_id
        components_enabled_for_tenant = {}

        # Define non-alerting reasons that should be excluded from comparison
        non_alerting_reasons = {"future_over_tolerance"}

        # log and yield
        msg = "Starting Ack expiration maintenance job"
        logging.info(msg)
        yield {"_time": str(time.time()), "_raw": {"event": msg}}

        # Get the records
        enabled_tenants = []
        try:
            records = collection.data.query(query=json.dumps(query_string))

            # Loop through the records
            for record in records:
                enabled_tenants.append(record["tenant_id"])

                # Add to our dict
                components_enabled_for_tenant[record["tenant_id"]] = {
                    "splk-dsm": int(record.get("tenant_dsm_enabled", 0)),
                    "splk-dhm": int(record.get("tenant_dhm_enabled", 0)),
                    "splk-mhm": int(record.get("tenant_mhm_enabled", 0)),
                    "splk-flx": int(record.get("tenant_flx_enabled", 0)),
                    "splk-fqm": int(record.get("tenant_fqm_enabled", 0)),
                    "splk-wlk": int(record.get("tenant_wlk_enabled", 0)),
                }

            # For each enabled tenant, access the Ack KVstore, loop through the records, verify the Ack expiration and update as needed
            for tenant_id in enabled_tenants:

                # log and yield
                msg = f'Starting Ack expiration maintenance job for tenant_id="{tenant_id}"'
                logging.info(msg)
                yield {
                    "_time": str(time.time()),
                    "_raw": {"tenant_id": tenant_id, "event": msg},
                }

                # Component mapping
                component_mapping = {
                    "splk-dsm": "dsm",
                    "splk-dhm": "dhm",
                    "splk-mhm": "mhm",
                    "splk-flx": "flx",
                    "splk-fqm": "fqm",
                    "splk-wlk": "wlk",
                }

                # Ack collection
                ack_collection_name = f"kv_trackme_common_alerts_ack_tenant_{tenant_id}"
                ack_collection = self.service.kvstore[ack_collection_name]

                # Define the query
                search = f'| inputlookup trackme_common_alerts_ack_tenant_{tenant_id} where ack_state="active"'

                kwargs_oneshot = {
                    "earliest_time": "-5m",
                    "latest_time": "now",
                    "output_mode": "json",
                    "count": 0,
                }

                # Log a summary of operation
                response_summary = []

                # ack_count
                ack_count = 0

                # run search
                try:
                    reader = run_splunk_search(
                        self.service,
                        search,
                        kwargs_oneshot,
                        24,
                        5,
                    )

                    for ack_record in reader:
                        if isinstance(ack_record, dict):

                            # counter
                            ack_count += 1

                            # debug logging
                            logging.debug(
                                f'tenant_id="{tenant_id}", ack_record="{json.dumps(ack_record, indent=1)}"'
                            )

                            # ack_mtime
                            ack_mtime = float(ack_record["ack_mtime"])
                            logging.debug(
                                f'tenant_id="{tenant_id}", ack_mtime="{ack_mtime}"'
                            )

                            # calculate the time in seconds spent since the ack_mtime
                            time_spent_since_ack_creation = round(
                                float(time.time() - ack_mtime), 3
                            )
                            logging.debug(
                                f'tenant_id="{tenant_id}", time_spent_since_ack_creation="{time_spent_since_ack_creation}"'
                            )

                            # record key
                            key = ack_record["_key"]

                            # retrieve the ack_expiration value
                            ack_expiration = float(ack_record["ack_expiration"])
                            logging.debug(
                                f'tenant_id="{tenant_id}", key="{key}", ack_expiration="{ack_expiration}", ack_record="{json.dumps(ack_record, indent=1)}"'
                            )

                            #
                            # component category
                            #

                            object_category = ack_record.get("object_category", None)

                            # from the components_enabled_for_tenant dict, get the component_enabled value
                            component_enabled = components_enabled_for_tenant[
                                tenant_id
                            ].get(object_category, 0)

                            record_is_valid = True

                            if not object_category:
                                record_is_valid = False
                                logging.error(
                                    f'object_category is missing in the ack_record="{ack_record}", this record is corrupted and will be immediately purged from the Ack collection'
                                )

                            elif object_category not in component_mapping:
                                record_is_valid = False
                                logging.error(
                                    f'object_category="{object_category}" is not a valid component category, this record is corrupted and will be immediately purged from the Ack collection'
                                )

                            # elif the component is not enabled, the record is invalid
                            elif object_category and component_enabled == 0:
                                record_is_valid = False
                                logging.warning(
                                    f'component="{object_category}" is not enabled for the tenant_id="{tenant_id}", this record is related to a disabled component and will be immediately purged from the Ack collection'
                                )

                            if not record_is_valid:

                                # Remove the record
                                try:
                                    ack_collection.data.delete(
                                        json.dumps({"_key": key})
                                    )
                                    msg = f'Ack record with key="{key}" is corrupted and has been purged from the Ack collection'
                                    logging.info(msg)
                                    yield {
                                        "_time": str(time.time()),
                                        "_raw": {
                                            "tenant_id": tenant_id,
                                            "event": msg,
                                        },
                                    }

                                    # add to response summary
                                    response_summary.append(
                                        {
                                            "object": ack_record["object"],
                                            "object_category": "corrupted",
                                            "action_description": "Corrupted record has been purged",
                                            "ack_attributes": ack_record,
                                        }
                                    )

                                except Exception as e:
                                    msg = f'Failed to purge the corrupted Ack record with key="{key}" with exception="{str(e)}"'
                                    logging.error(msg)
                                    yield {
                                        "_time": str(time.time()),
                                        "_raw": {
                                            "tenant_id": tenant_id,
                                            "event": msg,
                                        },
                                    }

                                    # add to response summary
                                    response_summary.append(
                                        {
                                            "object": ack_record["object"],
                                            "object_category": "corrupted",
                                            "action_description": f"Failed to purge corrupted record with exception={str(e)}",
                                            "ack_attributes": ack_record,
                                        }
                                    )

                            else:

                                try:
                                    # get target data collection
                                    component = component_mapping.get(
                                        object_category, None
                                    )
                                    component_collection_name = (
                                        f"kv_trackme_{component}_tenant_{tenant_id}"
                                    )
                                    component_collection = self.service.kvstore[
                                        component_collection_name
                                    ]

                                    # Define the KV query
                                    query_string = {
                                        "object": ack_record["object"],
                                    }

                                    entity_kvrecord = component_collection.data.query(
                                        query=json.dumps(query_string)
                                    )[0]
                                    entity_key = entity_kvrecord.get("_key")
                                    object_state = entity_kvrecord.get("object_state")
                                    anomaly_reason = entity_kvrecord.get(
                                        "anomaly_reason"
                                    )
                                except Exception as e:
                                    entity_key = None
                                    object_state = None
                                    anomaly_reason = None

                                # get ack_anomaly_reason
                                ack_anomaly_reason = ack_record.get(
                                    "anomaly_reason", None
                                )

                                # check both anomaly_reason and ack_anomaly_reason
                                anomaly_reason = normalize_anomaly_reason(
                                    anomaly_reason
                                )
                                ack_anomaly_reason = normalize_anomaly_reason(
                                    ack_anomaly_reason
                                )

                                # logging for anomaly_reason normalization
                                logging.info(
                                    f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", normalized_anomaly_reason="{anomaly_reason}", normalized_ack_anomaly_reason="{ack_anomaly_reason}"'
                                )

                                entity_has_returned_to_green = False
                                if entity_key:
                                    if not object_state:
                                        logging.info(
                                            f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", no object state information could be retrieved, this can be expected under specific circumstances'
                                        )
                                        entity_has_returned_to_green = False
                                    else:
                                        logging.debug(
                                            f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", object_state="{object_state}"'
                                        )
                                        if object_state == "green":
                                            entity_has_returned_to_green = True
                                            logging.info(
                                                f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", object_state="{object_state}", entity_has_returned_to_green="{entity_has_returned_to_green}"'
                                            )
                                        else:
                                            entity_has_returned_to_green = False
                                else:
                                    entity_has_returned_to_green = False

                                # current time
                                current_epoch = float(time.time())

                                # get the ack_type
                                try:
                                    ack_type = ack_record.get("ack_type")
                                except Exception as e:
                                    ack_type = "unsticky"
                                logging.debug(
                                    f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", object_state="{object_state}", ack_type="{ack_type}"'
                                )

                                # anomaly_reason_has_changed
                                anomaly_reason_has_changed = False

                                if ack_anomaly_reason and anomaly_reason:

                                    # ensure hashable
                                    anomaly_reason = self.ensure_hashable(
                                        anomaly_reason
                                    )
                                    ack_anomaly_reason = self.ensure_hashable(
                                        ack_anomaly_reason
                                    )

                                    # Only proceed if anomaly_reason isn't exactly ['none']
                                    if anomaly_reason != ["none"]:

                                        if (
                                            ack_anomaly_reason != "N/A"
                                            and anomaly_reason != "N/A"
                                        ):

                                            # Filter out non-alerting reasons from both
                                            filtered_anomaly_reason = (
                                                set(anomaly_reason)
                                                - non_alerting_reasons
                                            )
                                            filtered_ack_anomaly_reason = (
                                                set(ack_anomaly_reason)
                                                - non_alerting_reasons
                                            )

                                            # Don't consider it a change if the new reason is empty and the ack is sticky
                                            if (
                                                filtered_ack_anomaly_reason
                                                != filtered_anomaly_reason
                                                and not (
                                                    not filtered_anomaly_reason
                                                    and ack_type == "sticky"
                                                )
                                            ):
                                                anomaly_reason_has_changed = True
                                                logging.info(
                                                    f'tenant_id="{tenant_id}", object_category="{object_category}", object="{ack_record["object"]}", anomaly_reason_has_changed="{anomaly_reason_has_changed}", ack_anomaly_reason="{ack_anomaly_reason}", anomaly_reason="{anomaly_reason}", ack_type="{ack_type}"'
                                                )

                                # ack_can_be_expired_on_reason_change boolean
                                ack_can_be_expired_on_reason_change = False

                                # if trackme_ack_remove_on_reason_change_auto_ack_only is True, the ack_source must be auto_ack for ack_can_be_expired_on_reason_change to be True
                                # otherwise, ack_can_be_expired_on_reason_change is always True
                                if trackme_ack_remove_on_reason_change_auto_ack_only:
                                    if (
                                        ack_record.get("ack_source", "user_ack")
                                        == "auto_ack"
                                    ):
                                        ack_can_be_expired_on_reason_change = True

                                #
                                # Start main logic
                                #

                                # check for anomaly_reason change
                                if (
                                    anomaly_reason_has_changed
                                    and trackme_ack_remove_on_reason_change
                                    and time_spent_since_ack_creation
                                    > trackme_ack_remove_on_reason_change_min_time_sec
                                    and ack_can_be_expired_on_reason_change
                                ):
                                    msg = f'Ack with key="{str(key)}" is active, but trackme_ack_remove_on_reason_change is enabled and the anomaly_reason has changed, forcing its expiration now, anomaly_reason="{anomaly_reason}", ack_anomaly_reason="{ack_anomaly_reason}", ack_type="{ack_type}", time_spent_since_ack_creation="{time_spent_since_ack_creation}"'
                                    logging.info(msg)
                                    yield {
                                        "_time": str(time.time()),
                                        "_raw": {"tenant_id": tenant_id, "event": msg},
                                    }

                                    try:
                                        ack_collection.data.update(
                                            str(key),
                                            json.dumps(
                                                {
                                                    "object": ack_record["object"],
                                                    "object_category": ack_record[
                                                        "object_category"
                                                    ],
                                                    "ack_state": "inactive",
                                                    "ack_mtime": str(current_epoch),
                                                    "ack_expiration": "N/A",
                                                    "ack_comment": ack_record[
                                                        "ack_comment"
                                                    ],
                                                }
                                            ),
                                        )

                                        # log and yield
                                        msg = f'Ack with key="{key}" for object="{ack_record["object"]}" object_category="{ack_record["object_category"]}" was updated successfully'
                                        logging.info(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                                "record": ack_collection.data.query_by_id(
                                                    key
                                                ),
                                            },
                                        }
                                        # debug only
                                        logging.debug(
                                            f'tenant_id="{tenant_id}", updated_record={ack_collection.data.query_by_id(key)}'
                                        )

                                        # Record an audit change
                                        trackme_audit_event(
                                            session_key,
                                            reqinfo["server_rest_uri"],
                                            tenant_id,
                                            str(username),
                                            "success",
                                            "disable ack",
                                            ack_record["object"],
                                            ack_record["object_category"],
                                            ack_collection.data.query(
                                                query=json.dumps({"_key": key})
                                            )[0],
                                            f'Ack was expired, The anomaly_reason has changed and trackme_ack_remove_on_reason_change is enabled, anomaly_reason={anomaly_reason}, ack_anomaly_reason={ack_anomaly_reason}, ack_type="{ack_type}", time_spent_since_ack_creation="{time_spent_since_ack_creation}"',
                                            "Auto Ack management",
                                        )

                                        # add to response
                                        response_summary.append(
                                            {
                                                "object": ack_record["object"],
                                                "object_category": ack_record[
                                                    "object_category"
                                                ],
                                                "action_description": f'Ack was expired, The anomaly_reason has changed and trackme_ack_remove_on_reason_change is enabled, anomaly_reason={anomaly_reason}, ack_anomaly_reason={ack_anomaly_reason}, ack_type="{ack_type}", time_spent_since_ack_creation="{time_spent_since_ack_creation}"',
                                                "ack_attributes": ack_collection.data.query(
                                                    query=json.dumps({"_key": key})
                                                )[
                                                    0
                                                ],
                                            }
                                        )

                                    except Exception as e:
                                        msg = f'tenant_id="{tenant_id}", Failed to update the ack_record="{json.dumps(ack_record, indent=1)}" with exception="{str(e)}"'
                                        logging.error(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                            },
                                        }

                                # check if the entity has returned to green and the ack is sticky
                                elif (
                                    (
                                        trackme_ack_remove_when_green
                                        or ack_type == "sticky"
                                    )
                                    and entity_has_returned_to_green
                                    and self.action == "ack_expired"
                                ):
                                    if (
                                        ack_type == "sticky"
                                        and not current_epoch > ack_expiration
                                    ):
                                        msg = f'Ack with key="{str(key)}" is active in sticky mode, it will not be purged before its expiration'
                                        logging.info(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                            },
                                        }

                                    else:
                                        msg = f'Ack with key="{str(key)}" is active and {"sticky" if ack_type == "sticky" else "unsticky"}, the entity has returned to green{" and the ack has now expired" if ack_type == "sticky" else ", forcing its expiration now"}'
                                        logging.info(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                            },
                                        }

                                        try:
                                            ack_collection.data.update(
                                                str(key),
                                                json.dumps(
                                                    {
                                                        "object": ack_record["object"],
                                                        "object_category": ack_record[
                                                            "object_category"
                                                        ],
                                                        "ack_state": "inactive",
                                                        "ack_mtime": str(current_epoch),
                                                        "ack_expiration": "N/A",
                                                        "ack_comment": ack_record[
                                                            "ack_comment"
                                                        ],
                                                    }
                                                ),
                                            )

                                            # log and yield
                                            msg = f'Ack with key="{key}" for object="{ack_record["object"]}" object_category="{ack_record["object_category"]}" was updated successfully'
                                            logging.info(msg)
                                            yield {
                                                "_time": str(time.time()),
                                                "_raw": {
                                                    "tenant_id": tenant_id,
                                                    "event": msg,
                                                    "record": ack_collection.data.query_by_id(
                                                        key
                                                    ),
                                                },
                                            }
                                            # debug only
                                            logging.debug(
                                                f'tenant_id="{tenant_id}", updated_record={ack_collection.data.query_by_id(key)}'
                                            )

                                            # Record an audit change
                                            trackme_audit_event(
                                                session_key,
                                                reqinfo["server_rest_uri"],
                                                tenant_id,
                                                str(username),
                                                "success",
                                                "disable ack",
                                                ack_record["object"],
                                                ack_record["object_category"],
                                                ack_collection.data.query(
                                                    query=json.dumps({"_key": key})
                                                )[0],
                                                "The entity has returned to green state or the Ack has expired now.",
                                                "Auto Ack management",
                                            )

                                            # Add to response
                                            response_summary.append(
                                                {
                                                    "object": ack_record["object"],
                                                    "object_category": ack_record[
                                                        "object_category"
                                                    ],
                                                    "action_description": "The entity has returned to green state or the Ack has expired now.",
                                                    "ack_attributes": ack_collection.data.query(
                                                        query=json.dumps({"_key": key})
                                                    )[
                                                        0
                                                    ],
                                                }
                                            )

                                        except Exception as e:
                                            msg = f'tenant_id="{tenant_id}", Failed to update the ack_record="{json.dumps(ack_record, indent=1)}" with exception="{str(e)}"'
                                            logging.error(msg)
                                            yield {
                                                "_time": str(time.time()),
                                                "_raw": {
                                                    "tenant_id": tenant_id,
                                                    "event": msg,
                                                },
                                            }

                                elif self.action == "ack_expired":
                                    # handle expiration
                                    if current_epoch > ack_expiration:
                                        msg = f'Ack with key="{str(key)}" is expired since {str(round(current_epoch - ack_expiration, 2))} seconds, updating the record now'
                                        logging.info(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                            },
                                        }

                                        try:
                                            ack_collection.data.update(
                                                str(key),
                                                json.dumps(
                                                    {
                                                        "object": ack_record["object"],
                                                        "object_category": ack_record[
                                                            "object_category"
                                                        ],
                                                        "ack_state": "inactive",
                                                        "ack_mtime": str(current_epoch),
                                                        "ack_expiration": "N/A",
                                                        "ack_comment": ack_record[
                                                            "ack_comment"
                                                        ],
                                                    }
                                                ),
                                            )

                                            # log and yield
                                            msg = f'Ack with key="{key}" for object="{ack_record["object"]}" object_category="{ack_record["object_category"]}" was updated successfully'
                                            logging.info(msg)
                                            yield {
                                                "_time": str(time.time()),
                                                "_raw": {
                                                    "tenant_id": tenant_id,
                                                    "event": msg,
                                                    "record": ack_collection.data.query_by_id(
                                                        key
                                                    ),
                                                },
                                            }
                                            # debug only
                                            logging.debug(
                                                f'tenant_id="{tenant_id}", updated_record={ack_collection.data.query_by_id(key)}'
                                            )

                                            # Record an audit change
                                            trackme_audit_event(
                                                session_key,
                                                reqinfo["server_rest_uri"],
                                                tenant_id,
                                                str(username),
                                                "success",
                                                "disable ack",
                                                ack_record["object"],
                                                ack_record["object_category"],
                                                ack_collection.data.query(
                                                    query=json.dumps({"_key": key})
                                                )[0],
                                                "The Ack is now expired.",
                                                "Auto Ack management",
                                            )

                                            # add to response
                                            response_summary.append(
                                                {
                                                    "object": ack_record["object"],
                                                    "object_category": ack_record[
                                                        "object_category"
                                                    ],
                                                    "action_description": "The Ack is now expired.",
                                                    "ack_attributes": ack_collection.data.query(
                                                        query=json.dumps({"_key": key})
                                                    )[
                                                        0
                                                    ],
                                                }
                                            )

                                        except Exception as e:
                                            msg = f'tenant_id="{tenant_id}", Failed to update the expired ack_record="{json.dumps(ack_record, indent=1)}" with exception="{str(e)}"'
                                            logging.error(msg)
                                            yield {
                                                "_time": str(time.time()),
                                                "_raw": {
                                                    "tenant_id": tenant_id,
                                                    "event": msg,
                                                },
                                            }

                                elif self.action == "force_expire_all_ack":
                                    msg = f'Ack with key="{str(key)}" is active, forcing its expiration now'
                                    logging.info(msg)
                                    yield {
                                        "_time": str(time.time()),
                                        "_raw": {"tenant_id": tenant_id, "event": msg},
                                    }

                                    try:
                                        ack_collection.data.update(
                                            str(key),
                                            json.dumps(
                                                {
                                                    "object": ack_record["object"],
                                                    "object_category": ack_record[
                                                        "object_category"
                                                    ],
                                                    "ack_state": "inactive",
                                                    "ack_mtime": str(current_epoch),
                                                    "ack_expiration": "N/A",
                                                    "ack_comment": ack_record[
                                                        "ack_comment"
                                                    ],
                                                }
                                            ),
                                        )

                                        # log and yield
                                        msg = f'Ack with key="{key}" for object="{ack_record["object"]}" object_category="{ack_record["object_category"]}" was updated successfully'
                                        logging.info(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                                "record": ack_collection.data.query_by_id(
                                                    key
                                                ),
                                            },
                                        }
                                        # debug only
                                        logging.debug(
                                            f'tenant_id="{tenant_id}", updated_record={ack_collection.data.query_by_id(key)}'
                                        )

                                        # Record an audit change
                                        trackme_audit_event(
                                            session_key,
                                            reqinfo["server_rest_uri"],
                                            tenant_id,
                                            str(username),
                                            "success",
                                            "disable ack",
                                            ack_record["object"],
                                            ack_record["object_category"],
                                            ack_collection.data.query(
                                                query=json.dumps({"_key": key})
                                            )[0],
                                            "Force all Ack expired has been requested.",
                                            "Auto Ack management",
                                        )

                                        # add to response
                                        response_summary.append(
                                            {
                                                "object": ack_record["object"],
                                                "object_category": ack_record[
                                                    "object_category"
                                                ],
                                                "action_description": "Force all Ack expired has been requested.",
                                                "ack_attributes": ack_collection.data.query(
                                                    query=json.dumps({"_key": key})
                                                )[
                                                    0
                                                ],
                                            }
                                        )

                                    except Exception as e:
                                        msg = f'tenant_id="{tenant_id}", Failed to update the ack_record="{json.dumps(ack_record, indent=1)}" with exception="{str(e)}"'
                                        logging.error(msg)
                                        yield {
                                            "_time": str(time.time()),
                                            "_raw": {
                                                "tenant_id": tenant_id,
                                                "event": msg,
                                            },
                                        }

                                else:
                                    # log and yield
                                    msg = f'The Ack record with key="{key}" for object="{ack_record["object"]}" object_category="{ack_record["object_category"]}" will expire in {str(round(ack_expiration - current_epoch, 2))} seconds'
                                    logging.info(msg)
                                    yield {
                                        "_time": str(time.time()),
                                        "_raw": {"tenant_id": tenant_id, "event": msg},
                                    }

                except Exception as e:
                    msg = f'tenant_id="{tenant_id}", Failed to run the Ack maintenance job with exception="{str(e)}"'
                    logging.error(msg)

                # log and yield
                msg = (
                    f'Ending Ack expiration maintenance job for tenant_id="{tenant_id}"'
                )
                logging.info(msg)
                yield {
                    "_time": str(time.time()),
                    "_raw": {
                        "tenant_id": tenant_id,
                        "event": msg,
                        "ack_records_count": ack_count,
                        "no_ack_action": len(response_summary),
                        "response_summary": response_summary,
                    },
                }

            # log and yield
            duration = round(time.time() - start, 3)
            msg = f'Ending Ack expiration maintenance job, job_end=1, duration_sec="{duration}"'
            logging.info(msg)
            yield {
                "_time": str(time.time()),
                "_raw": {"event": msg, "duration_sec": str(duration)},
            }

        except Exception as e:
            # log and yield
            msg = f'failed to run the Ack maintenance job with exception="{str(e)}"'
            logging.error(msg)
            yield {"_time": str(time.time()), "_raw": {"event": msg}}


dispatch(TrackMeAckTracker, sys.argv, sys.stdin, sys.stdout, __name__)
