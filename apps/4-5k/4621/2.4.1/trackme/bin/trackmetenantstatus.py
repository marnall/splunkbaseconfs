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

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# Networking imports
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_load_tenants_summary.log" % splunkhome,
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

# Import trackme libs
from trackme_libs import trackme_reqinfo
from trackme_libs_load import has_user_access as _lib_has_user_access


@Configuration(distributed=False)
class TrackMeTenantsStatus(GeneratingCommand):
    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Optional, the tenant identifier.""",
        require=False,
        default=None,
    )

    output = Option(
        doc="""
        **Syntax:** **output=****
        **Description:** Optional, return the either the status per tenant/report (default), or the list of tenant the user is allowed to access to.
         Valid options are: status | tenants""",
        require=False,
        default="status",
        validate=validators.Match("output", r"^(status|tenants)$"),
    )

    # Thin pass-through to the lib's canonical access check so the role +
    # username allowlist logic lives in one place (trackme_libs_load).
    def has_user_access(self, effective_roles, record, username=None):
        return _lib_has_user_access(effective_roles, record, username)

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

    def generate(self, **kwargs):
        if self:
            # Get request info and set logging level
            reqinfo = trackme_reqinfo(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
            log.setLevel(reqinfo["logging_level"])

            # get current user
            username = self._metadata.searchinfo.username

            # get user info
            users = self.service.users

            # Get roles for the current user
            username_roles = []
            for user in users:
                if user.name == username:
                    username_roles = user.roles
            logging.info(f'username="{username}", roles="{username_roles}"')

            # get roles
            roles = self.service.roles
            roles_dict = {}

            for role in roles:
                imported_roles_value = role.content.get("imported_roles", [])
                if imported_roles_value:  # Check if it has a non-empty value
                    roles_dict[role.name] = imported_roles_value

            logging.debug(f"roles_dict={json.dumps(roles_dict, indent=2)}")

            # get effective roles, which takes into account both direct membership and inheritance
            effective_roles = self.get_effective_roles(username_roles, roles_dict)

            # Data collection
            collection_name = "kv_trackme_virtual_tenants"
            collection = self.service.kvstore[collection_name]

            # Exec summary collection
            collection_exec_summary_name = "kv_trackme_virtual_tenants_exec_summary"
            collection_exec_summary = self.service.kvstore[collection_exec_summary_name]

            # Define the KV query search string
            if self.tenant_id and self.tenant_id != "*":
                query_string_filter = {
                    "tenant_id": self.tenant_id,
                    "tenant_status": "enabled",
                }
            elif self.tenant_id and self.tenant_id == "*":
                query_string_filter = {
                    "tenant_status": "enabled",
                }
            else:
                query_string_filter = {
                    "tenant_status": "enabled",
                }

            query_string = {"$and": [query_string_filter]}

            # log debug
            logging.debug(f"query string={json.dumps(query_string)}")

            # Pull per-tenant `tenant_allowed_users` from the trackme_vtenants conf
            # so we can apply the username allowlist alongside the RBAC role check.
            # Failure here is non-fatal — fall back to "no allowlist" (role-only).
            vtenant_allowed_users_map = {}
            try:
                conf = self.service.confs["trackme_vtenants"]
                for stanza in conf:
                    vtenant_allowed_users_map[stanza.name] = stanza.content.get(
                        "tenant_allowed_users", ""
                    )
            except Exception as e:
                logging.warning(
                    f'unable to load trackme_vtenants conf for username allowlist, exception="{str(e)}"'
                )

            # Get the records
            filtered_records = []
            try:
                records = collection.data.query(query=json.dumps(query_string))

                # Loop through the records
                for record in records:
                    # handle all other cases and use RBAC accordingly to the tenant

                    # log
                    logging.info(
                        f'checking permissions of user="{username}" with roles="{username_roles}" for tenant_id="{record["tenant_id"]}"'
                    )

                    record["tenant_allowed_users"] = vtenant_allowed_users_map.get(
                        record["tenant_id"], ""
                    )

                    if self.has_user_access(
                        effective_roles, record, username
                    ) or username in ("splunk-system-user"):
                        filtered_records.append(record)

                # For each record in records, get the tenant_id, component and load the status as a dict
                for filtered_record in filtered_records:
                    tenant_id = filtered_record.get("tenant_id")
                    component = filtered_record.get("component")

                    # counter
                    count = 0

                    # Simply return the tenant record filtered from RBAC
                    if self.output == "tenants":

                        # Add schema_version_required to the record
                        schema_version_required = int(
                            reqinfo.get("schema_version_required")
                        )
                        filtered_record["schema_version_required"] = (
                            schema_version_required
                        )

                        # Set the status of tenant_updated_status, if schema_version in the record is equal to schema_version_required,
                        # the status is "updated", otherwise it is "pending"
                        # If schema_version_required is 0 (version retrieval failed), treat all tenants as "updated"
                        # to align with graceful degradation when DB Connect causes permission issues
                        if schema_version_required == 0:
                            filtered_record["tenant_updated_status"] = "updated"
                        else:
                            # Handle case where schema_version is missing from the record
                            schema_version_raw = filtered_record.get("schema_version")
                            if schema_version_raw is None:
                                # If schema_version is missing, use "undetermined" to indicate we cannot determine the status
                                # This is different from "pending" which implies an upgrade is in progress
                                filtered_record["tenant_updated_status"] = "undetermined"
                            elif int(schema_version_raw) == schema_version_required:
                                filtered_record["tenant_updated_status"] = "updated"
                            else:
                                filtered_record["tenant_updated_status"] = "pending"

                        # yield_record
                        yield_record = {}
                        for key, value in filtered_record.items():
                            if key == "_key":
                                continue
                            yield_record[key] = value

                        yield_record["_time"] = time.time()
                        yield_record["_raw"] = json.dumps(yield_record)

                        # yield
                        yield yield_record

                    # Handle and return the status record
                    elif self.output == "status":
                        try:
                            # Read exec summary from the dedicated collection
                            exec_summary_query = {"tenant_id": tenant_id}
                            exec_summary_records = collection_exec_summary.data.query(
                                query=json.dumps(exec_summary_query)
                            )
                            exec_summary_raw = (
                                exec_summary_records[0].get("tenant_objects_exec_summary")
                                if exec_summary_records
                                else None
                            )
                            tenant_objects_exec_summary = json.loads(exec_summary_raw) if exec_summary_raw else None
                            if not tenant_objects_exec_summary:
                                raise ValueError("No exec summary data available")

                            # increment
                            count += 1

                            # For each report, render the status summary
                            for report in tenant_objects_exec_summary:
                                subrecord_dict = tenant_objects_exec_summary.get(report)

                                try:
                                    last_duration = round(
                                        float(subrecord_dict.get("last_duration")), 3
                                    )
                                except Exception as e:
                                    last_duration = 0

                                # get last_exec
                                last_exec = subrecord_dict.get("last_exec", None)

                                if last_exec:
                                    # turn into a human readable format with strftime %c
                                    try:
                                        last_exec = float(last_exec)
                                        last_exec = time.strftime(
                                            "%c", time.localtime(last_exec)
                                        )
                                    except Exception as e:
                                        pass

                                subrecord = {
                                    "_time": time.time(),
                                    "tenant_id": tenant_id,
                                    "component": subrecord_dict.get("component"),
                                    "report": report,
                                    "earliest": subrecord_dict.get("earliest"),
                                    "latest": subrecord_dict.get("latest"),
                                    "last_status": subrecord_dict.get("last_status"),
                                    "last_exec": last_exec,
                                    "last_duration": last_duration,
                                    "last_result": subrecord_dict.get("last_result"),
                                }
                                subrecord["_raw"] = json.dumps(subrecord)

                                # yield
                                yield subrecord

                        except Exception as e:
                            logging.warning(
                                f'failed to retrieve tenant_objects_exec_summary with exception="{str(e)}"'
                            )

                        # if there are no reports for this tenant, yield a single placeholder record
                        if count == 0:
                            nonerecord = {
                                "_time": time.time(),
                                "tenant_id": tenant_id,
                                "component": "none",
                                "report": "none",
                                "earliest": "none",
                                "latest": "none",
                                "last_status": "none",
                                "last_exec": "none",
                                "last_duration": "none",
                                "last_result": "none",
                            }
                            nonerecord["_raw"] = json.dumps(nonerecord)

                            # yield
                            yield nonerecord

            except Exception as e:
                # yield
                yield {
                    "_time": str(time.time()),
                    "_raw": f'failed to retrieve tenant_objects_exec_summary with exception="{str(e)}"',
                }


dispatch(TrackMeTenantsStatus, sys.argv, sys.stdin, sys.stdout, __name__)
