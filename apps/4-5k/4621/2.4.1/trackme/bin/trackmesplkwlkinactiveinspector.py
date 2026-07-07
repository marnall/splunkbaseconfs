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
import threading
from logging.handlers import RotatingFileHandler

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
    f"{splunkhome}/var/log/splunk/trackme_splkwlk_inactive_inspector.log",
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
    trackme_register_tenant_object_summary,
    trackme_register_tenant_component_summary,
    trackme_handler_events,
)


@Configuration(distributed=False)
class SplkWlkInactiveEntitiesInspector(GeneratingCommand):
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

    max_days_since_inactivity = Option(
        doc="""
        **Syntax:** **max_sec_since_inactivity=****
        **Description:** value for max_days_since_inactivity is required. (0 disables the feature)""",
        require=False,
        default="7",
        validate=validators.Match("max_days_since_inactivity", r"^(\d|\.)*$"),
    )

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
        target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/splk_wlk/write/wlk_delete"

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

        # counter for the number of actions engaged
        count_actions_engaged = 0

        # end of main
        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, trackmesplkwlkinactiveinspector is starting'
        )

        # Data collection (no access is required in this custom command)
        data_collection_name = f"kv_trackme_wlk_tenant_{self.tenant_id}"

        # convert the max day in sec
        max_sec_record_age = self.max_days_since_inactivity
        if max_sec_record_age == "0" or max_sec_record_age == 0:
            max_sec_record_age = 0

        else:
            max_sec_record_age = float(self.max_days_since_inactivity) * 86400

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
        ) = self.get_collection_records("wlk")

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, component="wlk", successfully retrieved {len(collection_records_keys)} records in the KVstore collection={data_collection_name}, run_time={round(time.time()-collection_records_get_start, 3)}'
        )

        # records to be processed counter
        count = 0

        # capture exceptions
        errors_count = 0
        errors_list = []

        # entities_to_be_deleted
        entities_to_be_deleted = []
        entities_to_be_deleted_dict = {}

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "manage_inactive_entities"

        # for the handler events
        report_objects_dict = {}

        logging.info(
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # Loop in the results
        for record in collection_records:

            # get the age in seconds since the latest execution deleted
            sec_since_last_execution = time.time() - float(record.get("last_seen"))

            # if the requested conditions are met
            if max_sec_record_age > 0:

                if float(sec_since_last_execution) > max_sec_record_age:
                    count += 1

                    # append the key to the entities_to_be_deleted list
                    logging.info(
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, object="{record.get("object")}", this entity has been inactive for too long and will be purged automatically. (last seen update {round(sec_since_last_execution, 3)} is beyond the system wide auto-deletion period of {max_sec_record_age} seconds)'
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
                        f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, object="{record.get("object")}", this entity is active and will not be purged. (last seen update: {round(sec_since_last_execution, 3)} is not beyond the system wide auto-deletion period of {max_sec_record_age} seconds)'
                    )

        else:

            # set a global success flag for the mass deletion
            mass_deletion_success = False

            if len(entities_to_be_deleted) > 0:

                try:
                    entities_purge_response = self.purge_entities(
                        entities_to_be_deleted,
                        sec_since_last_execution,
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
                yield_record = {
                    "_time": time.time(),
                    "_raw": {
                        "response": f'processed with record deletion attempt, _key={key}, object={entity.get("object")}',
                        "record": entity,
                        "success": mass_deletion_success,
                    },
                }

                # add to report_objects_dict
                report_objects_dict[key] = entity.get("object")

                yield yield_record

            logging.info(
                f'tenant_id="{self.tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # handler event
            if report_objects_dict:

                handler_events_records = []
                for (
                    report_object_id,
                    report_object_name,
                ) in report_objects_dict.items():
                    handler_events_records.append(
                        {
                            "object": report_object_name,
                            "object_id": report_object_id,
                            "object_category": "splk-wlk",
                            "handler": self.report,
                            "handler_message": "Entity was inspected by an hybrid tracker.",
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
                        f'tenant_id="{self.tenant_id}", component="wlk", could not send notification event, exception="{e}"'
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
                        "splk-wlk",
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
                        f'tenant_id="{self.tenant_id}", component="wlk", Failed to call trackme_register_tenant_object_summary with exception="{str(e)}"'
                    )
        else:
            if self.register_component and self.tenant_id and self.report:
                try:
                    trackme_register_tenant_object_summary(
                        self._metadata.searchinfo.session_key,
                        self._metadata.searchinfo.splunkd_uri,
                        self.tenant_id,
                        "splk-wlk",
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
                        f'tenant_id="{self.tenant_id}", component="wlk", Failed to call trackme_register_tenant_object_summary with exception="{str(e)}"'
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
                    "splk-wlk",
                ),
            )
            thread.start()

        #
        # end of main
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
            f'tenant_id="{self.tenant_id}", instance_id={instance_id}, trackmesplkwlkinactiveinspector has terminated, run_time="{round(time.time() - start, 3)}"'
        )


dispatch(SplkWlkInactiveEntitiesInspector, sys.argv, sys.stdin, sys.stdout, __name__)
