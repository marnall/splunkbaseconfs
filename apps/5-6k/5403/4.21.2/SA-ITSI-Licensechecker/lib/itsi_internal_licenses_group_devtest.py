# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from abstract_itsi_internal_licenses_group import AbstractItsiInternalLicensesGroup
from itsi_internal_licenses import \
    itsi_internal_license_devtest, \
    plus_suite_signaling_license_devtest, \
    license_expiration_signaling_license_devtest


class ItsiInternalLicensesGroupDevTest(AbstractItsiInternalLicensesGroup):
    def get_itsi_internal_license(self):
        return itsi_internal_license_devtest

    def get_plus_suite_signaling_license(self):
        return plus_suite_signaling_license_devtest

    def get_license_expiration_signaling_license(self):
        return license_expiration_signaling_license_devtest
