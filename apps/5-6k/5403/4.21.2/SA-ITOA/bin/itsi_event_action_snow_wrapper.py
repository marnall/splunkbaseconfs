# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import time

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common', 'splunklib']))

import itsi_path

from splunklib import results
from splunklib import client
from splunklib.binding import HTTPError
from SA_ITOA_app_common.solnlib.splunkenv import get_splunkd_access_info
from ITOA.setup_logging import getLogger
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
from ITOA.event_management.notable_event_ticketing import ExternalTicket
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
from ITOA.event_management.notable_event_utils import Audit
from ITOA.itoa_common import is_feature_enabled


class SnowStreamingCommandWrapper(CustomGroupActionBase):
    """
    Class that performs ServiceNow incident creation followed by External Ticket creation.
    """

    def __init__(self, settings, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.snow_wrapper")

        super(SnowStreamingCommandWrapper, self).__init__(settings, self.logger)

        self.action_dispatch_config = ActionDispatchConfiguration(self.get_session_key(), self.logger)
        self.search_command = 'snowincidentalert'
        self.search_ticket_id_field_name = 'Incident Number'
        self.search_ticket_url_field_name = 'Incident Link'
        self.ticket_system_field_value = 'Service Now'
        _, _, port = get_splunkd_access_info()
        self.service = client.connect(token=self.get_session_key(), app='SA-ITOA', port=port)
        self.audit = Audit(self.get_session_key(), audit_token_name)
        self.itsi_policy_id = self.settings.get('result', {}).get('itsi_policy_id', None)
        self.kwargs = {}

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

    def generate_search(self, config, group_id):
        """
        Formats streaming search command with params passed in from alert action.
        @param config: config params for snow wrapper
        @param group_id: group/episode id
        """
        if not config:
            config = self.get_config()
        search_string = '| makeresults'
        if config:
            ci_identifier = config.get('configuration_item', None)
            if ci_identifier:
                config['ci_identifier'] = ci_identifier
            search_string += ' | eval'
            for field_name, value in config.items():
                value = value.replace('"', '\\"')  # escape double quotes
                if field_name != 'closing_status':
                    search_string += ' {field_name}="{value}",'.format(field_name=field_name, value=value)
            search_string = search_string.rstrip(',')
        search_string += ' | ' + self.search_command
        self.logger.info('Search string generated: `%s` for group_id: `%s`', search_string, group_id)
        return search_string

    def check_group_with_ticket(self, group_id):
        """
        Checks if any snow ticket is linked to the episode
        with given group id or not.
        @param group_id: group/episode id
        """
        ticket_system = self.ticket_system_field_value
        search_string = (
            '| inputlookup itsi_notable_event_external_ticket'
            '| where ticket_system="{}" and event_id="{}"'.format(ticket_system, group_id)
        )
        self.logger.info('Search string for checking snow ticket for group id "%s": `%s`', group_id, search_string)
        search_job = self.run_search(search_string, group_id)
        self.wait_for_job(search_job, 600)
        result_count = search_job['resultCount']
        if result_count == '0':
            self.logger.info(f'No ticket exist for group: {group_id}. New ticket will not be created for Resolved or Closed status')
            sys.exit(126)

    def run_search(self, search, group_id):
        """
        Runs the search command
        @param group_id: group/episode id
        """
        try:
            search_job = self.service.jobs.create(search)
        except HTTPError as e:
            raise Exception('Error when running search "{search}" for "{group_id}". Error: {e}'.format(search=search, group_id=group_id, e=e))
        return search_job

    def get_search_results(self, search_job, group_id):
        """
        Fetches the results of the streaming search command
        @param group_id: group/episode id
        """
        try:
            self.wait_for_job(search_job, 600)
            result = next(results.ResultsReader(search_job.results()))
            self.logger.info('Search results for group_id from ServiceNow "%s": %s', group_id, result)
        except StopIteration:
            error_messages = search_job.messages.get('error', [])
            if len(error_messages) > 0:
                raise Exception('Search command "{}" failed for group "{}" with the following error: {}'
                                .format(self.search_command, group_id, ' '.join(error_messages)))
            else:
                raise Exception('Search command "{}" failed for group "{}" to return a result. '
                                'Check the add-on configuration and input parameters.'.format(self.search_command, group_id))
        return result

    def create_external_ticket(self, search_results, group_id):
        """
        Creates an external ticket object with results of streaming search command
        @param group_id: group/episode id
        """
        ticket_id = search_results.get(self.search_ticket_id_field_name, None)
        ticket_url = search_results.get(self.search_ticket_url_field_name, None)
        if not ticket_id or not ticket_url:
            raise Exception('Search command "{}" failed for group "{}" to return an incident ID or URL. '
                            'Check the add-on configuration and input parameters.'.format(self.search_command, group_id))

        ticket_system = self.ticket_system_field_value
        group_id = self.get_config()['correlation_id']
        external_ticket = ExternalTicket(
            group_id, self.get_session_key(), self.logger,
            action_dispatch_config=self.action_dispatch_config,
            current_user_name=self.settings.get('owner', None)
        )
        return external_ticket.upsert(ticket_system, ticket_id, ticket_url, itsi_policy_id=self.itsi_policy_id)

    def execute(self):
        """
        Runs snow streaming command then uses the results to generate an external ticket
        """
        self.logger.debug('Received settings from splunkd=`%s`', json.dumps(self.settings))

        try:
            config = self.get_config()
            already_validated = False
            if is_feature_enabled('itsi-ea-snow-ticket-avoid-closed-status', self.get_session_key()):
                closing_status = config['closing_status']
                closing_status_list = []
                if closing_status:
                    closing_status_list = [status.strip() for status in closing_status.split(",")]
                if config['state'] and (config['state'] in closing_status_list):
                    self.check_group_with_ticket(config['correlation_id'])
                    already_validated = True
            # if customer passes itsi_validate=check in the Custom Fields, the system validates
            # if the SNOW ticket is already created or not. If not, throws an error.
            if not already_validated:
                custom_fields = config['custom_fields']
                if custom_fields:
                    custom_fields_split = custom_fields.split("||")
                    if 'itsi_validate=check' in custom_fields_split:
                        self.check_group_with_ticket(config['correlation_id'])
                        custom_fields_split.remove('validate=check')
                        # reconstruct custom_fields
                        custom_fields = "||".join(custom_fields_split)
                        config['custom_fields'] = custom_fields
            group_id = config['correlation_id']
            search = self.generate_search(config, group_id)
            search_job = self.run_search(search, group_id)
            search_results = self.get_search_results(search_job, group_id)
            self.create_external_ticket(search_results, group_id)
        except Exception as e:
            self.logger.error('Failed to create ServiceNow incident.')
            self.logger.exception(e)
            self.audit.send_activity_to_audit({
                'event_id': self.get_config()['correlation_id'],
                'itsi_policy_id': self.itsi_policy_id
            }, str(e), 'Action failed for episode')
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        search_command = SnowStreamingCommandWrapper(input_params)
        search_command.execute()
