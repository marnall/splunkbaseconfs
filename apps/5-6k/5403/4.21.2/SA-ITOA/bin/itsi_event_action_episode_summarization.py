# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json
import time
import os

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common', 'splunklib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'ITOA', 'event_management']))

import itsi_path

from splunklib import results
from splunklib import client
from splunklib.binding import HTTPError
from SA_ITOA_app_common.solnlib.splunkenv import get_splunkd_access_info
from ITOA.setup_logging import getLogger
from ITOA.version_check import VersionCheck
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
from ITOA.event_management.notable_event_utils import Audit
from ITOA.itoa_common import is_feature_enabled
from itsi.summarization.summarization_utils import SummarizationUtils
from urllib.parse import unquote
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from ITOA.itoa_exceptions import ItoaValidationError
from ITOA.event_management.itsi_counter import ITSICounter


class EpisodeSummarization(CustomGroupActionBase):
    """
    Initiates Episode Summarization action
    """

    def __init__(self, settings, audit_token_name='Auto Generated ITSI Notable Index Audit Token'):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.episode_summarization")
        super(EpisodeSummarization, self).__init__(settings, self.logger)
        self.action_dispatch_config = ActionDispatchConfiguration(self.get_session_key(), self.logger)
        _, _, port = get_splunkd_access_info()
        self.service = client.connect(token=self.get_session_key(), app='SA-ITOA', port=port)
        self.audit = Audit(self.get_session_key(), audit_token_name)
        self.itsi_policy_id = self.settings.get('result', {}).get('itsi_policy_id', None)
        self.kwargs = {}

    def get_is_python_for_scientific_computing_app_installed_and_enabled(self):
        """
        Checks if the Python for Scientific Computing app is installed and enabled in the apps directory
        @rtype: bool
        @return: whether of not the Python for Scientific Computing app is installed and enabled
        """
        apps_path = make_splunkhome_path(['etc', 'apps'])
        for entry in os.scandir(apps_path):
            if entry.is_dir() and entry.name.startswith('Splunk_SA_Scientific_Python'):
                try:
                    cfm = ConfManager(self.get_session_key(), entry.name)
                    conf = cfm.get_conf('app')
                    install = conf.get('install')
                    state = install.get('state', 'enabled')
                    launcher = conf.get('launcher')
                    version = launcher.get('version', '4.2.0')
                    if state == 'enabled' and VersionCheck.compare(version, '4.2.0') >= 0:
                        return True
                # pylint:disable=broad-exception-caught
                except Exception as e:
                    self.logger.exception(e)
                    self.logger.error(
                        'Failed to fetch Splunk Python for Scientific Computing app info,'
                        'progressing as if app is enabled and version is 4.2.0 or later')
                    return True
        return False

    def get_summarization_settings(self):
        """
        Fetches summarization_limit from itsi_summarization.conf
        """
        summarization_limit = 30000  # return default value in case misconfiguration
        try:
            cfm = ConfManager(self.get_session_key(), 'SA-ITOA')
            conf = cfm.get_conf('itsi_summarization')
            episode_summarization = conf.get('itsi_episode_summarization')
            limit = episode_summarization.get('summarization_limit', 30000)
            try:
                summarization_limit = int(limit)
            except (ValueError, TypeError):
                self.logger.error('summarization_limit is not an integer, using default value of 30000')
        # pylint:disable=broad-exception-caught
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(
                'Failed to fetch summarization_limit for summarization,'
                'using default value of 30000 for summarization_limit')
        return summarization_limit

    def get_summarization_count(self):
        """
        Fetches the number of summarization jobs completed
        @param session_key: session key
        @param group_id: group/episode id
        """
        itsi_counter = ITSICounter(session_key=self.get_session_key(), current_user_name='nobody')
        summarization_count = 0
        current_value = itsi_counter.get("summarization")
        if current_value:
            summarization_count = current_value['value']
        return summarization_count

    def extract_group_status(self, group_data):
        """
        Extract status from given group_data
        @type group_data: basestring
        @param group_data: group object from which we try to extract status
        @rtype: int
        @return: status
        """
        if group_data is None:
            raise TypeError('No group_data received')

        group_status_key = 'status'
        if not isinstance(group_data, dict):
            try:
                group_data = json.loads(group_data)
            except (TypeError, ValueError) as exc:
                self.logger.exception(exc)
                msg = ('We will only work with JSON type data. '
                       'Received: {}. Type: {}').format(group_data,
                                                        type(group_data).__name__)
                self.logger.error(msg)
                raise Exception(msg)
        try:
            group_status = int(group_data.get(group_status_key))
        except (ValueError, TypeError):
            self.logger.error('status is not an integer, extracting as unknown')
            return 0
        return group_status

    def get_notable_event_end_status_label(self, status):
        """
        Gets the label defined in itsi_notable_event_status.conf if end flag enabled for status
        @type status: int
        @param status: status of notable event/group
        @rtype: string/NoneType
        @return: notable_event_status_label/None
        """
        notable_event_status_label = None
        try:
            cfm = ConfManager(self.get_session_key(), 'SA-ITOA')
            conf = cfm.get_conf('itsi_notable_event_status')
            itsi_notable_event_status = conf.get(str(status))
            notable_event_status_end_flag = itsi_notable_event_status.get('end', None)
            if notable_event_status_end_flag != '1':
                return notable_event_status_label
            notable_event_status_label = itsi_notable_event_status.get('label', None)
        # pylint:disable=broad-exception-caught
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(
                'Failed to fetch itsi_notable_event_status.conf label for summarization check,'
                'progressing as if episode is not in Closed status')
        return notable_event_status_label

    def execute(self):
        """
        Runs snow streaming command then uses the results to generate an external ticket
        """
        self.logger.debug('Received settings from splunkd=`%s`', json.dumps(self.settings))

        try:
            group = next(self.get_group())
            # Assuming only the first entry is the group id
            group_id = self.extract_group_or_event_id(group)
            self.logger.debug('Episode ID: %s', group_id)
            is_summarization_enabled = is_feature_enabled("itsi-episode-summarization", self.get_session_key())
            if not is_summarization_enabled:
                raise Exception("Summarization feature is not enabled")

            # Check if Python for Scientific Computing app is installed
            is_psc_installed = self.get_is_python_for_scientific_computing_app_installed_and_enabled()
            if not is_psc_installed:
                msg = "New Summarization is not allowed, Splunk Python for Scientific Computing version 4.2.0 or later must be installed and enabled to use episode summarization"
                self.logger.error(msg)
                raise Exception(msg)

            # Check if the summarization limit is reached
            summarization_limit = self.get_summarization_settings()
            self.logger.debug("summarization_limit %s", summarization_limit)
            summarization_count = self.get_summarization_count()
            self.logger.debug("summarization_count %s", summarization_count)
            # check if the number of summarization limit is reached
            if summarization_count >= summarization_limit:
                self.logger.error(f"New Summarization is not allowed, summarization limit {summarization_limit} reached")
                raise Exception(f"New Summarization is not allowed, summarization limit {summarization_limit} reached")

            # Check if the episode status is set to closed
            group_status = self.extract_group_status(group)
            status_label = self.get_notable_event_end_status_label(group_status)
            if status_label is not None:
                msg = f"New Summarization is not allowed, episode status is set to {status_label}"
                self.logger.error(msg)
                raise Exception(msg)

            config = self.get_config()
            data = None
            if config.get('custom_queries', None):
                custom_queries_str = config.get('custom_queries', None).replace('\'', '"')
                data = json.loads(custom_queries_str)
                for record in data:
                    spl = record.get('spl')
                    # Ensure spl data is decoded properly
                    spl = unquote(spl)
                    record['spl'] = spl
            invoked_by = self.settings.get('owner', 'splunk-system-user')
            summarization_util = SummarizationUtils(self.get_session_key(), 'nobody', 'episode')
            summarization_util.invoke_summarization_call(group_id, custom_queries=data, invoked_by=invoked_by, itsi_policy_id=self.itsi_policy_id)
        except Exception as e:
            self.audit.send_activity_to_audit({
                'event_id': group_id,
                'itsi_policy_id': self.itsi_policy_id
            }, str(e), 'Action failed for episode')
            self.logger.error(f'Failed to create Episode summarization. {str(e)}')
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        search_command = EpisodeSummarization(input_params)
        search_command.execute()
