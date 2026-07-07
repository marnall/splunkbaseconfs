#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_licensing.py"
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
import os
import re
import sys
import time
import uuid
from collections import OrderedDict

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.licensing_user", "trackme_rest_api_licensing_user.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_get_version, trackme_getloglevel, trackme_parse_describe_flag

# import trackme licensing libs
from trackme_libs_licensing import (
    trackme_return_license_status_offline,
    trackme_return_license_status_developer,
    trackme_return_license_status_foundation_trial,
    trackme_check_trial_watermark,
    trackme_create_trial_watermark,
    trackme_check_developer_watermark,
    MAX_DEVELOPER_ACTIVATIONS,
)

# import trackme schema
from trackme_libs_schema import trackme_schema_format_version

# import Splunk libs
import splunklib.client as client

# import cryptolense
from licensing.models import *
from licensing.methods import Key, Helpers


class TrackMeHandlerLicensingRead_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerLicensingRead_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_licensing(self, request_info, **kwargs):
        response = {
            "resource_group_name": "licensing",
            "resource_group_desc": "Endpoints for the purposes of license management (read only operations)",
        }

        return {"payload": response, "status": 200}

    # get the license status
    def get_license_status(self, request_info, **kwargs):
        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        describe = trackme_parse_describe_flag(request_info)


        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint verifies the status of the license, it requires a GET call with no options:",
                "resource_desc": "Get the license status",
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/license_status" mode="get"',
            }
            return {"payload": response, "status": 200}

        # Get splunkd port
        splunkd_port = request_info.server_rest_port

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        #
        # get TrackMe version
        #

        # TrackMe version
        trackme_version = trackme_get_version(service)

        # get the schema_version_required
        schema_version_required = trackme_schema_format_version(trackme_version)

        # license limitations verifications: get the number of currently active tenants

        # Data collection
        collection_name = "kv_trackme_virtual_tenants"
        collection = service.kvstore[collection_name]

        # Get the current number of active tenants for licensing purposes
        query_string = {
            "tenant_status": "enabled",
        }

        try:
            vtenant_active_tenants = len(
                collection.data.query(query=json.dumps(query_string))
            )
        except Exception as e:
            vtenant_active_tenants = 0

        # create a list of enabled tenants
        vtenant_active_tenants_list = []

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            vtenant_active_tenants_list.append(kvrecord.get("tenant_id"))

        # Count the total number of active hybrid trackers
        hybrid_trackers = []
        splk_components = [
            "tenant_dsm_hybrid_objects",
            "tenant_dhm_hybrid_objects",
            "tenant_mhm_hybrid_objects",
        ]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                hybrid_record = kvrecord.get(splk_component)
                if hybrid_record:
                    hybrid_record = json.loads(hybrid_record)
                    hybrid_reports = hybrid_record.get("reports")
                    if hybrid_reports:
                        for report in hybrid_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                hybrid_trackers.append(report)

        # Count the number of active hybrid trackers for splk-dsm
        splk_dsm_hybrid_trackers = []
        splk_components = ["tenant_dsm_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                hybrid_record = kvrecord.get(splk_component)
                if hybrid_record:
                    hybrid_record = json.loads(hybrid_record)
                    hybrid_reports = hybrid_record.get("reports")
                    if hybrid_reports:
                        for report in hybrid_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                splk_dsm_hybrid_trackers.append(report)

        # Count the number of active hybrid trackers for splk-dhm
        splk_dhm_hybrid_trackers = []
        splk_components = ["tenant_dhm_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                hybrid_record = kvrecord.get(splk_component)
                if hybrid_record:
                    hybrid_record = json.loads(hybrid_record)
                    hybrid_reports = hybrid_record.get("reports")
                    if hybrid_reports:
                        for report in hybrid_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                splk_dhm_hybrid_trackers.append(report)

        # Count the number of active hybrid trackers for splk-mhm
        splk_mhm_hybrid_trackers = []
        splk_components = ["tenant_mhm_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                hybrid_record = kvrecord.get(splk_component)
                if hybrid_record:
                    hybrid_record = json.loads(hybrid_record)
                    hybrid_reports = hybrid_record.get("reports")
                    if hybrid_reports:
                        for report in hybrid_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                splk_mhm_hybrid_trackers.append(report)

        # Count the number of active flex trackers
        flex_trackers = []
        splk_components = ["tenant_flx_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                flex_tracker = kvrecord.get(splk_component)
                if flex_tracker:
                    flex_tracker = json.loads(flex_tracker)
                    flex_reports = flex_tracker.get("reports")
                    if flex_reports:
                        for report in flex_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                flex_trackers.append(report)

        # Count the number of active fqm trackers
        fqm_trackers = []
        splk_components = ["tenant_fqm_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                fqm_tracker = kvrecord.get(splk_component)
                if fqm_tracker:
                    fqm_tracker = json.loads(fqm_tracker)
                    fqm_reports = fqm_tracker.get("reports")
                    if fqm_reports:
                        for report in fqm_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                fqm_trackers.append(report)

        # Count the number of active wlk trackers
        wlk_trackers = []
        splk_components = ["tenant_wlk_hybrid_objects"]

        for kvrecord in collection.data.query(query=json.dumps(query_string)):
            for splk_component in splk_components:
                wlk_tracker = kvrecord.get(splk_component)
                if wlk_tracker:
                    wlk_tracker = json.loads(wlk_tracker)
                    wlk_reports = wlk_tracker.get("reports")
                    if wlk_reports:
                        for report in wlk_reports:
                            if re.search(r"_tracker_", report) and not re.search(
                                r"_abstract_|_wrapper_", report
                            ):
                                wlk_trackers.append(report)

        #
        # check license
        #

        try:
            collection_name = "kv_trackme_license_key"
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                kvrecord = collection.data.query()[0]
                key = kvrecord.get("_key")
                license_string = kvrecord.get("license_string")
                license_type = kvrecord.get("license_type")
                license_override_expiration_epoch = kvrecord.get(
                    "license_override_expiration_epoch"
                )

            except Exception as e:
                key = None

            if key:
                # if license is subscription based
                if license_type == "subscription":
                    logger.debug("check license from signature")
                    response = trackme_return_license_status_offline(license_string)

                    # get license_subscription_class
                    license_features = response.get("license_features")
                    license_subscription_class = None

                    try:
                        enterprise = license_features[0].get("enterprise")
                        if enterprise == "True":
                            enterprise = True
                        else:
                            enterprise = False
                    except Exception as e:
                        enterprise = False

                    try:
                        unlimited = license_features[0].get("unlimited")
                        if unlimited == "True":
                            unlimited = True
                        else:
                            unlimited = False
                    except Exception as e:
                        unlimited = False

                    try:
                        free_extended = license_features[0].get("free_extended")
                        if free_extended == "True":
                            free_extended = True
                        else:
                            free_extended = False
                    except Exception as e:
                        free_extended = False

                    try:
                        foundation = license_features[0].get("foundation")
                        if foundation == "True":
                            foundation = True
                        else:
                            foundation = False
                    except Exception as e:
                        foundation = False

                    try:
                        developer = license_features[0].get("developer")
                        developer = developer == "True"
                    except Exception as e:
                        developer = False

                    if unlimited:
                        license_subscription_class = "unlimited"
                    elif enterprise:
                        license_subscription_class = "enterprise"
                    elif developer:
                        license_subscription_class = "developer"
                    elif foundation:
                        license_subscription_class = "foundation"
                    elif free_extended:
                        license_subscription_class = "free_extended"
                    # in case we failed, this could only happen for an already registered license before we
                    # introduced the distinction between unlimited and enteprise
                    else:
                        license_subscription_class = "unlimited"

                    # add to response
                    response["license_subscription_class"] = license_subscription_class
                    # add to response
                    response["license_type"] = "subscription"
                    # add to response
                    response["license_read_only"] = False
                    # add to response
                    response["license_active_tenants"] = vtenant_active_tenants
                    # add to response
                    response["license_active_tenants_list"] = (
                        vtenant_active_tenants_list
                    )
                    # add to response
                    response["license_active_hybrid_trackers"] = len(hybrid_trackers)
                    # add to response
                    response["license_active_hybrid_trackers_list"] = hybrid_trackers

                    # dsm
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers"] = len(
                        splk_dsm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers_list"] = (
                        splk_dsm_hybrid_trackers
                    )

                    # dhm
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers"] = len(
                        splk_dhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers_list"] = (
                        splk_dhm_hybrid_trackers
                    )

                    # mhm
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers"] = len(
                        splk_mhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers_list"] = (
                        splk_mhm_hybrid_trackers
                    )

                    # flex
                    # add to response
                    response["license_active_flex_trackers"] = len(flex_trackers)
                    # add to response
                    response["license_active_flex_trackers_list"] = flex_trackers

                    # fqm
                    # add to response
                    response["license_active_fqm_trackers"] = len(fqm_trackers)
                    # add to response
                    response["license_active_fqm_trackers_list"] = fqm_trackers

                    # wlk
                    # add to response
                    response["license_active_wlk_trackers"] = len(wlk_trackers)
                    # add to response
                    response["license_active_wlk_trackers_list"] = wlk_trackers

                    # add TrackMe version & schema_version_required
                    response["trackme_version"] = trackme_version
                    response["schema_version_required"] = schema_version_required

                elif license_type == "trial":
                    logger.debug("check license from signature")
                    response = trackme_return_license_status_offline(license_string)
                    # add to response
                    response["license_type"] = "trial"
                    # add to response
                    response["license_read_only"] = False
                    # override expiration window if configured
                    if license_override_expiration_epoch:
                        try:
                            override_epoch = int(license_override_expiration_epoch)
                            time_before_expiration = round(override_epoch - time.time())
                            response["license_expiration"] = time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime(override_epoch)
                            )
                            response["license_expiration_countdown_sec"] = (
                                time_before_expiration
                            )
                            if time_before_expiration > 0:
                                response["action"] = "success"
                                response["license_is_valid"] = 1
                                response["message"] = "The license is valid"
                            else:
                                response["action"] = "failure"
                                response["license_is_valid"] = 0
                                response["message"] = "The license has expired"
                        except Exception as e:
                            logger.error(
                                f'failed to apply trial override expiration, exception="{str(e)}"'
                            )
                    # add to response
                    response["license_active_tenants"] = vtenant_active_tenants
                    # add to response
                    response["license_active_tenants_list"] = (
                        vtenant_active_tenants_list
                    )

                    # add to response
                    response["license_active_hybrid_trackers"] = len(hybrid_trackers)
                    # add to response
                    response["license_active_hybrid_trackers_list"] = hybrid_trackers

                    # dsm
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers"] = len(
                        splk_dsm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers_list"] = (
                        splk_dsm_hybrid_trackers
                    )

                    # dhm
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers"] = len(
                        splk_dhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers_list"] = (
                        splk_dhm_hybrid_trackers
                    )

                    # mhm
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers"] = len(
                        splk_mhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers_list"] = (
                        splk_mhm_hybrid_trackers
                    )

                    # flex
                    # add to response
                    response["license_active_flex_trackers"] = len(flex_trackers)
                    # add to response
                    response["license_active_flex_trackers_list"] = flex_trackers

                    # fqm
                    # add to response
                    response["license_active_fqm_trackers"] = len(fqm_trackers)
                    # add to response
                    response["license_active_fqm_trackers_list"] = fqm_trackers

                    # wlk
                    # add to response
                    response["license_active_wlk_trackers"] = len(wlk_trackers)
                    # add to response
                    response["license_active_wlk_trackers_list"] = wlk_trackers

                    # add TrackMe version & schema_version_required
                    response["trackme_version"] = trackme_version
                    response["schema_version_required"] = schema_version_required

                elif license_type == "developer":
                    logger.debug("check license from signature")
                    response = trackme_return_license_status_developer(license_string)
                    # add to response
                    response["license_type"] = "developer"
                    # When developer mode expires, enter read-only mode (same as foundation_trial)
                    response["license_read_only"] = response.get("license_is_valid") != 1

                    # developer activation usage info
                    response["developer_activations_used"] = 0
                    response["developer_activations_max"] = MAX_DEVELOPER_ACTIVATIONS
                    try:
                        dev_watermark_check = trackme_check_developer_watermark(service)
                        if dev_watermark_check["exists"] and dev_watermark_check["valid"]:
                            response["developer_activations_used"] = dev_watermark_check["watermark"].get("usage_count", 0)
                    except Exception as e:
                        logger.error(f'failed to read developer watermark for status, exception="{str(e)}"')

                    # add to response
                    response["license_active_tenants"] = vtenant_active_tenants
                    # add to response
                    response["license_active_tenants_list"] = (
                        vtenant_active_tenants_list
                    )
                    # add to response
                    response["license_active_hybrid_trackers"] = len(hybrid_trackers)
                    # add to response
                    response["license_active_hybrid_trackers_list"] = hybrid_trackers

                    # dsm
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers"] = len(
                        splk_dsm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers_list"] = (
                        splk_dsm_hybrid_trackers
                    )

                    # dhm
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers"] = len(
                        splk_dhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers_list"] = (
                        splk_dhm_hybrid_trackers
                    )

                    # mhm
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers"] = len(
                        splk_mhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers_list"] = (
                        splk_mhm_hybrid_trackers
                    )

                    # flex
                    # add to response
                    response["license_active_flex_trackers"] = len(flex_trackers)
                    # add to response
                    response["license_active_flex_trackers_list"] = flex_trackers

                    # fqm
                    # add to response
                    response["license_active_fqm_trackers"] = len(fqm_trackers)
                    # add to response
                    response["license_active_fqm_trackers_list"] = fqm_trackers

                    # wlk
                    # add to response
                    response["license_active_wlk_trackers"] = len(wlk_trackers)
                    # add to response
                    response["license_active_wlk_trackers_list"] = wlk_trackers

                    # add TrackMe version & schema_version_required
                    response["trackme_version"] = trackme_version
                    response["schema_version_required"] = schema_version_required

                elif license_type == "foundation_trial":
                    logger.debug("check license from signature")
                    response = trackme_return_license_status_foundation_trial(license_string)
                    # add to response
                    response["license_type"] = "foundation_trial"
                    # add to response
                    response["license_subscription_class"] = "foundation"
                    # add to response
                    response["license_read_only"] = response.get("license_is_valid") != 1
                    # add to response
                    response["license_active_tenants"] = vtenant_active_tenants
                    # add to response
                    response["license_active_tenants_list"] = vtenant_active_tenants_list
                    # add to response
                    response["license_active_hybrid_trackers"] = len(hybrid_trackers)
                    # add to response
                    response["license_active_hybrid_trackers_list"] = hybrid_trackers

                    # dsm
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers"] = len(
                        splk_dsm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dsm_hybrid_trackers_list"] = (
                        splk_dsm_hybrid_trackers
                    )

                    # dhm
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers"] = len(
                        splk_dhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_dhm_hybrid_trackers_list"] = (
                        splk_dhm_hybrid_trackers
                    )

                    # mhm
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers"] = len(
                        splk_mhm_hybrid_trackers
                    )
                    # add to response
                    response["license_active_splk_mhm_hybrid_trackers_list"] = (
                        splk_mhm_hybrid_trackers
                    )

                    # flex
                    # add to response
                    response["license_active_flex_trackers"] = len(flex_trackers)
                    # add to response
                    response["license_active_flex_trackers_list"] = flex_trackers

                    # fqm
                    # add to response
                    response["license_active_fqm_trackers"] = len(fqm_trackers)
                    # add to response
                    response["license_active_fqm_trackers_list"] = fqm_trackers

                    # wlk
                    # add to response
                    response["license_active_wlk_trackers"] = len(wlk_trackers)
                    # add to response
                    response["license_active_wlk_trackers_list"] = wlk_trackers

                    # add TrackMe version & schema_version_required
                    response["trackme_version"] = trackme_version
                    response["schema_version_required"] = schema_version_required

                    # Backfill watermark for existing installs upgrading to new version
                    # If no watermark exists yet, create one using the current trial's data
                    try:
                        watermark_check = trackme_check_trial_watermark(service)
                        if not watermark_check["exists"]:
                            # Extract the current trial expiry from the license_string
                            license_data = json.loads(license_string)
                            current_expires = license_data.get("expires", 0)
                            # Approximate the original creation time (expires - 90 days)
                            current_created = int(current_expires) - 7776000
                            trackme_create_trial_watermark(
                                request_info.server_rest_uri,
                                request_info.system_authtoken,
                                current_created,
                                int(current_expires),
                            )
                            logger.info(
                                "foundation trial watermark backfilled for existing install"
                            )
                    except Exception as e:
                        logger.error(
                            f'failed to backfill foundation trial watermark, exception="{str(e)}"'
                        )

                    # developer activation usage info (visible before enabling developer mode)
                    response["developer_activations_used"] = 0
                    response["developer_activations_max"] = MAX_DEVELOPER_ACTIVATIONS
                    try:
                        dev_watermark_check = trackme_check_developer_watermark(service)
                        if dev_watermark_check["exists"] and dev_watermark_check["valid"]:
                            response["developer_activations_used"] = dev_watermark_check["watermark"].get("usage_count", 0)
                    except Exception as e:
                        logger.error(f'failed to read developer watermark for status, exception="{str(e)}"')

                return {"payload": response, "status": 200}

            else:
                if schema_version_required >= 2306:
                    try:
                        # Check if a foundation trial watermark already exists.
                        # This prevents trial reset abuse: if a watermark exists,
                        # the user has already used their trial and we create an
                        # EXPIRED record instead of a fresh 90-day trial.
                        watermark_check = trackme_check_trial_watermark(service)

                        if watermark_check["exists"]:
                            # Trial was already used (regardless of HMAC validity --
                            # tampering also counts as "already used", fail-closed)
                            logger.info(
                                "foundation trial watermark found, trial was already used - "
                                "creating expired foundation trial record"
                            )

                            # Retrieve original expiry from watermark if HMAC is valid,
                            # otherwise use epoch 0 (clearly expired)
                            if watermark_check["valid"]:
                                original_expires = watermark_check["watermark"].get(
                                    "trial_expires_epoch", 0
                                )
                            else:
                                logger.warning(
                                    "watermark HMAC invalid (possible tampering), forcing expired trial"
                                )
                                original_expires = 0

                            foundation_record = {
                                "license_string": json.dumps(
                                    {
                                        "uuid": str(uuid.uuid4()),
                                        "expires": int(original_expires),
                                    },
                                    indent=2,
                                ),
                                "license_type": "foundation_trial",
                            }
                            collection.data.insert(json.dumps(foundation_record))

                            response = trackme_return_license_status_foundation_trial(
                                foundation_record.get("license_string")
                            )
                            response["license_type"] = "foundation_trial"
                            response["license_subscription_class"] = "foundation"
                            response["license_read_only"] = (
                                response.get("license_is_valid") != 1
                            )

                        else:
                            # No watermark found -- this is a genuine first install.
                            # Create a fresh 90-day Foundation trial.
                            trial_created_epoch = int(time.time())
                            trial_expires_epoch = trial_created_epoch + 7776000  # 90 days

                            # Create the watermark FIRST to remember this trial was granted.
                            # This ensures the anti-abuse mechanism is in place before the
                            # trial record is committed to KVstore.
                            watermark_result = trackme_create_trial_watermark(
                                request_info.server_rest_uri,
                                request_info.system_authtoken,
                                trial_created_epoch,
                                trial_expires_epoch,
                            )
                            if watermark_result is None:
                                logger.warning(
                                    "failed to create trial watermark, "
                                    "trial will be created but anti-abuse protection may be incomplete"
                                )

                            foundation_record = {
                                "license_string": json.dumps(
                                    {
                                        "uuid": str(uuid.uuid4()),
                                        "expires": trial_expires_epoch,
                                    },
                                    indent=2,
                                ),
                                "license_type": "foundation_trial",
                            }
                            logger.info(
                                "no license record found and no watermark, "
                                "creating Foundation trial license record"
                            )

                            collection.data.insert(json.dumps(foundation_record))

                            response = trackme_return_license_status_foundation_trial(
                                foundation_record.get("license_string")
                            )
                            response["license_type"] = "foundation_trial"
                            response["license_subscription_class"] = "foundation"
                            response["license_read_only"] = (
                                response.get("license_is_valid") != 1
                            )

                    except Exception as e:
                        logger.error(
                            f'failed to create foundation trial record, exception="{str(e)}"'
                        )
                        response = None
                else:
                    response = None

                if response is None:
                    response = {
                        "action": "success",
                        "license_is_valid": 0,
                        "message": "This TrackMe deployment is currently unregistered, and running in free limited edition mode",
                        "license_read_only": False,
                    }

                # add to response
                response["license_active_tenants"] = vtenant_active_tenants
                # add to response
                response["license_active_tenants_list"] = vtenant_active_tenants_list
                # add to response
                response["license_active_hybrid_trackers"] = len(hybrid_trackers)
                # add to response
                response["license_active_hybrid_trackers_list"] = hybrid_trackers
                # add to response
                response["license_active_splk_dsm_hybrid_trackers"] = len(
                    splk_dsm_hybrid_trackers
                )
                # add to response
                response["license_active_splk_dsm_hybrid_trackers_list"] = (
                    splk_dsm_hybrid_trackers
                )
                # add to response
                response["license_active_splk_dhm_hybrid_trackers"] = len(
                    splk_dhm_hybrid_trackers
                )
                # add to response
                response["license_active_splk_dhm_hybrid_trackers_list"] = (
                    splk_dhm_hybrid_trackers
                )
                # add to response
                response["license_active_splk_mhm_hybrid_trackers"] = len(
                    splk_mhm_hybrid_trackers
                )
                # add to response
                response["license_active_splk_mhm_hybrid_trackers_list"] = (
                    splk_mhm_hybrid_trackers
                )

                # flex
                # add to response
                response["license_active_flex_trackers"] = len(flex_trackers)
                # add to response
                response["license_active_flex_trackers_list"] = flex_trackers

                # fqm
                # add to response
                response["license_active_fqm_trackers"] = len(fqm_trackers)
                # add to response
                response["license_active_fqm_trackers_list"] = fqm_trackers

                # wlk
                # add to response
                response["license_active_wlk_trackers"] = len(wlk_trackers)
                # add to response
                response["license_active_wlk_trackers_list"] = wlk_trackers

                # add TrackMe version & schema_version_required
                response["trackme_version"] = trackme_version
                response["schema_version_required"] = schema_version_required

                # developer activation usage info (visible before enabling developer mode)
                response["developer_activations_used"] = 0
                response["developer_activations_max"] = MAX_DEVELOPER_ACTIVATIONS
                try:
                    dev_watermark_check = trackme_check_developer_watermark(service)
                    if dev_watermark_check["exists"] and dev_watermark_check["valid"]:
                        response["developer_activations_used"] = dev_watermark_check["watermark"].get("usage_count", 0)
                except Exception as e:
                    logger.error(f'failed to read developer watermark for status, exception="{str(e)}"')

                return {"payload": response, "status": 200}

        except Exception as e:
            response = {
                "action": "failure",
                "message": "An exception was encountered while checking the license status, license status could not be verified.",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}
