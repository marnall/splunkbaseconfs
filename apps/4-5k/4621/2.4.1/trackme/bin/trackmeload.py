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

# Built-in modules
import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

# Third-party modules
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_load_tenants.log" % splunkhome,
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

# Splunk libs
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
    mode = Option(
        doc="""
        **Syntax:** **mode=****
        **Description:** The mode, valid options: <full|expanded>""",
        require=False,
        default="full",
        validate=validators.Match("mode", r"^(full|expanded)$"),
    )

    def get_suffix(self, s):
        parts = s.split("-")
        return parts[-1]

    def getfieldvalue(self, jsonData, fieldName):
        value = jsonData.get(fieldName, "null")
        if isinstance(value, bool):
            # Preserve numerical boolean values
            return int(value)
        return value

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

    def process_exec_summary(self, exec_summary_json):
        summary_data = json.loads(exec_summary_json)

        components_data = {}
        for item in summary_data.values():
            component = item["component"]

            if component not in components_data:
                components_data[component] = {"last_exec": 0, "status": 0}

            last_exec = float(item["last_exec"])
            if last_exec > components_data[component]["last_exec"]:
                components_data[component]["last_exec"] = last_exec
                components_data[component]["status"] = (
                    0 if item["last_status"] == "success" else 1
                )

        return components_data

    def get_vtenants_accounts(self, session_key, splunkd_uri):
        # Define an header for requests authenticated communications with splunkd
        header = {
            "Authorization": "Splunk %s" % session_key,
            "Content-Type": "application/json",
        }

        # Add the vtenant account
        url = "%s/services/trackme/v2/vtenants/vtenants_accounts" % (splunkd_uri)

        # Proceed
        try:
            response = requests.post(url, headers=header, verify=False, timeout=600)
            if response.status_code not in (200, 201, 204):
                msg = f'get vtenant account has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(msg)
            else:
                vtenants_account = response.json()
                logging.debug(
                    f'get vtenant account was operated successfully, response.status_code="{response.status_code}"'
                )
                logging.debug(
                    f"vtenants_account={json.dumps(vtenants_account, indent=2)}"
                )
        except Exception as e:
            msg = f'get vtenant account has failed, exception="{str(e)}"'
            logging.error(msg)
            raise Exception(msg)

        return vtenants_account

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
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

        # Summary state collection
        summary_state_collection_name = "kv_trackme_virtual_tenants_entities_summary"
        summary_state_collection = self.service.kvstore[summary_state_collection_name]

        # Exec summary collection
        exec_summary_collection_name = "kv_trackme_virtual_tenants_exec_summary"
        exec_summary_collection = self.service.kvstore[exec_summary_collection_name]

        # get vtenants_account
        try:
            vtenants_account = self.get_vtenants_accounts(
                self._metadata.searchinfo.session_key,
                self._metadata.searchinfo.splunkd_uri,
            )
        except Exception as e:
            raise Exception(
                f'get_vtenants_accounts has failed with exception="{str(e)}"'
            )

        # final yield record
        yield_record = []

        # Get the records
        filtered_records = []
        try:
            records = collection.data.query()

            # loop through records, for each record get the alias value from vtenants_account
            # and  add to the record
            for record in records:
                # get the tenant_id
                tenant_id = record["tenant_id"]

                # get the alias
                alias = vtenants_account[tenant_id].get("alias", tenant_id)

                # add alias to record
                record["tenant_alias"] = alias

                # Per-tenant username allowlist (vtenant_account-level config).
                record["tenant_allowed_users"] = vtenants_account[tenant_id].get(
                    "tenant_allowed_users", ""
                )

            sorted_records = sorted(records, key=lambda x: x["tenant_alias"])

            # Filter records based on user access
            filtered_records = [
                record
                for record in sorted_records
                if self.has_user_access(effective_roles, record, username)
                or username in ("splunk-system-user")
            ]

            # render
            for filtered_record in filtered_records:
                try:
                    # log debug
                    logging.info(
                        f'Inspecting record="{json.dumps(filtered_record, indent=2)}"'
                    )

                    # get the tenant_id
                    tenant_id = filtered_record["tenant_id"]

                    # lookup the summary state
                    try:
                        query_string = {
                            "tenant_id": tenant_id,
                        }
                        summary_state_record = summary_state_collection.data.query(
                            query=json.dumps(query_string)
                        )[0]
                        logging.debug(
                            f'tenant_id="{tenant_id}", summary state found, record="{json.dumps(summary_state_record)}"'
                        )

                        # add summary_state_record fields to filtered_record
                        for k, v in summary_state_record.items():
                            if k != "tenant_id" and not k.startswith("_"):
                                filtered_record[k] = v

                    except Exception as e:
                        logging.debug(
                            f'tenant_id="{tenant_id}", no summary state is available, exception="{str(e)}"'
                        )

                    # Read and process tenant_objects_exec_summary from the dedicated collection
                    try:
                        exec_summary_query = {"tenant_id": tenant_id}
                        exec_summary_records = exec_summary_collection.data.query(
                            query=json.dumps(exec_summary_query)
                        )
                        if exec_summary_records:
                            exec_summary_raw = exec_summary_records[0].get("tenant_objects_exec_summary")
                            filtered_record["tenant_objects_exec_summary"] = exec_summary_raw
                            exec_summary_data = self.process_exec_summary(exec_summary_raw)
                            for component, data in exec_summary_data.items():
                                # get suffix
                                short_component = self.get_suffix(component)

                                filtered_record[f"{short_component}_status"] = data[
                                    "status"
                                ]
                                filtered_record[f"{short_component}_last_exec"] = data[
                                    "last_exec"
                                ]
                    except Exception as e:
                        logging.error(
                            f'tenant_id="{tenant_id}", failed to process exec summary, exception="{str(e)}"'
                        )

                    # yield needs to be explicit and gen field names and values explicitly
                    try:
                        tenant_id = self.getfieldvalue(filtered_record, "tenant_id")
                        description = vtenants_account[tenant_id].get("description", "")
                        alias = vtenants_account[tenant_id].get("alias", tenant_id)

                        new_record = {
                            "tenant_id": tenant_id,
                            "tenant_alias": alias,
                            "tenant_status": self.getfieldvalue(
                                filtered_record, "tenant_status"
                            ),
                            "tenant_desc": description,
                            "tenant_owner": self.getfieldvalue(
                                filtered_record, "tenant_owner"
                            ),
                            "tenant_roles_admin": self.getfieldvalue(
                                filtered_record, "tenant_roles_admin"
                            ),
                            "tenant_roles_user": self.getfieldvalue(
                                filtered_record, "tenant_roles_user"
                            ),
                            "tenant_dsm_enabled": self.getfieldvalue(
                                filtered_record, "tenant_dsm_enabled"
                            ),
                            "tenant_cim_enabled": self.getfieldvalue(
                                filtered_record, "tenant_cim_enabled"
                            ),
                            "tenant_flx_enabled": self.getfieldvalue(
                                filtered_record, "tenant_flx_enabled"
                            ),
                            "tenant_fqm_enabled": self.getfieldvalue(
                                filtered_record, "tenant_fqm_enabled"
                            ),
                            "tenant_dhm_enabled": self.getfieldvalue(
                                filtered_record, "tenant_dhm_enabled"
                            ),
                            "tenant_mhm_enabled": self.getfieldvalue(
                                filtered_record, "tenant_mhm_enabled"
                            ),
                            "tenant_wlk_enabled": self.getfieldvalue(
                                filtered_record, "tenant_wlk_enabled"
                            ),
                            "tenant_dhm_root_constraint": self.getfieldvalue(
                                filtered_record, "tenant_dhm_root_constraint"
                            ),
                            "tenant_mhm_root_constraint": self.getfieldvalue(
                                filtered_record, "tenant_mhm_root_constraint"
                            ),
                            "tenant_cim_objects": self.getfieldvalue(
                                filtered_record, "tenant_cim_objects"
                            ),
                            "tenant_alert_objects": self.getfieldvalue(
                                filtered_record, "tenant_alert_objects"
                            ),
                            "tenant_dsm_hybrid_objects": self.getfieldvalue(
                                filtered_record, "tenant_dsm_hybrid_objects"
                            ),
                            "tenant_objects_exec_summary": self.getfieldvalue(
                                filtered_record, "tenant_objects_exec_summary"
                            ),
                            "tenant_idx_settings": self.getfieldvalue(
                                filtered_record, "tenant_idx_settings"
                            ),
                            "tenant_replica": self.getfieldvalue(
                                filtered_record, "tenant_replica"
                            ),
                            "key": self.getfieldvalue(filtered_record, "_key"),
                            "report_entities_count": self.getfieldvalue(
                                filtered_record, "report_entities_count"
                            ),
                            "dhm_entities": self.getfieldvalue(
                                filtered_record, "dhm_entities"
                            ),
                            "dhm_critical_red_priority": self.getfieldvalue(
                                filtered_record, "dhm_critical_red_priority"
                            ),
                            "dhm_high_red_priority": self.getfieldvalue(
                                filtered_record, "dhm_high_red_priority"
                            ),
                            "dhm_last_exec": self.getfieldvalue(
                                filtered_record, "dhm_last_exec"
                            ),
                            "dhm_low_red_priority": self.getfieldvalue(
                                filtered_record, "dhm_low_red_priority"
                            ),
                            "dhm_medium_red_priority": self.getfieldvalue(
                                filtered_record, "dhm_medium_red_priority"
                            ),
                            "dsm_entities": self.getfieldvalue(
                                filtered_record, "dsm_entities"
                            ),
                            "dsm_critical_red_priority": self.getfieldvalue(
                                filtered_record, "dsm_critical_red_priority"
                            ),
                            "dsm_high_red_priority": self.getfieldvalue(
                                filtered_record, "dsm_high_red_priority"
                            ),
                            "dsm_last_exec": self.getfieldvalue(
                                filtered_record, "dsm_last_exec"
                            ),
                            "dsm_low_red_priority": self.getfieldvalue(
                                filtered_record, "dsm_low_red_priority"
                            ),
                            "dsm_medium_red_priority": self.getfieldvalue(
                                filtered_record, "dsm_medium_red_priority"
                            ),
                            "mhm_entities": self.getfieldvalue(
                                filtered_record, "mhm_entities"
                            ),
                            "mhm_critical_red_priority": self.getfieldvalue(
                                filtered_record, "mhm_critical_red_priority"
                            ),
                            "mhm_high_red_priority": self.getfieldvalue(
                                filtered_record, "mhm_high_red_priority"
                            ),
                            "mhm_last_exec": self.getfieldvalue(
                                filtered_record, "mhm_last_exec"
                            ),
                            "mhm_low_red_priority": self.getfieldvalue(
                                filtered_record, "mhm_low_red_priority"
                            ),
                            "mhm_medium_red_priority": self.getfieldvalue(
                                filtered_record, "mhm_medium_red_priority"
                            ),
                            "cim_entities": self.getfieldvalue(
                                filtered_record, "cim_entities"
                            ),
                            "cim_critical_red_priority": self.getfieldvalue(
                                filtered_record, "cim_critical_red_priority"
                            ),
                            "cim_high_red_priority": self.getfieldvalue(
                                filtered_record, "cim_high_red_priority"
                            ),
                            "cim_last_exec": self.getfieldvalue(
                                filtered_record, "cim_last_exec"
                            ),
                            "cim_low_red_priority": self.getfieldvalue(
                                filtered_record, "cim_low_red_priority"
                            ),
                            "cim_medium_red_priority": self.getfieldvalue(
                                filtered_record, "cim_medium_red_priority"
                            ),
                            "flx_entities": self.getfieldvalue(
                                filtered_record, "flx_entities"
                            ),
                            "flx_critical_red_priority": self.getfieldvalue(
                                filtered_record, "flx_critical_red_priority"
                            ),
                            "flx_high_red_priority": self.getfieldvalue(
                                filtered_record, "flx_high_red_priority"
                            ),
                            "flx_last_exec": self.getfieldvalue(
                                filtered_record, "flx_last_exec"
                            ),
                            "flx_low_red_priority": self.getfieldvalue(
                                filtered_record, "flx_low_red_priority"
                            ),
                            "flx_medium_red_priority": self.getfieldvalue(
                                filtered_record, "flx_medium_red_priority"
                            ),
                            "fqm_entities": self.getfieldvalue(
                                filtered_record, "fqm_entities"
                            ),
                            "fqm_critical_red_priority": self.getfieldvalue(
                                filtered_record, "fqm_critical_red_priority"
                            ),
                            "fqm_high_red_priority": self.getfieldvalue(
                                filtered_record, "fqm_high_red_priority"
                            ),
                            "fqm_last_exec": self.getfieldvalue(
                                filtered_record, "fqm_last_exec"
                            ),
                            "fqm_low_red_priority": self.getfieldvalue(
                                filtered_record, "fqm_low_red_priority"
                            ),
                            "fqm_medium_red_priority": self.getfieldvalue(
                                filtered_record, "fqm_medium_red_priority"
                            ),
                            "wlk_entities": self.getfieldvalue(
                                filtered_record, "wlk_entities"
                            ),
                            "wlk_critical_red_priority": self.getfieldvalue(
                                filtered_record, "wlk_critical_red_priority"
                            ),
                            "wlk_high_red_priority": self.getfieldvalue(
                                filtered_record, "wlk_high_red_priority"
                            ),
                            "wlk_last_exec": self.getfieldvalue(
                                filtered_record, "wlk_last_exec"
                            ),
                            "wlk_low_red_priority": self.getfieldvalue(
                                filtered_record, "wlk_low_red_priority"
                            ),
                            "wlk_medium_red_priority": self.getfieldvalue(
                                filtered_record, "wlk_medium_red_priority"
                            ),
                            "all_status": self.getfieldvalue(
                                filtered_record, "all_status"
                            ),
                            "dhm_status": self.getfieldvalue(
                                filtered_record, "dhm_status"
                            ),
                            "dsm_status": self.getfieldvalue(
                                filtered_record, "dsm_status"
                            ),
                            "mhm_status": self.getfieldvalue(
                                filtered_record, "mhm_status"
                            ),
                            "cim_status": self.getfieldvalue(
                                filtered_record, "cim_status"
                            ),
                            "flx_status": self.getfieldvalue(
                                filtered_record, "flx_status"
                            ),
                            "fqm_status": self.getfieldvalue(
                                filtered_record, "fqm_status"
                            ),
                            "wlk_status": self.getfieldvalue(
                                filtered_record, "wlk_status"
                            ),
                            "all_last_exec": self.getfieldvalue(
                                filtered_record, "all_last_exec"
                            ),
                            "dhm_last_exec": self.getfieldvalue(
                                filtered_record, "dhm_last_exec"
                            ),
                            "dsm_last_exec": self.getfieldvalue(
                                filtered_record, "dsm_last_exec"
                            ),
                            "mhm_last_exec": self.getfieldvalue(
                                filtered_record, "mhm_last_exec"
                            ),
                            "cim_last_exec": self.getfieldvalue(
                                filtered_record, "cim_last_exec"
                            ),
                            "flx_last_exec": self.getfieldvalue(
                                filtered_record, "flx_last_exec"
                            ),
                            "fqm_last_exec": self.getfieldvalue(
                                filtered_record, "fqm_last_exec"
                            ),
                            "wlk_last_exec": self.getfieldvalue(
                                filtered_record, "wlk_last_exec"
                            ),
                        }

                        yield_record.append(new_record)
                    except Exception as e:
                        logging.error(
                            f'Failed to process tenant "{tenant_id}", skipping record. this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception: {str(e)}'
                        )
                        # Yield an error record for this tenant
                        yield {
                            "_time": str(time.time()),
                            "_raw": f'Failed to process tenant "{tenant_id}", this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception="{str(e)}"',
                        }
                        continue
                except Exception as e:
                    logging.error(
                        f"Failed to process tenant record, skipping, this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception: {str(e)}"
                    )
                    # Yield an error record for this tenant
                    yield {
                        "_time": str(time.time()),
                        "_raw": f'Failed to process tenant record, this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception="{str(e)}"',
                    }
                    continue

        except Exception as e:
            # yield
            yield {
                "_time": str(time.time()),
                "_raw": f'failed to retrieve tenants, this likely indicates a corrupted Virtual Tenant, run a POST call against /services/trackme/v2/vtenants/admin/del_tenant to purge the faulty tenant, exception="{str(e)}"',
            }

        # full mode
        if self.mode == "full":
            # yield
            yield {
                "time": time.time(),
                "_raw": json.dumps({"tenants": yield_record}),
                "tenants": yield_record,
            }

        # expanded mode
        elif self.mode == "expanded":
            for tenant_record in yield_record:
                # yield
                yield {
                    "time": time.time(),
                    "_raw": tenant_record,
                }

        # Log the run time
        logging.info(
            f"trackmeload has terminated, run_time={round(time.time() - start, 3)}"
        )


dispatch(TrackMeTenantsStatus, sys.argv, sys.stdin, sys.stdout, __name__)
