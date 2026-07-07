# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from abstract_itsi_internal_licenses_group import AbstractItsiInternalLicensesGroup
from itsi_internal_licenses import \
    itsi_internal_license, \
    plus_suite_signaling_license, \
    license_expiration_signaling_license


class ItsiInternalLicensesGroup(AbstractItsiInternalLicensesGroup):
    def get_itsi_internal_license(self):
        return itsi_internal_license

    def get_plus_suite_signaling_license(self):
        return plus_suite_signaling_license

    def get_license_expiration_signaling_license(self):
        return license_expiration_signaling_license
