# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from ITOA import itoa_refresh_queue_utils
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch, Option, validators
from itsi.objects.itsi_entity_management_policies import ItsiEntityManagementPolicies


@Configuration()
class SetRetiredEntities(GeneratingCommand):
    auto_retire = Option(
        doc='''
        **Syntax:** **auto_retire=***<Boolean>*
        **Description:** Transition to retired directly, instead of retirable?''',
        require=False,
        default=False,
        validate=validators.Boolean(),
    )
    clear_retirable = Option(
        doc='''
        **Syntax:** **clear_retirable=***<Boolean>*
        **Description:** Clear retirable flag for passed in entities''',
        require=False,
        default=False,
        validate=validators.Boolean(),
    )
    policy_id = Option(
        doc='''
        **Syntax:** **policy_id=***<string>*
        **Description:** Policy ID''',
        default='',
        require=False,
    )
    owner = 'nobody'

    def generate(self):
        try:
            # Error-catching for weird parameter combinations
            if self.clear_retirable and (self.auto_retire or self.policy_id):
                raise Exception('clear_retirable parameter is exclusive with auto_retire and policy_id parameters.')
            if not self.clear_retirable and not self.policy_id:
                raise Exception('One of [clear_retirable, policy_id] parameters must be present.')

            if not self.clear_retirable:
                self.mark_retirable()
            else:
                self.unmark_retirable()
            yield {}
        except Exception as e:
            # Explicitly specify Exception message due to missing Python3 support in error_exit()
            self.error_exit(e, message=str(e))

    def mark_retirable(self):
        policy_obj = ItsiEntityManagementPolicies(self.service.token, self.owner)
        policy = policy_obj.get(self.owner, self.policy_id)
        # Check here for error reporting (we also check during execution)
        if not policy:
            raise Exception('Policy %s not found. You may have deleted a policy without deleting the associated '
                            'savedsearch.' % self.policy_id)
        if policy.get('disabled'):
            raise Exception('Policy %s triggered despite being disabled. No action taken.' % self.policy_id)

        adapter = itoa_refresh_queue_utils.RefreshQueueAdapter(self.service.token)

        is_success = adapter.create_refresh_job(
            change_type='entity_lifecycle_management',
            changed_object_key=[],
            changed_object_type='entity_management_policies',
            change_detail={
                'action': 'mark_retirable',
                'auto_retire': self.auto_retire,
                'policy_id': self.policy_id,
            },
            transaction_id=self.metadata.searchinfo.sid,
        )
        if not is_success:
            raise Exception('Failed to create mark_retirable job.')
        return

    def unmark_retirable(self):
        adapter = itoa_refresh_queue_utils.RefreshQueueAdapter(self.service.token)
        is_success = adapter.create_refresh_job(
            change_type='entity_lifecycle_management',
            changed_object_key=[],
            changed_object_type='entity_management_policies',
            change_detail={
                'action': 'unmark_retirable',
            },
            transaction_id=self.metadata.searchinfo.sid,
        )
        if not is_success:
            raise Exception('Failed to create unmark_retirable job.')
        return


dispatch(SetRetiredEntities, sys.argv, sys.stdin, sys.stdout, __name__)
