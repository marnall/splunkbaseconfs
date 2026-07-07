# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import time

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from SA_ITOA_app_common.splunklib import results
from SA_ITOA_app_common.splunklib import client
from SA_ITOA_app_common.splunklib.binding import HTTPError
from SA_ITOA_app_common.solnlib.splunkenv import get_splunkd_access_info
from ITOA.setup_logging import getLogger
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
from ITOA.event_management.notable_event_ticketing import ExternalTicket
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
from ITOA.event_management.notable_event_utils import Audit


class JiraIssueCommandWrapper(CustomGroupActionBase):
    """
    Class that performs Jira incident creation followed by External Ticket creation.
    """

    def __init__(self, settings, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.jira_wrapper")

        super(JiraIssueCommandWrapper, self).__init__(settings, self.logger)

        self.action_dispatch_config = ActionDispatchConfiguration(self.get_session_key(), self.logger)
        self.search_command = 'jiracloudissue'
        self.search_ticket_id_field_name = 'jira_issue_key'
        self.search_ticket_url_field_name = 'jira_issue_link'
        self.ticket_system_field_value = 'Jira Cloud'
        _, _, port = get_splunkd_access_info()
        self.service = client.connect(token=self.get_session_key(), app='SA-ITOA', port=port)
        self.audit = Audit(self.get_session_key(), audit_token_name)
        self.itsi_policy_id = self.settings.get('result', {}).get('itsi_policy_id', None)
        self.kwargs = {}
        self.cfm = ConfManager(self.get_session_key(), 'SA-ITOA')

    def wait_for_job(self, searchjob, maxtime=-1):
        """
        Wait up to maxtime seconds for searchjob to finish.  If maxtime is
        negative (default), waits forever.  Returns true, if job finished.
        """
        pause = 0.2
        lapsed = 0.0
        while not searchjob.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return searchjob.is_done()

    def generate_search(self, group_id):
        """
        Formats eventing search command with params passed in from alert action.
        """
        config = self.get_config()
        search_string = '| makeresults | ' + self.search_command
        jira_ticket_id = self.settings.get('result', {}).get('jira_ticket_id', '')
        if config:
            for field_name, value in config.items():
                # Condition to update the Jira ticket via NEAP if already linked to an episode
                if field_name == 'jira_key' and not value:
                    value = jira_ticket_id
                if not value:
                    continue
                value = value.replace('"', '\\"')  # escape double quotes
                search_string += f' {field_name}="{value}",'
            search_string = search_string.rstrip(',')
        self.logger.info('Search string generated: `%s` for group_id: `%s`', search_string, group_id)
        return search_string

    def run_search(self, search, group_id):
        """
        Runs the search command
        """
        try:
            search_job = self.service.jobs.create(search)
        except HTTPError as e:
            raise Exception(f'Error when running search "{search}" for group_id={group_id}. Error: {e}')
        return search_job

    def get_search_results(self, search_job, group_id):
        """
        Fetches the results of the eventing search command
        """
        try:
            # Get job timeout from conf
            conf = self.cfm.get_conf('notable_event_actions')
            jira_settings = conf.get('jira_cloud_issue')
            wait_time = int(jira_settings.get('job_timeout', 2000))
            self.wait_for_job(search_job, wait_time)
            result = next(results.ResultsReader(search_job.results()))
            self.logger.info('Search results for group_id from Jira "%s": %s', group_id, result)
        except StopIteration:
            error_messages = search_job.messages.get('error', [])
            if len(error_messages) > 0:
                raise Exception(f'Search command "{self.search_command}" for group_id={group_id} failed with the following error: {" ".join(error_messages)}')
            else:
                raise Exception(f'Search command "{self.search_command}" for group_id={group_id} failed to return a result. '
                                'Check the add-on configuration and input parameters.')
        return result

    def create_external_ticket(self, search_results, group_id):
        """
        Creates an external ticket object with results of eventing search command
        """
        ticket_id = search_results.get(self.search_ticket_id_field_name, None)
        ticket_url = search_results.get(self.search_ticket_url_field_name, None)

        if not ticket_id or not ticket_url:
            raise Exception(f'Search command "{self.search_command}" for group_id={group_id} failed to return an Issue Key or URL. '
                            'Check the add-on configuration and input parameters.')

        ticket_system = self.ticket_system_field_value
        external_ticket = ExternalTicket(
            group_id, self.get_session_key(), self.logger,
            action_dispatch_config=self.action_dispatch_config,
            current_user_name=self.settings.get('owner', None)
        )
        return external_ticket.upsert(ticket_system, ticket_id, ticket_url, itsi_policy_id=self.itsi_policy_id)

    def execute(self):
        """
        Runs jira eventing command then uses the results to generate an external ticket
        """
        group_id = self.get_config()['correlation_id']
        self.logger.debug(f'Received settings from splunkd=`{json.dumps(self.settings)}`, group_id={group_id}')

        try:
            search = self.generate_search(group_id)
            search_job = self.run_search(search, group_id)
            search_results = self.get_search_results(search_job, group_id)
            self.create_external_ticket(search_results, group_id)
        except Exception as e:
            self.logger.error(f'Failed to create Jira incident for group_id={group_id}. Error: {str(e)}')
            self.logger.exception(e)
            self.audit.send_activity_to_audit({
                'event_id': group_id,
                'itsi_policy_id': self.itsi_policy_id
            }, str(e), 'Action failed for episode')
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        search_command = JiraIssueCommandWrapper(input_params)
        search_command.execute()
