
# encoding = utf-8
# Always put this line at the beginning of this file
from __future__ import print_function

import os
import sys
import json
import classes.eiq_logger as eiq_logger
import classes.splunk_info as si

from classes.eiq_api import EclecticIQ_api as eiqlib

current_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        sessionKey = str(payload["session_key"])
        splunk_info = si.Splunk_Info(sessionKey)
        splunk_paths = splunk_info.give_splunk_paths(current_dir)
        app_name = splunk_paths['app_name']

        # prepare the logger instance
        log_level = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'log_level')
        logger = eiq_logger.Logger()
        script_logger = logger.logger_setup("eiq_sightings_custom_action", level=log_level)

        # Get config params
        SOURCEGROUPNAME = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'sourcegroupname')
        BASEURL = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'eiq_baseurl')
        EIQ_VERSION = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'eiq_version')
        USERNAME = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'eiq_username')
        VERIFYSSL = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'verify-ssl')
        PROXY_IP = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'proxy_ip')
        PROXY_USERNAME = splunk_info.get_config(
            'sa-eclecticiq.conf',
            'main',
            'proxy_username')
        PASSWORD = splunk_info.get_credetials(USERNAME)
        PROXY_PASSWORD = splunk_info.get_credetials(PROXY_USERNAME)

        # make sure we have a username and a password
        # before we try to authenticate
        if len(USERNAME) == 0:
            script_logger.error("No username provided via the config.")
            sys.exit(2)

        if PASSWORD == "NO_PASSWORD_FOUND_FOR_THIS_USER":
            script_logger.error("No password found for user " + str(USERNAME))
            sys.exit(2)

        if EIQ_VERSION == "FC" or EIQ_VERSION == "Fc-essentials":
            script_logger.error("Fusion Center doesn't support creating sightings.")
            sys.exit(2)

        # make sure that VERIFYSSL is a boolean True or False
        VERIFYSSL = True if str(VERIFYSSL) == "1" else False

        type_names_list = [
            'ipv4', 'ipv6', 'domain', 'host', 'uri', 'hash-md5', 'hash-sha1', 'hash-sha256',
            'hash-sha512', 'email']
        filtered_types_list = []

        for type_name in type_names_list:
            val = splunk_info.get_config(
                "sa-eclecticiq.conf",
                'main',
                type_name)
            if val == '1':
                filtered_types_list.append(type_name)

        # sign in to the platform
        api = eiqlib(BASEURL, EIQ_VERSION, USERNAME, PASSWORD,
                     VERIFYSSL, PROXY_IP, PROXY_USERNAME,
                     PROXY_PASSWORD, script_logger)

        record = {}
        tag_string = str(payload["configuration"]["sighting_tags"])

        record['observable_type'] = str(payload["configuration"]["observable_type"])
        record['observable_value'] = str(payload["configuration"]["observable_value"])
        record['observable_classification'] = "bad"
        record['observable_maliciousness'] = str(payload["configuration"]["observable_confidence"])

        entity_title = str(payload["configuration"]["sighting_title"])
        entity_description = str(payload["configuration"]["sighting_description"])
        entity_confidence = str(payload["configuration"]["sighting_confidence"])
        entity_tags = tag_string.split(",")

        if record['observable_type'] in filtered_types_list:
            script_logger.debug("Creating Sighting through Custom Action.")
            api.create_entity([record], SOURCEGROUPNAME, entity_title,
                              entity_description, entity_confidence, entity_tags)
        else:
            script_logger.debug("Sightings type is not in the allowed list.")

    else:
        if sys.version_info >= (3, 0):
            print("FATAL Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        else:
            print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(2)
