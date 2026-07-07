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
import json
import logging
import os
import re
import sys
import time

# Third-party library imports
import urllib3
from logging.handlers import RotatingFileHandler

# Disable insecure request warnings for urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# set splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_cmdb.log" % splunkhome,
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

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo, run_splunk_search, trackme_vtenant_account
from trackme_libs_cmdb import resolve_cmdb_remote_service


@Configuration(distributed=False)
class TrackMeSplkCmdb(GeneratingCommand):
    component = Option(
        doc="""
        **Syntax:** **component=****
        **Description:** The TrackMe component""",
        require=True,
        validate=validators.Match("component", r"^(?:dsm|dhm|mhm|flx|fqm|wlk)$"),
    )

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** The tenant identifier.""",
        require=True,
        default=None,
    )

    object = Option(
        doc="""
        **Syntax:** **object=****
        **Description:** The TrackMe object value""",
        require=False,
        validate=validators.Match("object", r"^.*$"),
    )

    object_id = Option(
        doc="""
        **Syntax:** **object_id=****
        **Description:** The TrackMe object identifier""",
        require=False,
        validate=validators.Match("object_id", r"^.*$"),
    )

    # Function to replace placeholders
    def replace_placeholders(self, s, dictionary):
        return re.sub(r"\$(\w+)\$", lambda m: dictionary.get(m.group(1), m.group(0)), s)

    def generate(self, **kwargs):
        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # Get Virtual Tenant account
        vtenant_account = trackme_vtenant_account(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
            self.tenant_id,
        )

        # check args
        if not self.object and not self.object_id:
            raise Exception("object or object_id argument must be provided")
        elif self.object and self.object_id:
            raise Exception(
                "object or object_id argument must be provided, but not both"
            )

        # Create a mapping of components to their respective keys in the dictionary
        component_mapping = {
            "dsm": "splk_general_dsm_cmdb_search",
            "dhm": "splk_general_dhm_cmdb_search",
            "mhm": "splk_general_mhm_cmdb_search",
            "flx": "splk_general_flx_cmdb_search",
            "fqm": "splk_general_fqm_cmdb_search",
            "wlk": "splk_general_wlk_cmdb_search",
        }
        component_collection_mapping = {
            "dsm": f"kv_trackme_dsm_tenant_{self.tenant_id}",
            "dhm": f"kv_trackme_dhm_tenant_{self.tenant_id}",
            "mhm": f"kv_trackme_mhm_tenant_{self.tenant_id}",
            "flx": f"kv_trackme_flx_tenant_{self.tenant_id}",
            "fqm": f"kv_trackme_fqm_tenant_{self.tenant_id}",
            "wlk": f"kv_trackme_wlk_tenant_{self.tenant_id}",
        }

        # Use the mapping to get the value directly
        cmdb_lookup_search = reqinfo["trackme_conf"]["splk_general"].get(
            component_mapping.get(self.component)
        )

        # Respect the tenant-level CMDB lookup toggle. If disabled (cmdb_lookup=0),
        # do not execute any CMDB search regardless of configured search string.
        cmdb_lookup_toggle = vtenant_account.get("cmdb_lookup", 1)
        try:
            cmdb_lookup_enabled = int(str(cmdb_lookup_toggle)) == 1
        except (ValueError, TypeError):
            cmdb_lookup_enabled = True
        if not cmdb_lookup_enabled:
            yield {
                "_time": time.time(),
                "action": "success",
                "search": "",
                "_raw": {
                    "response": "CMDB lookup is disabled for this tenant (cmdb_lookup=0).",
                },
            }
            logging.info(
                f'trackmesplkcmdb skipped, tenant_id="{self.tenant_id}", reason=cmdb_lookup_disabled_for_tenant, run_time={round(time.time() - start, 3)}'
            )
            return

        # check if we have a non empty value for the CMDB lookup search at the Virtual Tenant level
        # the key will be called splk_<component>_cmdb_search
        try:
            tenant_cmdb_lookup_search = vtenant_account.get(
                f"splk_{self.component}_cmdb_search"
            )
            if tenant_cmdb_lookup_search and tenant_cmdb_lookup_search != "":
                cmdb_lookup_search = tenant_cmdb_lookup_search
        except Exception as e:
            pass

        # Resolve the CMDB account (local or remote)
        # Tenant-level override takes precedence, then system-level, then "local"
        cmdb_account = "local"
        try:
            tenant_cmdb_account = vtenant_account.get("cmdb_account", "")
            if tenant_cmdb_account and tenant_cmdb_account.strip():
                cmdb_account = tenant_cmdb_account.strip()
            else:
                system_cmdb_account = reqinfo["trackme_conf"]["splk_general"].get(
                    "splk_general_cmdb_account", "local"
                )
                if system_cmdb_account and system_cmdb_account.strip():
                    cmdb_account = system_cmdb_account.strip()
        except Exception as e:
            pass

        # KV collection
        collection = self.service.kvstore[
            component_collection_mapping.get(self.component)
        ]

        # Define the KV query
        if self.object:
            query_string = {
                "object": self.object,
            }

        elif self.object_id:
            query_string = {
                "_key": self.object_id,
            }

        # get the KVrecord
        try:
            kvrecord = collection.data.query(query=json.dumps(query_string))[0]
            key = kvrecord.get("_key")

        except Exception as e:
            key = None

        if key:
            # Resolve the service to use (local or remote) — only when entity exists
            # Uses the shared helper from trackme_libs_cmdb to avoid code duplication
            search_service = resolve_cmdb_remote_service(self.service, cmdb_account)

            # expand the search
            cmdb_lookup_search = self.replace_placeholders(cmdb_lookup_search, kvrecord)

            kwargs = {
                "earliest_time": "-5m",
                "latest_time": "now",
                "count": 0,
                "output_mode": "json",
            }

            # run the search
            search_results = []

            try:
                reader = run_splunk_search(
                    search_service,
                    cmdb_lookup_search,
                    kwargs,
                    24,
                    5,
                )

                for item in reader:
                    if isinstance(item, dict):
                        logging.debug(f'search_results="{item}"')
                        # append to the list of searches
                        search_results.append(item)

                if len(search_results) > 1:
                    yield_record = {
                        "_time": time.time(),
                        "action": "success",
                        "search": cmdb_lookup_search,
                        "_raw": json.dumps(search_results),
                    }
                elif len(search_results) == 0:
                    yield_record = {
                        "_time": time.time(),
                        "action": "success",
                        "search": cmdb_lookup_search,
                        "_raw": {
                            "response": "No results found, ensure the CMDB lookup search has been configured in TrackMe and your CMDB contains a record for this entity.",
                            "search": cmdb_lookup_search,
                        },
                    }
                else:
                    yield_record = {
                        "_time": time.time(),
                        "action": "success",
                        "search": cmdb_lookup_search,
                        "_raw": json.dumps(search_results[0], sort_keys=True),
                    }

                # yield
                yield yield_record

            except Exception as e:
                yield_record = {
                    "_time": time.time(),
                    "action": "failure",
                    "search": cmdb_lookup_search,
                    "response": "The CMDB search failed to be executed",
                    "_raw": {
                        "action": "failure",
                        "response": "The CMDB search failed to be executed",
                        "exception": str(e),
                    },
                }
                yield yield_record

        else:
            yield_record = {
                "_time": time.time(),
                "action": "failure",
                "search": cmdb_lookup_search,
                "response": f"The CMDB search failed to be executed, entity with query_string={json.dumps(query_string)} was not found in the collection",
                "_raw": {
                    "action": "failure",
                    "response": f"The CMDB search failed to be executed, entity with query_string={json.dumps(query_string)} was not found in the collection",
                    "exception": str(e),
                },
            }
            yield yield_record

        # Log the run time
        logging.info(
            f'trackmesplkcmdb has terminated, run_time={round(time.time() - start, 3)}, search="{cmdb_lookup_search}"'
        )


dispatch(TrackMeSplkCmdb, sys.argv, sys.stdin, sys.stdout, __name__)
