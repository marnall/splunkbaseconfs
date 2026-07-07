"""
(C) 2022 Splunk Inc. All rights reserved.

Cleans up deleted objects from the roles table.
"""
import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

import time
import semver
import json
from urllib.parse import urlencode, quote
from http import HTTPStatus
from typing import List
from splunkar import constants
from splunkar import kvstore
from splunkar import logging
from splunkar.model.hub_registrations import HubRegistration, RegistrationStatus
from splunkar.util import splunkd_requests, general_requests
from splunkar.util.modular_input_utils import SplunkARModularInput

sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk-app-ar', 'lib']))

LOGGER = logging.get_logger(__name__)

REGISTRATION_V2_ENDPOINT_PATH = 'services/ssg/registration/v2'
SSG_VERSION_3_3_30 = semver.VersionInfo.parse("3.3.30")
SSG_VERSION_3_6_13 = semver.VersionInfo.parse("3.6.13")


class HubRegistrationModularInput(SplunkARModularInput):
    """Modular input to complete registrations for Edge Hub devices."""

    title = 'Edge Hub Registration Modular Input'
    description = 'Calls SSG to complete registrations created for Edge Hub devices'
    app = constants.APP_NAME
    name = 'splunkedge_hub_registration_modular_input'
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    def run(self) -> None:
        self.logger.debug('Running Hub Registration Modular Input')
        results = self.handle_hub_registrations()

        if results:
            self.logger.debug(f"Hub Registration Modular Input completed with responses={results}")

    def _get_hub_registration_jobs(self) -> List[HubRegistration]:
        try:
            jobs = kvstore.load_many(self.session_key, HubRegistration, sort_key=HubRegistration.REGISTRATION_TIMESTAMP)
            return jobs
        except Exception as e:
            self.logger.error(f"Hub Registration Modular Input failed to fetch jobs from KVStore with error={e}")
            raise

    def clean_up_job(self, registration: HubRegistration) -> bool:
        try:
            key = registration.key
            if not key:
                raise ValueError("Cannot clean up job missing key.")

            kvstore.delete(self.session_key, HubRegistration, key)
            return True

        except Exception as e:
            self.logger.error(f"Hub Registration clean up failed, error={e}")
            return False

    def complete_registration_legacy_ssg(self, auth_code: str, user: str) -> HTTPStatus:
        sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk_secure_gateway', 'bin']))
        sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'splunk_secure_gateway', 'lib']))
        from spacebridgeapp.rest.registration.registration_v2 import handle_registration_v2

        sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk_secure_gateway', 'lib']))
        sys.path.remove(make_splunkhome_path(['etc', 'apps', 'splunk_secure_gateway', 'bin']))

        try:
            response = handle_registration_v2(
                auth_code=auth_code,
                auth_method="local_ldap",
                user=user,
                session_token=self.session_key,
                system_authtoken=self.session_key,
            )
            return response["status"]
        except Exception as e:
            self.logger.debug(f"Error while confirming registration with SSG. error={str(e)}")
            return HTTPStatus.NOT_FOUND

    def complete_registration(self, auth_code: str, user: str, auth_in_body=True) -> HTTPStatus:
        if auth_in_body:
            query_params = {"user": user}
            body = {"auth_code": auth_code, "auth_method": "local_ldap"}
            encoded_query = urlencode(query_params, quote_via=quote)
            response = splunkd_requests.post(
                path=f"{REGISTRATION_V2_ENDPOINT_PATH}?{encoded_query}",
                auth_header=self.session_key,
                jsonstr=json.dumps(body),
            )
        else:
            query_params = {"auth_code": auth_code, "auth_method": "local_ldap", "user": user}
            encoded_query = urlencode(query_params, quote_via=quote)
            response = splunkd_requests.post(
                path=f"{REGISTRATION_V2_ENDPOINT_PATH}?{encoded_query}", auth_header=self.session_key
            )

        return HTTPStatus(response.status_code)

    def run_registration_job(self, registration: HubRegistration) -> bool:
        # Fetch all fields
        key = registration.key
        status = registration.status
        user = registration.user
        job_expiry = registration.registration_expiry
        auth_code = registration.auth_code

        # If the job has outlived it's TTL or has any missing params update it's status to failed
        if None in (key, status, user, job_expiry, auth_code):
            registration.status = RegistrationStatus.FAILED
            self.logger.error(f"Hub Registration error for key={key}, setting status to status={registration.status}")
        elif time.time() > job_expiry:
            registration.status = RegistrationStatus.EXPIRED
            self.logger.debug(f"Hub Registration has expired for key={key}, setting status={registration.status}")
        elif status == RegistrationStatus.RUNNING:
            ssg_version = general_requests.get_app_version(constants.SSG_APP_NAME, self.session_key)
            semver_version = semver.VersionInfo.parse(ssg_version)
            if semver_version < SSG_VERSION_3_3_30:
                self.logger.debug("Running legacy registration completion")
                reg_status = self.complete_registration_legacy_ssg(auth_code, user=user)
            elif semver_version < SSG_VERSION_3_6_13:
                self.logger.debug(f"Running new registration completion for SSG < {SSG_VERSION_3_6_13}")
                reg_status = self.complete_registration(auth_code, user, auth_in_body=False)
            else:
                self.logger.debug(f"Running new registration completion for SSG >= {SSG_VERSION_3_6_13}")
                reg_status = self.complete_registration(auth_code, user)

            if reg_status == HTTPStatus.OK:
                registration.status = RegistrationStatus.COMPLETED
                self.logger.debug(
                    f"Hub Registration Modular Input registration successful for key={key}, setting status={registration.status}"
                )

        # If job status changes due to failure, TTL expiration or successful completion clean up the job
        if registration.status != RegistrationStatus.RUNNING:
            result = self.clean_up_job(registration)
            if result:
                self.logger.debug(
                    f"Clean up successful for job with key={key}, user={user}, status={registration.status}"
                )
                return True

        return False

    def handle_hub_registrations(self):
        try:
            jobs = self._get_hub_registration_jobs()

            if not jobs:
                self.logger.debug(f"Hub Registration Modular Input found no running jobs, ending early.")
                return {}

            # jobs are returned in sorted order based off their created at timestamp
            # stale or unused jobs will live longer since they won't ever complete until their TTL so process in reverse
            job_results = {job.key: self.run_registration_job(job) for job in reversed(jobs)}

            return job_results
        except Exception as e:
            self.logger.error(f"Hub Registration Modular Input failed handling registrations with error={e}")
            return {}


if __name__ == '__main__':
    m = HubRegistrationModularInput(LOGGER)
    m.execute()
