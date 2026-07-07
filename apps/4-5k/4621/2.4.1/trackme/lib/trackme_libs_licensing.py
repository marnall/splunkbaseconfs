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

import os
import sys
import requests
import re
import json
import time
import datetime
import logging
import uuid
import hashlib
import hmac as hmac_module
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append lib
sys.path.append(os.path.join(splunkhome, "etc", "apps", "trackme", "lib"))
from trackme_libs_logging import get_effective_logger

# import cryptolense
from licensing.models import *
from licensing.methods import Key, Helpers

# logging:
# To avoid overriding logging destination of callers, the libs will not set on purpose any logging definition
# and rely on callers themselves


def trackme_check_license(server_rest_uri, session_key, system_authtoken=None):
    # build header and target
    auth_token = system_authtoken or session_key
    header = {
        "Authorization": f"Splunk {auth_token}",
        "Content-Type": "application/json",
    }
    target_url = f"{server_rest_uri}/services/trackme/v2/licensing/license_status"

    try:
        response = requests.get(
            target_url,
            headers=header,
            verify=False,
            timeout=600,
        )
        return json.loads(response.text)

    except Exception as e:
        raise Exception(
            f'An exception was encountered while attempting to verify the license status, exception="{str(e)}"'
        )


def trackme_return_license_status(license_key):
    # Get the RSA pub key
    with open(
        os.path.join(
            splunkhome, "etc", "apps", "trackme", "lib", "licensing", "trackme_rsa.pub"
        ),
        "r",
    ) as f:
        for line in f:
            RSAPubKey = line
            break

    # Get the public access token
    with open(
        os.path.join(
            splunkhome,
            "etc",
            "apps",
            "trackme",
            "lib",
            "licensing",
            "trackme_token.pub",
        ),
        "r",
    ) as f:
        for line in f:
            auth = line
            break

    try:
        result = Key.activate(
            token=auth,
            rsa_pub_key=RSAPubKey,
            product_id=18301,
            key=license_key,
            machine_code="",
        )

        response = {}

        action = None
        message = None
        license_is_valid = 0
        license_expiration = None
        license_features = []
        license_string = None

        if result[0] == None:
            action = "failure"
            license_is_valid = 0
            message = str(result[1])

        else:
            license_key = result[0]
            license_expiration = str(license_key.expires)
            license_features.append(
                {
                    "time_limit": str(license_key.f1),
                    "trial": str(license_key.f2),
                    "enterprise": str(license_key.f3),
                    "unlimited": str(license_key.f4),
                    "free_extended": str(license_key.f5),
                    "foundation": str(license_key.f6),
                    "developer": str(license_key.f7),
                }
            )
            license_string = result[0].save_as_string()

            # get the remaining time in seconds
            expiration_dt = datetime.datetime.strptime(
                license_expiration, "%Y-%m-%d %H:%M:%S"
            )
            license_expiration_epoch = round(expiration_dt.timestamp())
            time_before_expiration = round(license_expiration_epoch - time.time())
            get_effective_logger().debug(f'license_expiration_epoch="{license_expiration_epoch}"')
            get_effective_logger().debug(f'time_before_expiration="{time_before_expiration}"')

            # the license has expired
            if not time_before_expiration > 0:
                action = "failure"
                license_is_valid = 0
                message = "The license has expired"

            else:
                action = "success"
                license_is_valid = 1
                message = "The license is valid"

        response = {
            "action": action,
            "license_is_valid": license_is_valid,
            "message": message,
            "license_expiration": license_expiration,
            "license_expiration_countdown_sec": time_before_expiration,
            "license_features": license_features,
            "license_string": license_string,
        }

        get_effective_logger().debug(f'response="{json.dumps(response, indent=2)}"')
        return response

    except Exception as e:
        get_effective_logger().error(
            f'An exception occurred while attempting to verify the license status, exception="{str(e)}"'
        )
        return response


