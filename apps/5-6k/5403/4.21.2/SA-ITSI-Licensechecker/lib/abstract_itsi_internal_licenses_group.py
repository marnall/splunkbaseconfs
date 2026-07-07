# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from abc import ABC, abstractmethod
from itsi_internal_licenses import old_itsi_internal_ea_license


class AbstractItsiInternalLicensesGroup(ABC):
    @abstractmethod
    def get_itsi_internal_license(self):
        pass

    @abstractmethod
    def get_plus_suite_signaling_license(self):
        pass

    @abstractmethod
    def get_license_expiration_signaling_license(self):
        pass

    def get_old_itsi_internal_ea_license(self):
        return old_itsi_internal_ea_license

    def is_license_in_group(self, lic):
        return lic.guid in self.get_license_guids()

    def get_license_guids(self):
        return [lic.guid for lic in self.get_licenses()]

    def get_licenses(self):
        return [self.get_old_itsi_internal_ea_license(),
                self.get_itsi_internal_license(),
                self.get_plus_suite_signaling_license(),
                self.get_license_expiration_signaling_license()]
