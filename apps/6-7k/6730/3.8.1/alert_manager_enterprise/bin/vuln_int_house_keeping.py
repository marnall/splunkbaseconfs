#!/usr/bin/env python3.9
#
# File: vuln_int_house_keeping.py - Version 3.8.1
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

from ame.consts.LicenseTypes import LicenseTypes
from ame.modinput_ame import AmeModularInput
from dpshared.consts.LogEntryStatus import LogEntryStatus


class VulnIntHousekeeping(AmeModularInput):
    def get_scheme(self) -> Scheme:
        scheme = Scheme("AME Vulnerability Intelligence Housekeeping")
        scheme.description = "This task retries to create realizations for staged realizations."

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

    def retry_staged_realizations(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "retry_staged_realizations",
                    "status": LogEntryStatus.STARTED,
                }
            )
            retry_start_time = time.time()
            vuln_int_realizations_service = self.service_factory.vuln_int_realizations_service
            vuln_int_realizations_service.retry_staged_realizations()
            self.logger.info(
                {
                    "action": "retry_staged_realizations",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - retry_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "retry_staged_realizations",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def process_active_realizations(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "process_active_realizations",
                    "status": LogEntryStatus.STARTED,
                }
            )
            processing_start_time = time.time()
            self.service_factory.vuln_int_active_realization_processing_service.process_active_realizations()
            self.logger.info(
                {
                    "action": "process_active_realizations",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - processing_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "process_active_realizations",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def process_unfixed_associated_risk_events(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "process_unfixed_associated_risk_events",
                    "status": LogEntryStatus.STARTED,
                }
            )
            processing_start_time = time.time()
            self.service_factory.vuln_int_associated_risk_events_processing_service.process_unfixed_associated_risk_events()
            self.logger.info(
                {
                    "action": "process_unfixed_associated_risk_events",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - processing_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "process_unfixed_associated_risk_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def auto_fix_old_realizations(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "auto_fix_old_realizations",
                    "status": LogEntryStatus.STARTED,
                }
            )
            auto_fix_start_time = time.time()
            vuln_int_realizations_service = self.service_factory.vuln_int_realizations_service
            vuln_int_realizations_service.auto_fix_old_realizations()
            self.logger.info(
                {
                    "action": "auto_fix_old_realizations",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - auto_fix_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "auto_fix_old_realizations",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def remove_old_fixed_realizations(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "remove_old_fixed_realizations",
                    "status": LogEntryStatus.STARTED,
                }
            )
            remove_start_time = time.time()
            vuln_int_realizations_service = self.service_factory.vuln_int_realizations_service
            vuln_int_realizations_service.remove_old_fixed_realizations()
            self.logger.info(
                {
                    "action": "remove_old_fixed_realizations",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - remove_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "remove_old_fixed_realizations",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def remove_old_staged_realizations(self) -> None:
        try:
            self.logger.info(
                {
                    "action": "remove_old_staged_realizations",
                    "status": LogEntryStatus.STARTED,
                }
            )
            remove_start_time = time.time()
            vuln_int_realizations_service = self.service_factory.vuln_int_realizations_service
            vuln_int_realizations_service.remove_old_staged_realizations()
            self.logger.info(
                {
                    "action": "remove_old_staged_realizations",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - remove_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "remove_old_staged_realizations",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )

    def collect_realization_metrics(self) -> None:
        realization_metrics_service = self.service_factory.vuln_int_realizations_metrics_service
        try:
            self.logger.info(
                {
                    "action": "collect_realization_metrics",
                    "status": LogEntryStatus.STARTED,
                }
            )
            metrics_start_time = time.time()
            realization_metrics_service.collect_realization_metrics()
            self.logger.info(
                {
                    "action": "collect_realization_metrics",
                    "status": LogEntryStatus.SUCCESS,
                    "duration": round(time.time() - metrics_start_time, 2),
                }
            )
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "collect_realization_metrics",
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
            license_service = self.service_factory.license_service
            if not license_service.has_valid_license(
                product_identifier=LicenseTypes.SECURITY_PACK
            ):
                self.logger.info(
                    {
                        "action": "handle_stream_events",
                        "status": LogEntryStatus.SKIPPED,
                        "reason": "no_valid_license",
                    }
                )
                return

            self.retry_staged_realizations()
            self.remove_old_staged_realizations()

            self.auto_fix_old_realizations()
            self.remove_old_fixed_realizations()

            self.process_active_realizations()
            self.process_unfixed_associated_risk_events()

            self.collect_realization_metrics()
        except Exception as exc:
            self.logger.exception(
                {
                    "action": "handle_stream_events",
                    "status": LogEntryStatus.FAILED,
                    "exception": exc,
                }
            )


if __name__ == "__main__":
    sys.exit(VulnIntHousekeeping().run(sys.argv))