def trackme_return_license_status_offline(license_string):
    # Get the RSA pub key
    with open(
        os.path.join(
            splunkhome, "etc", "apps", "trackme", "lib", "licensing", "trackme_rsa.pub"
        ),
        "r",
    ) as f:
        for line in f:
            RSAPubKey = line
            break

    try:
        # log
        get_effective_logger().debug(f'Verifying license from KVstore record="{license_string}"')

        # get license key
        license_key = LicenseKey.load_from_string(RSAPubKey, license_string)

        # init
        response = {}
        action = None
        message = None
        license_is_valid = 0
        license_expiration = None
        license_features = []

        if license_key == None:
            action = "failure"
            license_is_valid = 0
            message = "This license is not valid"
            license_string = None

        else:
            license_expiration = str(license_key.expires)
            license_features.append(
                {
                    "time_limit": str(license_key.f1),
                    "trial": str(license_key.f2),
                    "enterprise": str(license_key.f3),
                    "unlimited": str(license_key.f4),
                    "free_extended": str(license_key.f5),
                    "foundation": str(license_key.f6),
                    "developer": str(license_key.f7),
                }
            )
            license_string = license_key.save_as_string()

            # get the remaining time in seconds
            expiration_dt = datetime.datetime.strptime(
                license_expiration, "%Y-%m-%d %H:%M:%S"
            )
            license_expiration_epoch = round(expiration_dt.timestamp())
            time_before_expiration = round(license_expiration_epoch - time.time())
            get_effective_logger().debug(f'license_expiration_epoch="{license_expiration_epoch}"')
            get_effective_logger().debug(f'time_before_expiration="{time_before_expiration}"')

            # the license has expired
            if not time_before_expiration > 0:
                action = "failure"
                license_is_valid = 0
                message = "The license has expired"

            else:
                action = "success"
                license_is_valid = 1
                message = "The license is valid"

        response = {
            "action": action,
            "license_is_valid": license_is_valid,
            "message": message,
            "license_expiration": license_expiration,
            "license_expiration_countdown_sec": time_before_expiration,
            "license_features": license_features,
            "license_string": license_string,
        }

        get_effective_logger().debug(f'response="{json.dumps(response, indent=2)}"')
        return response

    except Exception as e:
        get_effective_logger().error(
            f'An exception occurred while attempting to verify the license status, exception="{str(e)}"'
        )
        return response


def trackme_return_license_status_developer(license_string):
    try:
        # load as a dict
        license_string = json.loads(license_string)

        # log
        get_effective_logger().debug(f'Verifying license from KVstore record="{license_string}"')

        # init
        response = {}
        action = None
        message = None
        license_is_valid = 0
        license_expiration = None
        license_features = []

        # get the remaining time in seconds
        license_expiration_epoch = license_string.get("expires")
        time_before_expiration = round(license_expiration_epoch - time.time())
        get_effective_logger().debug(f'license_expiration_epoch="{license_expiration_epoch}"')
        get_effective_logger().debug(f'time_before_expiration="{time_before_expiration}"')

        # convert
        license_expiration = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(license_expiration_epoch)
        )

        # the license has expired
        if not time_before_expiration > 0:
            action = "failure"
            license_is_valid = 0
            message = "The license has expired"

        else:
            action = "success"
            license_is_valid = 1
            message = "The license is valid"

        response = {
            "action": action,
            "license_is_valid": license_is_valid,
            "message": message,
            "license_expiration": license_expiration,
            "license_expiration_countdown_sec": time_before_expiration,
            "license_features": license_features,
            "license_string": json.dumps(license_string),
        }

        get_effective_logger().debug(f'response="{json.dumps(response, indent=2)}"')
        return response

    except Exception as e:
        get_effective_logger().error(
            f'An exception occurred while attempting to verify the license status, exception="{str(e)}"'
        )
        return response


def trackme_return_license_status_foundation_trial(license_string):
    response = {}
    try:
        # load as a dict
        license_string = json.loads(license_string)

        # log
        get_effective_logger().debug(f'Verifying license from KVstore record="{license_string}"')

        # init
        response = {}
        action = None
        message = None
        license_is_valid = 0
        license_expiration = None
        license_features = []

        # get the remaining time in seconds
        license_expiration_epoch = license_string.get("expires")
        time_before_expiration = round(license_expiration_epoch - time.time())
        get_effective_logger().debug(f'license_expiration_epoch="{license_expiration_epoch}"')
        get_effective_logger().debug(f'time_before_expiration="{time_before_expiration}"')

        # convert
        license_expiration = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(license_expiration_epoch)
        )

        # the license has expired
        if not time_before_expiration > 0:
            action = "failure"
            license_is_valid = 0
            message = "The license has expired"

        else:
            action = "success"
            license_is_valid = 1
            message = "The license is valid"

        license_features.append(
            {
                "time_limit": "False",
                "trial": "False",
                "enterprise": "False",
                "unlimited": "False",
                "free_extended": "False",
                "foundation": "True",
            }
        )

        response = {
            "action": action,
            "license_is_valid": license_is_valid,
            "message": message,
            "license_expiration": license_expiration,
            "license_expiration_countdown_sec": time_before_expiration,
            "license_features": license_features,
            "license_string": json.dumps(license_string),
        }

        get_effective_logger().debug(f'response="{json.dumps(response, indent=2)}"')
        return response

    except Exception as e:
        get_effective_logger().error(
            f'An exception occurred while attempting to verify the license status, exception="{str(e)}"'
        )
        return response


