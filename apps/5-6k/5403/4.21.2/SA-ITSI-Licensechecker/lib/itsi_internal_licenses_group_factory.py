# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

from itsi_internal_licenses_group import ItsiInternalLicensesGroup
from itsi_internal_licenses_group_devtest import ItsiInternalLicensesGroupDevTest
from itsi_internal_licenses import all_itsi_internal_licenses
from utils import setup_logging


class ItsiInternalLicensesGroupFactory(object):

    DEVTEST_SUBGROUP_ID = 'DevTest'

    def __init__(self, license_api):
        self.log = setup_logging(log_file='itsi_license_checker.log', logger_name='itsi.license_checker.ItsiInternalLicensesGroupFactory')
        self.licenses_api = license_api

    def get_license_group(self):
        subgroup = self._get_active_subgroup()
        self.log.info('Active subgroup: {}'.format(subgroup))
        if subgroup == self.DEVTEST_SUBGROUP_ID:
            return ItsiInternalLicensesGroupDevTest()
        else:
            return ItsiInternalLicensesGroup()

    def _get_active_subgroup(self):
        """
        This method retrieves active license subgroup in Splunk.
        In Splunk only licenses that belong to one subgroup can stack with each other.

        This method first looks for an active license group then gets all its licenses.
        Is then get active licenses in the currently active group.
        These active license should belong to the one subgroup.
        It returns active subgroups according to the existence of licenses in use.
        """

        active_group = self._get_active_license_group()
        self.log.info('Active license group: {}'.format(active_group.name))

        licenses = self.licenses_api.get_licenses()
        non_itsi_internal_licenses = [lic for lic in licenses if not lic.among_licenses(all_itsi_internal_licenses)]

        non_itsi_internal_licenses_in_active_group = \
            [lic for lic in non_itsi_internal_licenses if lic.group_id == active_group.name]

        licenses_in_use = self.licenses_api.get_licenses_in_use()
        non_itsi_internal_in_use_licenses_in_active_group = \
            [lic for lic in non_itsi_internal_licenses_in_active_group if lic.among_licenses(licenses_in_use)]
        self.log.info('Non ITSI internal licenses in active group: {}'
                      .format(non_itsi_internal_in_use_licenses_in_active_group))

        if len(non_itsi_internal_in_use_licenses_in_active_group) == 0:
            # Return the subgroup of license which belongs to the active group.
            subgroup_ids_of_active_group = \
                {lic.subgroup_id for lic in licenses if lic.group_id == active_group.name}
            assert len(subgroup_ids_of_active_group) == 1, \
                'Only one license subgroup should be active. Actual active subgroups: {}'\
                .format(subgroup_ids_of_active_group)
            return next(iter(subgroup_ids_of_active_group))

        else:
            subgroup_ids = {lic.subgroup_id for lic in non_itsi_internal_in_use_licenses_in_active_group}
            assert len(subgroup_ids) == 1, \
                'Only one license subgroup should be active. Actual active subgroups: {}'.format(subgroup_ids)
            return non_itsi_internal_in_use_licenses_in_active_group[0].subgroup_id

    def _get_active_license_group(self):
        groups = self.licenses_api.get_license_groups()
        return next(group for group in groups if group.active)
