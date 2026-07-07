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
import random
import difflib
import hashlib
import fnmatch
from datetime import datetime

# External libraries
import requests
from requests.structures import CaseInsensitiveDict
import urllib3
import urllib.parse

# Disable urllib3 warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
import logging
from logging.handlers import RotatingFileHandler

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splkwlk_getreportsdef_stream.log" % splunkhome,
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
    StreamingCommand,
    Configuration,
    Option,
    validators,
)
import splunklib.client as client

# import trackme libs (after lib appended)
from trackme_libs import (
    trackme_reqinfo,
    trackme_register_tenant_object_summary,
    run_splunk_search,
    trackme_handler_events,
)
from trackme_libs_splk_wlk import trackme_ingest_version
from trackme_libs_utils import decode_unicode, remove_leading_spaces

# import trackme libs croniter
from trackme_libs_croniter import cron_to_seconds


@Configuration(distributed=False)
class SplkWlkGetReportsDef(StreamingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    context = Option(
        doc="""
        **Syntax:** **context=****
        **Description:** The context is used for simulation purposes, defaults to live.""",
        require=False,
        default="live",
        validate=validators.Match("context", r"^(live|simulation)$"),
    )

    check_orphan = Option(
        doc="""
        **Syntax:** **check_orphan=****
        **Description:** Is enabled, check for orphan status.""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    register_component = Option(
        doc="""
        **Syntax:** **register_component=****
        **Description:** If the search is invoked by a tracker, register_component can be called to capture and regoster any execution exception.""",
        require=False,
        default=False,
    )

    report = Option(
        doc="""
        **Syntax:** **report=****
        **Description:** If register_component is set, a value for report is required.""",
        require=False,
        default=None,
        validate=validators.Match("report", r"^.*$"),
    )

    exclude_apps = Option(
        doc="""
        **Syntax:** **exlude_apps=****
        **Description:** A comma separated list of apps we are never going to consider.""",
        require=False,
        default="skynet-rest,cloud-monitoring-console-summarizer",
        validate=validators.Match("exclude_apps", r"^.*$"),
    )

    max_runtime_sec = Option(
        doc="""
        **Syntax:** **max_runtime_sec=****
        **Description:** The max runtime for the job in seconds, defaults to 15 minutes less 120 seconds of margin.""",
        require=False,
        default="900",
        validate=validators.Match("max_runtime_sec", r"^\d*$"),
    )

    filters_get_last_updates = Option(
        doc="""
        **Syntax:** **filters_get_last_updates=****
        **Description:** An optional search string to restrict the Search Head tiers when looking at the last updates of savedsearches (to identify who modified a search and when), defaults to host=*.""",
        require=False,
        default="host=*",
        validate=validators.Match("filters_get_last_updates", r"^.*$"),
    )

    def generate_diff_string(self, a, b):
        # Handle None values gracefully
        if a is None:
            a = ""
        if b is None:
            b = ""
        
        # Convert to strings if they aren't already
        a_str = str(a) if a is not None else ""
        b_str = str(b) if b is not None else ""
        
        a_lines = a_str.splitlines(keepends=True)
        b_lines = b_str.splitlines(keepends=True)
        diff = difflib.unified_diff(
            a_lines, b_lines, fromfile="last_known", tofile="current", lineterm=""
        )
        return "".join(diff)

    def is_reachable(self, session, url, timeout):
        try:
            session.get(url, timeout=timeout, verify=False)
            return True, None
        except Exception as e:
            return False, str(e)

    def select_url(self, session, splunk_url):
        splunk_urls = splunk_url.split(",")
        unreachable_errors = []

        reachable_urls = []
        for url in splunk_urls:
            reachable, error = self.is_reachable(session, url, 10)
            if reachable:
                reachable_urls.append(url)
            else:
                unreachable_errors.append((url, error))

        selected_url = random.choice(reachable_urls) if reachable_urls else False
        return selected_url, unreachable_errors

    def log_and_register_failure(self, error_msg, session_key, start, earliest, latest):
        logging.error(error_msg)

        if self.register_component and self.tenant_id and self.report:
            try:
                trackme_register_tenant_object_summary(
                    session_key,
                    self._metadata.searchinfo.splunkd_uri,
                    self.tenant_id,
                    "splk-wlk",
                    self.report,
                    "failure",
                    time.time(),
                    round(time.time() - start, 3),
                    error_msg,
                    earliest,
                    latest,
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="wlk", Failed to call trackme_register_tenant_object_summary with exception="{str(e)}"'
                )
        elif self.register_component:
            logging.error(
                "If register_component is set, then tenant_id, report, and component must be set too."
            )

        raise Exception(error_msg)

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
        headers["Content-Type"] = "application/json"
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

    # get a targeted KVrecord
    def get_kv_record(self, versioning_collection, record_object_id):
        try:
            query_string = {
                "_key": record_object_id,
            }
            kvrecord = versioning_collection.data.query(query=json.dumps(query_string))[
                0
            ]
            kvrecordkey = kvrecord.get("_key")
            kvrecorddict = json.loads(kvrecord.get("version_dict"))
        except Exception as e:
            kvrecordkey = None
            kvrecord = None
            kvrecorddict = None

        return kvrecord, kvrecordkey, kvrecorddict

    # sort the JSON dict by the most recent epoch
    def sort_json_by_epoch(self, json_dict: dict) -> dict:
        # Sort the dictionary by the "time_inspected_epoch" value in descending order
        sorted_json_dict = {
            k: v
            for k, v in sorted(
                json_dict.items(),
                key=lambda item: item[1]["time_inspected_epoch"],
                reverse=True,
            )
        }

        # Return the sorted dictionary
        return sorted_json_dict

    # establish remote connectivity
    def establish_remote_service(
        self, splunk_url, bearer_token, connect_user, record_app, account
    ):
        # use urlparse to extract relevant info from target
        parsed_url = urllib.parse.urlparse(splunk_url)

        # Establish the remote service
        logging.debug(
            f'Establishing connection to host="{parsed_url.hostname}" on port="{parsed_url.port}"'
        )

        # boolean for service connection check
        remote_service_established = False
        service = None
        header = None

        try:
            service = client.connect(
                host=parsed_url.hostname,
                splunkToken=str(bearer_token),
                owner=connect_user,
                app=record_app,
                port=parsed_url.port,
                autologin=True,
                timeout=600,
            )

            # get the list of remote apps to test the connectivity effectively
            remote_apps = [app.label for app in service.apps]
            if remote_apps:
                logging.debug(
                    f'remote search connectivity check to host="{parsed_url.hostname}" on port="{parsed_url.port}" was successful'
                )
                remote_service_established = True

                # set header
                header = {
                    "Authorization": "Bearer %s" % bearer_token,
                    "Content-Type": "application/json",
                }

            else:
                remote_service_established = False
                service = False
                error_msg = f'remote search for account="{account}" has failed at connectivity check, in some use cases this may be expected, host="{parsed_url.hostname}" on port="{parsed_url.port}", connect_user="{connect_user}", connect_app="{record_app}", no remote apps found'
                logging.error(error_msg)

        except Exception as e:
            remote_service_established = False
            service = False
            error_msg = f'remote search for account="{account}" has failed at connectivity check, in some use cases this may be expected, host="{parsed_url.hostname}" on port="{parsed_url.port}", connect_user="{connect_user}", connect_app="{record_app}", exception="{str(e)}"'
            logging.warning(error_msg)

        return remote_service_established, service, header

    # establish local connectivity
    def establish_local_service(self, session_key, connect_user, record_app):
        # set target
        selected_url = self._metadata.searchinfo.splunkd_uri
        parsed_url = urllib.parse.urlparse(selected_url)

        try:
            # explicit service
            service = client.connect(
                token=str(session_key),
                owner=connect_user,
                app=record_app,
                host=parsed_url.hostname,
                port=parsed_url.port,
                timeout=600,
            )

            remote_apps = [app.label for app in service.apps]
            if not remote_apps:
                service = False

        except Exception as e:
            service = False

        # set header
        header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }

        return selected_url, service, header

    # default record
    def yield_default_record(
        self,
        tenant_id,
        record_object,
        record_object_id,
        account,
        record_app,
        record_user,
        record_savedsearch_name,
        message,
    ):
        record = {
            "_time": time.time(),
            "tenant_id": tenant_id,
            "object": record_object,
            "object_id": record_object_id,
            "account": account,
            "app": record_app,
            "user": record_user,
            "savedsearch_name": record_savedsearch_name,
            "search": "None",
            "earliest_time": "None",
            "latest_time": "None",
            "cron_schedule": "None",
            "cron_exec_sequence_sec": "None",
            "description": "None",
            "disabled": "None",
            "is_scheduled": "None",
            "schedule_window": "None",
            "workload_pool": "None",
            "owner": "None",
            "sharing": "None",
            "metrics": "None",
            "json_data": "None",
            "version_id": "None",
            "message": message,
        }
        return record

    # ingest version
    def ingest_version(
        self, object_value, splunk_index, splunk_sourcetype, splunk_source, json_data
    ):
        # add for the indexing purposes
        new_event_json = {}
        new_event_json["tenant_id"] = self.tenant_id
        new_event_json["object"] = object_value
        new_event_json["object_category"] = "splk-wlk"

        for key, value in json_data.items():
            new_event_json[key] = value

        # add the event_id
        new_event_json["event_id"] = hashlib.sha256(
            json.dumps(json_data).encode()
        ).hexdigest()

        # Index the version
        try:
            trackme_ingest_version(
                index=splunk_index,
                sourcetype=splunk_sourcetype,
                source=splunk_source,
                event=json.dumps(new_event_json),
            )
            logging.debug(
                f'TrackMe version event created successfully, record="{json.dumps(json_data, indent=1)}"'
            )
        except Exception as e:
            logging.error(
                f'TrackMe version event creation failure, record="{json.dumps(json_data, indent=1)}", exception="{str(e)}"'
            )

    # get last updates table
    def get_last_updates(
        self,
        session_key,
        server_rest_uri,
        account,
    ):
        if account != "local":
            # get account
            account_dict = self.get_account(session_key, server_rest_uri, account)
            splunk_url = account_dict["splunk_url"]
            bearer_token = account_dict["token"]

            # Create a session within the generate function
            session = requests.Session()

            # Call target selector and pass the session as an argument
            selected_url, errors = self.select_url(session, splunk_url)

            # end of get configuration

            # If none of the endpoints could be reached
            if not selected_url:
                error_msg = "None of the endpoints provided in the account URLs could be reached successfully, verify your network connectivity!"
                error_msg += "Errors: " + ", ".join(
                    [f"{url}: {error}" for url, error in errors]
                )
                logging.error(error_msg)
                remote_service_established = None

            else:
                # Enforce https and remove trailing slash in the URL, if any
                selected_url = (
                    f"https://{selected_url.replace('https://', '').rstrip('/')}"
                )

                # use urlparse to extract relevant info from target
                parsed_url = urllib.parse.urlparse(selected_url)

                # Establish the remote service
                logging.debug(
                    f'Establishing connection to host="{parsed_url.hostname}" on port="{parsed_url.port}"'
                )

                # establish connectivity
                (
                    remote_service_established,
                    service,
                    header,
                ) = self.establish_remote_service(
                    selected_url,
                    bearer_token,
                    "nobody",
                    "search",
                    account,
                )

        else:
            # local connectivity
            service = self.service

        # Start logic
        if account == "local" or remote_service_established:
            # run a Splunk search against the target and store as a dict per savedsearch_name, containing the last known update epochtime and the user who updated it

            # kwargs
            kwargs_oneshot = {
                "earliest_time": "-60m",
                "latest_time": "now",
                "output_mode": "json",
                "count": 0,
            }

            search_string = f"""\
                search index=_internal sourcetype=splunkd_ui_access splunkd servicesNS "saved/searches" method=POST {self.filters_get_last_updates}
                | regex uri="/[^/]*/splunkd/__raw/servicesNS/[^/]*/[^/]*/saved/searches/[^/ ]*$" 
                | rex field=uri "/[^/]*/splunkd/__raw/servicesNS/[^/]*/[^/]*/saved/searches/(?<search_encoded>[^/\\? ]*)" 
                | eval savedsearch_name=urldecode(search_encoded) 
                | rename user as user 
                | fields _time savedsearch_name user
                | stats latest(user) as user, max(_time) as time by savedsearch_name
                | sort 0 savedsearch_name
            """

            start_time = time.time()

            # last_updates dict
            last_updates_dict = {}

            # run search
            try:
                reader = run_splunk_search(
                    service,
                    remove_leading_spaces(search_string),
                    kwargs_oneshot,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        last_updates_dict[item["savedsearch_name"]] = {
                            "user": item["user"],
                            "time": item["time"],
                        }

                # break while
                logging.debug(
                    f'tenant_id="{self.tenant_id}", get_last_updates successfully completed in {round(time.time() - start_time, 2)} seconds, {len(last_updates_dict)} results were returned.'
                )

            except Exception as e:
                msg = f'tenant_id="{self.tenant_id}", main search failed with exception="{str(e)}"'
                logging.error(msg)
                raise Exception(msg)

            # return the last_updates_dict
            return last_updates_dict

    # process savedsearch
    def process_savedsearch(
        self,
        session,
        record,
        kvrecordkey,
        kvrecorddict,
        local_splunkd_port,
        session_key,
        server_rest_uri,
        splunk_index,
        splunk_sourcetype,
        splunk_source,
        last_updates_dict,
        splk_general_workload_version_id_keys,
        account_cache=None,
        connection_cache=None,
    ):
        if account_cache is None:
            account_cache = {}
        if connection_cache is None:
            connection_cache = {}

        tenant_id = record.get("tenant_id")
        account = record.get("account")
        record_app = record.get("app")
        record_user = record.get("user")
        record_savedsearch_name = decode_unicode(record.get("savedsearch_name"))
        record_object = record.get("object")
        record_object_id = record.get("object_id")
        record_metrics = json.loads(record.get("metrics"))

        # if user is system, connect as nobody
        if record_user == "system":
            connect_user = "nobody"
        else:
            connect_user = record_user

        if record_savedsearch_name.startswith("_ACCELERATE"):
            return self.yield_default_record(
                tenant_id,
                record_object,
                record_object_id,
                account,
                record_app,
                record_user,
                record_savedsearch_name,
                "Not applicable for datamodel acceleration searches",
            )

        else:

            # check if record_savedsearch_name contains backslashes replaced with unicode, if so, decode it
            if "\\u005c" in record_savedsearch_name:
                record_savedsearch_name = record_savedsearch_name.replace(
                    "\\u005c", "\\"
                )

            if account != "local":
                # Performance optimization: cache account credentials per account name
                if account in account_cache:
                    account_dict = account_cache[account]
                else:
                    account_dict = self.get_account(session_key, server_rest_uri, account)
                    account_cache[account] = account_dict

                splunk_url = account_dict["splunk_url"]
                bearer_token = account_dict["token"]

                # Performance optimization: cache connection per (account, connect_user, app) tuple
                cache_key = (account, connect_user, record_app)
                if cache_key in connection_cache:
                    remote_service_established, service, header, selected_url = connection_cache[cache_key]
                    logging.debug(
                        f'reusing cached connection for account="{account}", user="{connect_user}", app="{record_app}"'
                    )
                else:
                    # Initialize defaults for the failure case
                    service = None
                    header = None

                    # Call target selector and pass the session as an argument
                    selected_url, errors = self.select_url(session, splunk_url)

                    # If none of the endpoints could be reached
                    if not selected_url:
                        error_msg = "None of the endpoints provided in the account URLs could be reached successfully, verify your network connectivity!"
                        logging.error(error_msg)
                        remote_service_established = None

                    else:
                        # Enforce https and remove trailing slash in the URL, if any
                        selected_url = (
                            f"https://{selected_url.replace('https://', '').rstrip('/')}"
                        )

                        # use urlparse to extract relevant info from target
                        parsed_url = urllib.parse.urlparse(selected_url)

                        # Establish the remote service
                        logging.debug(
                            f'Establishing connection to host="{parsed_url.hostname}" on port="{parsed_url.port}"'
                        )

                        # establish connectivity
                        (
                            remote_service_established,
                            service,
                            header,
                        ) = self.establish_remote_service(
                            selected_url,
                            bearer_token,
                            connect_user,
                            record_app,
                            account,
                        )

                        # will fail if the user does not exist anymore, then connect as nobody
                        if not remote_service_established:

                            logging.info(
                                f'connection has failed for user="{record_user}", retrying with "nobody", this is expected if we have a low level of privileges.'
                            )

                            (
                                remote_service_established,
                                service,
                                header,
                            ) = self.establish_remote_service(
                                selected_url,
                                bearer_token,
                                "nobody",
                                record_app,
                                account,
                            )

                    # Only cache successful connections to allow retry on transient failures
                    if remote_service_established:
                        connection_cache[cache_key] = (remote_service_established, service, header, selected_url)

            else:
                # Performance optimization: cache local connections per (account, connect_user, app) tuple
                cache_key = ("local", connect_user, record_app)
                if cache_key in connection_cache:
                    remote_service_established, service, header, selected_url = connection_cache[cache_key]
                    logging.debug(
                        f'reusing cached local connection for user="{connect_user}", app="{record_app}"'
                    )
                else:
                    # local connectivity
                    logging.debug("establish local connectivity")
                    selected_url, service, header = self.establish_local_service(
                        session_key, connect_user, record_app
                    )

                    # will fail if the user does not exist anymore, then connect as nobody
                    if not service:
                        selected_url, service, header = self.establish_local_service(
                            session_key, "nobody", record_app
                        )

                    if service:
                        logging.debug("local connectivity established successfully")

                    # Cache the local connection
                    connection_cache[cache_key] = (True if service else False, service, header, selected_url)

            # Start logic
            if account == "local" or remote_service_established:
                # Versioning collection
                versioning_collection_name = "kv_trackme_wlk_versioning_tenant_%s" % (
                    self.tenant_id
                )
                versioning_collection = self.service.kvstore[versioning_collection_name]

                # Orphan collection
                orphan_collection_name = "kv_trackme_wlk_orphan_status_tenant_%s" % (
                    self.tenant_id
                )
                orphan_collection = self.service.kvstore[orphan_collection_name]

                # process
                try:
                    logging.debug(
                        f"processing record_savedsearch_name={record_savedsearch_name}"
                    )
                    savedsearch = service.saved_searches[record_savedsearch_name]

                    # debug
                    logging.debug(
                        f'savedsearch="{savedsearch.name}", alternate="{savedsearch.links["alternate"]}"'
                    )

                    # record

                    # init
                    savedsearch_owner = None
                    savedsearch_sharing = None
                    savedsearch_orphan = None
                    version_id = None

                    #
                    # check orphan & retrieve acl
                    #

                    if self.check_orphan:
                        record_url = "%s/%s/%s" % (
                            selected_url,
                            savedsearch.links["alternate"],
                            "?add_orphan_field=yes&output_mode=json",
                        )
                    else:
                        record_url = "%s/%s/%s" % (
                            selected_url,
                            savedsearch.links["alternate"],
                            "/acl/list?output_mode=json",
                        )

                    try:
                        response = session.get(record_url, headers=header, verify=False)
                        savedsearch_content = json.loads(response.text).get("entry")[0][
                            "content"
                        ]
                        savedsearch_acl = json.loads(response.text).get("entry")[0][
                            "acl"
                        ]
                        savedsearch_owner = savedsearch_acl.get("owner")
                        savedsearch_app = savedsearch_acl.get("app")
                        savedsearch_sharing = savedsearch_acl.get("sharing")
                        savedsearch_orphan = savedsearch_content.get("orphan")
                        logging.debug(
                            f'get extended metadata for savedsearch="{savedsearch.name}" successful, orphan="{savedsearch_orphan}", acl="{json.dumps(savedsearch_acl, indent=2)}"'
                        )

                    except Exception as e:
                        logging.error(
                            f'get extended metadata for savedsearch="{savedsearch.name}" error, exception="{str(e)}"'
                        )
                        return self.yield_default_record(
                            tenant_id,
                            record_object,
                            record_object_id,
                            account,
                            record_app,
                            record_user,
                            record_savedsearch_name,
                            f'get extended metadata for savedsearch="{savedsearch.name}" error, exception="{str(e)}"',
                        )

                    # if check orphan
                    if self.check_orphan:
                        # Define the KV query
                        query_string = {
                            "_key": record_object_id,
                        }

                        try:
                            currentorphanrecord = orphan_collection.data.query(
                                query=json.dumps(query_string)
                            )[0]
                        except Exception as e:
                            currentorphanrecord = None

                        # set the orphan record
                        neworphanrecord = {
                            "_key": record_object_id,
                            "mtime": time.time(),
                            "object": record_object,
                            "app": record_app,
                            "user": record_user,
                            "orphan": savedsearch_orphan,
                        }

                        # update or insert
                        try:
                            if not currentorphanrecord:
                                # Register a new record
                                orphan_collection.data.insert(
                                    json.dumps(neworphanrecord)
                                )
                                # Update the existing record
                            else:
                                orphan_collection.data.update(
                                    record_object_id, json.dumps(neworphanrecord)
                                )
                        except Exception as e:
                            logging.error(
                                f'failed to update or insert the orphan collection record="{json.dumps(neworphanrecord, indent=2)}", exception="{str(e)}"'
                            )

                    # mandatory, stop here if we cannot retrieve the search
                    try:
                        savedsearch_search = savedsearch.content["search"]
                        savedsearch_content = savedsearch.content
                    except Exception as e:
                        logging.error(
                            f'failed to retrieve savedsearch content for savedsearch="{record_savedsearch_name}" we might not have enough permissions to do so, exception="{str(e)}"'
                        )
                        return self.yield_default_record(
                            tenant_id,
                            record_object,
                            record_object_id,
                            account,
                            record_app,
                            record_user,
                            record_savedsearch_name,
                            f'failed to retrieve savedsearch content for savedsearch="{record_savedsearch_name}", exception="{str(e)}"',
                        )

                    # do not fail for the following
                    savedsearch_cron_schedule = savedsearch_content.get("cron_schedule")
                    savedsearch_description = savedsearch_content.get("description")
                    savedsearch_disabled = savedsearch_content.get("disabled")
                    savedsearch_is_scheduled = savedsearch_content.get("is_scheduled")
                    savedsearch_schedule_window = savedsearch_content.get(
                        "schedule_window"
                    )
                    savedsearch_workload_pool = savedsearch_content.get("workload_pool")
                    savedsearch_earliest_time = savedsearch_content.get(
                        "dispatch.earliest_time"
                    )
                    savedsearch_latest_time = savedsearch_content.get(
                        "dispatch.latest_time"
                    )

                    # set the version_id using configurable keys
                    # splk_general_workload_version_id_keys is already a list from upstream processing
                    try:
                        if isinstance(splk_general_workload_version_id_keys, list):
                            version_id_keys = [key.strip() for key in splk_general_workload_version_id_keys if key and key.strip()]
                        else:
                            version_id_keys = [key.strip() for key in splk_general_workload_version_id_keys.split(",") if key and key.strip()]
                        
                        # Map configuration keys to their corresponding savedsearch values
                        key_mapping = {
                            "search": savedsearch_search,
                            "dispatch.earliest": savedsearch_earliest_time,
                            "dispatch.latest": savedsearch_latest_time,
                        }
                        
                        # Build version_hash using the configured keys
                        version_values = []
                        for key in version_id_keys:
                            try:
                                if key in key_mapping:
                                    # Use the mapped value for the 3 default keys
                                    value = key_mapping[key]
                                    version_values.append(str(value) if value is not None else "")
                                elif '*' in key or '?' in key:
                                    # Wildcard pattern - find all matching keys
                                    if savedsearch_content:
                                        matching_keys = [k for k in savedsearch_content.keys() if fnmatch.fnmatch(k, key)]
                                        matching_keys.sort()  # Sort for consistent ordering
                                        for matching_key in matching_keys:
                                            value = savedsearch_content.get(matching_key, "")
                                            version_values.append(str(value) if value is not None else "")
                                    else:
                                        # If no savedsearch_content, add empty string for consistency
                                        version_values.append("")
                                else:
                                    # For other keys, try to get the value directly from savedsearch_content
                                    value = savedsearch_content.get(key, "")
                                    version_values.append(str(value) if value is not None else "")
                            except Exception as e:
                                # If there's an error processing a specific key, use empty string and log
                                logging.warning(f'Error processing version_id key "{key}" for savedsearch "{savedsearch.name}": {str(e)}')
                                version_values.append("")
                        
                        version_hash = ":".join(version_values)
                    except Exception as e:
                        # Fallback to default behavior if there's an error with the configurable keys
                        logging.error(f'Error processing version_id keys for savedsearch "{savedsearch.name}": {str(e)}, falling back to default')
                        version_hash = "%s:%s:%s" % (
                            savedsearch_search or "",
                            savedsearch_earliest_time or "",
                            savedsearch_latest_time or "",
                        )
                    version_id = hashlib.sha256(
                        version_hash.encode("utf-8")
                    ).hexdigest()

                    # get the cron_exec_sequence_sec
                    try:
                        cron_exec_sequence_sec = cron_to_seconds(
                            savedsearch_cron_schedule
                        )
                    except Exception as e:
                        cron_exec_sequence_sec = 0

                    # set the json_data
                    json_data = {
                        "time_inspected": time.strftime(
                            "%d %b %Y %H:%M", time.localtime(time.time())
                        ),
                        "time_inspected_epoch": time.time(),
                        "savedsearch_name": savedsearch.name,
                        "search": savedsearch_search,
                        "earliest_time": savedsearch_earliest_time,
                        "latest_time": savedsearch_latest_time,
                        "cron_schedule": savedsearch_cron_schedule,
                        "cron_exec_sequence_sec": cron_exec_sequence_sec,
                        "description": savedsearch_description,
                        "disabled": savedsearch_disabled,
                        "is_scheduled": savedsearch_is_scheduled,
                        "schedule_window": savedsearch_schedule_window,
                        "workload_pool": savedsearch_workload_pool,
                        "app": savedsearch_app,
                        "owner": savedsearch_owner,
                        "sharing": savedsearch_sharing,
                        "metrics_summary": record_metrics,
                        "version_id": version_id,
                    }

                    if self.check_orphan:
                        json_data["orphan"] = savedsearch_orphan

                    # try find in the dict last_updates_dict the last known update for this savedsearch (time and user)
                    try:
                        if record_savedsearch_name in last_updates_dict:
                            last_update = last_updates_dict[record_savedsearch_name]
                            json_data["last_update_time_epoch"] = last_update["time"]
                            # create a last_update_time_human which is epoch strftime %c
                            json_data["last_update_time_human"] = time.strftime(
                                "%c", time.localtime(float(last_update["time"]))
                            )
                            json_data["last_update_user"] = last_update["user"]
                    except Exception as e:
                        logging.error(
                            f'failed to retrieve last update info for savedsearch="{record_savedsearch_name}", exception="{str(e)}"'
                        )

                    # empty json_dict
                    json_dict = {}

                    # if it exists already, update the KVstore record, otherwise create a new record
                    # if the record exists already, we also need to update the dictionary
                    if self.context in ("live"):
                        try:
                            if not kvrecordkey:
                                json_dict[version_id] = json_data
                                sorted_json_dict = self.sort_json_by_epoch(json_dict)
                                versioning_collection.data.insert(
                                    json.dumps(
                                        {
                                            "_key": record_object_id,
                                            "mtime": time.time(),
                                            "object": record_object,
                                            "version_dict": json.dumps(
                                                sorted_json_dict, indent=2
                                            ),
                                            "description": savedsearch_description,
                                            "current_version_id": version_id,
                                            "cron_exec_sequence_sec": cron_exec_sequence_sec,
                                        }
                                    )
                                )

                                # ingest
                                self.ingest_version(
                                    record_object,
                                    splunk_index,
                                    splunk_sourcetype,
                                    splunk_source,
                                    json_data,
                                )

                            else:
                                # update
                                search_change_detected = False
                                if not version_id in kvrecorddict:
                                    search_change_detected = True

                                # get the last currently known record for that instance
                                sorted_json_dict = self.sort_json_by_epoch(kvrecorddict)
                                last_known_record = sorted_json_dict[
                                    list(sorted_json_dict)[0]
                                ]

                                # get the last known earliest_time, latest_time, search from last_known_record
                                last_known_earliest_time = last_known_record.get(
                                    "earliest_time"
                                )
                                last_known_latest_time = last_known_record.get(
                                    "latest_time"
                                )
                                last_known_search = last_known_record.get("search")

                                kvrecorddict[version_id] = json_data
                                sorted_json_dict = self.sort_json_by_epoch(kvrecorddict)

                                # for each configured key, compare with the current record and create a diff_<field>
                                try:
                                    # Map configuration keys to their corresponding savedsearch values and last known values
                                    key_mapping = {
                                        "search": (savedsearch_search, last_known_search),
                                        "dispatch.earliest": (savedsearch_earliest_time, last_known_earliest_time),
                                        "dispatch.latest": (savedsearch_latest_time, last_known_latest_time),
                                    }
                                    
                                    # Generate diff strings for all configured keys
                                    for key in version_id_keys:
                                        try:
                                            if key in key_mapping:
                                                # Use the mapped values for the 3 default keys
                                                current_value, last_known_value = key_mapping[key]
                                                
                                                # Generate diff string if values are different (including empty to non-empty transitions)
                                                # Normalize values for comparison (treat None and empty string as equivalent)
                                                last_known_normalized = str(last_known_value).strip() if last_known_value is not None else ""
                                                current_normalized = str(current_value).strip() if current_value is not None else ""
                                                
                                                if last_known_normalized != current_normalized:
                                                    diff_string = self.generate_diff_string(
                                                        last_known_value, current_value
                                                    )
                                                    # Create diff field name by replacing dots with underscores and adding diff_ prefix
                                                    diff_field_name = f"diff_{key.replace('.', '_')}"
                                                    json_data[diff_field_name] = diff_string
                                                    
                                            elif '*' in key or '?' in key:
                                                # Wildcard pattern - find all matching keys and generate diff for each
                                                if savedsearch_content:
                                                    matching_keys = [k for k in savedsearch_content.keys() if fnmatch.fnmatch(k, key)]
                                                    matching_keys.sort()  # Sort for consistent ordering
                                                    
                                                    for matching_key in matching_keys:
                                                        current_value = savedsearch_content.get(matching_key, "") if savedsearch_content else ""
                                                        last_known_value = last_known_record.get(matching_key) if last_known_record else None
                                                        
                                                        # Generate diff string if values are different (including empty to non-empty transitions)
                                                        # Normalize values for comparison (treat None and empty string as equivalent)
                                                        last_known_normalized = str(last_known_value).strip() if last_known_value is not None else ""
                                                        current_normalized = str(current_value).strip() if current_value is not None else ""
                                                        
                                                        if last_known_normalized != current_normalized:
                                                            diff_string = self.generate_diff_string(
                                                                last_known_value, current_value
                                                            )
                                                            # Create diff field name by replacing dots with underscores and adding diff_ prefix
                                                            diff_field_name = f"diff_{matching_key.replace('.', '_')}"
                                                            json_data[diff_field_name] = diff_string
                                            else:
                                                # For other keys, get values directly from savedsearch_content and last_known_record
                                                current_value = savedsearch_content.get(key, "") if savedsearch_content else ""
                                                last_known_value = last_known_record.get(key) if last_known_record else None
                                                
                                                # Generate diff string if values are different (including empty to non-empty transitions)
                                                # Normalize values for comparison (treat None and empty string as equivalent)
                                                last_known_normalized = str(last_known_value).strip() if last_known_value is not None else ""
                                                current_normalized = str(current_value).strip() if current_value is not None else ""
                                                
                                                if last_known_normalized != current_normalized:
                                                    diff_string = self.generate_diff_string(
                                                        last_known_value, current_value
                                                    )
                                                    # Create diff field name by replacing dots with underscores and adding diff_ prefix
                                                    diff_field_name = f"diff_{key.replace('.', '_')}"
                                                    json_data[diff_field_name] = diff_string
                                        except Exception as e:
                                            # If there's an error processing a specific key, log and continue
                                            logging.warning(f'Error generating diff for key "{key}" for savedsearch "{savedsearch.name}": {str(e)}')
                                            continue
                                except Exception as e:
                                    # If there's an error with the entire diff generation, log and continue
                                    logging.error(f'Error in diff string generation for savedsearch "{savedsearch.name}": {str(e)}')

                                # ingest if a change is detected
                                if search_change_detected:
                                    # ingest
                                    self.ingest_version(
                                        record_object,
                                        splunk_index,
                                        splunk_sourcetype,
                                        splunk_source,
                                        json_data,
                                    )

                                # otherwise and if we have diff information for this record, make sure to preserve it
                                else:
                                    # Carry over last update and diff information if no change is detected
                                    if "last_update_time_epoch" in last_known_record:
                                        json_data["last_update_time_epoch"] = (
                                            last_known_record["last_update_time_epoch"]
                                        )
                                    if "last_update_time_human" in last_known_record:
                                        json_data["last_update_time_human"] = (
                                            last_known_record["last_update_time_human"]
                                        )
                                    if "last_update_user" in last_known_record:
                                        json_data["last_update_user"] = (
                                            last_known_record["last_update_user"]
                                        )
                                    if "diff_search" in last_known_record:
                                        json_data["diff_search"] = last_known_record[
                                            "diff_search"
                                        ]

                                # update the KVstore record
                                versioning_collection.data.update(
                                    record_object_id,
                                    {
                                        "_key": record_object_id,
                                        "mtime": time.time(),
                                        "object": record_object,
                                        "version_dict": json.dumps(
                                            sorted_json_dict, indent=2
                                        ),
                                        "description": savedsearch_description,
                                        "current_version_id": version_id,
                                        "cron_exec_sequence_sec": cron_exec_sequence_sec,
                                    },
                                )

                        except Exception as e:
                            logging.error(
                                f'tenant_id="{tenant_id}", object="{record_object}", failure while trying to insert the hybrid KVstore record, exception="{e}"'
                            )

                    # return the final record
                    return {
                        "_time": time.time(),
                        "tenant_id": tenant_id,
                        "object": record_object,
                        "object_id": record_object_id,
                        "account": account,
                        "app": record_app,
                        "user": record_user,
                        "savedsearch_name": record_savedsearch_name,
                        "search": savedsearch_search,
                        "earliest_time": savedsearch_earliest_time,
                        "latest_time": savedsearch_latest_time,
                        "cron_schedule": savedsearch_cron_schedule,
                        "cron_exec_sequence_sec": cron_exec_sequence_sec,
                        "description": savedsearch_description,
                        "disabled": savedsearch_disabled,
                        "is_scheduled": savedsearch_is_scheduled,
                        "schedule_window": savedsearch_schedule_window,
                        "workload_pool": savedsearch_workload_pool,
                        "owner": savedsearch_owner,
                        "sharing": savedsearch_sharing,
                        "metrics": json.dumps(record_metrics, indent=2),
                        "message": "saved search metadata were retrieved successfully",
                        "version_id": version_id,
                        "json_data": json_data,
                    }

                except Exception as e:
                    # Use the new function to yield the default record when an error occurs
                    return self.yield_default_record(
                        tenant_id,
                        record_object,
                        record_object_id,
                        account,
                        record_app,
                        record_user,
                        record_savedsearch_name,
                        f'failed to retrieve saved search metadata, if the report was recently deleted then this is expected and will disappear shortly, exception="{str(e)}"',
                    )

            else:
                # Use the new function to yield the default record when an error occurs
                return self.yield_default_record(
                    tenant_id,
                    record_object,
                    record_object_id,
                    account,
                    record_app,
                    record_user,
                    record_savedsearch_name,
                    "failed to retrieve saved search metadata, if the report was recently deleted then this is expected and will disappear shortly",
                )

    # main
    def stream(self, records):
        if self:
            # start perf duration counter
            start = time.time()

            # Add records in a proper list rather than the builtin generator to address some issues with complex savedsearch names
            records_list = []
            for record in records:
                records_list.append(record)

            # Track execution times
            average_execution_time = 0

            # max runtime
            max_runtime = int(self.max_runtime_sec)

            # Retrieve the search cron schedule
            savedsearch_name = self.report.replace("_wrapper", "_tracker")
            savedsearch = self.service.saved_searches[savedsearch_name]
            savedsearch_cron_schedule = savedsearch.content["cron_schedule"]

            # get the cron_exec_sequence_sec
            try:
                cron_exec_sequence_sec = int(cron_to_seconds(savedsearch_cron_schedule))
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="wlk", failed to convert the cron schedule to seconds, error="{str(e)}"'
                )
                cron_exec_sequence_sec = max_runtime

            # the max_runtime cannot be bigger than the cron_exec_sequence_sec
            if max_runtime > cron_exec_sequence_sec:
                max_runtime = cron_exec_sequence_sec

            logging.info(
                f'max_runtime="{max_runtime}",  savedsearch_name="{savedsearch_name}", savedsearch_cron_schedule="{savedsearch_cron_schedule}", cron_exec_sequence_sec="{cron_exec_sequence_sec}"'
            )

            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # Get the session key
            session_key = self._metadata.searchinfo.session_key

            # Get splunkd_port
            local_splunkd_port = urllib.parse.urlparse(
                self._metadata.searchinfo.splunkd_uri
            ).port

            # from global configuration, get the value for splk_general_workload_version_id_keys
            splk_general_workload_version_id_keys = reqinfo["trackme_conf"]["splk_general"]["splk_general_workload_version_id_keys"]

            # split the value into a list
            splk_general_workload_version_id_keys = splk_general_workload_version_id_keys.split(",")

            # list of forbidden apps
            exclude_apps = set(self.exclude_apps.split(","))

            # Versioning collection
            versioning_collection_name = "kv_trackme_wlk_versioning_tenant_%s" % (
                self.tenant_id
            )
            versioning_collection = self.service.kvstore[versioning_collection_name]

            # Get configuration and define metadata
            trackme_summary_idx = reqinfo["trackme_conf"]["index_settings"][
                "trackme_summary_idx"
            ]
            splunk_index = trackme_summary_idx
            splunk_sourcetype = "trackme:wlk:version_id"
            splunk_source = "trackme_ingest_version"

            # end of get configuration

            #
            # before processing the records, loop in records and get the first value for account in the first record
            #

            target_account = None
            for record in records_list:
                target_account = record.get("account")
                break

            if target_account is not None:
                try:
                    last_updates_dict = self.get_last_updates(
                        session_key,
                        reqinfo["server_rest_uri"],
                        target_account,
                    )

                except Exception as e:
                    logging.error(
                        f'tenant_id="{self.tenant_id}", component="wlk", Failed to call get_last_updates with exception="{str(e)}"'
                    )
                    last_updates_dict = {}
            else:
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="wlk", no records received from upstream, skipping get_last_updates'
                )
                last_updates_dict = {}

            #
            # Performance optimization: batch-load versioning collection upfront
            # Instead of per-record KV Store queries, load all records once into a dict
            #

            versioning_dict = {}
            versioning_batch_loaded = False
            try:
                batch_load_start = time.time()
                end = False
                skip_tracker = 0
                while not end:
                    process_records = versioning_collection.data.query(skip=skip_tracker, limit=1000)
                    if len(process_records) == 0:
                        end = True
                    else:
                        for item in process_records:
                            key = item.get("_key")
                            if key:
                                versioning_dict[key] = item
                        skip_tracker += len(process_records)
                versioning_batch_loaded = True
                logging.info(
                    f'tenant_id="{self.tenant_id}", component="wlk", batch-loaded versioning collection, no_records="{len(versioning_dict)}", run_time="{round(time.time() - batch_load_start, 3)}"'
                )
            except Exception as e:
                logging.error(
                    f'tenant_id="{self.tenant_id}", component="wlk", failed to batch-load versioning collection, will use per-record queries as fallback, exception="{str(e)}"'
                )
                versioning_dict = {}
                versioning_batch_loaded = False

            #
            # Performance optimization: connection caching
            # Cache account credentials and service connections to avoid re-establishing per record
            #

            account_cache = {}       # account_name -> account_dict (credentials, urls)
            connection_cache = {}    # (account, connect_user, app) -> (service, header, selected_url)

            #
            # loop through upstream records
            #

            # Initialize sum of execution times and count of iterations
            total_execution_time = 0
            iteration_count = 0

            # Other initializations
            max_runtime = int(self.max_runtime_sec)

            # for the handler events
            report_objects_dict = {}

            with requests.Session() as session:
                # Loop in the results
                for record in records_list:

                    # iteration start
                    iteration_start_time = time.time()

                    if not record.get("app") in exclude_apps:
                        # object_id
                        record_object_id = record.get("object_id")

                        # add the object_id to the report_objects_dict
                        report_objects_dict[record_object_id] = record.get("object")

                        # Try to get the KVstore record
                        if versioning_batch_loaded:
                            # Use batch-loaded dict for O(1) lookup
                            if record_object_id in versioning_dict:
                                kvrecord = versioning_dict[record_object_id]
                                try:
                                    kvrecordkey = kvrecord.get("_key")
                                    kvrecorddict = json.loads(kvrecord.get("version_dict"))
                                except Exception:
                                    # Match get_kv_record() error handling: set all to None
                                    kvrecordkey = None
                                    kvrecord = None
                                    kvrecorddict = None
                            else:
                                kvrecord = None
                                kvrecordkey = None
                                kvrecorddict = None
                        else:
                            # Fallback to per-record KV Store query
                            kvrecord, kvrecordkey, kvrecorddict = self.get_kv_record(
                                versioning_collection, record_object_id
                            )

                        # Process the saved search and yield the result
                        yield self.process_savedsearch(
                            session,
                            record,
                            kvrecordkey,
                            kvrecorddict,
                            local_splunkd_port,
                            session_key,
                            reqinfo["server_rest_uri"],
                            splunk_index,
                            splunk_sourcetype,
                            splunk_source,
                            last_updates_dict,
                            splk_general_workload_version_id_keys,
                            account_cache,
                            connection_cache,
                        )

                    # Calculate the execution time for this iteration
                    iteration_end_time = time.time()
                    execution_time = iteration_end_time - iteration_start_time

                    # Update total execution time and iteration count
                    total_execution_time += execution_time
                    iteration_count += 1

                    # Calculate average execution time
                    if iteration_count > 0:
                        average_execution_time = total_execution_time / iteration_count
                    else:
                        average_execution_time = 0

                    # Check if there is enough time left to continue
                    current_time = time.time()
                    elapsed_time = current_time - start
                    if elapsed_time + average_execution_time + 120 >= max_runtime:
                        logging.info(
                            f'tenant_id="{self.tenant_id}", component="wlk", max_runtime="{max_runtime}" is about to be reached, current_runtime="{elapsed_time}", job will be terminated now'
                        )
                        break

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
                                "handler_troubleshoot_search": f"index=_internal sourcetype=trackme:custom_commands:trackmesplkwlkgetreportsdefstream tenant_id={self.tenant_id}",
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

                if self.report:
                    logging.info(
                        f'trackmesplkwlkgetreportsdefstream has terminated, report="{self.report}", run_time="{round(time.time() - start, 3)}"'
                    )
                else:
                    logging.info(
                        f'trackmesplkwlkgetreportsdefstream has terminated, run_time="{round(time.time() - start, 3)}"'
                    )


dispatch(SplkWlkGetReportsDef, sys.argv, sys.stdin, sys.stdout, __name__)
