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

# Standard library imports
import os
import sys
import time
import json
import random
import re
import logging
from logging.handlers import RotatingFileHandler

# Third-party library imports
import urllib3
import requests
from requests.structures import CaseInsensitiveDict
import urllib.parse

# Disable warnings for insecure requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splunkremotesearch.log" % splunkhome,
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
import splunklib.client as client

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    trackme_register_tenant_object_summary_gen_non_persistent,
    trackme_register_tenant_object_summary_gen_persistent,
    run_splunk_search,
    is_reachable_with_retry,
)

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license


@Configuration(distributed=False)
class SplunkRemoteSearch(GeneratingCommand):
    account = Option(
        doc="""
        **Syntax:** **account=****
        **Description:** Splunk remote deployment account to be used for the query.""",
        require=True,
        default=None,
    )

    search = Option(
        doc="""
        **Syntax:** **search=****
        **Description:** The Splunk query to be executed.""",
        require=True,
        default=None,
    )

    earliest = Option(
        doc="""
        **Syntax:** **earliest=****
        **Description:** The earliest time for the search.""",
        require=False,
        default=None,
    )

    latest = Option(
        doc="""
        **Syntax:** **latest=****
        **Description:** The latest time for the search.""",
        require=False,
        default=None,
    )

    register_component = Option(
        doc="""
        **Syntax:** **register_component=****
        **Description:** If the search is invoked by a tracker, register_component can be called to capture and regoster any execution exception.""",
        require=False,
        default=False,
    )

    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** If register_component is set, a value for component is required.""",
        require=False,
        default=None,
        validate=validators.Match("component", r"^.*$"),
    )

    report = Option(
        doc="""
        **Syntax:** **report=****
        **Description:** If register_component is set, a value for report is required.""",
        require=False,
        default=None,
        validate=validators.Match("report", r"^.*$"),
    )

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** If register_component is set, a value for tenant_id is required.""",
        require=False,
        default=None,
        validate=validators.Match("tenant_id", r"^.*$"),
    )

    run_against_each_member = Option(
        doc="""
        **Syntax:** **run_against_each_member=****
        **Description:** If set to true, the search will be run against each member of the account.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    report_runtime = Option(
        doc="""
        **Syntax:** **report_runtime=****
        **Description:** If set to true, the runtime of the search will be reported.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    sample_ratio = Option(
        doc="""
        **Syntax:** **sample_ratio=****
        **Description:** If set to a numeric value (e.g., 100), enables sampling with 1 sample for N events.""",
        require=False,
        default=None,
        validate=validators.Match("sample_ratio", r"^\d+$"),
    )

    # get current user and roles membership
    def get_user_roles(self):
        """
        Retrieve current user and his roles.
        """

        # get current user
        username = self._metadata.searchinfo.username

        # get user info
        users = self.service.users

        # Get roles for the current user
        username_roles = []
        for user in users:
            if user.name == username:
                username_roles = user.roles
        logging.debug(f'username="{username}", roles="{username_roles}"')

        # return current user roles as a list
        return username_roles

    def get_effective_roles(self, user_roles, roles_dict):
        effective_roles = set(user_roles)  # start with user's direct roles
        to_check = list(user_roles)  # roles to be checked for inherited roles

        while to_check:
            current_role = to_check.pop()
            inherited_roles = roles_dict.get(current_role, [])
            for inherited_role in inherited_roles:
                if inherited_role not in effective_roles:
                    effective_roles.add(inherited_role)
                    to_check.append(inherited_role)

        return effective_roles

    # get account creds with least privilege approach
    def get_account(self, session_key, splunkd_uri, account):
        """
        Retrieve account creds.
        """

        # Ensure splunkd_uri starts with "https://"
        if not splunkd_uri.startswith("https://"):
            splunkd_uri = f"https://{splunkd_uri}"

        # Build header and target URL
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Splunk {session_key}"
        headers["Content-Type"] = "application/json"
        target_url = (
            f"{splunkd_uri}/services/trackme/v2/configuration/get_remote_account"
        )

        # Create a requests session for better performance
        session = requests.Session()
        session.headers.update(headers)

        try:
            # Use a context manager to handle the request
            with session.post(
                target_url, data=json.dumps({"account": account}), verify=False
            ) as response:
                if response.ok:
                    response_json = response.json()
                    return response_json
                else:
                    error_message = f'Failed to retrieve account, status_code={response.status_code}, response_text="{response.text}"'
                    logging.error(error_message)
                    raise Exception(error_message)

        except Exception as e:
            error_message = f'Failed to retrieve account, exception="{str(e)}"'
            logging.error(error_message)
            raise Exception(error_message)

    # get the list of all accounts with least privileges approach
    def list_accounts(self, session_key, splunkd_uri):
        """
        List all accounts.
        """

        # Ensure splunkd_uri starts with "https://"
        if not splunkd_uri.startswith("https://"):
            splunkd_uri = f"https://{splunkd_uri}"

        # Build header and target URL
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Splunk {session_key}"
        target_url = f"{splunkd_uri}/services/trackme/v2/configuration/list_accounts"

        # Create a requests session for better performance
        session = requests.Session()
        session.headers.update(headers)

        try:
            # Use a context manager to handle the request
            with session.get(target_url, verify=False) as response:
                if response.ok:
                    logging.debug(
                        f'Success retrieving list of accounts, data="{response.json()}", response_text="{response.text}"'
                    )
                    response_json = response.json()
                    return response_json
                else:
                    error_message = f'Failed to retrieve accounts, status_code={response.status_code}, response_text="{response.text}"'
                    logging.error(error_message)
                    raise Exception(error_message)

        except Exception as e:
            error_message = f'Failed to retrieve account, exception="{str(e)}"'
            logging.error(error_message)
            raise Exception(error_message)

    def is_reachable(self, session, url, timeout):
        try:
            session.get(url, timeout=timeout, verify=False)
            return True, None
        except Exception as e:
            return False, str(e)

    def select_url(self, session, splunk_url, timeout=15, retry_config=None):
        splunk_urls = splunk_url.split(",")
        unreachable_errors = []

        reachable_urls = []
        for url in splunk_urls:
            if retry_config:
                # Use shared retry function, passing self.is_reachable as the function to use
                reachable, error = is_reachable_with_retry(session, url, timeout, retry_config, self.is_reachable)
            else:
                reachable, error = self.is_reachable(session, url, timeout)
            
            if reachable:
                reachable_urls.append(url)
            else:
                unreachable_errors.append((url, error))

        selected_url = random.choice(reachable_urls) if reachable_urls else False
        return selected_url, unreachable_errors

    def log_and_register_failure(self, error_msg, session_key, start, earliest, latest):
        logging.error(error_msg)

        if (
            self.register_component
            and self.tenant_id
            and self.component
            and self.report
        ):
            try:
                trackme_register_tenant_object_summary_gen_persistent(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    self.component,
                    self.report,
                    "failure",
                    time.time(),
                    str(time.time() - start),
                    error_msg,
                    earliest,
                    latest,
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", Failed to call trackme_register_tenant_object_summary_gen_persistent with exception="{str(e)}"'
                )
        elif self.register_component:
            logging.error(
                "If register_component is set, then tenant_id, report, and component must be set too."
            )

        raise Exception(error_msg)

    def register_success(self, session_key, start, earliest, latest):

        if (
            self.register_component
            and self.tenant_id
            and self.component
            and self.report
        ):
            try:
                trackme_register_tenant_object_summary_gen_non_persistent(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    self.component,
                    self.report,
                    "success",
                    time.time(),
                    str(time.time() - start),
                    "splunkremotesearch success",
                    earliest,
                    latest,
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="{self.component}", Failed to call trackme_register_tenant_object_summary_gen_non_persistent with exception="{str(e)}"'
                )
        elif self.register_component:
            logging.error(
                "If register_component is set, then tenant_id, report, and component must be set too."
            )

        return True

    def establish_remote_service(
        self,
        parsed_url,
        bearer_token,
        app_namespace,
        session_key,
        start,
        earliest,
        latest,
        timeout=600,
    ):
        try:
            service = client.connect(
                host=parsed_url.hostname,
                splunkToken=str(bearer_token),
                owner="nobody",
                app=app_namespace,
                port=parsed_url.port,
                autologin=True,
                timeout=timeout,
            )

            remote_apps = [app.label for app in service.apps]
            if remote_apps:
                logging.info(
                    f'Remote search connectivity check to host="{parsed_url.hostname}" on port="{parsed_url.port}" was successful'
                )
                return service

        except Exception as e:
            error_msg = f'Remote search for account="{self.account}" has failed at connectivity check, host="{parsed_url.hostname}" on port="{parsed_url.port}" with exception="{str(e)}"'
            self.log_and_register_failure(
                error_msg, session_key, start, earliest, latest
            )

        return None

    def run_remote_search(
        self,
        service,
        searchStr,
        session_key,
        start,
        earliest,
        latest,
        report_runtime=False,
        sample_ratio=None,
    ):
        result_count = 0
        records = []
        search_start = time.time()

        try:
            kwargs_oneshot = {
                "earliest_time": earliest,
                "latest_time": latest,
                "search_mode": "normal",
                "preview": False,
                "time_format": "%s",
                "count": 0,
                "output_mode": "json",
            }

            # Add sample_ratio to kwargs_oneshot if provided
            if sample_ratio is not None:
                kwargs_oneshot["sample_ratio"] = sample_ratio

            # If the search is a raw search but doesn't start with the search keyword, fix this automatically
            if not re.search(r"^search\s", searchStr) and not re.search(
                r"^\s{0,}\|", searchStr
            ):
                searchStr = f"search {searchStr}"

            reader = run_splunk_search(service, searchStr, kwargs_oneshot, 24, 5)

            # Loop through the reader results
            for item in reader:
                if isinstance(item, dict):
                    search_results = item
                    epochtime = str(search_results.get("_time", time.time()))
                    yield_record = {"_time": epochtime}

                    for k in search_results:
                        if not k.startswith("_"):
                            yield_record[k] = search_results[k]

                    yield_record["_raw"] = search_results.get("_raw", search_results)
                    records.append(yield_record)
                    result_count += 1

            search_runtime = round(time.time() - search_start, 3)

            if report_runtime:
                return {
                    "status": "success",
                    "exception": "",
                    "result_count": result_count,
                    "runtime_seconds": search_runtime,
                    "records": records,
                }
            else:
                return {
                    "status": "success",
                    "records": records,
                    "result_count": result_count,
                    "runtime_seconds": search_runtime,
                }

        except Exception as e:
            search_runtime = round(time.time() - search_start, 3)
            error_msg = f"Remote search failed with exception: {str(e)}"

            if report_runtime:
                return {
                    "status": "failed",
                    "exception": str(e),
                    "result_count": 0,
                    "runtime_seconds": search_runtime,
                    "records": [],
                }
            else:
                self.log_and_register_failure(
                    error_msg, session_key, start, earliest, latest
                )
                raise Exception(error_msg)

    def generate_fields(self, records):
        # this function ensures that records have the same list of fields to allow Splunk to automatically extract these fields
        # if a given result does not have a given field, it will be added to the record as an empty value
        all_keys = set()
        for record in records:
            all_keys.update(record.keys())

        for record in records:
            for key in all_keys:
                if key not in record:
                    record[key] = ""
            yield record

    def generate(self, **kwargs):
        # start perf duration counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get the session key
        session_key = self._metadata.searchinfo.session_key

        # set earliest and latest
        if not self.earliest:
            earliest = self._metadata.searchinfo.earliest_time
        else:
            earliest = self.earliest

        if not self.latest:
            latest = self._metadata.searchinfo.latest_time
        else:
            latest = self.latest

        # list of all accounts
        accounts_list = self.list_accounts(session_key, reqinfo["server_rest_uri"])
        accounts = accounts_list["accounts"]

        # remove local from accounts list
        accounts = [account for account in accounts if account != "local"]

        # check requested account
        if not self.account in accounts:
            error_msg = f'The account="{self.account}" has not been configured on this instance, cannot proceed!'
            self.log_and_register_failure(
                error_msg, session_key, start, earliest, latest
            )

        # check license state
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"], session_key
            )
            license_is_valid = check_license.get("license_is_valid")
            license_subscription_class = check_license.get("license_subscription_class")
            logging.debug(
                f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
            )

        except Exception as e:
            license_is_valid = 0
            license_subscription_class = "free"
            logging.error(f'function check_license exception="{str(e)}"')

        # try and return
        if (
            (license_is_valid != 1 or license_subscription_class == "free_extended")
            and len(accounts) >= 2
            and accounts[0] != self.account
        ):
            raise Exception(
                f"This TrackMe deployment is running in Free limited edition and you have reached the maximum number of 1 remote deployment, only the first remote account ({accounts[0]}) can be used"
            )

        # get account
        account_dict = self.get_account(
            session_key, reqinfo["server_rest_uri"], self.account
        )
        splunk_url = account_dict["splunk_url"]
        app_namespace = account_dict["app_namespace"]
        bearer_token = account_dict["token"]
        rbac_roles = set(account_dict["rbac_roles"])

        # timeouts
        timeout_connect_check = account_dict.get("timeout_connect_check", 15)

        # ensures this is an integer
        try:
            timeout_connect_check = int(timeout_connect_check)
        except Exception as e:
            logging.error(
                f"timeout_connect_check is not an integer, received value: {timeout_connect_check}, setting to 15"
            )

        timeout_search_check = account_dict.get("timeout_search_check", 300)

        # ensures this is an integer
        try:
            timeout_search_check = int(timeout_search_check)
        except Exception as e:
            logging.error(
                f"timeout_search_check is not an integer, received value: {timeout_search_check}, setting to 300"
            )

        # retry configuration
        retry_config = {
            "retry_enabled": account_dict.get("retry_enabled", "1"),
            "retry_max_total_time": account_dict.get("retry_max_total_time", "30"),
            "retry_initial_delay": account_dict.get("retry_initial_delay", "2"),
            "retry_backoff_multiplier": account_dict.get("retry_backoff_multiplier", "2.0"),
            "retry_max_attempts": account_dict.get("retry_max_attempts", "10"),
        }

        # Get user's direct roles
        user_roles = self.get_user_roles()

        # Get roles dictionary
        roles = self.service.roles
        roles_dict = {}

        for role in roles:
            imported_roles_value = role.content.get("imported_roles", [])
            if imported_roles_value:  # Check if it has a non-empty value
                roles_dict[role.name] = imported_roles_value

        logging.debug(f"roles_dict={json.dumps(roles_dict, indent=2)}")

        # Get effective roles (direct roles + inherited roles)
        effective_roles = self.get_effective_roles(user_roles, roles_dict)

        # Check RBAC using effective roles
        rbac_granted = bool(effective_roles & rbac_roles)

        # Grant the system user
        if self._metadata.searchinfo.username in ("splunk-system-user", "admin"):
            rbac_granted = True

        if not rbac_granted:
            logging.debug(
                f'RBAC access not granted to this account, user_roles="{user_roles}", effective_roles="{effective_roles}", account_roles="{rbac_roles}", username="{self._metadata.searchinfo.username}"'
            )
            raise Exception(
                "Access to this Remote account has been refused, please contact your TrackMe administrator to grant access to this Remote account"
            )
        else:
            logging.debug(
                f'RBAC access granted to this account, user_roles="{user_roles}", effective_roles="{effective_roles}", account_roles="{rbac_roles}"'
            )

        # Create a session within the generate function
        session = requests.Session()

        # Get the search string
        searchStr = self.search

        # Process
        if self.run_against_each_member:
            splunk_urls = splunk_url.split(",")
            for member_url in splunk_urls:
                member_url = f"https://{member_url.replace('https://', '').rstrip('/')}"
                parsed_url = urllib.parse.urlparse(member_url)

                logging.info(f"Processing member URL: {member_url}")

                try:
                    remoteservice = self.establish_remote_service(
                        parsed_url,
                        bearer_token,
                        app_namespace,
                        session_key,
                        start,
                        earliest,
                        latest,
                        timeout=timeout_search_check,
                    )

                    if not remoteservice:
                        raise Exception("Could not establish remote service")

                    result = self.run_remote_search(
                        remoteservice,
                        searchStr,
                        session_key,
                        start,
                        earliest,
                        latest,
                        report_runtime=self.report_runtime,
                        sample_ratio=self.sample_ratio,
                    )

                    result["member"] = member_url

                    if self.report_runtime:
                        result["_raw"] = json.dumps(result)
                        result["_time"] = time.time()
                        yield result
                    else:
                        for yield_record in self.generate_fields(result["records"]):
                            yield yield_record

                except Exception as e:
                    logging.error(
                        f"Search failed for member={member_url}, exception={str(e)}"
                    )

                    if self.report_runtime:
                        result = {
                            "member": member_url,
                            "status": "failed",
                            "exception": str(e),
                            "result_count": 0,
                            "runtime_seconds": 0,
                        }
                        result["_raw"] = json.dumps(result)
                        result["_time"] = time.time()
                        yield result

        else:
            # original behavior: select one working URL
            selected_url, errors = self.select_url(
                session, splunk_url, timeout_connect_check, retry_config
            )

            if not selected_url:
                error_msg = f"None of the endpoints provided in the account URLs could be reached successfully, verify your network connectivity! (timeout_connect_check={timeout_connect_check})"
                error_msg += (
                    f"Errors: {' '.join([f'{url}: {error}' for url, error in errors])}"
                )
                logging.error(error_msg)
                self.log_and_register_failure(
                    error_msg, session_key, start, earliest, latest
                )

            else:
                selected_url = (
                    f"https://{selected_url.replace('https://', '').rstrip('/')}"
                )
                parsed_url = urllib.parse.urlparse(selected_url)

                remoteservice = self.establish_remote_service(
                    parsed_url,
                    bearer_token,
                    app_namespace,
                    session_key,
                    start,
                    earliest,
                    latest,
                    timeout=timeout_search_check,
                )

                if not remoteservice:
                    raise Exception("Failed to establish remote service connection")

                result = self.run_remote_search(
                    remoteservice,
                    searchStr,
                    session_key,
                    start,
                    earliest,
                    latest,
                    report_runtime=self.report_runtime,
                    sample_ratio=self.sample_ratio,
                )

                if self.report_runtime:
                    result["member"] = selected_url
                    result["_raw"] = json.dumps(result)
                    result["_time"] = time.time()
                    yield result
                else:
                    for yield_record in self.generate_fields(result["records"]):
                        yield yield_record


dispatch(SplunkRemoteSearch, sys.argv, sys.stdin, sys.stdout, __name__)
