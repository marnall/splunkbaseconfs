#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Migration Command."""
import os
import sys
from distutils.version import StrictVersion

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from migration import Migration_0_0_1
from migration import Migration_0_0_2
from migration import Migration_0_0_3
from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class MigrationCommand(BaseGeneratingCommand):
    """Playbook download command."""

    # args
    force = Option(default=False, doc='To force a migration. Defaults to False', require=False)
    version = Option(doc='The migration version.', require=True)

    # properties
    current_migration_version = None
    filename = os.path.basename(__file__)
    settings = None

    def can_migrate_to(self, requested_version, force, current=None):
        """Return True if migration is an option."""
        if force:
            return True

        if current is None:
            current = self.current_migration_version
        try:
            return StrictVersion(current) < StrictVersion(requested_version)
        except Exception:
            err = f'Failed parsing requested VERSION: [{requested_version}]'
            self.logger.error(err)
            self.error_exit(None, err)

    def check_args(self):
        """Check args to ensure migration should be run."""
        if not self.can_migrate_to(self.version, self.force):
            err = (
                f'Invalid `VERSION` param. Version must be higher than current version. '
                f'Current version is: {self.current_migration_version}'
            )
            self.logger.error(err)
            self.error_exit(None, err)

    def check_min_version(self, min_allowed_version):
        """Check min version."""
        if self.force:
            return

        if StrictVersion(self.current_migration_version) < StrictVersion(min_allowed_version):
            err = (
                f'Min required version of {min_allowed_version} for this upgrade. '
                f'Please upgrade to at least {min_allowed_version} before continuing.'
            )
            self.logger.error(err)
            self.error_exit(None, err)

    def check_settings(self):
        """Update settings if required."""
        self.settings = self.tcs.collections.settings.query()
        if (
            'tc_migration_version' not in self.settings[0]
            or not self.settings[0]['tc_migration_version']
        ):
            self.current_migration_version = '0.0.0'
            self.update_setting()
        else:
            self.current_migration_version = self.settings[0]['tc_migration_version']

    def generate(self):
        """Implement generate method for demo data and results."""
        self.check_args()
        self.check_setting()
        self.migrate()

        # display results
        for r in self.results:
            yield r

    def migrate(self):
        """Run migration process."""
        valid_versions = ['0.0.1', '0.0.2', '0.0.3']

        try:
            StrictVersion(self.current_migration_version)
        except Exception:
            err = 'Invalid version format, please use ex.0.0.1 format'
            self.logger(err)
            self.error_exit(None, err)

        if self.version not in valid_versions:
            err = f'Version [{self.version}] does not exist.'
            self.logger(err)
            self.error_exit(None, err)

        if self.version == '0.0.1':
            self.logger.info('Migration for 0.0.1')
            migration_0_0_1 = Migration_0_0_1(self.logger, self.service, self.tcs)
            try:
                migration_0_0_1.migrate()
                self.current_migration_version = '0.0.1'
                self.update_setting('0_0_1')
                sys.exit(0)
            except Exception as e:
                self.error_exit(None, e)
        elif self.version == '0.0.2':
            self.logger.info('Migration for 0.0.2')
            migration_0_0_2 = Migration_0_0_2(self.logger, self.service, self.tcs)
            try:
                migration_0_0_2.migrate()
                self.current_migration_version = '0.0.2'
                self.update_setting('0_0_2')
                sys.exit(0)
            except Exception as e:
                self.error_exit(None, e)

        self.check_min_version('0.0.2')

        if self.version == '0.0.3':
            self.logger.info('Migration for 0.0.3')
            migration_0_0_3 = Migration_0_0_3(self.logger, self.service, self.tcs)
            try:
                migration_0_0_3.migrate()
                self.current_migration_version = '0.0.3'
                self.update_setting('0_0_3')
            except Exception as e:
                self.error_exit(None, e)

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update args
        self.force = self.tcs.utils.to_bool(self.force)

    def update_setting(self, migration_version_completed=None):
        """Update the settings in the KV Store."""
        setting = self.settings[0]
        setting['tc_migration_version'] = self.current_migration_version
        if migration_version_completed:
            key = f'migration_{migration_version_completed}_executed'
            setting[key] = True
        self.tcs.collections.settings.update(key=setting.pop('_key'), data=setting)


if __name__ == '__main__':
    dispatch(MigrationCommand, sys.argv, sys.stdin, sys.stdout, __name__)
