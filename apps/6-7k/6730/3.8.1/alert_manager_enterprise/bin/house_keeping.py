#!/usr/bin/env python3.9
#
# File: house_keeping.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import json
import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument, Scheme

from ame.consts.CollectionNames import CollectionNames
from ame.modinput_ame import AmeModularInput
from ame.wrappers.HECWrapper import HECWrapper
from dpshared.consts.CommonKeys import QueryOperators
from dpshared.consts.LogEntryStatus import LogEntryStatus
from dpshared.models.cache.CacheObject import CacheObjectFields


class HouseKeeper(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME Housekeeping")
        scheme.description = "This task does everything, that has to be done in the background, like mapping users and checking the events time to live."

        ## Optional settings
        # Run this script for all instances
        scheme.use_single_instance = False
        # External validation, if set to true, validate_input() will be run.
        scheme.use_external_validation = True

        # Add arguments to the scheme. Has to match with inputs.conf.spec
        dummy_argument = Argument("default")
        dummy_argument.data_type = Argument.data_type_string
        dummy_argument.description = "Unused Default Argument"
        dummy_argument.required_on_create = True
        scheme.add_argument(dummy_argument)

        return scheme

    def update_tenant_users(self) -> None:
        try:
            self.logger.info({"action": "update_tenant_users", "status": LogEntryStatus.STARTED})
            # This will map user names with a matching role to the user_names of the tenants
            self.service_factory.tenant_service.update_tenant_users()
            self.logger.info({"action": "update_tenant_users", "status": LogEntryStatus.SUCCESS})
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "update_tenant_users",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def apply_ttl(self) -> None:
        try:
            self.logger.info({"action": "apply_ttl", "status": LogEntryStatus.STARTED})
            event_service = self.service_factory.event_service
            updated_events = event_service.apply_ttl()
            self.logger.info(
                {
                    "action": "apply_ttl",
                    "status": LogEntryStatus.SUCCESS,
                    "updated_events": updated_events,
                }
            )

        except Exception as exc:
            self.logger.exception(
                {"action": "apply_ttl", "status": LogEntryStatus.FAILED, "exception": exc}
            )

    def apply_cache_ttl(self) -> None:
        try:
            current_time = int(time.time())
            entries = self.sdk_wrapper.get_collection(name=CollectionNames.CACHE).data.query(
                query={CacheObjectFields.TIMEOUT: {QueryOperators.LT: current_time}}
            )
            all_entries = self.sdk_wrapper.get_collection(name=CollectionNames.CACHE).data.query(
                query={}
            )
            self.logger.info(
                {
                    "action": "apply_cache_ttl",
                    "status": LogEntryStatus.STARTED,
                    "found_entries": len(all_entries),
                }
            )

            self.sdk_wrapper.get_collection(name=CollectionNames.CACHE).data.delete(
                query=json.dumps({CacheObjectFields.TIMEOUT: {QueryOperators.LT: current_time}})
            )
            self.logger.info(
                {
                    "action": "apply_cache_ttl",
                    "status": LogEntryStatus.SUCCESS,
                    "deleted_entries": len(entries),
                    "remaining_entries": len(all_entries) - len(entries),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {"action": "apply_cache_ttl", "status": LogEntryStatus.FAILED, "exception": exc}
            )

    def apply_tenant_retention(self) -> None:
        current_time = int(time.time())
        tenant_dataservice = self.service_factory.tenant_dataservice
        tenant_service = self.service_factory.tenant_service
        tenants = tenant_dataservice.all()
        self.logger.info(
            {
                "action": "apply_tenant_retention",
                "status": LogEntryStatus.STARTED,
                "tenants": len(tenants),
            }
        )

        for tenant in tenants:
            if tenant.retention_configuration.events > 0:
                try:
                    self.logger.info(
                        {
                            "action": "apply_tenant_retention",
                            "status": LogEntryStatus.STARTED,
                            "tenant": tenant.name,
                            "retention": tenant.retention_configuration.events,
                        }
                    )
                    tenant_service.apply_retention(tenant=tenant, current_time=current_time)
                    self.logger.info(
                        {"action": "apply_tenant_retention", "status": LogEntryStatus.SUCCESS}
                    )
                except Exception as exc:
                    self.logger.exception(
                        {
                            "action": "apply_tenant_retention",
                            "status": LogEntryStatus.FAILED,
                            "exception": exc,
                        }
                    )
            else:
                self.logger.info(
                    {
                        "action": "apply_tenant_retention",
                        "status": LogEntryStatus.SKIPPED,
                        "tenant": tenant.name,
                        "retention": tenant.retention_configuration.events,
                    }
                )

    def retry_resilience(self) -> None:
        try:
            self.logger.info({"action": "retry_resilience", "status": LogEntryStatus.STARTED})
            hec_wrapper = HECWrapper(sdk_wrapper=self.sdk_wrapper)
            hec_wrapper.retry_resilience(tenant_service=self.service_factory.tenant_dataservice)
            self.logger.info({"action": "retry_resilience", "status": LogEntryStatus.SUCCESS})
        except Exception as exc:
            self.logger.exception(
                {"action": "retry_resilience", "status": LogEntryStatus.FAILED, "exception": exc}
            )

    def validate_licenses(self) -> None:
        try:
            self.logger.info({"action": "validate_licenses", "status": LogEntryStatus.STARTED})
            license_service = self.service_factory.license_service
            license_service.validate_licenses()
            self.logger.info({"action": "validate_licenses", "status": LogEntryStatus.SUCCESS})
        except Exception as exc:
            self.logger.exception(
                {"action": "validate_licenses", "status": LogEntryStatus.FAILED, "exception": exc}
            )

    def observables_group_cleanup(self) -> None:
        try:
            self.logger.info(
                {"action": "observables_group_cleanup", "status": LogEntryStatus.STARTED}
            )
            observable_group_dataservice = self.service_factory.observable_group_dataservice
            observable_group_dataservice.ensure_all_groups_in_order()
            self.logger.info(
                {"action": "observables_group_cleanup", "status": LogEntryStatus.SUCCESS}
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "observables_group_cleanup",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def handle_stream_events(
        self,
        inputs: Any,  # noqa: ANN401
        ew: Any,  # noqa: ANN401
    ) -> None:
        try:
            self.update_tenant_users()
            self.apply_ttl()
            self.apply_cache_ttl()
            self.apply_tenant_retention()
            self.retry_resilience()
            self.validate_licenses()
            self.observables_group_cleanup()
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "handle_stream_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )


if __name__ == "__main__":
    sys.exit(HouseKeeper().run(sys.argv))