#
# Foundation trial watermark functions
#
# These functions manage a persistent watermark stored in trackme_settings.conf
# to prevent Foundation Edition trial license reset abuse. The watermark is
# created when a trial is first granted and persists across KVstore resets.
#

# Embedded salt for HMAC key derivation
_WATERMARK_HMAC_SALT = "trackme:foundation:trial:watermark:v1"


def _compute_watermark_hmac(trial_created_epoch, trial_expires_epoch, watermark_secret):
    """Compute HMAC-SHA256 over the watermark payload fields.

    The signing key is derived from the combination of the embedded salt
    and a random watermark_secret generated at first trial creation.
    """
    # Derive signing key: HMAC(salt, watermark_secret)
    signing_key = hmac_module.new(
        _WATERMARK_HMAC_SALT.encode("utf-8"),
        str(watermark_secret).encode("utf-8"),
        hashlib.sha256,
    ).digest()

    # Build the message: delimited epoch values
    message = f"{trial_created_epoch}|{trial_expires_epoch}"

    return hmac_module.new(
        signing_key,
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _read_trial_watermark_from_conf(service):
    """Read the trial_watermark value from trackme_settings.conf.

    Returns the raw string value (or empty string if not set).
    """
    try:
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]
        for stanza in confs:
            if stanza.name == "trackme_general":
                for stanzakey, stanzavalue in stanza.content.items():
                    if stanzakey == "trial_watermark":
                        return stanzavalue if stanzavalue else ""
    except Exception as e:
        get_effective_logger().error(
            f'failed to read trial_watermark from trackme_settings.conf, exception="{str(e)}"'
        )
    return ""


def trackme_check_trial_watermark(service):
    """Check if a foundation trial watermark exists and is valid.

    Returns a dict with:
        - "exists": bool - whether a watermark record was found
        - "valid": bool - whether the HMAC signature is valid
        - "watermark": dict or None - the watermark record if found

    If the watermark exists but the HMAC is invalid (tampered),
    the caller should treat this as "trial already used" (fail-closed).
    """
    result = {"exists": False, "valid": False, "watermark": None}

    watermark_raw = _read_trial_watermark_from_conf(service)
    if not watermark_raw:
        return result

    # Parse the JSON watermark
    try:
        watermark = json.loads(watermark_raw)
    except Exception as e:
        get_effective_logger().warning(
            f'trial watermark JSON parse failed (possible tampering), exception="{str(e)}"'
        )
        result["exists"] = True
        return result

    result["exists"] = True
    result["watermark"] = watermark

    # Validate the HMAC signature
    watermark_secret = watermark.get("watermark_secret", "")
    if not watermark_secret:
        get_effective_logger().warning("trial watermark missing watermark_secret - possible tampering")
        return result

    expected_hmac = _compute_watermark_hmac(
        watermark.get("trial_created_epoch"),
        watermark.get("trial_expires_epoch"),
        watermark_secret,
    )

    # Use hmac.compare_digest for timing-safe comparison
    result["valid"] = hmac_module.compare_digest(
        expected_hmac, watermark.get("hmac_signature", "")
    )

    if not result["valid"]:
        get_effective_logger().warning(
            "foundation trial watermark HMAC validation failed - possible tampering"
        )

    return result


