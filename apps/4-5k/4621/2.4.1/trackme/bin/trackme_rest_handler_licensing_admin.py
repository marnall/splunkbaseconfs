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
    "trackme.rest.licensing_admin", "trackme_rest_api_licensing_admin.log"
)


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_getloglevel, trackme_parse_describe_flag, trackme_audit_event

# import trackme licensing libs
from trackme_libs_licensing import (
    trackme_return_license_status,
    trackme_start_trial,
    trackme_return_license_status_offline,
    trackme_clear_trial_watermark,
    trackme_check_developer_watermark,
    trackme_create_or_update_developer_watermark,
    trackme_clear_developer_watermark,
    MAX_DEVELOPER_ACTIVATIONS,
)

# import Splunk libs
import splunklib.client as client

# import global cache libs
from trackme_libs_global_cache import global_cache_invalidate

# import cryptolense
from licensing.models import *
from licensing.methods import Key, Helpers


class TrackMeHandlerLicensingAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerLicensingAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_licensing(self, request_info, **kwargs):
        response = {
            "resource_group_name": "licensing",
            "resource_group_desc": "Endpoints for the purposes of license management (admin operations)",
        }

        return {"payload": response, "status": 200}

    # set the license key
    def post_set_license(self, request_info, **kwargs):
        describe = False
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = False

        if not describe:
            license_key = resp_dict["license_key"]
            update_comment = resp_dict.get("update_comment") or "API update"

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint sets the license key for this deployment, it requires a POST call with the no options:",
                "resource_desc": "Get the license status",
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/admin/license_key" mode="post"',
                "options": [
                    {
                        "license_key": "The license key to be set",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
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

        try:
            # check the license validity first
            response = trackme_return_license_status(license_key)

            if int(response.get("license_is_valid")) == 1:
                collection_name = "kv_trackme_license_key"
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    kvrecords = collection.data.query()

                except Exception as e:
                    kvrecords = None

                if kvrecords:
                    # Remove any record in the KV
                    for kvrecord in kvrecords:
                        key = kvrecord.get("_key")
                        logger.info(
                            f'purging KVrecord="{json.dumps(kvrecord, indent=2)}"'
                        )
                        collection.data.delete(json.dumps({"_key": key}))

                # set
                logger.info("attempting to set the license key KVstore record")
                collection.data.insert(
                    json.dumps(
                        {
                            "_key": license_key,
                            "license_string": response.get("license_string"),
                            "license_type": "subscription",
                        }
                    )
                )

                # Clear any stale Foundation trial watermark now that a valid
                # subscription is registered. The watermark is no longer needed
                # and leaving it could cause confusion if the KV record is ever
                # lost (the stale watermark would recreate an expired trial
                # instead of the clean "unregistered" state).
                trackme_clear_trial_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                )

                # Also clear the developer watermark (same reasoning)
                trackme_clear_developer_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                )

                # log
                logger.info(
                    f'license set key operation terminated, response="{json.dumps(response, indent=2)}"'
                )

                # Invalidate global license cache so all tenants pick up the change immediately
                global_cache_invalidate(service, "license_cache")

                # Audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "set license key",
                        "license",
                        "licensing",
                        json.dumps(
                            {
                                "license_type": "subscription",
                                "license_is_valid": response.get("license_is_valid"),
                            },
                            default=str,
                        ),
                        f'License key was registered successfully by user="{request_info.user}"',
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'function=post_set_license, step="audit", exception="{str(audit_e)}"'
                    )

                # return
                return {"payload": response, "status": 200}

            else:
                # return
                return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "message": "An exception was encountered while attempting to setup the license key",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}

    # Upload license file
    def post_upload_license_file(self, request_info, **kwargs):
        describe = False
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
        else:
            describe = False

        if not describe:
            license_file = resp_dict["license_file"]
            update_comment = resp_dict.get("update_comment") or "API update"

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint verifies and upload a license file, it requires a POST call with the following options:",
                "resource_desc": "Upload license file",
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/admin/upload_license_file" mode="post"',
                "options": [
                    {
                        "license_file": "The license file content",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
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

        try:
            # check the license validity first
            response = trackme_return_license_status_offline(license_file)

            if int(response.get("license_is_valid")) == 1:
                collection_name = "kv_trackme_license_key"
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    kvrecords = collection.data.query()

                except Exception as e:
                    kvrecords = None

                if kvrecords:
                    # Remove any record in the KV
                    for kvrecord in kvrecords:
                        key = kvrecord.get("_key")
                        logger.info(
                            f'purging KVrecord="{json.dumps(kvrecord, indent=2)}"'
                        )
                        collection.data.delete(json.dumps({"_key": key}))

                # set
                logger.info("attempting to set the license key KVstore record")
                collection.data.insert(
                    json.dumps(
                        {
                            "license_string": response.get("license_string"),
                            "license_type": "subscription",
                        }
                    )
                )

                # Clear any stale Foundation trial watermark now that a valid
                # subscription is registered.
                trackme_clear_trial_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                )

                # Also clear the developer watermark (same reasoning)
                trackme_clear_developer_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                )

                # log
                logger.info(
                    f'license set key operation terminated, response="{json.dumps(response, indent=2)}"'
                )

                # Invalidate global license cache so all tenants pick up the change immediately
                global_cache_invalidate(service, "license_cache")

                # Audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "upload license file",
                        "license",
                        "licensing",
                        json.dumps(
                            {
                                "license_type": "subscription",
                                "license_is_valid": response.get("license_is_valid"),
                            },
                            default=str,
                        ),
                        f'License file was uploaded successfully by user="{request_info.user}"',
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'function=post_upload_license_file, step="audit", exception="{str(audit_e)}"'
                    )

                # return
                return {"payload": response, "status": 200}

            else:
                # return
                return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "message": "An exception was encountered while attempting to setup the license key",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}

    # Start trial license
    def post_start_trial(self, request_info, **kwargs):
        describe = False
        company_name = None
        email_contact = None
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            # Extract company_name and email_contact for trial request notes
            try:
                company_name = resp_dict.get("company_name")
                email_contact = resp_dict.get("email_contact")
                update_comment = resp_dict.get("update_comment") or "API update"
            except Exception as e:
                pass
        else:
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint starts a trial license period for this deployment, it requires a POST call with optional company_name and email_contact parameters:",
                "resource_desc": "Starts a Trial period",
                "options": {
                    "company_name": "The company name requesting the trial (optional, added as note to license)",
                    "email_contact": "The email contact for the trial request (optional, added as note to license)",
                    "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                },
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/admin/start_trial" mode="post" body="{\'company_name\': \'Acme Corp\', \'email_contact\': \'user@acme.com\'}"',
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

        try:
            # check the license validity first
            response = trackme_start_trial(request_info, company_name=company_name, email_contact=email_contact)

            logger.info(f'response="{response}"')

            if int(response.get("license_is_valid")) == 1:
                collection_name = "kv_trackme_license_key"
                collection = service.kvstore[collection_name]

                # Get the current record
                # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

                try:
                    kvrecords = collection.data.query()

                except Exception as e:
                    kvrecords = None

                if kvrecords:
                    # Remove any record in the KV
                    for kvrecord in kvrecords:
                        key = kvrecord.get("_key")
                        logger.info(
                            f'purging KVrecord="{json.dumps(kvrecord, indent=2)}"'
                        )
                        collection.data.delete(json.dumps({"_key": key}))

                # set
                logger.info("attempting to set the Trial license key KVstore record")
                collection.data.insert(
                    json.dumps(
                        {
                            "_key": response.get("trial_key"),
                            "license_string": response.get("license_string"),
                            "license_type": "trial",
                            "license_override_expiration_epoch": int(time.time())
                            + 7776000,
                        }
                    )
                )

                # log
                logger.info(
                    f'license Trial operation terminated, response="{json.dumps(response, indent=2)}"'
                )

                # Invalidate global license cache so all tenants pick up the change immediately
                global_cache_invalidate(service, "license_cache")

                # Audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "start trial",
                        "license",
                        "licensing",
                        json.dumps(
                            {
                                "license_type": "trial",
                                "company_name": company_name,
                                "email_contact": email_contact,
                            },
                            default=str,
                        ),
                        f'Trial license was started successfully by user="{request_info.user}"',
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'function=post_start_trial, step="audit", exception="{str(audit_e)}"'
                    )

                # return
                if response.get("action") == "success":
                    return {"payload": response, "status": 200}

                else:
                    return {"payload": response, "status": 500}

            else:
                # return
                return {"payload": response, "status": 500}

        except Exception as e:
            error_message = str(e)
            # Extract the actual error from nested exception messages
            # Format is: 'An exception occurred while attempting to generate the trial license, exception="<error>"'
            if 'exception="' in error_message:
                # Extract the inner exception message and remove surrounding quotes
                error_message = error_message.split('exception="')[-1].rstrip('"').strip()
            
            response = {
                "action": "failure",
                "message": f"Failed to generate Trial license: {error_message}",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}

    # Enable developer mode
    def post_enable_developer_license(self, request_info, **kwargs):
        describe = False
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint enables the developer mode for this deployment, it requires a POST call with no options:",
                "resource_desc": "Enable the developer mode license",
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/admin/enable_developer_license" mode="post"',
                "options": [
                    {
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
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

        try:
            collection_name = "kv_trackme_license_key"
            collection = service.kvstore[collection_name]

            # Check the developer watermark to enforce the activation limit
            watermark_check = trackme_check_developer_watermark(service)
            usage_count = 0

            if watermark_check["exists"]:
                if not watermark_check["valid"]:
                    logger.warning(
                        "developer watermark HMAC invalid (tampered) - denying activation"
                    )
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "Developer mode activation denied due to a watermark integrity issue. "
                            "Please contact TrackMe support for a named developer license.",
                        },
                        "status": 409,
                    }

                usage_count = watermark_check["watermark"].get("usage_count", 0)
                if usage_count >= MAX_DEVELOPER_ACTIVATIONS:
                    logger.warning(
                        f"developer mode activation denied: usage_count={usage_count} "
                        f"has reached the maximum of {MAX_DEVELOPER_ACTIVATIONS}"
                    )
                    return {
                        "payload": {
                            "action": "failure",
                            "message": f"You have reached the maximum of {MAX_DEVELOPER_ACTIVATIONS} "
                            "developer mode activations. Please contact TrackMe to obtain "
                            "a named developer license for continued developer access.",
                        },
                        "status": 409,
                    }

            new_usage_count = usage_count + 1
            now_epoch = int(time.time())
            expires_epoch = now_epoch + 2592000

            # Write the watermark BEFORE inserting the KV record
            watermark_result = trackme_create_or_update_developer_watermark(
                request_info.server_rest_uri,
                request_info.system_authtoken,
                new_usage_count,
                now_epoch,
                expires_epoch,
            )
            if not watermark_result:
                logger.error(
                    "developer mode activation aborted: failed to create/update watermark"
                )
                return {
                    "payload": {
                        "action": "failure",
                        "message": "Failed to update the developer watermark. "
                        "Please retry the operation or contact TrackMe support.",
                    },
                    "status": 500,
                }

            # Purge existing KV records and insert the new developer license.
            # Both operations are wrapped so that any failure triggers a
            # watermark rollback to avoid permanently consuming an activation.
            def _rollback_watermark():
                logger.warning(
                    "rolling back developer watermark to previous usage_count"
                )
                rb = trackme_create_or_update_developer_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                    usage_count,
                    watermark_result.get("last_activated_epoch", now_epoch),
                    watermark_result.get("last_expires_epoch", expires_epoch),
                )
                if not rb:
                    logger.error(
                        "developer watermark rollback FAILED — activation may be permanently consumed"
                    )

            try:
                kvrecords = collection.data.query()
            except Exception as e:
                kvrecords = None

            try:
                if kvrecords:
                    for kvrecord in kvrecords:
                        key = kvrecord.get("_key")
                        logger.info(f'purging KVrecord="{json.dumps(kvrecord, indent=2)}"')
                        collection.data.delete(json.dumps({"_key": key}))

                logger.info(
                    "attempting to set the developer mode license key KVstore record"
                )

                new_record = {
                    "license_string": json.dumps(
                        {
                            "uuid": str(uuid.uuid4()),
                            "expires": expires_epoch,
                        },
                        indent=2,
                    ),
                    "license_type": "developer",
                }

                collection.data.insert(json.dumps(new_record))
                response = {
                    "action": "success",
                    "license_string": new_record.get("license_string"),
                    "licence_type": new_record.get("license_type"),
                    "developer_activations_used": new_usage_count,
                    "developer_activations_max": MAX_DEVELOPER_ACTIVATIONS,
                }

            except Exception as e:
                _rollback_watermark()
                response = {
                    "action": "failure",
                    "message": "Failed to update the KVstore developer license record. "
                    "The activation has been rolled back. Please retry.",
                    "exception": str(e),
                }

            logger.info(
                f'license developer operation terminated, response="{json.dumps(response, indent=2)}"'
            )

            if response.get("action") == "success":
                # Invalidate global license cache so all tenants pick up the change immediately
                global_cache_invalidate(service, "license_cache")

                # Audit
                try:
                    trackme_audit_event(
                        request_info.system_authtoken,
                        request_info.server_rest_uri,
                        "all",
                        request_info.user,
                        "success",
                        "enable developer license",
                        "license",
                        "licensing",
                        json.dumps(
                            {
                                "license_type": "developer",
                                "developer_activations_used": new_usage_count,
                                "developer_activations_max": MAX_DEVELOPER_ACTIVATIONS,
                            },
                            default=str,
                        ),
                        f'Developer license was enabled successfully by user="{request_info.user}"',
                        str(update_comment),
                    )
                except Exception as audit_e:
                    logger.warning(
                        f'function=post_enable_developer_license, step="audit", exception="{str(audit_e)}"'
                    )

                return {"payload": response, "status": 200}
            else:
                return {"payload": response, "status": 500}

        except Exception as e:
            response = {
                "action": "failure",
                "message": "An exception was encountered while attempting to enable the developer license",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}

    # Reset licensing
    def post_reset_license(self, request_info, **kwargs):
        describe = False
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint resets the current license registration, it requires a POST call with no options:",
                "resource_desc": "Enable the developer mode license",
                "resource_spl_example": '| trackme url="/services/trackme/v2/licensing/admin/reset_license" mode="post"',
                "options": [
                    {
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
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

        try:
            collection_name = "kv_trackme_license_key"
            collection = service.kvstore[collection_name]

            # Get the current record
            # Notes: the record is returned as an array, as we search for a specific record, we expect one record only

            try:
                kvrecords = collection.data.query()

            except Exception as e:
                kvrecords = None

            # Check current license type before allowing reset
            # Reset is not permitted for foundation_trial or developer license types
            if kvrecords:
                for kvrecord in kvrecords:
                    current_license_type = kvrecord.get("license_type")
                    if current_license_type in ("foundation_trial", "developer"):
                        logger.warning(
                            f'reset license operation refused: current license type is "{current_license_type}"'
                        )
                        return {
                            "payload": {
                                "action": "failure",
                                "message": f"Reset is not permitted when the current license type is '{current_license_type}'. "
                                "The reset function is only available for subscription-based licenses. "
                                "If you need assistance, please contact TrackMe support.",
                            },
                            "status": 409,
                        }

            if kvrecords:
                # Clear the trial watermark BEFORE deleting KV records.
                # If the watermark clear fails, abort the reset so the user
                # can retry -- otherwise the KV would be gone but a stale
                # watermark would recreate an expired foundation_trial on
                # the next license check, locking the user out of the clean
                # "unregistered" state.
                # This is inside the `if kvrecords:` block to ensure we only
                # clear the watermark when a valid subscription license exists.
                # If kvrecords is empty (e.g., KV record manually deleted),
                # the license-type guard above was never evaluated, so we must
                # NOT clear the watermark to prevent abuse.
                watermark_cleared = trackme_clear_trial_watermark(
                    request_info.server_rest_uri,
                    request_info.system_authtoken,
                )
                if not watermark_cleared:
                    logger.error(
                        "reset license operation aborted: failed to clear the trial watermark"
                    )
                    return {
                        "payload": {
                            "action": "failure",
                            "message": "Failed to clear the trial watermark. "
                            "The license reset was aborted to prevent an inconsistent state. "
                            "Please retry the operation or contact TrackMe support.",
                        },
                        "status": 500,
                    }

                # Remove any record in the KV
                for kvrecord in kvrecords:
                    key = kvrecord.get("_key")
                    logger.info(f'purging KVrecord="{json.dumps(kvrecord, indent=2)}"')
                    collection.data.delete(json.dumps({"_key": key}))

            # log
            logger.info("reset license operation terminated")

            # Invalidate global license cache so all tenants pick up the change immediately
            global_cache_invalidate(service, "license_cache")

            # Audit
            try:
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    request_info.user,
                    "success",
                    "reset license",
                    "license",
                    "licensing",
                    json.dumps(
                        {"records_purged": len(kvrecords or [])}, default=str
                    ),
                    f'License registration was reset successfully by user="{request_info.user}"',
                    str(update_comment),
                )
            except Exception as audit_e:
                logger.warning(
                    f'function=post_reset_license, step="audit", exception="{str(audit_e)}"'
                )

            return {
                "payload": {
                    "action": "success",
                },
                "status": 200,
            }

        except Exception as e:
            response = {
                "action": "failure",
                "message": "An exception was encountered while attempting to reset the current license registration",
                "exception": str(e),
            }

            return {"payload": response, "status": 500}
