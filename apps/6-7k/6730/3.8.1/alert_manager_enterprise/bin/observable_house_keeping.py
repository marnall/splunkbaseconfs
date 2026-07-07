#!/usr/bin/env python3.9
#
# File: observable_house_keeping.py - Version 3.8.1
# Copyright © Datapunctum AG 2026-04-07
#
# CONFIDENTIAL - Use or disclosure of this material in whole or in part
# without a valid written license from Datapunctum AG is PROHIBITED.
#

import os
import sys
import time
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import Argument, Scheme

from ame.modinput_ame import AmeModularInput
from dpshared.consts.LogEntryStatus import LogEntryStatus


class ObservableHouseKeeper(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME Observables Housekeeping")
        scheme.description = "This task checks all observables and assigns them to the correct group, updates transforms.conf entries"

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

    def age_out_keeping(self) -> None:
        try:
            self.logger.info({"action": "observables_age_out", "status": LogEntryStatus.STARTED})
            age_out_start_time = time.time()
            observables_service = self.service_factory.observables_service
            observables_service.process_age_out_limit_housekeeping()
            self.logger.info(
                {
                    "action": "observables_age_out",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - age_out_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "observables_age_out",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def transforms_keeping(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "update_transforms",
                    "status": LogEntryStatus.STARTED,
                }
            )
            transforms_start_time = time.time()
            self.service_factory.observables_service.update_transforms_housekeeping()
            self.logger.info(
                {
                    "action": "update_transforms",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - transforms_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "update_transforms",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def group_keeping(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "map_observables_to_groups",
                    "status": LogEntryStatus.STARTED,
                }
            )
            mapping_start_time = time.time()
            observables_group_service = self.service_factory.observable_group_service
            observables_group_service.map_observables_to_groups()
            self.logger.info(
                {
                    "action": "map_observables_to_groups",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - mapping_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "map_observables_to_groups",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def age_out_alert_action_observable_groups(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "age_out_alert_action_observable_groups",
                    "status": LogEntryStatus.STARTED,
                }
            )
            age_out_start_time = time.time()
            observable_group_dataservice = self.service_factory.observable_group_dataservice
            observable_group_dataservice.age_out_alert_action_observable_groups()
            self.logger.info(
                {
                    "action": "age_out_alert_action_observable_groups",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": time.time() - age_out_start_time,
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "age_out_alert_action_observable_groups",
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
            self.age_out_keeping()
            self.age_out_alert_action_observable_groups()

            self.group_keeping()
            self.transforms_keeping()
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "handle_stream_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )


if __name__ == "__main__":
    sys.exit(ObservableHouseKeeper().run(sys.argv))