def trackme_create_trial_watermark(
    server_rest_uri, auth_token, trial_created_epoch, trial_expires_epoch
):
    """Create and store a watermark record when a Foundation trial is first created.

    The watermark is stored in trackme_settings.conf via the UCC REST endpoint,
    which naturally replicates across SHC members.

    Returns the watermark record dict, or None on failure.
    """
    # Generate a random secret that will be used as the HMAC key
    watermark_secret = str(uuid.uuid4())

    hmac_signature = _compute_watermark_hmac(
        trial_created_epoch, trial_expires_epoch, watermark_secret
    )

    watermark_record = {
        "trial_created_epoch": trial_created_epoch,
        "trial_expires_epoch": trial_expires_epoch,
        "watermark_secret": watermark_secret,
        "hmac_signature": hmac_signature,
    }

    watermark_json = json.dumps(watermark_record)

    # Write to trackme_settings.conf via the UCC REST endpoint
    header = {
        "Authorization": f"Splunk {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    target_url = (
        f"{server_rest_uri}/servicesNS/nobody/trackme/trackme_settings/trackme_general"
    )

    try:
        response = requests.post(
            target_url,
            headers=header,
            data={"trial_watermark": watermark_json},
            verify=False,
            timeout=60,
        )
        if response.status_code in (200, 201):
            get_effective_logger().info("foundation trial watermark created successfully")
            return watermark_record
        else:
            get_effective_logger().error(
                f'failed to create trial watermark, status_code="{response.status_code}", '
                f'response="{response.text}"'
            )
            return None

    except Exception as e:
        get_effective_logger().error(
            f'failed to create trial watermark, exception="{str(e)}"'
        )
        return None


def trackme_clear_trial_watermark(server_rest_uri, auth_token):
    """Clear the trial watermark from trackme_settings.conf.

    This is called when a subscription license is legitimately reset (not
    foundation_trial or developer). Clearing the watermark ensures that on
    the next license check, the user enters the "unregistered" state rather
    than having an old watermark recreate an expired foundation_trial.

    Returns True on success, False on failure.
    """
    header = {
        "Authorization": f"Splunk {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    target_url = (
        f"{server_rest_uri}/servicesNS/nobody/trackme/trackme_settings/trackme_general"
    )

    try:
        response = requests.post(
            target_url,
            headers=header,
            data={"trial_watermark": ""},
            verify=False,
            timeout=60,
        )
        if response.status_code in (200, 201):
            get_effective_logger().info(
                "foundation trial watermark cleared (subscription license reset)"
            )
            return True
        else:
            get_effective_logger().error(
                f'failed to clear trial watermark, status_code="{response.status_code}", '
                f'response="{response.text}"'
            )
            return False

    except Exception as e:
        get_effective_logger().error(f'failed to clear trial watermark, exception="{str(e)}"')
        return False


#
# Developer mode watermark functions
#
# These functions manage a persistent watermark stored in trackme_settings.conf
# to enforce a maximum number of self-service developer mode activations.
# After the limit is reached, the user must contact TrackMe for a named
# developer license (Cryptolens Feature 7).
#

_DEV_WATERMARK_HMAC_SALT = "trackme:developer:mode:watermark:v1"

MAX_DEVELOPER_ACTIVATIONS = 3


