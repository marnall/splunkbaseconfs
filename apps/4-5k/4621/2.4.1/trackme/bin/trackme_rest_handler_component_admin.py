#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_component_admin.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import json
import os
import sys
import time
import requests

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger(
    "trackme.rest.component_admin", "trackme_rest_api_component_admin.log"
)

# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import (
    trackme_getloglevel_from_service,
    trackme_parse_describe_flag,
    trackme_vtenant_account_from_service,
)

# import shadow copy libs
from trackme_libs_shadow import (
    write_shadow_records,
    should_use_shadow,
)

# import trackme libs utils
from trackme_libs_utils import get_uuid

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerComponentAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerComponentAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    def get_resource_group_desc_component(self, request_info, **kwargs):
        response = {
            "resource_group_name": "component/admin",
            "resource_group_desc": "These endpoints provide component-level admin operations (shadow copy management)",
        }
        return {"payload": response, "status": 200}

    def post_refresh_shadow(self, request_info, **kwargs):
        """
        Refresh the shadow copy for a given tenant/component.

        This endpoint runs the full enrichment pipeline via load_component_data,
        then writes the enriched records to the shadow collection.

        Only backend callers (health tracker, hybrid tracker executor) should call this.
        Protected by trackmeadminoperations capability (Splunk RBAC enforced).
        """
        describe = False

        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)

            if not describe:
                # tenant_id
                try:
                    tenant_id = resp_dict["tenant_id"]
                except Exception:
                    return {
                        "payload": {"error": "tenant_id is required"},
                        "status": 400,
                    }

                # component
                try:
                    component = resp_dict["component"]
                    if component not in (
                        "dsm",
                        "dhm",
                        "mhm",
                        "flx",
                        "fqm",
                        "wlk",
                    ):
                        return {
                            "payload": {"error": "component is invalid"},
                            "status": 400,
                        }
                except Exception:
                    return {
                        "payload": {"error": "component is required"},
                        "status": 400,
                    }
                # requester (optional)
                requester = resp_dict.get("requester")

        else:
            describe = True

        # if describe is requested, show the usage
        if describe:
            response = {
                "describe": "This endpoint refreshes the shadow copy collection for a given tenant and component. "
                "It runs the full enrichment pipeline then writes enriched records to the shadow collection. "
                "This endpoint is intended for backend callers only (health tracker, hybrid tracker executor).",
                "resource_desc": "Refresh shadow copy for a tenant/component",
                "resource_spl_example": '| trackme url="/services/trackme/v2/component/admin/refresh_shadow" mode="post" '
                'body="{\'tenant_id\': \'mytenant\', \'component\': \'flx\'}"',
                "options": [
                    {
                        "tenant_id": "REQUIRED. The tenant identifier",
                        "component": "component identifier, valid options are: flx, dsm, dhm, mhm, wlk, fqm",
                        "requester": "(optional) identifier of the caller, e.g. health_tracker, hybrid_tracker_executor",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Generate instance ID
        instance_id = get_uuid()

        # set loglevel
        splunkd_port = request_info.server_rest_port
        service_system = client.connect(
            owner="nobody",
            app="trackme",
            port=splunkd_port,
            token=request_info.system_authtoken,
            timeout=600,
        )
        loglevel = trackme_getloglevel_from_service(service_system)
        logger.setLevel(loglevel)

        # performance counter
        start = time.time()

        logger.info(
            f'instance_id={instance_id}, tenant_id="{tenant_id}", '
            f'component="{component}", refresh_shadow starting'
        )

        try:
            # Check if shadow is applicable for this tenant/component
            vtenant_conf = trackme_vtenant_account_from_service(service_system, tenant_id)
            shadow_enabled = int(vtenant_conf.get("shadow_enabled", 0))
            shadow_entity_threshold = int(vtenant_conf.get("shadow_entity_threshold", 1000))

            if shadow_enabled == 0:
                logger.info(
                    f'instance_id={instance_id}, tenant_id="{tenant_id}", '
                    f'component="{component}", shadow disabled (shadow_enabled=0), skipping'
                )
                return {
                    "payload": {
                        "action": "success",
                        "response": "shadow is disabled for this tenant (shadow_enabled=0)",
                    },
                    "status": 200,
                }

            # Call load_component_data internally to get enriched records
            header = {
                "Authorization": f"Splunk {request_info.system_authtoken}",
                "Content-Type": "application/json",
            }

            params = {
                "tenant_id": tenant_id,
                "component": component,
                "page": 1,
                "size": 0,
                "caller": "refresh_shadow",
            }

            url = f"{request_info.server_rest_uri}/services/trackme/v2/component/load_component_data"

            response = requests.get(
                url,
                headers=header,
                params=params,
                verify=False,
                timeout=600,
            )

            if response.status_code not in (200, 201, 204):
                msg = (
                    f'load_component_data failed, status_code="{response.status_code}", '
                    f'response="{response.text}"'
                )
                logger.error(f"instance_id={instance_id}, {msg}")
                return {
                    "payload": {"action": "failure", "response": msg},
                    "status": 500,
                }

            response_json = response.json()
            enriched_records = response_json.get("data", [])
            total_count = len(enriched_records)

            # Always write shadow with the enriched (post-blocklist) records.
            #
            # The shadow_entity_threshold only controls the READ side (whether
            # the UI reads from shadow vs calling load_component_data directly).
            # On the WRITE side, we always persist because:
            #   1. load_component_data (the expensive enrichment) has already run
            #   2. The actual write (clear + batch insert) is sub-second
            #   3. Skipping writes based on the filtered count causes staleness
            #      when blocklists reduce the visible entity count below threshold
            #      while the shadow retains stale pre-blocklist records
            write_shadow_records(
                service_system,
                tenant_id,
                component,
                enriched_records,
                instance_id,
                requester=requester,
                shadow_enabled=shadow_enabled,
            )

            run_time = round(time.time() - start, 3)
            logger.info(
                f'instance_id={instance_id}, tenant_id="{tenant_id}", '
                f'component="{component}", refresh_shadow completed, '
                f'records={total_count}, run_time={run_time}'
            )

            return {
                "payload": {
                    "action": "success",
                    "response": f"shadow refreshed with {total_count} records in {run_time} seconds",
                },
                "status": 200,
            }

        except Exception as e:
            run_time = round(time.time() - start, 3)
            msg = f'refresh_shadow failed: {e}'
            logger.error(
                f'instance_id={instance_id}, tenant_id="{tenant_id}", '
                f'component="{component}", {msg}, run_time={run_time}'
            )
            return {
                "payload": {"action": "failure", "response": msg},
                "status": 500,
            }
