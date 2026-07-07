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
import uuid
import datetime

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
    "%s/var/log/splunk/trackme_general_health_manager.log" % splunkhome,
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
from trackme_libs import (
    trackme_reqinfo,
)

# import trackme libs
from trackme_libs import (
    run_splunk_search,
    trackme_manage_report_schedule,
    trackme_report_update_enablement,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import TrackMe get data libs
from trackme_libs_get_data import get_full_kv_collection

# import the collections dict
from collections_data import collections_dict
from collections_data import (
    collections_list_dsm,
    collections_list_flx,
    collections_list_fqm,
    collections_list_dhm,
    collections_list_mhm,
    collections_list_wlk,
    collections_list_common,
)

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


@Configuration(distributed=False)
class HealthTracker(GeneratingCommand):

    @staticmethod
    def safe_create_datetime(year, month, day, hour=0, minute=0, second=0, tzinfo=None):
        """
        Safely create a datetime object, handling leap years.
        If trying to create Feb 29 in a non-leap year, falls back to Feb 28.
        
        Args:
            year: Year
            month: Month (1-12)
            day: Day of month
            hour: Hour (default 0)
            minute: Minute (default 0)
            second: Second (default 0)
            tzinfo: Timezone info (default None)
            
        Returns:
            datetime.datetime object
        """
        # Check if this is Feb 29 and the year is not a leap year
        if month == 2 and day == 29:
            # Check if year is a leap year
            is_leap_year = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if not is_leap_year:
                # Fall back to Feb 28 for non-leap years
                day = 28
                logging.debug(f'Leap year adjustment: Feb 29 in non-leap year {year} adjusted to Feb 28')
        
        return datetime.datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)

    def get_uuid(self):
        """
        Function to return a unique uuid which is used to trace performance run_time of each subtask.
        """
        return str(uuid.uuid4())

    def get_ml_rules_collection(self, collection):
        """
        Get all records from an ML rules collection.

        :param collection: The collection to query.
        :return: A list of records, a dictionary of records, a list of keys.
        """

        collection_records = []
        collection_records_dict = {}
        count_to_process_list = []

        end = False
        skip_tracker = 0
        while not end:
            process_collection_records = collection.data.query(skip=skip_tracker)
            if process_collection_records:
                for item in process_collection_records:
                    collection_records.append(item)
                    collection_records_dict[item.get("_key")] = (
                        item  # Add the entire item to the dictionary
                    )
                    count_to_process_list.append(item.get("_key"))
                skip_tracker += len(process_collection_records)
            else:
                end = True

        return collection_records, collection_records_dict, count_to_process_list

    def remove_ml_model(
        self,
        component,
        rest_url,
        header,
        ml_model_lookup_name,
        instance_id=None,
        task_name=None,
        task_instance_id=None,
    ):
        """
        Removes an orphan Machine Learning model from the collection.

        :param component: The component name.
        :param rest_url: The REST URL to use.
        :param header: The header to use.
        :param ml_model_lookup_name: The Machine Learning model lookup name.
        :param instance_id: The instance ID for logging purposes.
        :param task_name: The task name for logging purposes.
        :param task_instance_id: The task instance ID for logging purposes.
        :return: True if the model was removed successfully, otherwise False.

        """

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, component="{component}", attempting to delete orphan Machine Learning lookup_name="{ml_model_lookup_name}"'
        )
        try:
            response = requests.delete(
                rest_url,
                headers=header,
                verify=False,
                timeout=600,
            )
            if response.status_code not in (
                200,
                201,
                204,
            ):
                error_msg = f'failure to delete ML lookup_name="{ml_model_lookup_name}", url="{rest_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(error_msg)
            else:
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, action="success", deleted lookup_name="{ml_model_lookup_name}" successfully'
                )
                return True

        except Exception as e:
            error_msg = f'failure to delete ML lookup_name="{ml_model_lookup_name}" with exception="{str(e)}"'
            raise Exception(error_msg)

    def reassign_ml_model(
        self,
        model_id,
        rest_url,
        header,
        instance_id=None,
        task_name=None,
        task_instance_id=None,
    ):
        """
        Reasign a Machine Learning model to the Splunk system user.

        :param model_id: The model_id to reassign.
        :param rest_url: The REST URL to use.
        :param header: The header to use.
        :param instance_id: The instance ID for logging purposes.
        :param task_name: The task name for logging purposes.
        :param task_instance_id: The task instance ID for logging purposes.
        :return: True if the model was reassigned successfully, otherwise False.

        """

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, attempting to re-assign model_id="{model_id}" to splunk-system-user'
        )

        acl_properties = {
            "sharing": "user",
            "owner": "splunk-system-user",
        }

        # proceed boolean
        proceed = False

        # before re-assigning, check if the model exist by running a GET request, if the status code is different from 2**, do not proceed and log an informational message instead
        try:
            response = requests.get(
                f"{rest_url}",
                headers=header,
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, model_id="{model_id}" does not exist, it might have been re-assigned in the meantime, skipping re-assignment'
                )
                return False
            else:
                proceed = True
        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, model_id="{model_id}" failed to retrieve model, exception="{str(e)}"'
            )

        if proceed:

            try:
                response = requests.post(
                    f"{rest_url}/acl",
                    headers=header,
                    data=acl_properties,
                    verify=False,
                    timeout=600,
                )
                if response.status_code not in (
                    200,
                    201,
                    204,
                ):
                    error_msg = f'failure to reassign model_id="{model_id}", url="{rest_url}", response.status_code="{response.status_code}", response.text="{response.text}"'
                    raise Exception(error_msg)
                else:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, action="success", model_id="{model_id}" reassigned successfully'
                    )
                    return True

            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, action="failure", model_id="{model_id}" reassigned failed, exception="{str(e)}"'
                )
                raise Exception(str(e))

    def get_all_accounts(self, instance_id=None, task_name=None, task_instance_id=None):
        """
        Update the configuration of any existing remote account, to ensure that the configuration is up to date.

        :param instance_id: The instance ID for logging purposes.
        :param task_name: The task name for logging purposes.
        :param task_instance_id: The task instance ID for logging purposes.
        :return: A list of remote accounts.
        """

        # endpoint target
        url = f"{self._metadata.searchinfo.splunkd_uri}/servicesNS/nobody/trackme/trackme_account"

        # current_remote_accounts_list
        current_remote_accounts_list = []

        # first, get the list of remote accounts
        try:
            response = requests.get(
                url,
                headers={
                    "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                    "Content-Type": "application/json",
                },
                verify=False,
                params={
                    "output_mode": "json",
                    "count": -1,
                },
                timeout=600,
            )

            response.raise_for_status()
            response_json = response.json()

            # The list of remote accounts is stored as a list in entry
            remote_accounts = response_json.get("entry", [])

            # iterate through the remote accounts, adding them to the dict, name is the key, then we care about "content" which is a dict of our parameters
            # for this account

            for remote_account in remote_accounts:
                remote_account_name = remote_account.get("name", None)

                # add to list
                current_remote_accounts_list.append(remote_account_name)

            return current_remote_accounts_list

        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, error while fetching remote account list: {str(e)}'
            )
            return []

    #
    # Main
    #

    def generate(self, **kwargs):
        if self:
            # performance counter
            global_start = time.time()

            # set instance_id
            instance_id = self.get_uuid()

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # Splunk header for REST requests
            header = {
                "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                "Content-Type": "application/json",
            }

            logging.info(  # First log message
                f'context="general_execution", trackmegeneralhealthmanager is starting now.'
            )

            # global_results_dict to store results of the execution
            global_results_dict = {}

            # Register the object summary in the vtenant collection
            collection_vtenants_name = "kv_trackme_virtual_tenants"
            collection_vtenants = self.service.kvstore[collection_vtenants_name]

            # get all vtenants records, this job is not tenant specific
            vtenant_records = collection_vtenants.data.query()

            ############################################################
            # Machine Learning related global health manager tasks
            # Goals:
            # - Inspect all ML collections, identify orphans models,
            # and reassign if necessary
            ############################################################

            # Reassignment: Ensures that all ML models are owned by splunk-system-user, amd re-assign otherwise
            # run the following search to retrieve the list of existing ML models

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "mlmodels-management:splunk-system-user_reassignment"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # counters
            ml_models_reassigned_success_count = 0
            ml_models_reassigned_failures_count = 0

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting verification of ML models ownership and reassignment if necessary'
            )

            # Define the query
            search = f'| rest splunk_server=local timeout=1200 "/servicesNS/nobody/trackme/data/lookup-table-files" | search eai:acl.app="trackme" AND title="__mlspl_model_*.mlmodel" | table title, id'

            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # A list to store current ml models (filename)
            ml_models_for_reassignement_current_list = []

            # A dict to store the existing models
            ml_models_for_reassignement_dict_existing = {}

            try:
                reader = run_splunk_search(
                    self.service,
                    search,
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        ml_models_for_reassignement_current_list.append(
                            item.get("title")
                        )  # this is the model filename
                        ml_models_for_reassignement_dict_existing[item.get("title")] = {
                            "id": item.get("id")
                        }

            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to retrieve the list of ML models, exception="{str(e)}"'
                )

            # Loop
            for model_id in ml_models_for_reassignement_current_list:

                # reassign the model
                rest_url = ml_models_for_reassignement_dict_existing[model_id].get("id")

                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, attempting reassignment of model_id={model_id}"'
                )

                try:
                    reassigned_model = self.reassign_ml_model(
                        model_id,
                        rest_url,
                        header,
                        instance_id,
                        task_name,
                        task_instance_id,
                    )
                    if reassigned_model:
                        ml_models_reassigned_success_count += 1
                except Exception as e:
                    ml_models_reassigned_failures_count += 1
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to reassign the model, model_id="{model_id}", exception="{str(e)}"'
                    )

            ############################################################
            # Identify ML models owned by splunk-system-user
            ############################################################

            # run the following search to retrieve the list of existing ML models

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting verification of ML models ownership and reassignment if necessary'
            )

            # Define the query
            search = f'| rest splunk_server=local timeout=1200 "/servicesNS/splunk-system-user/trackme/data/lookup-table-files" | search eai:acl.app="trackme" AND title="__mlspl_model_*.mlmodel" | table title, id'

            kwargs_oneshot = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # A list to store current ml models (filename)
            ml_models_current_list = []

            # A dict to store the existing models
            ml_models_dict_existing = {}

            try:
                reader = run_splunk_search(
                    self.service,
                    search,
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        ml_models_current_list.append(
                            item.get("title")
                        )  # this is the model filename
                        ml_models_dict_existing[item.get("title")] = {
                            "id": item.get("id")
                        }

            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to retrieve the list of ML models, exception="{str(e)}"'
                )

            ############################################################
            # Identify ML models configured in TrackMe
            ############################################################

            # A list to store ml_rules_outliers_collections
            ml_rules_outliers_collections = []

            # A dict to ml models definitions
            ml_models_dict = {}

            # A list to store ml models currently configured
            ml_models_list = []

            for vtenant_record in vtenant_records:
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, processing vtenant_record={json.dumps(vtenant_record, indent=2)}'
                )

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # check if tenant is disabled, if so, skip it
                tenant_status = vtenant_record.get("tenant_status", "enabled")
                if tenant_status == "disabled":
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, tenant is disabled, skipping.'
                    )
                    continue

                # for component in dsm, dhm, flx, fqm, wlk
                for component in ["dsm", "dhm", "flx", "fqm", "wlk"]:

                    # get status
                    component_status = vtenant_record.get(f"tenant_{component}_enabled")

                    # append the collection
                    if component_status == 1:
                        ml_rules_outliers_collections.append(
                            f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                        )

            # for each outliers rules collection
            for ml_rules_collection_name in ml_rules_outliers_collections:

                # connect to the collection service and retrieve the records
                ml_rules_collection = self.service.kvstore[ml_rules_collection_name]

                # extract ml_rules_tenant_id from the collection name: trackme_<component>_outliers_entity_rules_tenant_<ml_rules_tenant_id>
                ml_rules_tenant_id = ml_rules_collection_name.split("_")[-1]

                # get records
                try:
                    ml_rules_records, ml_rules_records_dict, ml_rules_records_count = (
                        self.get_ml_rules_collection(ml_rules_collection)
                    )

                    for ml_rules_record in ml_rules_records:

                        # get key
                        ml_rules_record_key = ml_rules_record.get("_key")

                        # get dictionary entities_outliers from the field entities_outliers
                        entities_outliers = json.loads(
                            ml_rules_record.get("entities_outliers")
                        )

                        # loop through entities_outliers, the dict key is the model_id
                        for ml_model_entity in entities_outliers:

                            ml_models_dict[ml_model_entity] = {
                                "model_id": ml_model_entity,
                                "collection_name": ml_rules_collection_name,
                                "collection_key": ml_rules_record_key,
                                "tenant_id": ml_rules_tenant_id,
                            }
                            ml_models_list.append(
                                f"__mlspl_{ml_model_entity}.mlmodel"
                            )  # this is the filename

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to retrieve the records from the collection, collection_name="{ml_rules_collection_name}", exception="{str(e)}"'
                    )

                # log
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, {len(ml_models_dict)} ML models were found configured in TrackMe collections, will now start inspecting Splunk existing models.'
                )

            # log the number of currently existing models
            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, {len(ml_models_current_list)} ML models were found in the system, starting orphan models inspection'
            )

            #
            # orphan models purge / reassign
            #

            ml_models_purged_success_count = 0
            ml_models_purged_failures_count = 0

            # for each model in ml_models_current_list, if the model is not in ml_models_list, delete it
            for model_id in ml_models_current_list:
                if model_id not in ml_models_list and not model_id == "pending":
                    # remove the model
                    rest_url = ml_models_dict_existing[model_id].get("id")

                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, attempting removal of model_id={model_id}"'
                    )

                    try:
                        self.remove_ml_model(
                            "trackme",
                            rest_url,
                            header,
                            model_id,
                            instance_id,
                            task_name,
                            task_instance_id,
                        )
                        ml_models_purged_success_count += 1
                    except Exception as e:
                        ml_models_purged_failures_count += 1
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to remove the orphan model, model_id="{model_id}", exception="{str(e)}"'
                        )

            # end context="mlmodels-management"

            # log
            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, {ml_models_purged_success_count} orphan ML models were removed, {ml_models_purged_failures_count} orphan ML models removals failed, {ml_models_reassigned_success_count} ML models were reassigned to splunk-system-user, {ml_models_reassigned_failures_count} ML models reassignments failed'
            )

            # add to results
            global_results_dict["mlmodels_management"] = {
                "ml_models_in_system_count": len(ml_models_current_list),
                "ml_models_configured_count": len(ml_models_list),
                "ml_models_purged_success_count": ml_models_purged_success_count,
                "ml_models_purged_failures_count": ml_models_purged_failures_count,
                "ml_models_reassigned_success_count": ml_models_reassigned_success_count,
                "ml_models_reassigned_failures_count": ml_models_reassigned_failures_count,
                "result": f"{ml_models_purged_success_count} orphan ML models were removed, {ml_models_purged_failures_count} orphan ML models removals failed, {ml_models_reassigned_success_count} ML models were reassigned to splunk-system-user, {ml_models_reassigned_failures_count} ML models reassignments failed",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # KVstore native ML models orphan cleanup
            # Goals:
            # - For each tenant, inspect the native ML models KVstore collection
            # - Identify model records whose model_id is no longer referenced
            #   in any outlier entity rules for that tenant
            # - Purge orphan model records from the KVstore
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "mlmodels-management:kvstore_orphan_cleanup"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            kvstore_models_purged_success_count = 0
            kvstore_models_purged_failures_count = 0
            kvstore_models_total_count = 0

            for vtenant_record in vtenant_records:
                tenant_id = vtenant_record.get("tenant_id")
                native_ml_collection_name = f"kv_trackme_native_ml_models_tenant_{tenant_id}"

                # Try to access the native ML models collection for this tenant
                try:
                    native_ml_collection = self.service.kvstore[native_ml_collection_name]
                except Exception:
                    # Collection doesn't exist for this tenant, skip
                    continue

                # Get all model records from the native ML models collection
                try:
                    native_ml_records = native_ml_collection.data.query()
                except Exception as e:
                    logging.warning(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'tenant_id="{tenant_id}", failed to query native ML models collection, exception="{str(e)}"'
                    )
                    continue

                if not native_ml_records:
                    continue

                kvstore_models_total_count += len(native_ml_records)

                # Build the set of model_ids that are currently referenced in outlier entity rules
                # (reuse ml_models_dict which was already built above from all tenant outlier rules)
                tenant_active_model_ids = set()
                for component in ["dsm", "dhm", "flx", "fqm", "wlk"]:
                    component_status = vtenant_record.get(f"tenant_{component}_enabled")
                    if component_status != 1:
                        continue

                    rules_collection_name = f"kv_trackme_{component}_outliers_entity_rules_tenant_{tenant_id}"
                    try:
                        rules_collection = self.service.kvstore[rules_collection_name]
                        rules_records, _, _ = self.get_ml_rules_collection(rules_collection)

                        for rule_record in rules_records:
                            entities_outliers_raw = rule_record.get("entities_outliers")
                            if not entities_outliers_raw:
                                continue
                            try:
                                entities_outliers = json.loads(entities_outliers_raw)
                                for model_id in entities_outliers:
                                    tenant_active_model_ids.add(model_id)
                            except Exception:
                                pass

                    except Exception:
                        # Collection doesn't exist or can't be accessed, skip this component
                        continue

                # Purge orphan records from the native ML models collection
                for record in native_ml_records:
                    model_key = record.get("_key")
                    if model_key and model_key not in tenant_active_model_ids:
                        try:
                            native_ml_collection.data.delete_by_id(model_key)
                            kvstore_models_purged_success_count += 1
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'tenant_id="{tenant_id}", purged orphan KVstore model, model_id="{model_key}"'
                            )
                        except Exception as e:
                            kvstore_models_purged_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'tenant_id="{tenant_id}", failed to purge orphan KVstore model, model_id="{model_key}", exception="{str(e)}"'
                            )

            # add to results
            global_results_dict["kvstore_mlmodels_management"] = {
                "kvstore_models_total_count": kvstore_models_total_count,
                "kvstore_models_purged_success_count": kvstore_models_purged_success_count,
                "kvstore_models_purged_failures_count": kvstore_models_purged_failures_count,
                "result": f"{kvstore_models_purged_success_count} orphan KVstore ML models were removed, {kvstore_models_purged_failures_count} removals failed",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'{kvstore_models_purged_success_count} orphan KVstore ML models were removed, '
                f'{kvstore_models_purged_failures_count} removals failed, '
                f'run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # End Machine Learning related global health manager tasks
            ############################################################

            ############################################################
            # Per-entity maintenance: purge long-expired windows
            # Goals:
            # - Records go inert the moment now > maintenance_end_epoch (the
            #   decision maker ignores them), so this is housekeeping only.
            # - Delete records whose window ended more than the grace period
            #   ago so the collection stays small. The grace keeps a recently
            #   expired window visible in the UI / audit briefly.
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "entity-maintenance:purge_expired_windows"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            entity_maintenance_purged_success_count = 0
            entity_maintenance_purged_failures_count = 0
            # Grace: keep expired windows for 7 days before purging.
            entity_maintenance_purge_grace_sec = 604800
            purge_threshold_epoch = time.time() - entity_maintenance_purge_grace_sec

            for vtenant_record in vtenant_records:
                tenant_id = vtenant_record.get("tenant_id")
                entity_maintenance_collection_name = (
                    f"kv_trackme_common_entity_maintenance_tenant_{tenant_id}"
                )

                try:
                    entity_maintenance_collection = self.service.kvstore[
                        entity_maintenance_collection_name
                    ]
                except Exception:
                    # Collection doesn't exist for this tenant yet, skip
                    continue

                try:
                    entity_maintenance_records = entity_maintenance_collection.data.query()
                except Exception as e:
                    logging.warning(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'tenant_id="{tenant_id}", failed to query entity maintenance collection, exception="{str(e)}"'
                    )
                    continue

                for record in entity_maintenance_records or []:
                    try:
                        end_epoch = float(record.get("maintenance_end_epoch", 0) or 0)
                    except (TypeError, ValueError):
                        end_epoch = 0.0
                    record_key = record.get("_key")
                    if record_key and 0 < end_epoch < purge_threshold_epoch:
                        try:
                            entity_maintenance_collection.data.delete_by_id(record_key)
                            entity_maintenance_purged_success_count += 1
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'tenant_id="{tenant_id}", purged expired entity maintenance window, object_id="{record_key}"'
                            )
                        except Exception as e:
                            entity_maintenance_purged_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                f'tenant_id="{tenant_id}", failed to purge expired entity maintenance window, object_id="{record_key}", exception="{str(e)}"'
                            )

            global_results_dict["entity_maintenance_management"] = {
                "entity_maintenance_purged_success_count": entity_maintenance_purged_success_count,
                "entity_maintenance_purged_failures_count": entity_maintenance_purged_failures_count,
                "result": f"{entity_maintenance_purged_success_count} expired entity maintenance windows were removed, {entity_maintenance_purged_failures_count} removals failed",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'{entity_maintenance_purged_success_count} expired entity maintenance windows were removed, '
                f'{entity_maintenance_purged_failures_count} removals failed, '
                f'run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # Splunk Remote Accounts maintenance
            # Goals:
            # - Calls the associated REST endpoint for each existing account,
            # to verify, update account parameters if needed, and perform tokens
            # rotation if needed
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "splunk-remote-accounts:verify_and_maintain_accounts"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, context="splunk-remote-accounts", starting verification and maintenance of Splunk remote accounts'
            )

            # get all accounts
            current_remote_accounts_list = self.get_all_accounts(
                instance_id, task_name, task_instance_id
            )

            # remote_accounts_maintenance_dict
            remote_accounts_maintenance_dict = {}

            # Loop through accounts, and call the endpoint
            for account in current_remote_accounts_list:

                url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/configuration/admin/maintain_remote_account"

                try:
                    response = requests.post(
                        url,
                        headers={
                            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}",
                            "Content-Type": "application/json",
                        },
                        verify=False,
                        data=json.dumps(
                            {
                                "accounts": account,
                            }
                        ),
                        timeout=600,
                    )

                    response.raise_for_status()
                    response_json = response.json()
                    remote_accounts_maintenance_dict[account] = response_json

                except Exception as e:
                    error_msg = f'error calling endpoint, exception="{str(e)}"'
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, {error_msg}'
                    )
                    remote_accounts_maintenance_dict[account] = error_msg

            # add to global_results_dict, if the dict is empty, add a message to the global_results_dict as we had no actions to perform
            if not remote_accounts_maintenance_dict:
                global_results_dict[f"{task_name}"] = {
                    "message": "No actions to perform."
                }
            else:
                global_results_dict[f"{task_name}"] = (
                    remote_accounts_maintenance_dict
                )

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # Configuration Guardian — system-scoped checks
            #
            # These piggyback on the general health manager's daily cadence
            # (8 AM UTC). They must NOT live inside trackmetrackerhealth.py —
            # the remote-account check is system-scoped by nature, and the
            # health-tracker-executing meta-check cannot diagnose its own
            # absence from inside the tracker it is observing.
            ############################################################

            guardian_audit_idx = (
                reqinfo.get("trackme_conf", {})
                .get("index_settings", {})
                .get("trackme_audit_idx", "trackme_audit")
            )

            # --- Guardian: remote_account_token_expiring_soon ---

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:remote_account_token_expiring_soon"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_remote_account_token_expiry

                # The runner returns a list of per-account outcomes (one item
                # per remote account) so run_checks can flatten them into
                # accurate delta counts. Wrap in a dict here for uniform
                # global_results_dict shape across tasks.
                guardian_outcome = check_remote_account_token_expiry(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    audit_index_name=guardian_audit_idx,
                )
                accounts_outcomes = (
                    guardian_outcome
                    if isinstance(guardian_outcome, list)
                    else [guardian_outcome]
                )
                global_results_dict[task_name] = {"accounts": accounts_outcomes}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: remote_account_connectivity_degraded ---
            #
            # Probes `POST /trackme/v2/configuration/test_remote_account` for
            # every configured remote account; alerts on failures. Severity
            # starts at `warning` on first cycle of failure and escalates to
            # `critical` once the failure has persisted past 24h (tracked in
            # the alert's metadata via `first_failure_mtime`).

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:remote_account_connectivity_degraded"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_remote_account_connectivity

                guardian_outcome = check_remote_account_connectivity(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    audit_index_name=guardian_audit_idx,
                )
                accounts_outcomes = (
                    guardian_outcome
                    if isinstance(guardian_outcome, list)
                    else [guardian_outcome]
                )
                global_results_dict[task_name] = {"accounts": accounts_outcomes}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: assigned_index_does_not_exist (per tenant, fan-out) ---
            #
            # Uses run_checks so the pre_run helper fetches the SH-wide index
            # catalogue ONCE and reuses it across every tenant — avoids the
            # N REST calls a per-tenant tracker TIER_4 task would cost.

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:assigned_index_does_not_exist"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import (
                    run_checks,
                    CHECK_ASSIGNED_INDEX_EXISTS,
                )

                delta = run_checks(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    vtenant_records,
                    check_type=CHECK_ASSIGNED_INDEX_EXISTS,
                    audit_index_name=guardian_audit_idx,
                )
                global_results_dict[task_name] = {
                    "counts": {
                        k: len(v) for k, v in delta.items() if isinstance(v, list)
                    },
                }
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: ai_provider_unreachable ---
            #
            # Daily connectivity probe for every configured AI provider via
            # `test_llm_connectivity()`. Skips entirely when AI is disabled
            # (`enable_ai_assistant=0`) or no providers are configured, so
            # non-AI installs pay zero cost for this task.

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:ai_provider_unreachable"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_ai_provider_unreachable

                guardian_outcome = check_ai_provider_unreachable(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    audit_index_name=guardian_audit_idx,
                )
                providers_outcomes = (
                    guardian_outcome
                    if isinstance(guardian_outcome, list)
                    else [guardian_outcome]
                )
                global_results_dict[task_name] = {"providers": providers_outcomes}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: backup_archive_too_old ---
            #
            # Reads `kv_trackme_backup_archives_info` and compares the most-recent
            # record's mtime against the `trackme_backup_scheduler` saved-search
            # cadence × 1.5. Skipped when the scheduler is disabled — backups
            # are opt-in, so "no recent backup" is only a signal when the admin
            # has explicitly enabled the scheduler.

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:backup_archive_too_old"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_backup_archive_too_old

                guardian_outcome = check_backup_archive_too_old(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    audit_index_name=guardian_audit_idx,
                )
                outcomes_wrapped = (
                    guardian_outcome
                    if isinstance(guardian_outcome, list)
                    else [guardian_outcome]
                )
                global_results_dict[task_name] = {"outcomes": outcomes_wrapped}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: backup_run_incomplete (3.0.0 multi-archive only) ---
            #
            # Warns when the latest 3.0.0 backup run produced fewer tenant
            # archives than there are enabled tenants. Distinct from
            # backup_archive_too_old, which is the catastrophic-DR
            # freshness signal. This one is the "DR is degraded for tenant
            # X" signal — post_backup's per-tenant isolation lets the run
            # continue even when one tenant's payload is corrupted, but
            # the operator still needs to know that tenant X's data isn't
            # restorable from that run. Skipped cleanly on un-upgraded
            # installs (no global rows in KV yet).

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:backup_run_incomplete"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_backup_run_incomplete

                guardian_outcome = check_backup_run_incomplete(
                    self._metadata.searchinfo.session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.service,
                    audit_index_name=guardian_audit_idx,
                )
                outcomes_wrapped = (
                    guardian_outcome
                    if isinstance(guardian_outcome, list)
                    else [guardian_outcome]
                )
                global_results_dict[task_name] = {"outcomes": outcomes_wrapped}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            # --- Guardian: health_tracker_not_executing (per tenant, meta-check) ---

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "guardian:health_tracker_not_executing"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            try:
                from trackme_libs_guardian import check_health_tracker_executing

                ht_outcomes = []
                for vtenant_record in vtenant_records or []:
                    try:
                        outcome = check_health_tracker_executing(
                            self._metadata.searchinfo.session_key,
                            self._metadata.searchinfo.splunkd_uri,
                            self.service,
                            vtenant_record,
                            audit_index_name=guardian_audit_idx,
                        )
                        ht_outcomes.append(outcome)
                    except Exception as e:
                        rec_tenant_id = str(vtenant_record.get("tenant_id", ""))
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", '
                            f'task_instance_id={task_instance_id}, tenant_id="{rec_tenant_id}", '
                            f'per-tenant check failed, exception="{str(e)}"'
                        )
                        ht_outcomes.append({
                            "status": "skipped",
                            "tenant_id": rec_tenant_id,
                            "reason": f"exception: {str(e)}",
                        })
                global_results_dict[task_name] = {"tenants": ht_outcomes}
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, check failed, exception="{str(e)}"'
                )
                global_results_dict[task_name] = {
                    "status": "failed",
                    "exception": str(e),
                }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants auto-repair
            # Goals:
            # - For each enable Virtual Tenant, verify that all expected
            # are effectively available in the system. (KV collections...)
            # - If for some reasons an expected object is missing,
            # auto-repair will attempt to create it and fix the tenant inconsistency.
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:auto-repair:collections_and_transforms"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # init auto_repair_actions_list
            auto_repair_actions_list = []

            # A dict to store objects that were verified and their status, per tenant_id as the key
            tenants_objects_status_dict = {}

            # collections map per component, including common collections
            collections_map_per_component = {
                "dsm": collections_list_dsm,
                "dhm": collections_list_dhm,
                "mhm": collections_list_mhm,
                "flx": collections_list_flx,
                "fqm": collections_list_fqm,
                "wlk": collections_list_wlk,
                "common": collections_list_common,  # Add common collections
            }

            for vtenant_record in vtenant_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # init tenant_id_checked_status_dict
                tenant_id_checked_status_dict = {}

                # get RBAC
                tenant_owner = str(vtenant_record.get("tenant_owner"))
                tenant_roles_admin = str(vtenant_record.get("tenant_roles_admin"))
                tenant_roles_user = str(vtenant_record.get("tenant_roles_user"))
                tenant_roles_power = str(vtenant_record.get("tenant_roles_power"))
                # TrackMe sharing level
                trackme_default_sharing = reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_default_sharing"
                ]

                # for read permissions, concatenate admin, power and user
                tenant_roles_read_perms = (
                    f"{tenant_roles_admin},{tenant_roles_power},{tenant_roles_user}"
                )

                # for write permissions, concatenate admin, power
                tenant_roles_write_perms = f"{tenant_roles_admin},{tenant_roles_power}"

                # for component in dsm, dhm, flx, fqm, wlk and common
                for component in ["dsm", "dhm", "mhm", "flx", "fqm", "wlk", "common"]:

                    # get status
                    try:
                        component_status = int(
                            vtenant_record.get(
                                f"tenant_{component}_enabled", 1
                            )  # Default to 1 for common
                        )
                    except Exception as e:
                        component_status = 0

                    # only continue if component is enabled
                    if component_status == 1:

                        # Handle collections
                        for object_name in collections_map_per_component[component]:

                            #
                            # Verify that the KV collection exists
                            #

                            kvstore_collection_name = (
                                f"kv_{object_name}_tenant_{tenant_id}"
                            )
                            kvstore_collection_exists = (
                                True  # assume the collection exists
                            )

                            # check if the collection exists
                            try:
                                collection = self.service.kvstore[
                                    kvstore_collection_name
                                ]
                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, collection_name={kvstore_collection_name}, kvstore_collection_exists={kvstore_collection_exists}'
                                )
                                tenant_id_checked_status_dict[
                                    kvstore_collection_name
                                ] = {
                                    "result": "success",
                                    "type": "kvstore_collection",
                                }
                            except Exception as e:
                                kvstore_collection_exists = False
                                logging.error(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, failed to retrieve the collection, collection_name="{kvstore_collection_name}", exception="{str(e)}"'
                                )
                                tenant_id_checked_status_dict[
                                    kvstore_collection_name
                                ] = {
                                    "result": "failure",
                                    "exception": str(e),
                                    "type": "kvstore_collection",
                                }

                            #
                            # Verify that the transform exists and contains the expected fields
                            #

                            transform_name = f"{object_name}_tenant_{tenant_id}"
                            transform_exists = True  # assume the transform exists
                            transforms_fields_list_csv = None
                            transforms_fields_list = None
                            transforms_expected_fields_list_csv = collections_dict[
                                object_name
                            ]
                            transforms_expected_fields_list = [
                                x.strip()
                                for x in transforms_expected_fields_list_csv.split(",")
                            ]
                            transforms_has_missing_fields = False  # assume False

                            # check if the transform exists
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, inspecting transform_name={transform_name}'
                            )
                            try:
                                transform = self.service.confs["transforms"][
                                    transform_name
                                ]
                                transforms_fields_list_csv = transform["fields_list"]
                                transforms_fields_list = (
                                    [
                                        x.strip()
                                        for x in transforms_fields_list_csv.split(",")
                                    ]
                                    if transforms_fields_list_csv
                                    else []
                                )

                                # Verify that the transforms has at the minimum the expected fields
                                for expected_field in transforms_expected_fields_list:
                                    if expected_field not in transforms_fields_list:
                                        transforms_has_missing_fields = True

                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_fields_list={transforms_fields_list}, transforms_has_missing_fields={transforms_has_missing_fields}'
                                )
                            except Exception as e:
                                transform_exists = False
                                logging.error(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, failed to retrieve the transform, transform_name="{transform_name}", exception="{str(e)}"'
                                )

                            # temp logging
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, kvstore_collection_exists={kvstore_collection_exists}, transform_exists={transform_exists}, transform_fields_list={transforms_fields_list}, transforms_has_missing_fields={transforms_has_missing_fields}'
                            )

                            #
                            # Take action if needed
                            #

                            #
                            # KVstore collection
                            #

                            # If the KVstore collection does not exist, create it
                            if not kvstore_collection_exists:
                                logging.warning(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, collection_name={kvstore_collection_name}, kvstore_collection_exists={kvstore_collection_exists}, the KVstore collection was detected missing, it will be created.'
                                )

                                # create the KVstore collection
                                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvcollection'
                                data = {
                                    "tenant_id": tenant_id,
                                    "collection_name": kvstore_collection_name,
                                    "collection_acl": {
                                        "owner": tenant_owner,
                                        "sharing": trackme_default_sharing,
                                        "perms.write": tenant_roles_write_perms,
                                        "perms.read": tenant_roles_read_perms,
                                    },
                                    "owner": tenant_owner,
                                }

                                try:
                                    response = requests.post(
                                        url,
                                        headers={
                                            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}"
                                        },
                                        data=json.dumps(data),
                                        verify=False,
                                        timeout=600,
                                    )
                                    response.raise_for_status()
                                    logging.info(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, collection_name={kvstore_collection_name}, kvstore_collection_exists={kvstore_collection_exists}, the KVstore collection was detected missing, it has been created successfully.'
                                    )

                                    # add to auto_repair_actions_list
                                    auto_repair_actions_list.append(
                                        {
                                            "action": "create_kvcollection",
                                            "tenant_id": tenant_id,
                                            "component": component,
                                            "collection_name": kvstore_collection_name,
                                            "message": "KVstore collection was detected missing, it has been created successfully.",
                                        }
                                    )

                                except Exception as e:
                                    logging.error(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, collection_name={kvstore_collection_name}, kvstore_collection_exists={kvstore_collection_exists}, the KVstore collection was detected missing, attempt to create it has failed, exception="{str(e)}"'
                                    )

                                    # add to auto_repair_actions_list
                                    auto_repair_actions_list.append(
                                        {
                                            "action": "create_kvcollection",
                                            "tenant_id": tenant_id,
                                            "component": component,
                                            "collection_name": kvstore_collection_name,
                                            "message": "KVstore collection was detected missing, attempt to create it has failed.",
                                            "exception": str(e),
                                        }
                                    )

                            #
                            # Transforms definition: If the transforms does not exist, create it, if it exists but has missing fields, it will be deleted and recreated
                            #

                            if transform_exists and not transforms_has_missing_fields:
                                tenant_id_checked_status_dict[transform_name] = {
                                    "result": "success",
                                    "type": "transform",
                                }
                            elif not transform_exists:
                                tenant_id_checked_status_dict[transform_name] = {
                                    "result": "failure",
                                    "exception": "The transform was detected missing.",
                                    "type": "transform",
                                }
                            elif transform_exists and transforms_has_missing_fields:
                                tenant_id_checked_status_dict[transform_name] = {
                                    "result": "failure",
                                    "exception": "The transform was detected as existing but has missing fields.",
                                    "type": "transform",
                                }
                            else:
                                tenant_id_checked_status_dict[transform_name] = {
                                    "result": "unknown",
                                    "transform_exists": transform_exists,
                                    "transforms_has_missing_fields": transforms_has_missing_fields,
                                    "type": "transform",
                                }

                            if not transform_exists or transforms_has_missing_fields:

                                if not transform_exists:
                                    logging.warning(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected missing, it will be created.'
                                    )

                                if transform_exists and transforms_has_missing_fields:
                                    logging.warning(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected as existing but has missing fields, it will be recreated.'
                                    )

                                    #
                                    # delete the transform
                                    #

                                    url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/delete_kvtransform'
                                    data = {
                                        "tenant_id": tenant_id,
                                        "transform_name": transform_name,
                                    }

                                    try:
                                        response = requests.post(
                                            url,
                                            headers={
                                                "Authorization": f"Splunk {self._metadata.searchinfo.session_key}"
                                            },
                                            data=json.dumps(data),
                                            verify=False,
                                            timeout=600,
                                        )
                                        response.raise_for_status()
                                        logging.info(
                                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected as existing but has missing fields, it has been deleted successfully.'
                                        )

                                        # add to auto_repair_actions_list
                                        auto_repair_actions_list.append(
                                            {
                                                "action": "delete_kvtransform",
                                                "tenant_id": tenant_id,
                                                "component": component,
                                                "transform_name": transform_name,
                                                "message": "The transform was detected as existing but has missing fields, it has been deleted successfully.",
                                            }
                                        )

                                    except Exception as e:
                                        logging.error(
                                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected as existing but has missing fields, it has been deleted successfully.'
                                        )

                                        # add to auto_repair_actions_list
                                        auto_repair_actions_list.append(
                                            {
                                                "action": "delete_kvtransform",
                                                "tenant_id": tenant_id,
                                                "component": component,
                                                "transform_name": transform_name,
                                                "message": "The transform was detected as existing but has missing fields, attempt to delete it has failed.",
                                                "exception": str(e),
                                            }
                                        )

                                #
                                # create the transform
                                #

                                url = f'{reqinfo["server_rest_uri"]}/services/trackme/v2/configuration/admin/create_kvtransform'
                                data = {
                                    "tenant_id": tenant_id,
                                    "transform_name": transform_name,
                                    "transform_fields": transforms_expected_fields_list_csv,
                                    "collection_name": kvstore_collection_name,
                                    "transform_acl": {
                                        "owner": tenant_owner,
                                        "sharing": trackme_default_sharing,
                                        "perms.write": tenant_roles_write_perms,
                                        "perms.read": tenant_roles_read_perms,
                                    },
                                    "owner": tenant_owner,
                                }

                                try:
                                    response = requests.post(
                                        url,
                                        headers={
                                            "Authorization": f"Splunk {self._metadata.searchinfo.session_key}"
                                        },
                                        data=json.dumps(data),
                                        verify=False,
                                        timeout=600,
                                    )
                                    response.raise_for_status()
                                    logging.info(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected missing, it has been created successfully.'
                                    )

                                    # add to auto_repair_actions_list
                                    auto_repair_actions_list.append(
                                        {
                                            "action": "create_kvtransform",
                                            "tenant_id": tenant_id,
                                            "component": component,
                                            "transform_name": transform_name,
                                            "message": "The transform was detected missing or inconsistent, it has been created successfully.",
                                        }
                                    )

                                except Exception as e:
                                    logging.error(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component={component}, transforms_name={transform_name}, transforms_exists={transform_exists}, the transform was detected missing, it has been created successfully.'
                                    )

                                    # add to auto_repair_actions_list
                                    auto_repair_actions_list.append(
                                        {
                                            "action": "create_kvtransform",
                                            "tenant_id": tenant_id,
                                            "component": component,
                                            "transform_name": transform_name,
                                            "message": "The transform was detected missing or inconsistent, attempt to create it has failed.",
                                            "exception": str(e),
                                        }
                                    )

                # add to tenants_objects_status_dict
                tenants_objects_status_dict[tenant_id] = tenant_id_checked_status_dict

            # add to global_results_dict
            global_results_dict[f"{task_name}"] = {
                "knowledge_objects_status": tenants_objects_status_dict,
                "auto_repair_actions_list": (
                    auto_repair_actions_list
                    if auto_repair_actions_list
                    else "No actions to perform."
                ),
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants configuration issues fixer
            # Goals:
            # - Run a Splunk search to identify Virtual Tenants with configuration issues (missing reports)
            # - For each tenant found, identify enabled components from the central KVstore collection
            # - For each tenant/component combination, run the REST API call to fix issues
            # - Exclude replica tenants (tenant_replica = 1)
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:auto-repair:components_reports"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Step 1: Run Splunk search to identify tenants with missing reports
            search = remove_leading_spaces(
            """
                search (index=_internal sourcetype=trackme:rest_api) OR (index=_internal sourcetype=trackme:custom_commands:*)
                log_level=error 
                task="optimize_tenant_scheduled_reports" 
                "failure to get report report_name" 
                "urlencoded"
                | stats count by tenant_id
            """)

            kwargs_oneshot = {
                "earliest_time": "-24h",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            # Counters
            tenants_with_issues_found = 0
            tenants_processed = 0
            tenants_fixed = 0
            tenants_skipped = 0
            total_components_fixed = 0
            total_components_failed = 0

            # Lists to store detailed information
            tenants_with_issues = []
            tenants_processed_details = []
            rest_call_responses = []

            try:
                reader = run_splunk_search(
                    self.service,
                    search,
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        tenant_id = item.get("tenant_id")
                        error_count = item.get("count", 0)
                        if tenant_id:
                            tenants_with_issues.append({
                                "tenant_id": tenant_id,
                                "error_count": error_count
                            })
                            tenants_with_issues_found += 1

            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to run search for tenants with issues, exception="{str(e)}"'
                )

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, found {tenants_with_issues_found} tenants with configuration issues'
            )

            # Step 2: Process each tenant found
            for tenant_info in tenants_with_issues:
                tenant_id = tenant_info["tenant_id"]
                error_count = tenant_info["error_count"]
                tenants_processed += 1

                # Initialize tenant processing details
                tenant_processing_detail = {
                    "tenant_id": tenant_id,
                    "error_count": error_count,
                    "enabled_components": [],
                    "components_fixed": 0,
                    "components_failed": 0,
                    "is_replica": False,
                    "skipped_reason": None,
                    "processing_status": "processing"
                }

                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, processing tenant {tenant_id} with {error_count} errors'
                )

                # Get tenant record from central KVstore collection
                try:
                    # Find the tenant record in vtenant_records (already loaded)
                    tenant_record = None
                    for vtenant_record in vtenant_records:
                        if vtenant_record.get("tenant_id") == tenant_id:
                            tenant_record = vtenant_record
                            break

                    if not tenant_record:
                        logging.warning(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, tenant record not found in central collection, skipping'
                        )
                        tenant_processing_detail["skipped_reason"] = "tenant record not found in central collection"
                        tenant_processing_detail["processing_status"] = "skipped"
                        tenants_processed_details.append(tenant_processing_detail)
                        tenants_skipped += 1
                        continue

                    # Check if tenant is a replica (exclude if so)
                    try:
                        tenant_replica = int(tenant_record.get("tenant_replica", 0))
                    except Exception as e:
                        tenant_replica = 0

                    tenant_processing_detail["is_replica"] = (tenant_replica == 1)

                    if tenant_replica == 1:
                        logging.info(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping'
                        )
                        tenant_processing_detail["skipped_reason"] = "replica tenant"
                        tenant_processing_detail["processing_status"] = "skipped"
                        tenants_processed_details.append(tenant_processing_detail)
                        tenants_skipped += 1
                        continue

                    # Get enabled components for this tenant
                    enabled_components = []
                    component_fields = {
                        "dsm": "tenant_dsm_enabled",
                        "dhm": "tenant_dhm_enabled", 
                        "mhm": "tenant_mhm_enabled",
                        "flx": "tenant_flx_enabled",
                        "wlk": "tenant_wlk_enabled",
                        "fqm": "tenant_fqm_enabled"
                    }

                    for component, field_name in component_fields.items():
                        try:
                            if int(tenant_record.get(field_name, 0)) == 1:
                                enabled_components.append(component)
                        except (ValueError, TypeError):
                            continue

                    tenant_processing_detail["enabled_components"] = enabled_components

                    if not enabled_components:
                        logging.info(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, has no enabled components, skipping'
                        )
                        tenant_processing_detail["skipped_reason"] = "no enabled components"
                        tenant_processing_detail["processing_status"] = "skipped"
                        tenants_processed_details.append(tenant_processing_detail)
                        tenants_skipped += 1
                        continue

                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, has enabled components: {enabled_components}'
                    )

                    # Step 3: Fix each enabled component
                    tenant_components_fixed = 0
                    tenant_components_failed = 0

                    for component in enabled_components:
                        try:
                            # Prepare the REST API call
                            target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/vtenants/admin/check_component_tenant"
                            
                            payload = {
                                "tenant_id": tenant_id,
                                "component_target": component,
                                "update_comment": f"Automated fix for missing reports - general health manager task"
                            }

                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, fixing component {component}'
                            )

                            # Make the REST call
                            response = requests.post(
                                target_url,
                                headers=header,
                                data=json.dumps(payload),
                                verify=False,
                                timeout=600
                            )

                            # Store REST call response details
                            rest_call_response = {
                                "tenant_id": tenant_id,
                                "component": component,
                                "status_code": response.status_code,
                                "success": response.status_code == 200,
                                "response_text": response.text,
                                "timestamp": time.time()
                            }

                            # Try to parse JSON response if possible
                            try:
                                rest_call_response["response_json"] = response.json()
                            except:
                                rest_call_response["response_json"] = None

                            rest_call_responses.append(rest_call_response)

                            if response.status_code == 200:
                                tenant_components_fixed += 1
                                total_components_fixed += 1
                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component {component}, successfully fixed'
                                )
                            else:
                                tenant_components_failed += 1
                                total_components_failed += 1
                                logging.error(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component {component}, failed to fix: {response.status_code} - {response.text}'
                                )

                        except Exception as e:
                            tenant_components_failed += 1
                            total_components_failed += 1
                            
                            # Store exception details
                            rest_call_response = {
                                "tenant_id": tenant_id,
                                "component": component,
                                "status_code": None,
                                "success": False,
                                "response_text": str(e),
                                "timestamp": time.time(),
                                "exception": True
                            }
                            rest_call_responses.append(rest_call_response)
                            
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, component {component}, exception during fix: {str(e)}'
                            )

                    if tenant_components_fixed > 0:
                        tenants_fixed += 1

                    # Update tenant processing details
                    tenant_processing_detail["components_fixed"] = tenant_components_fixed
                    tenant_processing_detail["components_failed"] = tenant_components_failed
                    tenant_processing_detail["processing_status"] = "completed"

                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, completed: {tenant_components_fixed} components fixed, {tenant_components_failed} components failed'
                    )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, exception during processing: {str(e)}'
                    )
                    tenant_processing_detail["skipped_reason"] = f"exception during processing: {str(e)}"
                    tenant_processing_detail["processing_status"] = "error"
                    tenants_skipped += 1

                # Always add the tenant processing detail to the list
                tenants_processed_details.append(tenant_processing_detail)

            # add to global_results_dict
            global_results_dict[f"{task_name}"] = {
                "tenants_with_issues_found": tenants_with_issues_found,
                "tenants_processed": tenants_processed,
                "tenants_fixed": tenants_fixed,
                "tenants_skipped": tenants_skipped,
                "total_components_fixed": total_components_fixed,
                "total_components_failed": total_components_failed,
                "tenants_with_issues": tenants_with_issues,
                "tenants_processed_details": tenants_processed_details,
                "rest_call_responses": rest_call_responses,
                "result": f"{tenants_with_issues_found} tenants with issues found, {tenants_processed} processed, {tenants_fixed} fixed, {tenants_skipped} skipped, {total_components_fixed} components fixed, {total_components_failed} components failed",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants Check Health Tracker
            # Goals:
            # - If the tenant is enabled, then the health tracker should be enabled and scheduled.
            # - If the tenant is disabled, then the health tracker should be disabled.
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:check_health_tracker"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            def manage_savedsearch_schedule(
                tenant_id, savedsearch_names, feature_enabled, feature_name
            ):
                """
                Helper function to manage saved search scheduling based on feature enablement.

                Args:
                    savedsearch_names: List of saved search names to manage
                    feature_enabled: Boolean indicating if the feature should be enabled
                    feature_name: String name of the feature for logging purposes
                """
                for savedsearch_name in savedsearch_names:
                    # get the status of the savedsearch
                    savedsearch_properties, savedsearch_acl = (
                        trackme_manage_report_schedule(
                            logging,
                            self._metadata.searchinfo.session_key,
                            self._metadata.searchinfo.splunkd_uri,
                            tenant_id,
                            savedsearch_name,
                            action="status",
                        )
                    )

                    # log
                    logging.info(
                        f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", savedsearch_properties="{json.dumps(savedsearch_properties, indent=2)}", savedsearch_acl="{json.dumps(savedsearch_acl, indent=2)}"'
                    )

                    # get the disabled status
                    disabled = int(savedsearch_properties.get("disabled", 0))

                    # get the is_scheduled status
                    is_scheduled = int(savedsearch_properties.get("is_scheduled", 0))

                    # Check tenant status first - if tenant is disabled, ensure health tracker is disabled
                    if feature_enabled == False:
                        # Tenant is disabled - ensure health tracker is disabled (but keep it scheduled)
                        if disabled == 0:
                            # Report is enabled - disable it
                            logging.info(
                                f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", tenant is disabled, disabling savedsearch.'
                            )
                            try:
                                trackme_report_update_enablement(
                                    self._metadata.searchinfo.session_key,
                                    self._metadata.searchinfo.splunkd_uri,
                                    tenant_id,
                                    savedsearch_name,
                                    "disable",
                                )
                                logging.info(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", savedsearch disabled successfully.'
                                )
                                return {
                                    "action": "disable_savedsearch",
                                    "tenant_id": tenant_id,
                                    "savedsearch_name": savedsearch_name,
                                    "message": "The savedsearch has been disabled successfully.",
                                }
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", an exception was encountered while trying to disable savedsearch, exception="{str(e)}"'
                                )
                        else:
                            # Report is already disabled - nothing to do
                            logging.info(
                                f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", tenant is disabled and savedsearch is already disabled, nothing to do.'
                            )
                            return {
                                "action": "nothing_to_do",
                                "tenant_id": tenant_id,
                                "savedsearch_name": savedsearch_name,
                                "message": "Tenant is disabled and savedsearch is already disabled, nothing to do.",
                            }

                    # Tenant is enabled - ensure health tracker is enabled AND scheduled
                    elif feature_enabled == True:
                        # Track if we performed any actions
                        action_performed = False
                        action_message = ""
                        
                        # Check if we need to enable the report
                        if disabled == 1:
                            logging.info(
                                f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", the report is currently disabled and needs to be enabled.'
                            )
                            try:
                                trackme_report_update_enablement(
                                    self._metadata.searchinfo.session_key,
                                    self._metadata.searchinfo.splunkd_uri,
                                    tenant_id,
                                    savedsearch_name,
                                    "enable",
                                )
                                logging.info(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", savedsearch enabled successfully.'
                                )
                                action_performed = True
                                action_message = "The savedsearch has been enabled successfully"
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", an exception was encountered while trying to enable the savedsearch, exception="{str(e)}"'
                                )
                                # stop here if we had an exception enabling the savedsearch
                                continue

                        # Check if we need to schedule the report
                        if is_scheduled == 0:
                            logging.info(
                                f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", the report needs to be scheduled.'
                            )
                            try:
                                savedsearch_properties, savedsearch_acl = (
                                    trackme_manage_report_schedule(
                                        logging,
                                        self._metadata.searchinfo.session_key,
                                        self._metadata.searchinfo.splunkd_uri,
                                        tenant_id,
                                        savedsearch_name,
                                        action="enable",
                                    )
                                )
                                logging.info(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", savedsearch scheduled successfully, properties="{json.dumps(savedsearch_properties, indent=2)}"'
                                )
                                action_performed = True
                                if action_message:
                                    action_message += " and scheduled successfully."
                                else:
                                    action_message = "The savedsearch has been scheduled successfully."
                            except Exception as e:
                                logging.error(
                                    f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", an exception was encountered while trying to schedule savedsearch, exception="{str(e)}"'
                                )

                        # Return appropriate result based on actions performed
                        if action_performed:
                            return {
                                "action": "enable_savedsearch",
                                "tenant_id": tenant_id,
                                "savedsearch_name": savedsearch_name,
                                "message": action_message,
                            }
                        else:
                            # Report is already enabled and scheduled - nothing to do
                            logging.info(
                                f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", disabled="{disabled}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", tenant is enabled and savedsearch is already enabled and scheduled, nothing to do.'
                            )
                            return {
                                "action": "nothing_to_do",
                                "tenant_id": tenant_id,
                                "savedsearch_name": savedsearch_name,
                                "message": "Tenant is enabled and savedsearch is already enabled and scheduled, nothing to do.",
                            }

                    else:
                        # This should not happen as we've covered all cases above
                        logging.warning(
                            f'tenant_id="{tenant_id}", instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, savedsearch="{savedsearch_name}", is_scheduled="{is_scheduled}", {feature_name}_feature_enabled="{feature_enabled}", unexpected state, nothing to do.'
                        )
                        return {
                            "action": "nothing_to_do",
                            "tenant_id": tenant_id,
                            "savedsearch_name": savedsearch_name,
                            "message": "Unexpected state, nothing to do.",
                        }

            # init auto_repair_actions_list
            auto_repair_actions_list = []

            # A dict to store objects that were verified and their status, per tenant_id as the key
            tenants_objects_status_dict = {}

            for vtenant_record in vtenant_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # get the tenant_status (enabled/disabled)
                tenant_status = vtenant_record.get("tenant_status", "enabled")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # init health_tracker_report_name
                health_tracker_report_name = (
                    f"trackme_health_tracker_tenant_{tenant_id}"
                )
                health_tracker_check_result = {}

                try:
                    # Determine if health tracker should be enabled based on tenant status
                    health_tracker_enabled = (tenant_status == "enabled")

                    health_tracker_check_result = manage_savedsearch_schedule(
                        tenant_id, [health_tracker_report_name], health_tracker_enabled, "health_tracker"
                    )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, an exception was encountered while trying to manage savedsearch schedule, exception="{str(e)}"'
                    )

                # add to tenants_objects_status_dict
                tenants_objects_status_dict[tenant_id] = health_tracker_check_result

            # add to global_results_dict
            global_results_dict[f"{task_name}"] = {
                "health_tracker_check_result": tenants_objects_status_dict,
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants orphan account cleanup
            # Goals:
            # - Detect and clean up orphan vtenant accounts (UCC conf stanzas)
            # that no longer have a corresponding record in the KV Store
            # kv_trackme_virtual_tenants collection.
            # This can happen when the vtenant account deletion fails during
            # tenant deletion (e.g., due to timing issues or transient errors).
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:orphan_vtenant_account_cleanup"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # Reload vtenant records fresh from KV Store to avoid race conditions.
            # The original vtenant_records was loaded at the start of the generate method
            # and may be stale — tenants created since then would be falsely detected as orphans.
            # Use a boolean flag to track success — relying on set emptiness is insufficient
            # because a partial failure mid-iteration could leave the set non-empty but incomplete.
            known_tenant_ids = set()
            kv_reload_success = False
            try:
                fresh_vtenant_records = collection_vtenants.data.query()
                for vtenant_record in fresh_vtenant_records:
                    tenant_id = vtenant_record.get("tenant_id")
                    if tenant_id:
                        known_tenant_ids.add(tenant_id)
                kv_reload_success = True
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                    f'failed to reload vtenant records from KV Store, skipping orphan cleanup, exception="{str(e)}"'
                )

            orphan_accounts_cleaned = 0

            if not kv_reload_success or not known_tenant_ids:
                logging.warning(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                    f'kv_reload_success="{kv_reload_success}", known_tenant_ids_count="{len(known_tenant_ids)}", '
                    f'skipping orphan cleanup to avoid false positives (KV Store reload failed or returned no tenants).'
                )
            else:
                try:
                    # List all vtenant accounts from the UCC-managed conf
                    url = f"{self._metadata.searchinfo.splunkd_uri}/servicesNS/nobody/trackme/trackme_vtenants"
                    response = requests.get(
                        url,
                        headers=header,
                        params={"output_mode": "json", "count": 0},
                        verify=False,
                        timeout=120,
                    )

                    if response.status_code in (200, 201):
                        vtenant_accounts = response.json().get("entry", [])

                        for account_entry in vtenant_accounts:
                            account_name = account_entry.get("name")

                            if account_name and account_name not in known_tenant_ids:
                                # This is an orphan vtenant account — no matching KV Store record
                                logging.warning(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'detected orphan vtenant account="{account_name}" with no matching KV Store record, attempting cleanup.'
                                )

                                try:
                                    delete_url = f"{self._metadata.searchinfo.splunkd_uri}/servicesNS/nobody/trackme/trackme_vtenants/{account_name}"
                                    delete_response = requests.delete(
                                        delete_url,
                                        headers=header,
                                        verify=False,
                                        timeout=120,
                                    )

                                    if delete_response.status_code in (200, 201, 204):
                                        orphan_accounts_cleaned += 1
                                        logging.info(
                                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                            f'orphan vtenant account="{account_name}" was successfully deleted, '
                                            f'response.status_code="{delete_response.status_code}"'
                                        )
                                    else:
                                        logging.error(
                                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                            f'failed to delete orphan vtenant account="{account_name}", '
                                            f'response.status_code="{delete_response.status_code}", response.text="{delete_response.text}"'
                                        )
                                except Exception as e:
                                    logging.error(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                        f'failed to delete orphan vtenant account="{account_name}", exception="{str(e)}"'
                                    )
                    else:
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                            f'failed to list vtenant accounts, response.status_code="{response.status_code}", response.text="{response.text}"'
                        )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'failed to perform orphan vtenant account cleanup, exception="{str(e)}"'
                    )

            # add to global_results_dict
            global_results_dict[f"{task_name}"] = {
                "orphan_accounts_cleaned": orphan_accounts_cleaned,
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'orphan_accounts_cleaned="{orphan_accounts_cleaned}", '
                f'run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants stateful alerts records expiration
            # Goals:
            # - For each enable Virtual Tenant, search for closed stateful alerts records
            # in the KVstore collection, and delete them if they are older than 30 days.
            # When purging statefule alerts records, search and purge associated charts records. (if any)
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:stateful_alerts_records_expiration"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # get the stateful records expiration days
            stateful_records_expiration_days = int(
                reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_stateful_records_expiration_days"
                ]
            )

            # counters
            expired_statefule_records_deleted_count = 0
            expired_associated_charts_records_deleted_count = 0
            orphans_charts_records_deleted_count = 0
            for vtenant_record in vtenant_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # check if tenant is disabled, if so, skip it
                tenant_status = vtenant_record.get("tenant_status", "enabled")
                if tenant_status == "disabled":
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, tenant is disabled, skipping.'
                    )
                    continue

                # Define the query
                search = remove_leading_spaces(
                    f"""
                    | inputlookup trackme_stateful_alerting_tenant_{tenant_id} where alert_status="closed" | eval keyid=_key
                    | eval record_age=now()-ctime, is_expired=if(record_age > 86400*{stateful_records_expiration_days}, 1, 0)
                    | where is_expired=1
                    | table keyid, incident_id
                  """
                )

                # A list to stored expired incident_id
                expired_incident_id_list = []

                # A list to store expired records
                expired_records_list = []

                # A list to store expired associated charts records
                expired_associated_charts_records_list = []

                # A list to store orphans charts records
                orphans_charts_records = []

                # Run the search
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, running search="{search}"'
                )
                try:
                    reader = run_splunk_search(
                        self.service,
                        search,
                        {
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        },
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            expired_records_list.append(item.get("keyid"))
                            expired_incident_id_list.append(item.get("incident_id"))
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, records for incident_id={item.get("incident_id")} have been detected as expired and will be deleted from the KVstore collections, keyid={item.get("keyid")}'
                            )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to retrieve the list of expired records, exception="{str(e)}"'
                    )

                # If nothing to do, continue
                if not expired_records_list:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, no expired records to process, skipping.'
                    )
                    continue

                else:

                    # Run a new search to retrieve the list of associated charts records

                    # Convert the list to a CSV string filtered
                    expired_records_filtered_csv = (
                        f"({','.join(expired_incident_id_list)})"
                    )

                    search = remove_leading_spaces(
                        f"""
                        | inputlookup trackme_stateful_alerting_charts_tenant_{tenant_id} where incident_id IN {expired_records_filtered_csv} | eval keyid=_key
                        | table keyid, incident_id
                    """
                    )

                    # Run the search
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, running search="{search}"'
                    )
                    try:
                        reader = run_splunk_search(
                            self.service,
                            search,
                            {
                                "earliest_time": "-5m",
                                "latest_time": "now",
                                "output_mode": "json",
                                "count": 0,
                            },
                            24,
                            5,
                        )

                        for item in reader:
                            if isinstance(item, dict):
                                expired_associated_charts_records_list.append(
                                    item.get("keyid")
                                )

                    except Exception as e:
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to retrieve the list of associated charts records, exception="{str(e)}"'
                        )

                # Run a new search to retrieve the list of orphans charts records
                search = remove_leading_spaces(
                    f"""
                    | inputlookup trackme_stateful_alerting_charts_tenant_{tenant_id} | eval keyid=_key
                    | lookup trackme_stateful_alerting_tenant_{tenant_id} incident_id AS incident_id OUTPUT incident_id as parent_incident_id
                    | where (isnull(parent_incident_id) OR parent_incident_id="")
                    | table keyid, incident_id
                """
                )

                # Run the search
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, running search="{search}"'
                )
                try:
                    reader = run_splunk_search(
                        self.service,
                        search,
                        {
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        },
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            orphans_charts_records.append(item.get("keyid"))

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to retrieve the list of orphans charts records, exception="{str(e)}"'
                    )

                # Purge expired records from the stateful collection, if any
                if expired_records_list:

                    # connect to the collection
                    collection_stateful_alerting_name = (
                        f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
                    )
                    collection_stateful_alerting = self.service.kvstore[
                        collection_stateful_alerting_name
                    ]

                    # for each expired record, delete the record from the stateful collection
                    for expired_record in expired_records_list:

                        try:
                            # Remove the record
                            collection_stateful_alerting.data.delete(
                                json.dumps({"_key": expired_record})
                            )
                            expired_statefule_records_deleted_count += 1

                        except Exception as e:
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to delete the record from collection="{collection_stateful_alerting_name}", exception="{str(e)}"'
                            )

                # Purge expired associated charts records from the stateful collection, if any
                if expired_associated_charts_records_list:

                    # connect to the collection
                    collection_stateful_alerting_name = (
                        f"kv_trackme_stateful_alerting_charts_tenant__{tenant_id}"
                    )

                    # for each expired record, delete the record from the stateful collection
                    for expired_record in expired_associated_charts_records_list:

                        try:
                            # Remove the record
                            collection_stateful_alerting.data.delete(
                                json.dumps({"_key": expired_record})
                            )
                            expired_associated_charts_records_deleted_count += 1
                        except Exception as e:
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to delete the record from collection="{collection_stateful_alerting_name}", exception="{str(e)}"'
                            )

                # Purge orphans charts records from the stateful collection, if any
                if orphans_charts_records:

                    # connect to the collection
                    collection_stateful_alerting_name = (
                        f"kv_trackme_stateful_alerting_charts_tenant__{tenant_id}"
                    )

                    # for each expired record, delete the record from the stateful collection
                    for orphan_record in orphans_charts_records:

                        try:
                            # Remove the record
                            collection_stateful_alerting.data.delete(
                                json.dumps({"_key": orphan_record})
                            )
                            expired_associated_charts_records_deleted_count += 1
                        except Exception as e:
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to delete the record from collection="{collection_stateful_alerting_name}", exception="{str(e)}"'
                            )

            # add to global_results_dict
            global_results_dict[
                f"{task_name}"
            ] = {
                "expired_statefule_records_deleted_count": expired_statefule_records_deleted_count,
                "expired_associated_charts_records_deleted_count": expired_associated_charts_records_deleted_count,
                "orphans_charts_records_deleted_count": orphans_charts_records_deleted_count,
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Score Cache cleanup
            # Goals:
            # - For each enabled Virtual Tenant, purge expired score cache records
            #   (older than 24 hours) from kv_trackme_common_score_cache_tenant_{tenant_id}
            # - These cache records provide immediate visibility for false positive
            #   and manual score changes, and are no longer needed after 24 hours
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:score_cache_cleanup"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            score_cache_deleted_count = 0

            for vtenant_record in vtenant_records:

                tenant_id = vtenant_record.get("tenant_id")

                # skip replica tenants
                if vtenant_record.get("tenant_replica") == 1:
                    continue

                collection_name = f"kv_trackme_common_score_cache_tenant_{tenant_id}"
                cutoff = time.time() - 86400  # 24 hours ago

                try:
                    query = json.dumps({"ctime": {"$lt": cutoff}})
                    self.service.kvstore[collection_name].data.delete(query=query)
                    logging.debug(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'tenant_id={tenant_id}, purged expired score cache records from collection="{collection_name}"'
                    )
                    score_cache_deleted_count += 1
                except Exception as e:
                    logging.debug(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                        f'tenant_id={tenant_id}, failed to purge score cache records from collection="{collection_name}", '
                        f'exception="{str(e)}"'
                    )

            global_results_dict[f"{task_name}"] = {
                "tenants_cleaned": score_cache_deleted_count,
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants stateful alerts duplicate opened incidents cleanup
            # Goals:
            # - For each enabled Virtual Tenant, verify that for a given object_id,
            # there should not be more than one opened incident (alert_status="opened") in the KVstore
            # - If there are more than one incident_id for the same object_id, keep only the latest
            # (based on the field mtime which is the epochtime of the last modification of the incident_id),
            # other records should be updated with alert_status="closed"
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = (
                "virtual_tenants:stateful_alerts_duplicate_opened_incidents_cleanup"
            )

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # counters
            duplicate_opened_incidents_found_count = 0
            duplicate_opened_incidents_resolved_count = 0
            duplicate_opened_incidents_resolution_failures_count = 0

            for vtenant_record in vtenant_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # check if tenant is disabled, if so, skip it
                tenant_status = vtenant_record.get("tenant_status", "enabled")
                if tenant_status == "disabled":
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, tenant is disabled, skipping.'
                    )
                    continue

                # Define the query to find duplicate opened incidents for the same object_id
                search = remove_leading_spaces(
                    f"""
                        | inputlookup trackme_stateful_alerting_tenant_{tenant_id} where alert_status="opened" | eval keyid=_key
                        | eval _time=mtime
                        | stats count as incident_count, values(incident_id) as incident_ids, latest(incident_id) as latest_incident_id, latest(keyid) as latest_keyid, values(keyid) as keyids, max(mtime) as max_mtime by object_id
                        | where incident_count > 1
                        | eval to_close_keyids=mvmap(keyids, if(mvfind(keyids, "^\\\\"" + latest_keyid + "\\$")=0, null(), keyids))
                        | eval to_close_incident_ids=mvmap(incident_ids, if(mvfind(incident_ids, "^\\\\"" + latest_incident_id + "\\$")=0, null(), incident_ids))
                        | table object_id, incident_count, latest_incident_id, latest_keyid, max_mtime, to_close_keyids, to_close_incident_ids
                  """
                )

                # A list to store duplicate opened incidents data
                duplicate_opened_incidents_list = []

                # Run the search
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, running search="{search}"'
                )
                try:
                    reader = run_splunk_search(
                        self.service,
                        search,
                        {
                            "earliest_time": "-5m",
                            "latest_time": "now",
                            "output_mode": "json",
                            "count": 0,
                        },
                        24,
                        5,
                    )

                    for item in reader:
                        if isinstance(item, dict):
                            duplicate_opened_incidents_list.append(item)
                            duplicate_opened_incidents_found_count += 1
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, found duplicate opened incidents for object_id={item.get("object_id")}, incident_count={item.get("incident_count")}, latest_incident_id={item.get("latest_incident_id")}, latest_keyid={item.get("latest_keyid")}, max_mtime={item.get("max_mtime")}'
                            )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to retrieve the list of duplicate opened incidents, exception="{str(e)}"'
                    )

                # If nothing to do, continue
                if not duplicate_opened_incidents_list:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, no duplicate opened incidents to process, skipping.'
                    )
                    continue

                # Process duplicate opened incidents
                for duplicate_incident in duplicate_opened_incidents_list:

                    object_id = duplicate_incident.get("object_id")
                    to_close_keyids = duplicate_incident.get("to_close_keyids", [])
                    # if not a list, turn into a list csv
                    if not isinstance(to_close_keyids, list):
                        to_close_keyids = to_close_keyids.split(",")
                    to_close_incident_ids = duplicate_incident.get(
                        "to_close_incident_ids", []
                    )
                    # if not a list, turn into a list csv
                    if not isinstance(to_close_incident_ids, list):
                        to_close_incident_ids = to_close_incident_ids.split(",")

                    # Parse the to_close_keyids and to_close_incident_ids
                    if to_close_keyids:
                        to_close_keyids_list = [
                            keyid.strip()
                            for keyid in to_close_keyids
                            if keyid.strip()
                        ]
                    else:
                        to_close_keyids_list = []

                    if to_close_incident_ids:
                        to_close_incident_ids_list = [
                            incident_id.strip()
                            for incident_id in to_close_incident_ids
                            if incident_id.strip()
                        ]
                    else:
                        to_close_incident_ids_list = []

                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, object_id={object_id}, will close {len(to_close_keyids_list)} duplicate incidents: keyids={to_close_keyids_list}, incident_ids={to_close_incident_ids_list}'
                    )

                    # Connect to the collection
                    collection_stateful_alerting_name = (
                        f"kv_trackme_stateful_alerting_tenant_{tenant_id}"
                    )
                    collection_stateful_alerting = self.service.kvstore[
                        collection_stateful_alerting_name
                    ]

                    # Update each duplicate incident to closed status
                    for keyid in to_close_keyids_list:
                        try:

                            # Get the current record
                            record_list = collection_stateful_alerting.data.query(
                                query=json.dumps({"_key": keyid})
                            )

                            if record_list and len(record_list) > 0:
                                # Extract the first (and should be only) record from the list
                                record = record_list[0]
                                # Update the record to closed status
                                record["alert_status"] = "closed"
                                record["mtime"] = int(
                                    time.time()
                                )  # Update modification time

                                # Update the record in the collection
                                collection_stateful_alerting.data.update(
                                    keyid, json.dumps(record)
                                )
                                duplicate_opened_incidents_resolved_count += 1

                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, object_id={object_id}, successfully closed duplicate incident with keyid={keyid}'
                                )
                            else:
                                logging.warning(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, object_id={object_id}, record with keyid={keyid} not found in collection'
                                )

                        except Exception as e:
                            duplicate_opened_incidents_resolution_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, object_id={object_id}, failed to close duplicate incident with keyid={keyid}, exception="{str(e)}"'
                            )

            # add to global_results_dict
            global_results_dict[
                f"{task_name}"
            ] = {
                "duplicate_opened_incidents_found_count": duplicate_opened_incidents_found_count,
                "duplicate_opened_incidents_resolved_count": duplicate_opened_incidents_resolved_count,
                "duplicate_opened_incidents_resolution_failures_count": duplicate_opened_incidents_resolution_failures_count,
                "result": f"{duplicate_opened_incidents_found_count} duplicate opened incidents found, {duplicate_opened_incidents_resolved_count} resolved successfully, {duplicate_opened_incidents_resolution_failures_count} resolution failures",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

            ############################################################
            # TrackMe Virtual Tenants stateful charts records expiration
            # Goals:
            # - For each Virtual tenant, purge any record in the stateful charts KVstore collection:
            #   trackme_stateful_alerting_charts_tenant_<tenant_id>
            # - For each KVrecord which is equal or older to 48 hours, based on the field "ctime" 
            #   of the record which contains the epochtime of its creation
            ############################################################

            task_start = time.time()
            task_instance_id = self.get_uuid()
            task_name = "virtual_tenants:stateful_charts_records_expiration"

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
            )

            # get the stateful records expiration days
            stateful_records_expiration_days = int(
                reqinfo["trackme_conf"]["trackme_general"][
                    "trackme_stateful_charts_records_expiration_days"
                ]
            )

            # Define the expiration threshold (based on the expiration days)
            charts_records_expiration_seconds = stateful_records_expiration_days * 24 * 3600
            current_time = time.time()

            # counters
            expired_charts_records_deleted_count = 0
            expired_charts_records_deletion_failures_count = 0

            for vtenant_record in vtenant_records:

                # get the tenant_id
                tenant_id = vtenant_record.get("tenant_id")

                # check if tenant is a replica tenant, if so, skip it
                if vtenant_record.get("tenant_replica", 0) == 1:
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, is a replica tenant, skipping.'
                    )
                    continue

                # check if tenant is disabled, if so, skip it
                tenant_status = vtenant_record.get("tenant_status", "enabled")
                if tenant_status == "disabled":
                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, tenant is disabled, skipping.'
                    )
                    continue

                # connect to the stateful charts collection
                collection_stateful_charts_name = (
                    f"kv_trackme_stateful_alerting_charts_tenant_{tenant_id}"
                )

                try:
                    collection_stateful_charts = self.service.kvstore[collection_stateful_charts_name]
                    
                    # get all records from the collection
                    (
                        charts_records,
                        charts_collection_keys,
                        charts_collection_dict,
                    ) = get_full_kv_collection(
                        collection_stateful_charts, collection_stateful_charts_name
                    )
                    
                    # A list to store expired records to delete
                    expired_charts_records_list = []

                    # Process each record to check if it's older than 48 hours
                    for record in charts_records:
                        try:
                            # Get the ctime field and convert from string to float if needed
                            ctime_str = record.get("ctime")
                            if ctime_str is None:
                                logging.warning(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, record with key={record.get("_key")} has no ctime field, skipping.'
                                )
                                continue
                            
                            # Convert string to float if needed
                            if isinstance(ctime_str, str):
                                ctime_float = float(ctime_str)
                            else:
                                ctime_float = float(ctime_str)
                            
                            # Calculate age in seconds
                            record_age_seconds = current_time - ctime_float
                            
                            # Check if record is older than 48 hours
                            if record_age_seconds >= charts_records_expiration_seconds:
                                expired_charts_records_list.append(record.get("_key"))
                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, record with key={record.get("_key")} is {round(record_age_seconds/3600, 2)} hours old (>= 48 hours), will be deleted.'
                                )
                        
                        except (ValueError, TypeError) as e:
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to process ctime field for record with key={record.get("_key")}, ctime="{ctime_str}", exception="{str(e)}"'
                            )
                            continue

                    # If no expired records, continue to next tenant
                    if not expired_charts_records_list:
                        logging.info(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, no expired charts records to process, skipping.'
                        )
                        continue

                    # Delete expired records from the collection
                    for expired_record_key in expired_charts_records_list:
                        try:
                            # Remove the record
                            collection_stateful_charts.data.delete(
                                json.dumps({"_key": expired_record_key})
                            )
                            expired_charts_records_deleted_count += 1
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, successfully deleted expired charts record with key={expired_record_key}'
                            )

                        except Exception as e:
                            expired_charts_records_deletion_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to delete expired charts record with key={expired_record_key}, exception="{str(e)}"'
                            )

                except Exception as e:
                    logging.error(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, tenant_id={tenant_id}, failed to access collection="{collection_stateful_charts_name}", exception="{str(e)}"'
                    )

            # add to global_results_dict
            global_results_dict[f"{task_name}"] = {
                "expired_charts_records_deleted_count": expired_charts_records_deleted_count,
                "expired_charts_records_deletion_failures_count": expired_charts_records_deletion_failures_count,
                "result": f"{expired_charts_records_deleted_count} expired charts records deleted, {expired_charts_records_deletion_failures_count} deletion failures",
            }

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
            )

        ############################################################
        # Recurring Bank Holidays Management
        # Goals:
        # - Process recurring bank holidays and create future occurrences
        # - Handle holidays that span across years (e.g., Dec 31 - Jan 1)
        # - Clean up past bank holiday periods that have already ended
        ############################################################

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "bank-holidays:recurring_periods_management"

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # counters
        recurring_holidays_processed_count = 0
        new_periods_created_count = 0
        periods_creation_failures_count = 0
        past_periods_deleted_count = 0
        past_periods_deletion_failures_count = 0

        try:
            # Connect to bank holidays collection
            collection_name = "kv_trackme_bank_holidays"
            collection = self.service.kvstore[collection_name]

            # Get current time and year
            current_time = time.time()
            current_year = datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc).year

            ############################################################
            # Step 1: Clean up past bank holiday periods
            # Strategy:
            # - For recurring holidays: Keep the oldest one for each pattern (template), delete other past duplicates
            # - For non-recurring holidays: Delete all that are past
            ############################################################

            logging.info(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting cleanup of past bank holiday periods.'
            )

            try:
                # Get all bank holidays
                all_holidays = collection.data.query()
                
                # Group recurring holidays by pattern to identify templates
                recurring_by_pattern = {}
                non_recurring_past = []
                
                for holiday in all_holidays:
                    holiday_dict = dict(holiday)
                    holiday_key = holiday_dict.get("_key")
                    end_date_epoch = holiday_dict.get("end_date")
                    is_recurring = holiday_dict.get("is_recurring", False)
                    
                    if not end_date_epoch:
                        logging.warning(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, holiday with key={holiday_key} has no end_date, skipping cleanup check.'
                        )
                        continue
                    
                    # Check if period has already passed
                    if int(end_date_epoch) < int(current_time):
                        if is_recurring:
                            # For recurring holidays, group by pattern to keep templates
                            period_name = holiday_dict.get("period_name", "")
                            country_code = holiday_dict.get("country_code", "")
                            start_date_epoch = holiday_dict.get("start_date")
                            
                            if start_date_epoch:
                                try:
                                    start_dt = datetime.datetime.fromtimestamp(start_date_epoch, tz=datetime.timezone.utc)
                                    end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
                                    
                                    # Create pattern key
                                    pattern_key = f"{period_name}|{country_code}|{start_dt.month:02d}-{start_dt.day:02d}|{end_dt.month:02d}-{end_dt.day:02d}"
                                    
                                    if pattern_key not in recurring_by_pattern:
                                        recurring_by_pattern[pattern_key] = []
                                    recurring_by_pattern[pattern_key].append({
                                        "key": holiday_key,
                                        "time_created": holiday_dict.get("time_created", 0),
                                        "holiday": holiday_dict
                                    })
                                except Exception as e:
                                    logging.warning(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to parse dates for holiday key={holiday_key}, exception="{str(e)}", treating as non-recurring for cleanup.'
                                    )
                                    non_recurring_past.append(holiday_dict)
                            else:
                                # Missing start_date, treat as non-recurring
                                non_recurring_past.append(holiday_dict)
                        else:
                            # Non-recurring past holiday - mark for deletion
                            non_recurring_past.append(holiday_dict)
                
                # Delete non-recurring past holidays via REST API
                for holiday_dict in non_recurring_past:
                    holiday_key = holiday_dict.get("_key")
                    period_name = holiday_dict.get("period_name", "unknown")
                    try:
                        end_date_epoch = holiday_dict.get("end_date")
                        end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
                        end_date_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Use REST API endpoint for deletion (enables auditing)
                        target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/bank_holidays/admin/delete"
                        payload = {"_key": holiday_key}
                        
                        response = requests.post(
                            target_url,
                            headers=header,
                            data=json.dumps(payload),
                            verify=False,
                            timeout=600
                        )
                        
                        if response.status_code == 200:
                            past_periods_deleted_count += 1
                            logging.info(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, deleted past non-recurring bank holiday via REST API: key={holiday_key}, period_name="{period_name}", end_date={end_date_str}'
                            )
                        else:
                            past_periods_deletion_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to delete past non-recurring bank holiday via REST API: key={holiday_key}, period_name="{period_name}", status_code={response.status_code}, response={response.text}'
                            )
                    except Exception as e:
                        past_periods_deletion_failures_count += 1
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to delete past non-recurring bank holiday: key={holiday_key}, period_name="{period_name}", exception="{str(e)}"'
                        )
                
                # For recurring holidays, keep the oldest one (template) for each pattern, delete others
                for pattern_key, holidays_list in recurring_by_pattern.items():
                    if len(holidays_list) > 1:
                        # Sort by time_created (oldest first) - keep the first one as template
                        holidays_list.sort(key=lambda x: x.get("time_created", 0))
                        template = holidays_list[0]
                        duplicates = holidays_list[1:]
                        
                        logging.debug(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, pattern="{pattern_key}" has {len(holidays_list)} past occurrences, keeping template (key={template["key"]}), deleting {len(duplicates)} duplicates.'
                        )
                        
                        # Delete duplicate past periods via REST API
                        for duplicate in duplicates:
                            duplicate_key = duplicate["key"]
                            duplicate_holiday = duplicate["holiday"]
                            period_name = duplicate_holiday.get("period_name", "unknown")
                            try:
                                end_date_epoch = duplicate_holiday.get("end_date")
                                end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
                                end_date_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Use REST API endpoint for deletion (enables auditing)
                                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/bank_holidays/admin/delete"
                                payload = {"_key": duplicate_key}
                                
                                response = requests.post(
                                    target_url,
                                    headers=header,
                                    data=json.dumps(payload),
                                    verify=False,
                                    timeout=600
                                )
                                
                                if response.status_code == 200:
                                    past_periods_deleted_count += 1
                                    logging.info(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, deleted duplicate past recurring bank holiday via REST API: key={duplicate_key}, period_name="{period_name}", pattern="{pattern_key}", end_date={end_date_str}'
                                    )
                                else:
                                    past_periods_deletion_failures_count += 1
                                    logging.error(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to delete duplicate past recurring bank holiday via REST API: key={duplicate_key}, period_name="{period_name}", status_code={response.status_code}, response={response.text}'
                                    )
                            except Exception as e:
                                past_periods_deletion_failures_count += 1
                                logging.error(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to delete duplicate past recurring bank holiday: key={duplicate_key}, period_name="{period_name}", exception="{str(e)}"'
                                )
                    # If only one past occurrence, keep it as template (no deletion needed)
                
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, cleanup completed: {past_periods_deleted_count} past periods deleted, {past_periods_deletion_failures_count} deletion failures.'
                )
            except Exception as e:
                logging.error(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed during cleanup of past bank holidays, exception="{str(e)}"'
                )

            ############################################################
            # Step 2: Process recurring holidays and create future occurrences
            # Ensure we have periods for current year + next year (year+1)
            ############################################################

            # Get all recurring bank holidays (after cleanup)
            query_recurring = json.dumps({"is_recurring": True})
            recurring_holidays = collection.data.query(query=query_recurring)

            if not recurring_holidays:
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, no recurring bank holidays found, skipping creation task.'
                )
            else:
                logging.info(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, found {len(recurring_holidays)} recurring bank holiday(s) to process.'
                )

                # Plan ahead for current year + next year (year+1)
                # This ensures we always have periods for the current year (if not yet passed) and next year
                years_to_check = [current_year, current_year + 1]

                # Get all existing bank holidays to check for duplicates
                all_existing_holidays = collection.data.query()
                existing_periods_by_pattern = {}

                # Group existing holidays by pattern (period_name + country_code + month/day)
                for holiday in all_existing_holidays:
                    holiday_dict = dict(holiday)
                    period_name = holiday_dict.get("period_name", "")
                    country_code = holiday_dict.get("country_code", "")
                    start_date_epoch = holiday_dict.get("start_date")
                    end_date_epoch = holiday_dict.get("end_date")
                    
                    if start_date_epoch and end_date_epoch:
                        start_dt = datetime.datetime.fromtimestamp(start_date_epoch, tz=datetime.timezone.utc)
                        end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
                        
                        # Create a pattern key: period_name + country_code + month/day of start and end
                        pattern_key = f"{period_name}|{country_code}|{start_dt.month:02d}-{start_dt.day:02d}|{end_dt.month:02d}-{end_dt.day:02d}"
                        
                        if pattern_key not in existing_periods_by_pattern:
                            existing_periods_by_pattern[pattern_key] = []
                        existing_periods_by_pattern[pattern_key].append({
                            "year": start_dt.year,
                            "record": holiday_dict
                        })

                # Process each recurring holiday
                for recurring_holiday in recurring_holidays:
                    recurring_holidays_processed_count += 1
                    holiday_dict = dict(recurring_holiday)
                    
                    period_name = holiday_dict.get("period_name", "")
                    country_code = holiday_dict.get("country_code", "")
                    comment = holiday_dict.get("comment", "")
                    start_date_epoch = holiday_dict.get("start_date")
                    end_date_epoch = holiday_dict.get("end_date")
                    src_user = holiday_dict.get("src_user", "system")
                    
                    if not start_date_epoch or not end_date_epoch:
                        logging.warning(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, recurring holiday with key={holiday_dict.get("_key")} has invalid dates, skipping.'
                        )
                        continue

                    # Parse original dates
                    try:
                        start_dt = datetime.datetime.fromtimestamp(start_date_epoch, tz=datetime.timezone.utc)
                        end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
                    except Exception as e:
                        logging.error(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to parse dates for recurring holiday key={holiday_dict.get("_key")}, exception="{str(e)}"'
                        )
                        continue

                    # Extract month/day from original dates
                    start_month = start_dt.month
                    start_day = start_dt.day
                    start_hour = start_dt.hour
                    start_minute = start_dt.minute
                    
                    end_month = end_dt.month
                    end_day = end_dt.day
                    end_hour = end_dt.hour
                    end_minute = end_dt.minute

                    # Create pattern key for this recurring holiday
                    pattern_key = f"{period_name}|{country_code}|{start_month:02d}-{start_day:02d}|{end_month:02d}-{end_day:02d}"

                    # Check which years already have this holiday
                    # We check both by year and by actual date range to be more robust
                    existing_years = set()
                    existing_date_ranges = {}  # year -> list of (start_epoch, end_epoch) tuples
                    
                    if pattern_key in existing_periods_by_pattern:
                        for existing_period in existing_periods_by_pattern[pattern_key]:
                            year = existing_period["year"]
                            existing_years.add(year)
                            record = existing_period["record"]
                            if year not in existing_date_ranges:
                                existing_date_ranges[year] = []
                            existing_date_ranges[year].append((
                                record.get("start_date"),
                                record.get("end_date")
                            ))

                    logging.info(
                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, processing recurring holiday: period_name="{period_name}", pattern_key="{pattern_key}", existing_years={sorted(existing_years)}'
                    )

                    # Create periods for missing years
                    for target_year in years_to_check:
                        # Check if year already exists
                        if target_year in existing_years:
                            # Double-check by verifying the date range matches
                            # This handles edge cases where same year might have been created manually
                            should_skip = False
                            if target_year in existing_date_ranges:
                                # Calculate what the date range should be for this year
                                if end_month < start_month or (end_month == start_month and end_day < start_day):
                                    # Year-spanning: target_year to target_year+1
                                    expected_start = self.safe_create_datetime(
                                        target_year, start_month, start_day, start_hour, start_minute,
                                        tzinfo=datetime.timezone.utc
                                    ).timestamp()
                                    expected_end = self.safe_create_datetime(
                                        target_year + 1, end_month, end_day, end_hour, end_minute,
                                        tzinfo=datetime.timezone.utc
                                    ).timestamp()
                                else:
                                    # Normal: both in target_year
                                    expected_start = self.safe_create_datetime(
                                        target_year, start_month, start_day, start_hour, start_minute,
                                        tzinfo=datetime.timezone.utc
                                    ).timestamp()
                                    expected_end = self.safe_create_datetime(
                                        target_year, end_month, end_day, end_hour, end_minute,
                                        tzinfo=datetime.timezone.utc
                                    ).timestamp()
                                
                                # Check if any existing period matches this date range (within same day tolerance)
                                for existing_start, existing_end in existing_date_ranges[target_year]:
                                    if existing_start and existing_end:
                                        # Check if dates are on the same day (tolerance for time differences)
                                        existing_start_dt = datetime.datetime.fromtimestamp(existing_start, tz=datetime.timezone.utc)
                                        expected_start_dt = datetime.datetime.fromtimestamp(expected_start, tz=datetime.timezone.utc)
                                        if (existing_start_dt.year == expected_start_dt.year and
                                            existing_start_dt.month == expected_start_dt.month and
                                            existing_start_dt.day == expected_start_dt.day):
                                            should_skip = True
                                            break
                            
                            if should_skip:
                                logging.debug(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, period already exists for year={target_year}, period_name="{period_name}", skipping.'
                                )
                                continue

                        # Calculate start and end dates for target year
                        try:
                            # Handle year-spanning holidays (e.g., Dec 31 - Jan 1)
                            if end_month < start_month or (end_month == start_month and end_day < start_day):
                                # Holiday spans across years (e.g., Dec 31 - Jan 1)
                                # Start date is in target_year, end date is in target_year + 1
                                new_start_dt = self.safe_create_datetime(
                                    target_year, start_month, start_day, start_hour, start_minute,
                                    tzinfo=datetime.timezone.utc
                                )
                                new_end_dt = self.safe_create_datetime(
                                    target_year + 1, end_month, end_day, end_hour, end_minute,
                                    tzinfo=datetime.timezone.utc
                                )
                            else:
                                # Normal holiday within the same year
                                new_start_dt = self.safe_create_datetime(
                                    target_year, start_month, start_day, start_hour, start_minute,
                                    tzinfo=datetime.timezone.utc
                                )
                                new_end_dt = self.safe_create_datetime(
                                    target_year, end_month, end_day, end_hour, end_minute,
                                    tzinfo=datetime.timezone.utc
                                )

                            # Convert to epoch timestamps
                            new_start_epoch = int(round(new_start_dt.timestamp()))
                            new_end_epoch = int(round(new_end_dt.timestamp()))

                            # Validate date range
                            if new_end_epoch <= new_start_epoch:
                                logging.warning(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, invalid date range for year={target_year}, period_name="{period_name}", skipping.'
                                )
                                continue

                            # Create new record via REST API (enables auditing and delegates complexity)
                            try:
                                target_url = f"{self._metadata.searchinfo.splunkd_uri}/services/trackme/v2/bank_holidays/admin/create"
                                payload = {
                                    "period_name": period_name,
                                    "start_date": new_start_epoch,
                                    "end_date": new_end_epoch,
                                    "comment": comment,
                                    "country_code": country_code,
                                    "is_recurring": True,  # Keep recurring flag
                                }
                                
                                response = requests.post(
                                    target_url,
                                    headers=header,
                                    data=json.dumps(payload),
                                    verify=False,
                                    timeout=600
                                )
                                
                                if response.status_code == 200:
                                    response_data = response.json()
                                    created_record = response_data.get("payload", {})
                                    new_key = created_record.get("_key")
                                    new_periods_created_count += 1
                                    logging.info(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, successfully created recurring bank holiday period via REST API: key={new_key}, period_name="{period_name}", year={target_year}, start_date={new_start_dt.strftime("%Y-%m-%d %H:%M")}, end_date={new_end_dt.strftime("%Y-%m-%d %H:%M")}'
                                    )
                                elif response.status_code == 409:
                                    # 409 Conflict means the period already exists (duplicate detection)
                                    # This is expected behavior, not an error - log at debug level
                                    logging.debug(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, recurring bank holiday period already exists (duplicate detected): period_name="{period_name}", year={target_year}, status_code=409'
                                    )
                                else:
                                    periods_creation_failures_count += 1
                                    logging.error(
                                        f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to create recurring bank holiday period via REST API for year={target_year}, period_name="{period_name}", status_code={response.status_code}, response={response.text}'
                                    )
                            except Exception as e:
                                periods_creation_failures_count += 1
                                logging.error(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to create recurring bank holiday period for year={target_year}, period_name="{period_name}", exception="{str(e)}"'
                                )

                        except Exception as e:
                            periods_creation_failures_count += 1
                            logging.error(
                                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to calculate dates for year={target_year}, period_name="{period_name}", exception="{str(e)}"'
                            )

        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, failed to process recurring bank holidays, exception="{str(e)}"'
            )

        # add to global_results_dict
        global_results_dict[f"{task_name}"] = {
            "recurring_holidays_processed_count": recurring_holidays_processed_count,
            "new_periods_created_count": new_periods_created_count,
            "periods_creation_failures_count": periods_creation_failures_count,
            "past_periods_deleted_count": past_periods_deleted_count,
            "past_periods_deletion_failures_count": past_periods_deletion_failures_count,
            "result": f"{recurring_holidays_processed_count} recurring holidays processed, {new_periods_created_count} new periods created, {periods_creation_failures_count} creation failures, {past_periods_deleted_count} past periods deleted, {past_periods_deletion_failures_count} deletion failures",
        }

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
        )

        ############################################################
        # Support Diagnostic — purge expired archives
        # Goals:
        # - Walk $SPLUNK_HOME/etc/apps/trackme/diag/
        # - Delete .tgz/.tar.gz archive files older than the retention window
        # - Delete orphan staging_* directories from killed or failed runs
        # The support_diag REST handler writes here; it relies on this task
        # for periodic cleanup rather than performing it inline.
        ############################################################

        task_start = time.time()
        task_instance_id = self.get_uuid()
        task_name = "support_diag:purge_expired_archives"

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, starting task.'
        )

        # Retention windows (seconds)
        # - Archive files: 2 days. Archives are meant to be downloaded by the
        #   customer immediately after generation; older ones are abandoned.
        # - Staging directories: 1 hour. Staging dirs only exist while a
        #   diag is being assembled (tarred+rm'd in a finally block); a
        #   leftover older than 1h means the handler process was killed.
        archive_retention_seconds = 2 * 24 * 3600
        staging_retention_seconds = 3600

        archives_purged_count = 0
        archive_purge_failures_count = 0
        staging_dirs_purged_count = 0
        staging_dirs_purge_failures_count = 0

        try:
            splunk_home = os.environ.get("SPLUNK_HOME")
            diag_dir = (
                os.path.join(splunk_home, "etc", "apps", "trackme", "diag")
                if splunk_home
                else None
            )
            now = time.time()

            if diag_dir and os.path.isdir(diag_dir):
                for name in os.listdir(diag_dir):
                    path = os.path.join(diag_dir, name)
                    try:
                        if os.path.isfile(path):
                            # Only touch recognised archive extensions; never
                            # delete arbitrary files that may land there.
                            if not (name.endswith(".tgz") or name.endswith(".tar.gz")):
                                continue
                            age = now - os.path.getmtime(path)
                            if age > archive_retention_seconds:
                                os.remove(path)
                                archives_purged_count += 1
                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'purged expired archive, file="{name}", age_seconds={int(age)}'
                                )
                        elif os.path.isdir(path):
                            # Only touch staging dirs created by the handler.
                            if not name.startswith("staging_"):
                                continue
                            age = now - os.path.getmtime(path)
                            if age > staging_retention_seconds:
                                import shutil as _shutil
                                _shutil.rmtree(path, ignore_errors=True)
                                staging_dirs_purged_count += 1
                                logging.info(
                                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                                    f'purged orphan staging dir, dir="{name}", age_seconds={int(age)}'
                                )
                    except Exception as e:
                        if os.path.isdir(path):
                            staging_dirs_purge_failures_count += 1
                        else:
                            archive_purge_failures_count += 1
                        logging.warning(
                            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                            f'failed to purge "{path}", exception="{str(e)}"'
                        )
            else:
                logging.debug(
                    f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                    f'diag dir does not exist yet, nothing to purge.'
                )
        except Exception as e:
            logging.error(
                f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, '
                f'support_diag purge task failed, exception="{str(e)}"'
            )

        global_results_dict[f"{task_name}"] = {
            "archives_purged_count": archives_purged_count,
            "archive_purge_failures_count": archive_purge_failures_count,
            "staging_dirs_purged_count": staging_dirs_purged_count,
            "staging_dirs_purge_failures_count": staging_dirs_purge_failures_count,
            "archive_retention_seconds": archive_retention_seconds,
            "staging_retention_seconds": staging_retention_seconds,
            "result": (
                f"{archives_purged_count} expired archives purged, "
                f"{archive_purge_failures_count} archive purge failures, "
                f"{staging_dirs_purged_count} orphan staging dirs purged, "
                f"{staging_dirs_purge_failures_count} staging purge failures"
            ),
        }

        logging.info(
            f'instance_id={instance_id}, task="{task_name}", task_instance_id={task_instance_id}, run_time="{round(time.time()-task_start, 3)}", task has terminated.'
        )

        #
        # End
        #

        # yield the results
        yield_record = {
            "_time": time.time(),
            "_raw": global_results_dict,
            "results": global_results_dict,
        }

        yield yield_record

        #
        # END
        #

        # end general task
        logging.info(
            f"instance_id={instance_id}, trackmegeneralhealthmanager has terminated, total_run_time={round(time.time() - global_start, 3)}"
        )


dispatch(HealthTracker, sys.argv, sys.stdin, sys.stdout, __name__)
