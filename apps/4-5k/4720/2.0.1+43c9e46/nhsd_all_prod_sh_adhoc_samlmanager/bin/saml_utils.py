"""
saml-common.py
Common functions
"""

import ta_saml_manager_declare

import splunk.rest
from splunk.clilib import cli_common as cli

from splunk_aoblib.setup_util import Setup_Util

import json
import logging as logger
import os, sys
import requests



from cStringIO import StringIO
from ConfigParser import ConfigParser

class saml_utils():

    def __init__(self, logger, settings):
        logger.info("Started...")
        self.logger = logger
        self.settings = settings
        self.get_setup_util()

    def get_setup_util(self):
        if not hasattr(self, 'setup_util'):
            self.session_key = self.settings.get("sessionKey")
            uri = "https://localhost:8089"
            self.setup_util = Setup_Util(uri, self.session_key, logger)

        return self.setup_util

    def get_session_key(self):
        return self.session_key

    def pull_remote_saml(self):

        auth_string = self.setup_util.get_customized_setting("auth_string")
        auth_type = self.setup_util.get_customized_setting("auth_type")
        authorization_conf_url = self.setup_util.get_customized_setting("authorization_conf_url")
        if not authorization_conf_url.startswith("https"):
            self.logger.critical("Authorisation conf URL must be HTTPS")
            sys.exit(1)

        auth_type_headers = {
            "PRIVATE_TOKEN" : { "PRIVATE-TOKEN":auth_string },
            "BASIC_AUTH" : {},
            "NO_AUTH" : {},
            "AUTHORIZATION_AUTH" : { "Authorization":auth_string }
        }

        headers = auth_type_headers.get(auth_type)

        if auth_type == "BASIC_AUTH":
            login_segments = auth_string.split(":")
            auth_user = login_segments[0]
            auth_password = login_segments[1]
            r = requests.get(authorization_conf_url, auth=(auth_user, auth_password), headers=headers)
        else:
            r = requests.get(authorization_conf_url, headers=headers)

        rows = []
        if r.status_code == 200:
            content_IO = StringIO(r.content)
            parser = ConfigParser()
            parser.optionxform = str
            parser.readfp(content_IO)
            roles = {}
            for item in parser.items("roleMap_SAML"):
                rows.append({
                    "splunk_group": item[0],
                    "saml_group": item[1]
                })
        return rows

    def pull_local_saml(self):
        saml_groups = {}
        r_response, r_content = splunk.rest.simpleRequest(
            '/services/admin/SAML-groups?output_mode=json',
            method='GET',
            sessionKey=self.session_key
        )
        for saml_group in json.loads(r_content)['entry']:
            saml_groups[saml_group['name']] = saml_group['content']['roles']

        return saml_groups

    def pull_local_groups(self):
        splunk_groups = []

        paging_iterate = True
        paging_offset = 0

        while paging_iterate:
            r_response, r_content = splunk.rest.simpleRequest(
                '/services/authorization/roles?output_mode=json&offset={}'.format(paging_offset),
                method='GET',
                sessionKey=self.session_key
            )
            paging = json.loads(r_content)['paging']
            if ( (paging['offset']+paging['perPage']) > paging['total']):
                paging_iterate = False
            paging_offset = paging_offset + paging['perPage']
            self.logger.debug("Iterating  over groups page with offset of {}".format(paging_offset))
            for splunk_group in json.loads(r_content)['entry']:
                splunk_groups.append(splunk_group['name'].upper())

        return splunk_groups
