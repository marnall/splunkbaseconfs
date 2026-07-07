#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = ["Guilhem Marchand"]
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library
import os
import sys
import time
import json
import uuid
import hashlib
import threading
from logging.handlers import RotatingFileHandler

# External libraries
import urllib3

# Networking imports
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    f"{splunkhome}/var/log/splunk/trackme_splkfqm_inactive_inspector.log",
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

# import Splunk libs (after lib appended)
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs (after lib appended)
from trackme_libs import (
    trackme_reqinfo,
    trackme_audit_event,
    trackme_audit_flip,
    trackme_register_tenant_object_summary,
    trackme_register_tenant_component_summary,
    trackme_gen_state,
    trackme_handler_events,
)

# import trackme libs sla
from trackme_libs_sla import trackme_sla_gen_metrics

# Import TrackMe splk-fqm libs
from trackme_libs_splk_fqm import trackme_fqm_gen_metrics


@Configuration(distributed=False)
class SplkFlxInactiveEntitiesInspector(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    register_component = Option(
        doc="""
        **Syntax:** **register_component=****
        **Description:** If the search is invoked by a tracker, register_component can be called to capture and register any execution exception.""",
        require=False,
        default=True,
    )

    report = Option(
        doc="""
        **Syntax:** **report=****
        **Description:** If register_component is set, a value for report is required.""",
        require=False,
        default=None,
        validate=validators.Match("report", r"^.*$"),
    )

    max_days_since_inactivity_before_purge = Option(
        doc="""
        **Syntax:** **max_days_since_inactivity_before_purge=****
        **Description:** value for max_days_since_inactivity_before_purge is required. (0 disabled this feature)""",
        require=False,
        default="30",
        validate=validators.Match(
            "max_days_since_inactivity_before_purge", r"^(\d|\.)*$"
        ),
    )

    """
    convert_seconds_to_duration
    behaviour: converts seconds to duration, duration is a string from as [D+]HH:MM:SS
    The first segment represents the number of days, the second the number of hours, third the number of minutes, and the fourth the number of seconds.
    """

    def convert_seconds_to_duration(self, seconds):

        try:
            original_seconds = int(seconds)
        except ValueError:
            return 0

        # Check if the original seconds were negative
        is_negative = original_seconds < 0
        seconds = abs(original_seconds)

        # Calculate days, hours, minutes, and seconds
        days = seconds // (24 * 3600)
        seconds = seconds % (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        # Format the duration string
        if days > 0:
            duration = f"{days}+{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            duration = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Add "-" if the original seconds were negative
        if is_negative:
            duration = "-" + duration

        return duration

    """
    Function to return a unique uuid which is used to trace performance run_time of each subtask.
    """

    def get_uuid(self):
        return str(uuid.uuid4())

    """
    Queries and processes records from a collection based on specific criteria.

    :param collection: The collection object to query.
    :return: Tuple containing collection records and a dictionary of records.
    """

    def get_collection_records(self, component):

        # data_records
        collection_records = []
        collection_records_objects = set()
        collection_records_keys = set()
        collection_records_dict = {}

        params = {
            "tenant_id": self.tenant_id,
            "component": component,
            "page": 1,
            "size": 0,
        }

        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
            "Content-Type": "application/json",
        }

        # Set url
        url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/component/load_component_data"

        try:
            response = requests.get(
                url,
                headers=header,
                params=params,
                verify=False,
                timeout=600,
            )

            if response.status_code not in (200, 201, 204):
                msg = f'get component has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(msg)

            else:
                response_json = response.json()
                data = response_json.get("data", [])

                # add the data to the data_records
                for record in data:
                    collection_records.append(record)
                    collection_records_objects.add(record.get("object"))
                    collection_records_dict[record.get("_key")] = {
                        "object": record.get("object"),
                        "object_state": record.get("object_state"),
                        "status_message": record.get("status_message", []),
                        "anomaly_reason": record.get("anomaly_reason", []),
                    }
                    collection_records_keys.add(record.get("_key"))

            return (
                collection_records,
                collection_records_objects,
                collection_records_keys,
                collection_records_dict,
            )

        except Exception as e:
            msg = f'get component has failed, exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

    """
    retrieve the tenant metric index
    """

    def get_tenant_metric_idx(self):
        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % self._metadata.searchinfo.session_key,
            "Content-Type": "application/json",
        }

        # get the index conf for this tenant
        url = "%s/services/trackme/v2/vtenants/tenant_idx_settings" % (
            self._metadata.searchinfo.splunkd_uri
        )
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
                error_msg = f'failed to retrieve the tenant metric index, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(error_msg)
                raise Exception(error_msg)
            else:
                response_data = json.loads(json.dumps(response.json(), indent=1))
                tenant_trackme_metric_idx = response_data["trackme_metric_idx"]
        except Exception as e:
            error_msg = (
                f'failed to retrieve the tenant metric index, exception="{str(e)}"'
            )
            logging.error(error_msg)
            raise Exception(error_msg)

        return tenant_trackme_metric_idx

    """
    Purge entities using the trackme API.

    :param keys_list: List of keys to be purged.
    :param system_deletion_period: The system wide auto-deletion period.
    :param instance_id: The instance identifier.
    :param task_name: The task name.
    :param task_instance_id: The task instance identifier.
    :return: None
    """

    def purge_entities(
        self,
        keys_list,
        system_deletion_period,
        instance_id,
        task_name,
        task_instance_id,
    ):

        # turn entities_to_be_deleted_csv list into CSV
        entities_to_be_deleted_csv = ",".join(keys_list)

        # endpoint target
        target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_fqm/write/fqm_delete"

        # header
        header = {
            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                target_url,
                headers=header,
                data=json.dumps(
                    {
                        "tenant_id": self.tenant_id,
                        "keys_list": entities_to_be_deleted_csv,
                        "deletion_type": "temporary",
                        "update_comment": f"auto-deleted by the system, last seen data is beyond the system wide auto-deletion period of {system_deletion_period} days.",
                    }
                ),
                verify=False,
                timeout=600,
            )

            if response.status_code not in (200, 201, 204):
                msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, query has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                logging.error(msg)
                raise Exception(msg)
            else:
                try:
                    success_count = response.json().get("success_count")
                except Exception as e:
                    success_count = 0
                msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, request was successful, success_count="{success_count}"'
                logging.info(msg)
                return True

        except Exception as e:
            msg = f'tenant_id="{self.tenant_id}", instance_id={instance_id}, ctask="{task_name}", task_instance_id={task_instance_id}, request failed with exception="{str(e)}"'
            logging.error(msg)

    """
    Register the component summary.
    """

    def register_component_summary_async(
        self, session_key, splunkd_uri, tenant_id, component
    ):
        try:
            summary_register_response = trackme_register_tenant_component_summary(
                session_key,
                splunkd_uri,
                tenant_id,
                component,
            )
            logging.debug(
                f'function="trackme_register_tenant_component_summary", response="{json.dumps(summary_register_response, indent=2)}"'
            )
        except Exception as e:
            logging.error(
                f'failed to register the component summary with exception="{str(e)}"'
            )

    # main
    def generate(self, **kwargs):

        # start perf duration counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        # set instance_id
        instance_id = self.get_uuid()

        # end of main
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, trackmesplkfqminactiveinspector is starting'
        )

        # get metric index
        metric_index = self.get_tenant_metric_idx()

        # Get configuration and define metadata
        trackme_summary_idx = reqinfo["trackme_conf"]["index_settings"][
            "trackme_summary_idx"
        ]

        # Data collection
        data_collection_name = f"kv_trackme_fqm_tenant_{self.tenant_id}"
        data_collection = self.service.kvstore[data_collection_name]

        # convert the max day in sec (purge)
        max_sec_record_age_before_purge = self.max_days_since_inactivity_before_purge
        if (
            max_sec_record_age_before_purge == "0"
            or max_sec_record_age_before_purge == 0
        ):
            max_sec_record_age_before_purge = 0

        else:
            max_sec_record_age_before_purge = (
                float(self.max_days_since_inactivity_before_purge) * 86400
            )

        # end of get configuration

        #
        # loop through the KVstore records
        #

        # call the function get collection records
        collection_records_get_start = time.time()
        (
            collection_records,
            collection_records_objects,
            collection_records_keys,
            collection_records_dict,
        ) = self.get_collection_records("fqm")

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="fqm", successfully retrieved {len(collection_records_keys)} records in the KVstore collection={data_collection_name}, run_time={round(time.time()-collection_records_get_start, 3)}'
        )

        # records to be processed counter
        count = 0

        # capture exceptions
        errors_count = 0
        errors_list = []

        # entities_to_be_deleted
        entities_to_be_deleted = []
        entities_to_be_deleted_dict = {}

        # counter for the number of actions engaged
        count_actions_engaged = 0

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "manage_inactive_entities"

        # for the handler events
        report_objects_list = []

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # Loop in the results
        for record in collection_records:

            # object
            object_name = record.get("object")
            object_id = record.get("_key")

            # entity_is_inactive record boolean
            entity_is_inactive = False

            # get the age in seconds since the latest execution
            sec_since_last_execution = time.time() - float(
                record.get("tracker_runtime")
            )

            # get status
            record_status = int(record.get("status"))

            # get current_state
            record_current_state = record.get("current_state")

            # attempt to retrieve max_sec_inactive on a per record basic
            max_sec_inactive = record.get("max_sec_inactive", None)
            if not max_sec_inactive:
                max_sec_inactive = 0
                # If max_sec_inactive is 0, skip updating this record
            else:
                max_sec_inactive = float(max_sec_inactive)

            #
            # update inactive entities status
            #

            # A record will be processed only if max_sec_inactive is more than 0
            if max_sec_inactive > 0:
                entity_is_inactive = True

            if entity_is_inactive:

                # if the entity is inactive and already red, generate the status metrics
                if (
                    float(sec_since_last_execution) > max_sec_inactive
                    and record_status == 2
                ):

                    try:
                        trackme_fqm_gen_metrics(
                            time.time(),
                            self.tenant_id,
                            object_name,
                            object_id,
                            metric_index,
                            json.dumps({"status": 2}),
                        )
                    except Exception as e:
                        error_msg = f'Failed to call trackme_fqm_gen_metrics with exception="{str(e)}"'
                        logging.error(error_msg)

                    # add to the report_objects_list if not already present
                    if object_name not in report_objects_list:
                        report_objects_list.append(object_name)

                # if the entity is inactive but does not yet have a status red
                elif (
                    float(sec_since_last_execution) > max_sec_inactive
                    and record_status != 2
                ):
                    count += 1

                    # add to the report_objects_list if not already present
                    if object_name not in report_objects_list:
                        report_objects_list.append(object_name)

                    duration_since_last_execution = self.convert_seconds_to_duration(
                        sec_since_last_execution
                    )

                    # append object_name to the report_objects_list if not already present
                    if object_name not in report_objects_list:
                        report_objects_list.append(object_name)

                    # Update the record
                    record["object_state"] = "red"
                    record["current_state"] = "red"
                    record["status"] = 2
                    record["status_message"] = (
                        f"This entity has been inactive for more than {duration_since_last_execution} (D+HH:MM:SS) and was not actively managed by any tracker, its status was updated automatically by the inactive entities tracker"
                    )
                    record["status_description_short"] = (
                        "entity is red due to inactivity"
                    )
                    record["status_description"] = (
                        f"The entity status is red due to inactivity, it was not actively managed by any tracker for more than {duration_since_last_execution} (D+HH:MM:SS)"
                    )
                    record["anomaly_reason"] = "inactive"
                    flip_previous_state = record.get("latest_flip_state")
                    record["latest_flip_state"] = "red"
                    record["latest_flip_time"] = time.time()

                    try:
                        data_collection.data.update(
                            str(record.get("_key")), json.dumps(record)
                        )
                        logging.info(
                            f'successfully updated record="{json.dumps(record, indent=2)}"'
                        )
                        count_actions_engaged += 1

                        # flip
                        new_latest_flip_state = "red"
                        new_latest_flip_time = time.time()
                        new_flip_time_human = time.strftime(
                            "%d/%m/%Y %H:%M:%S",
                            time.localtime(new_latest_flip_time),
                        )
                        flip_result = f'{new_flip_time_human}, object="{object_name}" has flipped from previous_state="{flip_previous_state}" to state="{new_latest_flip_state}" with anomaly_reason="inactive"'

                        # Generate the flipping state event
                        try:
                            trackme_audit_flip(
                                self._metadata.searchinfo.session_key,
                                reqinfo["server_rest_uri"],
                                tenant_id=self.tenant_id,
                                keyid=object_id,
                                alias=record.get("alias"),
                                object=object_name,
                                object_category="splk-fqm",
                                priority=record.get("priority"),
                                object_state="red",
                                object_previous_state=flip_previous_state,
                                latest_flip_time=new_latest_flip_time,
                                latest_flip_state=new_latest_flip_state,
                                anomaly_reason="inactive",
                                result=flip_result,
                            )
                        except Exception as e:
                            logging.error(
                                f'tenant_id="{self.tenant_id}", object="{object_name}", failed to generate a flipping state event with exception="{str(e)}"'
                            )

                        # Generate the audit event
                        trackme_audit_event(
                            self._metadata.searchinfo.session_key,
                            reqinfo["server_rest_uri"],
                            self.tenant_id,
                            "system",
                            "success",
                            "update status inactive entity",
                            object_name,
                            "splk-fqm",
                            str(json.dumps(record, indent=1)),
                            "Entity was updated successfully",
                            "automated management of inactive entities",
                        )

                        # Generate the summary event
                        record["event_id"] = hashlib.sha256(
                            json.dumps(record).encode()
                        ).hexdigest()
                        try:
                            trackme_gen_state(
                                index=trackme_summary_idx,
                                sourcetype="trackme:state",
                                source=f"current_state_tracking:splk-fqm:{self.tenant_id}",
                                event=record,
                            )
                            logging.debug(
                                f'TrackMe summary event created successfully, record="{json.dumps(record, indent=1)}"'
                            )
                        except Exception as e:
                            logging.error(
                                f'TrackMe summary event creation failure, record="{json.dumps(record, indent=1)}", exception="{str(e)}"'
                            )

                        # Generate SLA metrics
                        sla_record = [
                            {
                                "tenant_id": self.tenant_id,
                                "object_id": object_id,
                                "object": object_name,
                                "alias": record.get("alias"),
                                "object_category": "splk-fqm",
                                "monitored_state": record.get("current_state"),
                                "priority": record.get("priority"),
                                "metrics_event": {"object_state": 2},
                            }
                        ]

                        try:
                            sla_metrics = trackme_sla_gen_metrics(
                                self.tenant_id,
                                metric_index,
                                sla_record,
                            )
                            logging.debug(
                                f'context="sla_gen_metrics", tenant_id="{self.tenant_id}", object="{object_name}, function trackme_sla_gen_metrics was successful'
                            )
                        except Exception as e:
                            logging.error(
                                f'context="sla_gen_metrics", tenant_id="{self.tenant_id}", object="{object_name}, function trackme_sla_gen_metrics failed with exception {str(e)}'
                            )

                        # generate the status metric
                        try:
                            trackme_fqm_gen_metrics(
                                time.time(),
                                self.tenant_id,
                                object_name,
                                object_id,
                                metric_index,
                                json.dumps({"status": 2}),
                            )
                        except Exception as e:
                            error_msg = f'Failed to call trackme_fqm_gen_metrics with exception="{str(e)}"'
                            logging.error(error_msg)

                        # yield record
                        yield_record = {
                            "_time": time.time(),
                            "_raw": {
                                "response": f"processing with record update, _key={record.get('_key')}, object={object_name}",
                                "action": "success",
                                "record": record,
                            },
                        }

                        yield yield_record

                    except Exception as e:
                        error_msg = f'An exception was encountered while attempting to update the KVstore record, exception="{str(e)}", record="{json.dumps(record, indent=2)}"'
                        errors_count += 1
                        errors_list.append(error_msg)
                        yield_record = {
                            "_time": time.time(),
                            "_raw": {
                                "response": f"processing with record deletion, _key={record.get('_key')}, object={object_name}",
                                "action": "failure",
                                "exception": str(e),
                                "record": record,
                            },
                        }

                        yield yield_record

                # if the entity is already red but inactive, gen a summary event
                elif float(sec_since_last_execution) > max_sec_inactive:
                    if record_current_state != "red":
                        try:
                            record["current_state"] = "red"
                            data_collection.data.update(
                                str(record.get("_key")), json.dumps(record)
                            )
                            logging.info(
                                f'successfully updated record="{json.dumps(record, indent=2)}"'
                            )
                            count_actions_engaged += 1
                        except Exception as e:
                            error_msg = f'An exception was encountered while attempting to update the KVstore record, exception="{str(e)}", record="{json.dumps(record, indent=2)}"'
                            errors_count += 1
                            errors_list.append(error_msg)
                            yield_record = {
                                "_time": time.time(),
                                "_raw": {
                                    "response": f"processing with record update, _key={record.get('_key')}, object={object_name}",
                                    "action": "failure",
                                    "exception": str(e),
                                    "record": record,
                                },
                            }

                            yield yield_record

                    # sunnary state
                    record["event_id"] = hashlib.sha256(
                        json.dumps(record).encode()
                    ).hexdigest()
                    try:
                        trackme_gen_state(
                            index=trackme_summary_idx,
                            sourcetype="trackme:state",
                            source=f"current_state_tracking:splk-fqm:{self.tenant_id}",
                            event=record,
                        )
                        logging.debug(
                            f'TrackMe summary event created successfully, record="{json.dumps(record, indent=1)}"'
                        )
                    except Exception as e:
                        logging.error(
                            f'TrackMe summary event creation failure, record="{json.dumps(record, indent=1)}", exception="{str(e)}"'
                        )

            #
            # purge inactive entities
            #

            # if the requested conditions are met
            if max_sec_record_age_before_purge > 0:

                if float(sec_since_last_execution) > max_sec_record_age_before_purge:
                    count += 1

                    # append the key to the entities_to_be_deleted list
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, object="{record.get("object")}", this entity has been inactive for too long and will be purged automatically. (last seen update {round(sec_since_last_execution, 3)} is beyond the system wide auto-deletion period of {max_sec_record_age_before_purge} seconds)'
                    )
                    entities_to_be_deleted.append(record.get("_key"))
                    # add to a dict for yield and logging purposes
                    entities_to_be_deleted_dict[record.get("_key")] = {
                        "object": record.get("object"),
                        "object_state": record.get("object_state"),
                        "status_message": record.get("status_message", []),
                    }

                else:
                    logging.debug(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, object="{record.get("object")}", this entity is active and will not be purged. (last seen update: {round(sec_since_last_execution, 3)} is not beyond the system wide auto-deletion period of {max_sec_record_age_before_purge} seconds)'
                    )

        # end task
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
        )

        #
        # purge inactive entities
        #

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "purge_inactive_entities"

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # set a global success flag for the mass deletion
        mass_deletion_success = False

        if len(entities_to_be_deleted) > 0:

            try:
                entities_purge_response = self.purge_entities(
                    entities_to_be_deleted,
                    max_sec_record_age_before_purge,
                    instance_id,
                    task_name,
                    task_instance_id,
                )
                mass_deletion_success = True
                count_actions_engaged += len(entities_to_be_deleted)

            except Exception as e:
                mass_deletion_success = False
                error_msg = f'An exception was encountered while attempting to purge the entities, exception="{str(e)}"'
                errors_count += 1
                errors_list.append(error_msg)
                logging.error(error_msg)

        # yield the entities to be deleted
        for key, entity in entities_to_be_deleted_dict.items():

            # append object_name to the report_objects_list if not already present
            if entity.get("object") not in report_objects_list:
                report_objects_list.append(entity.get("object"))

            yield_record = {
                "_time": time.time(),
                "_raw": {
                    "response": f'processed with record deletion attempt, _key={key}, object={entity.get("object")}',
                    "record": entity,
                    "success": mass_deletion_success,
                },
            }

            yield yield_record

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
        )

        # handler event
        if report_objects_list:

            # if report_objects_list is a string (a single object was reported), convert it to a list
            if isinstance(report_objects_list, str):
                report_objects_list = [report_objects_list]

            handler_events_records = []
            for object_name in report_objects_list:
                # Find the object_id (key) for this object from collection_records_dict
                object_id = None
                for key, data in collection_records_dict.items():
                    if data.get("object") == object_name:
                        object_id = key
                        break

                handler_events_records.append(
                    {
                        "object": object_name,
                        "object_id": object_id,
                        "object_category": "splk-fqm",
                        "handler": self.report,
                        "handler_message": "Entity was inspected by the Flex inactive entities inspector, which tracks entities that are not actively managed by any tracker.",
                        "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackmetrackerexecutor tenant_id={self.tenant_id} report={self.report}",
                        "handler_time": time.time(),
                    }
                )

            # notification event
            try:
                trackme_handler_events(
                    session_key=self._metadata.searchinfo.session_key,
                    splunkd_uri=self._metadata.searchinfo.splunkd_uri,
                    tenant_id=self.tenant_id,
                    sourcetype="trackme:handler",
                    source=f"trackme:handler:{self.tenant_id}",
                    handler_events=handler_events_records,
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="fqm", could not send notification event, exception="{e}"'
                )

        #
        # check job status
        #

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "check_job_status"

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # capture the job status
        if errors_count > 0:
            if self.register_component and self.tenant_id and self.report:
                try:
                    trackme_register_tenant_object_summary(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "splk-fqm",
                        self.report,
                        "failure",
                        time.time(),
                        round(time.time() - start, 3),
                        errors_list,
                        "-5m",
                        "now",
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="fqm", Failed to call trackme_register_tenant_object_summary with exception="{str(e)}"'
                    )
        else:
            if self.register_component and self.tenant_id and self.report:
                try:
                    trackme_register_tenant_object_summary(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "splk-fqm",
                        self.report,
                        "success",
                        time.time(),
                        round(time.time() - start, 3),
                        "the job was executed successfully",
                        "-5m",
                        "now",
                    )
                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="fqm", Failed to call trackme_register_tenant_object_summary with exception="{str(e)}"'
                    )

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
        )

        #
        # Call the trackme_register_tenant_component_summary
        #

        if count_actions_engaged > 0:

            # Use threading to do an async call to the register summary without waiting for it to complete
            thread = threading.Thread(
                target=self.register_component_summary_async,
                args=(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "splk-fqm",
                ),
            )
            thread.start()

        #
        # process
        #

        if not count > 0:
            yield_record = {
                "_time": time.time(),
                "_raw": {
                    "response": "There are not records to be processed at the moment, nothing to do.",
                    "action": "success",
                },
            }

            yield yield_record

        # end of main
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, trackmesplkfqminactiveinspector has terminated, run_time="{round(time.time() - start, 3)}"'
        )


dispatch(SplkFlxInactiveEntitiesInspector, sys.argv, sys.stdin, sys.stdout, __name__)
