# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import logging
import json
import http.client
from splunk.rest import simpleRequest
from license import License
from splunk_api_license_group import SplunkAPILicenseGroup
from utils import setup_logging


class SplunkLicensesAPI(object):
    """
    Installs and updates ITSI built-in sourcetype licenses.
    Also installs/uninstalls ITSI built-in licenses for suitification signaling to license peers.
    This class is designed to run on LM or self-licensed instance.
    """

    LICENSER_ENDPOINT_BASE = '/services/licenser/'
    LICENSES_ENDPOINT = LICENSER_ENDPOINT_BASE + 'licenses'
    GROUPS_ENDPOINT = LICENSER_ENDPOINT_BASE + 'groups'
    LOCALSLAVE_ENDPOINT = LICENSER_ENDPOINT_BASE + 'localslave'
    LOCALPEER_ENDPOINT = LICENSER_ENDPOINT_BASE + 'localpeer'
    MASTER_URI_ENDPOINT = '/services/properties/server/license/master_uri'

    def __init__(self, splunkd_uri, session_key, app_name):
        self.splunkd_uri = splunkd_uri
        self.session_key = session_key
        self.app_name = app_name
        self.log = setup_logging(log_file='itsi_license_checker.log', logger_name='itsi.license_checker.SplunkLicensesAPI')
        self.licenses_uri = self.splunkd_uri + self.LICENSES_ENDPOINT
        self.groups_uri = self.splunkd_uri + self.GROUPS_ENDPOINT

    def is_license_dependent(self):
        """
        This method returns whether current instance is dependent on the connected LM.

        @rtype: bool
        @return: True - when this instance is connected to LM, otherwise - False.
        """

        try:
            response, contents = simpleRequest(
                path=self.splunkd_uri + self.LOCALPEER_ENDPOINT,
                getargs={'output_mode': 'json'},
                sessionKey=self.session_key)

            if response.status == http.client.OK:
                manager_uri = self.get_license_uri(contents, 'manager_uri')
                self.log.info('Checking is license dependent : License manager uri : {} :'.format(manager_uri))
                return manager_uri != 'self'
            else:
                raise Exception("Failed to get License manager uri. Response: {}. Response body: {}".
                                format(response, contents))
        except Exception as e:
            self.log.info('Failed to get License manager uri : {} : Now trying with License master uri.'.format(e))
            response, contents = simpleRequest(
                path=self.splunkd_uri + self.LOCALSLAVE_ENDPOINT,
                getargs={'output_mode': 'json'},
                sessionKey=self.session_key)

            if response.status == http.client.OK:
                master_uri = self.get_license_uri(contents, 'master_uri')
                self.log.info('Checking is license dependent : License master uri : {} :'.format(master_uri))
                return master_uri != 'self'
            else:
                raise Exception("Failed to get License master uri. Response: {}. Response body: {}".
                                format(response, contents))

    def get_license_uri(self, api_contents, uri):
        for entry in json.loads(api_contents).get('entry', None):
            content = entry.get('content', None)
            if content is None:
                continue
            return content.get(uri)

    def get_license_groups(self):
        response, content = simpleRequest(path=self.groups_uri,
                                          getargs={'output_mode': 'json'},
                                          sessionKey=self.session_key)
        if response.status != http.client.OK:
            raise Exception("Failed to get license groups. Response: {}. Response body: {}".
                            format(response, content))

        license_groups = []
        for response_group in json.loads(content).get('entry'):
            content = response_group['content']
            license_groups.append(
                SplunkAPILicenseGroup(name=response_group['name'],
                                      active=content['is_active']))
        return license_groups

    def get_licenses(self):
        response, content = simpleRequest(path=self.licenses_uri,
                                          getargs={'output_mode': 'json', 'count' : 0},
                                          sessionKey=self.session_key)
        if response.status != http.client.OK:
            raise Exception("Failed to get licenses. Response: {}. Response body: {}".
                            format(response, content))
        licenses = []
        for response_license in json.loads(content).get('entry'):
            content = response_license.get('content')
            if content is None:
                continue
            licenses.append(
                License(
                    guid=content.get('guid'),
                    hash=response_license.get('name'),
                    label=response_license.get('label'),
                    expiration_time=content.get('expiration_time'),
                    status=content.get('status'),
                    group_id=content.get('group_id'),
                    subgroup_id=content.get('subgroup_id'),
                    add_ons=content.get('add_ons')))
        return licenses

    def get_itsi_licenses(self, include_future_licenses=False):
        licenses = self.get_licenses()

        itsi_licenses = []
        for curr_license in licenses:
            if curr_license.add_ons is None:
                continue
            if not include_future_licenses and curr_license.is_from_future():
                continue
            if self.app_name in curr_license.add_ons.keys():
                itsi_licenses.append(curr_license)
        return itsi_licenses

    def get_licenses_in_use(self):
        response, contents = simpleRequest(
            path=self.LOCALSLAVE_ENDPOINT,
            getargs={'output_mode': 'json'},
            sessionKey=self.session_key)
        if response.status != http.client.OK:
            raise Exception('Failed to get license information. Response={} Contents={}'.format(response, contents))

        licenses = []

        for entry in json.loads(contents).get('entry', None):
            content = entry.get('content', None)
            if content is None:
                continue
            hashes = content.get('license_keys')
            if hashes is not None:
                for hash in hashes:
                    licenses.append(License(hash=hash))
        return licenses

    def install_license(self, lic):
        self.log.info('Installing new ITSI internal license: {} ...'.format(self._log_license(lic)))

        response, content = simpleRequest(
            path=self.licenses_uri,
            postargs={
                'name': lic.name,
                'payload': lic.body},
            sessionKey=self.session_key)

        if response.status not in [http.client.OK, http.client.CREATED]:
            raise Exception("Failed to install a license {}. Response: {}. Response body: {}".
                            format(self._log_license(lic), response, content))

        self.log.info('Installed new ITSI internal license: {}. License information: {}'.
                      format(self._log_license(lic), str(content)))
        return

    def remove_license(self, lic):
        self.log.info('Removing license {} ...'.format(self._log_license(lic)))

        try:
            response, content = simpleRequest(
                path=self.licenses_uri + '/' + lic.hash,
                sessionKey=self.session_key,
                method='DELETE')
        except Exception as e:
            raise Exception("Request to remove license {} failed".format(self._log_license(lic))) from e
        if response.status != http.client.OK:
            raise Exception("Failed to remove license {}. Response: {}. Response body: {}".
                            format(self._log_license(lic), response, content))
        self.log.info('Removed license {}'.format(self._log_license(lic)))

    def is_license_exists(self, lic):
        response, content = simpleRequest(
            path=self.licenses_uri + '/' + lic.name,
            sessionKey=self.session_key)
        return response.status == http.client.OK

    def _is_debug_logging(self):
        return self.log.isEnabledFor(logging.DEBUG)

    def _log_license(self, lic):
        if self._is_debug_logging():
            return 'Name: {} GUID: {} hash: {}'.format(lic.name, lic.guid, lic.hash)
        else:
            return 'Name: {}'.format(lic.name)