def _compute_developer_watermark_hmac(
    usage_count, last_activated_epoch, last_expires_epoch, watermark_secret
):
    signing_key = hmac_module.new(
        _DEV_WATERMARK_HMAC_SALT.encode("utf-8"),
        str(watermark_secret).encode("utf-8"),
        hashlib.sha256,
    ).digest()

    message = f"{usage_count}|{last_activated_epoch}|{last_expires_epoch}"

    return hmac_module.new(
        signing_key,
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _read_developer_watermark_from_conf(service):
    try:
        conf_file = "trackme_settings"
        confs = service.confs[str(conf_file)]
        for stanza in confs:
            if stanza.name == "trackme_general":
                for stanzakey, stanzavalue in stanza.content.items():
                    if stanzakey == "developer_watermark":
                        return stanzavalue if stanzavalue else ""
    except Exception as e:
        get_effective_logger().error(
            f'failed to read developer_watermark from trackme_settings.conf, exception="{str(e)}"'
        )
    return ""


def trackme_check_developer_watermark(service):
    """Check if a developer mode watermark exists and is valid.

    Returns a dict with:
        - "exists": bool
        - "valid": bool - whether the HMAC signature is valid
        - "watermark": dict or None - the watermark record if found
    """
    result = {"exists": False, "valid": False, "watermark": None}

    watermark_raw = _read_developer_watermark_from_conf(service)
    if not watermark_raw:
        return result

    try:
        watermark = json.loads(watermark_raw)
    except Exception as e:
        get_effective_logger().warning(
            f'developer watermark JSON parse failed (possible tampering), exception="{str(e)}"'
        )
        result["exists"] = True
        return result

    result["exists"] = True
    result["watermark"] = watermark

    watermark_secret = watermark.get("watermark_secret", "")
    if not watermark_secret:
        get_effective_logger().warning("developer watermark missing watermark_secret - possible tampering")
        return result

    expected_hmac = _compute_developer_watermark_hmac(
        watermark.get("usage_count"),
        watermark.get("last_activated_epoch"),
        watermark.get("last_expires_epoch"),
        watermark_secret,
    )

    result["valid"] = hmac_module.compare_digest(
        expected_hmac, watermark.get("hmac_signature", "")
    )

    if not result["valid"]:
        get_effective_logger().warning(
            "developer watermark HMAC validation failed - possible tampering"
        )

    return result


def trackme_create_or_update_developer_watermark(
    server_rest_uri, auth_token, usage_count, last_activated_epoch, last_expires_epoch
):
    """Create or update the developer mode watermark with current activation info.

    Returns the watermark record dict, or None on failure.
    """
    watermark_secret = str(uuid.uuid4())

    hmac_signature = _compute_developer_watermark_hmac(
        usage_count, last_activated_epoch, last_expires_epoch, watermark_secret
    )

    watermark_record = {
        "usage_count": usage_count,
        "last_activated_epoch": last_activated_epoch,
        "last_expires_epoch": last_expires_epoch,
        "watermark_secret": watermark_secret,
        "hmac_signature": hmac_signature,
    }

    watermark_json = json.dumps(watermark_record)

    header = {
        "Authorization": f"Splunk {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    target_url = (
        f"{server_rest_uri}/servicesNS/nobody/trackme/trackme_settings/trackme_general"
    )

    try:
        response = requests.post(
            target_url,
            headers=header,
            data={"developer_watermark": watermark_json},
            verify=False,
            timeout=60,
        )
        if response.status_code in (200, 201):
            get_effective_logger().info(
                f"developer watermark created/updated successfully (usage_count={usage_count})"
            )
            return watermark_record
        else:
            get_effective_logger().error(
                f'failed to create/update developer watermark, status_code="{response.status_code}", '
                f'response="{response.text}"'
            )
            return None

    except Exception as e:
        get_effective_logger().error(
            f'failed to create/update developer watermark, exception="{str(e)}"'
        )
        return None


def trackme_clear_developer_watermark(server_rest_uri, auth_token):
    """Clear the developer watermark from trackme_settings.conf.

    Called when a named developer subscription license is registered.
    Returns True on success, False on failure.
    """
    header = {
        "Authorization": f"Splunk {auth_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    target_url = (
        f"{server_rest_uri}/servicesNS/nobody/trackme/trackme_settings/trackme_general"
    )

    try:
        response = requests.post(
            target_url,
            headers=header,
            data={"developer_watermark": ""},
            verify=False,
            timeout=60,
        )
        if response.status_code in (200, 201):
            get_effective_logger().info(
                "developer watermark cleared (subscription license registered)"
            )
            return True
        else:
            get_effective_logger().error(
                f'failed to clear developer watermark, status_code="{response.status_code}", '
                f'response="{response.text}"'
            )
            return False

    except Exception as e:
        get_effective_logger().error(f'failed to clear developer watermark, exception="{str(e)}"')
        return False


def trackme_start_trial(reqinfo, company_name=None, email_contact=None):
    header = {
        "Authorization": f"Splunk {reqinfo.session_key}",
        "Content-Type": "application/json",
    }

    #
    # retrieve the instance guid
    #

    instance_guid = None
    target_url = f"{reqinfo.server_rest_uri}/services/server/info"

    try:
        response = requests.get(target_url, headers=header, verify=False, timeout=600)
        get_effective_logger().debug(f'success retrieving server info, data="{response.text}"')

        pattern = r'name="guid">([^<]+)</s:key>'
        match = re.search(pattern, response.text)

        if match:
            instance_guid = match.group(1)
            get_effective_logger().debug(f'instance_guid="{instance_guid}"')

    except Exception as e:
        get_effective_logger().error(f'failed to retrieve the instance info, exception="{str(e)}"')

    #
    # verify if running in SHC, if so retrieve the shc_label
    #

    target_url = f"{reqinfo.server_rest_uri}/services/server/roles"
    is_shc = False

    try:
        response = requests.get(target_url, headers=header, verify=False, timeout=600)
        get_effective_logger().debug(f'success retrieving server roles, data="{response.text}"')

        if "<s:item>shc_member</s:item>" in response.text:
            is_shc = True
            get_effective_logger().debug("this instance is a member of a SHC cluster")

    except Exception as e:
        get_effective_logger().error(f'failed to retrieve the instance roles, exception="{str(e)}"')

    # if running in SHC, extract the shc_label
    if is_shc:
        target_url = f"{reqinfo.server_rest_uri}/services/shcluster/config"

        try:
            response = requests.get(
                target_url, headers=header, verify=False, timeout=600
            )
            get_effective_logger().debug(f'success retrieving shcluster info, data="{response.text}"')

            pattern = r'<s:key\sname="shcluster_label">([^<]+)</s:key>'
            match = re.search(pattern, response.text)

            if match:
                shcluster_label = match.group(1)
                get_effective_logger().debug(f'shcluster_label="{shcluster_label}"')

        except Exception as e:
            get_effective_logger().error(
                f'failed to retrieve the shcluster_label, exception="{str(e)}"'
            )

    # define the license_identifier
    license_identifier = None

    # if we failed to identify the instance_guid, generate a unique uuid
    if not instance_guid:
        instance_guid = uuid.uuid4()

    # investigate and set
    if is_shc:
        if shcluster_label:
            license_identifier = shcluster_label
        else:
            license_identifier = instance_guid

    else:
        license_identifier = instance_guid

    # Get the RSA pub key
    with open(
        os.path.join(
            splunkhome, "etc", "apps", "trackme", "lib", "licensing", "trackme_rsa.pub"
        ),
        "r",
    ) as f:
        for line in f:
            RSAPubKey = line
            break

    # Get the trial access token
    with open(
        os.path.join(
            splunkhome,
            "etc",
            "apps",
            "trackme",
            "lib",
            "licensing",
            "trackme_trial.pub",
        ),
        "r",
    ) as f:
        for line in f:
            auth_createtrial = line
            break

    # Get the trial access token
    with open(
        os.path.join(
            splunkhome,
            "etc",
            "apps",
            "trackme",
            "lib",
            "licensing",
            "trackme_token.pub",
        ),
        "r",
    ) as f:
        for line in f:
            auth = line
            break

    try:
        # Build friendly_name from company name and email contact
        # This will be visible in Cryptolens on the activated machine entry
        friendly_name = ""
        if company_name or email_contact:
            friendly_name_parts = []
            if company_name:
                friendly_name_parts.append(f"Company: {company_name}")
            if email_contact:
                friendly_name_parts.append(f"Email: {email_contact}")
            friendly_name = " | ".join(friendly_name_parts)
            get_effective_logger().info(f'Trial request with friendly_name="{friendly_name}"')

        trial_key = Key.create_trial_key(auth_createtrial, 18301, license_identifier, friendly_name)

        if trial_key[0] == None:
            get_effective_logger().error(
                f"An error occurred while attempting to create a trial key: {trial_key[1]}"
            )
            raise Exception(
                f"An error occurred while attempting to create a trial key: {trial_key[1]}"
            )

        else:
            get_effective_logger().info(
                f'The Trial license_key="{trial_key[0]}" was successfully generated'
            )
            result = Key.activate(
                token=auth,
                rsa_pub_key=RSAPubKey,
                product_id=18301,
                key=trial_key[0],
                machine_code=license_identifier,
                friendly_name=friendly_name,
            )

            # init
            response = {}
            action = None
            message = None
            license_is_valid = 0

            if result[0] == None:
                action = "failure"
                license_is_valid = 0
                message = str(result[1])

                get_effective_logger().error(
                    f'Failed to activate the license key, message="{str(result[1])}"'
                )
                raise Exception(
                    f'Failed to activate the license key, message="{str(result[1])}"'
                )

            else:
                action = "success"
                license_is_valid = 1
                trial_key = trial_key[0]
                message = "The trial license was generated successfully"
                license_string = result[0].save_as_string()

            response = {
                "action": action,
                "license_is_valid": license_is_valid,
                "trial_key": trial_key,
                "message": message,
                "license_string": license_string,
                "license_type": "trial",
            }

            get_effective_logger().info(f'response="{json.dumps(response, indent=2)}"')
            return response

    except Exception as e:
        get_effective_logger().error(
            f'An exception occurred while attempting to generate the trial license, exception="{str(e)}"'
        )
        raise Exception(
            f'An exception occurred while attempting to generate the trial license, exception="{str(e)}"'
        )
