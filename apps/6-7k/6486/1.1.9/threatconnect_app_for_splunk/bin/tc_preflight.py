#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Datamodel Fields"""
# standard library
import os
import sys

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand  # isort: skip

import splunklib.results as results  # isort: skip
from splunklib.searchcommands import Configuration, dispatch  # isort: skip


@Configuration()
class TCPreflightCommand(BaseGeneratingCommand):
    """Command to generate Datamodel field.

    This command create a KV Store with all Datamodel fields to be used in the
    Datamodel search configuration page to increase the performance of the dropdown.
    The command is run on as a saved search on a schedule.

    Usage:
    | tcpreflight
    """

    # properties
    _command = 'tcpreflight'
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for Collection KV Store Stats."""
        yield from self.check_indexes()
        yield from self.check_settings()
        yield from self.check_permissions()

    def check_permissions(self):
        """Verify tc_admin role exists and has appropriate permissions."""
        try:
            tc_admin_role = next(
                (role for role in self.service.roles if role.name == 'tc_admin'), None
            )
            if tc_admin_role:
                tc_admin_capabilities = set(
                    [
                        *tc_admin_role.capabilities,
                        *tc_admin_role.imported_capabilities,
                    ]
                )
                required_permissions = set(
                    [
                        'list_storage_passwords',
                        'schedule_search',
                    ]
                )
                missing_permissions = required_permissions - tc_admin_capabilities
                if missing_permissions:
                    yield {
                        'order': 2,
                        'title': 'Check tcadmin role.',
                        'status': 'Failure',
                        'message': f'tc_admin role missing required capabilities: {", ".join(missing_permissions)}.',
                    }
                else:
                    yield {
                        'order': 2,
                        'title': 'Check tc_admin role.',
                        'status': 'Success',
                        'message': None,
                    }
            else:
                yield {
                    'order': 2,
                    'title': 'Check tc_admin role.',
                    'status': 'Failure',
                    'message': 'tc_admin role does not exist.  Create role and assign to user.',
                }
        except Exception as e:
            yield {
                'order': 2,
                'title': 'Check tc_admin role.',
                'status': 'Warning',
                'message': f'Unable to retrieve roles: {e}',
            }
            return

    def check_settings(self):
        """Validate settings are set and valid."""
        settings = None
        try:
            settings = self.tcs.collections.settings.query()
            # do this to create the session and catch any errors
            self.tcs.session  # pylint: disable=pointless-statement
        except (Exception, KeyError):
            yield {
                'order': 3,
                'title': 'Check settings exist.',
                'status': 'Failure',
                'message': 'No settings found.  Go to Configure > Settings to configure.',
            }
            return

        # validate settings have been given
        if not settings:
            yield {
                'order': 3,
                'title': 'Check settings exist.',
                'status': 'Failure',
                'message': 'No settings found.  Go to Configure > Settings to configure.',
            }
            return
        else:
            settings = settings[0]
            yield {
                'order': 3,
                'title': 'Check settings exist.',
                'status': 'Success',
                'message': None,
            }

        # validate API connectivity
        try:
            r = self.tcs.session.get('/v2/owners')
            if not r.ok:
                response = None
                try:
                    response = r.text
                except Exception:
                    pass

                yield {
                    'order': 4,
                    'title': 'Check ThreatConnect API connectivity.',
                    'status': 'Failure',
                    'message': f'Unable to connect to ThreatConnect API: {r.status_code} - {response}',
                }
            else:
                yield {
                    'order': 4,
                    'title': 'Check ThreatConnect API connectivity.',
                    'status': 'Success',
                    'message': None,
                }
        except Exception as e:
            yield {
                'order': 4,
                'title': 'Check ThreatConnect API connectivity.',
                'status': 'Failure',
                'message': f'Unable to connect to ThreatConnect API: {e}',
            }

        # validate gateway service is available
        try:
            r = self.tcs.session.get(
                f'{settings.service_path}/sync', params={'splunk_id': settings.serviceId}
            )
            if not r.ok:
                if r.status_code == 400:
                    yield {
                        'order': 5,
                        'title': 'Check gateway service is available.',
                        'status': 'Failure',
                        'message': 'Gateway service is running in multitennant mode.  Validate that "Splunk Instance Name" is set on the Settings page and that its value matches the "Splunk Instance Name" value in the Settings page of ThreatConnect App for Splunk.',
                    }
                else:
                    yield {
                        'order': 5,
                        'title': 'Check gateway service is available.',
                        'status': 'Failure',
                        'message': 'Gateway service is not available.  Validate service is created and running in ThreatConnect.',
                    }
            else:
                if r.json() == []:
                    yield {
                        'order': 5,
                        'title': 'Check gateway service is available.',
                        'status': 'Warning',
                        'message': 'Gateway service is available but no data has been synced.  Validate that at least one Indicator Collection has been defined in ThreatConnect App For Splunk.  Validate that the "Splunk Instance Name" is set on the Settings page and that its value matches the "Splunk Instance Name" value in the Settings page of ThreatConnect App for Splunk.  If the "Splunk Instance Name" is correct, validate that the "TC-Gateway-Push" saved search in from ThreatConnect App For Splunk has successfully run and is enabled, and that the "TC-ModuleImportSync" saved search from TA ThreatConnect Threat Intel has successfully run and is enabled.',
                    }

                else:
                    yield {
                        'order': 5,
                        'title': 'Check gateway service is available.',
                        'status': 'Success',
                        'message': None,
                    }
        except Exception as e:
            yield {
                'order': 5,
                'title': 'Check gateway service is available.',
                'status': 'Failure',
                'message': f'Gateway service is not available.  Validate service is created and running in ThreatConnect. {e}',
            }

    def check_indexes(self):
        """Validate that all indexes are available."""
        check_indexes = ['tc_indicator_data', 'tc_dm_search_events']
        try:
            spl = '| rest /services/data/indexes | fields title '
            kwargs = {'output_mode': 'json'}
            job = self.service.jobs.oneshot(spl, **kwargs)
            reader = results.JSONResultsReader(job)

            # retrieve results from Splunk
            indexes = [r.get('title') for r in reader]
            for index in check_indexes:
                if index not in indexes:
                    yield {
                        'order': 1,
                        'title': 'Check indexes exists.',
                        'status': 'Warning',
                        'message': (
                            f'Could not validate that {index}' ' exist, please manually verify.'
                        ),
                    }
                else:
                    yield {
                        'order': 1,
                        'title': f'Check index {index} exists.',
                        'status': 'Success',
                        'message': None,
                    }
        except Exception:
            for index in check_indexes:
                yield {
                    'order': 1,
                    'title': 'Check indexes exists.',
                    'status': 'Warning',
                    'message': (
                        f'Could not validate that {index}' ' exist, please manually verify.'
                    ),
                }

    @staticmethod
    def is_base(parent_name):
        """Return True is parent is BaseEvent."""
        return parent_name == 'BaseEvent'

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    dispatch(TCPreflightCommand, sys.argv, sys.stdin, sys.stdout, __name__)
