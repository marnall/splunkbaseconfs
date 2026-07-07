# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import json

from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path

from ITOA.setup_logging import getLogger
from itsi.event_management.sdk.custom_group_action_base import CustomGroupActionBase
from ITOA.event_management.notable_event_ref_url import NotableEventReferenceURL
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration


class LinkURL(CustomGroupActionBase):
    """
    Class that performs Link URL action on notable events group.
    """

    URL_KEY = 'url'
    URL_DESCRIPTION_KEY = 'url_description'
    URL_OPERATION_KEY = 'operation'
    URL_KWARGS_KEY = 'kwargs'

    def __init__(self, settings):
        """
        Initialize the object
        @type settings: dict/basestring
        @param settings: incoming settings for this alert action that splunkd
            passes via stdin.

        @returns Nothing
        """
        self.logger = getLogger(logger_name="itsi.event_action.link_url")

        super(LinkURL, self).__init__(settings, self.logger)

        self.action_dispatch_config = ActionDispatchConfiguration(self.get_session_key(), self.logger)
        self.url = None
        self.url_description = None
        self.url_operation = None
        self.kwargs = {}

    def check_str_return_none_for_empty(self, input_str):
        """
        Check if the given string is empty, if yes, return None. Otherwise, return original string.
        We will use this function to simplify None/Empty string check.
        @type input_str: basestring
        @param input_str: the given string

        @rtype basestring
        @return: the original string or None
        """
        return input_str if input_str is not None and len(input_str.strip()) > 0 else None

    def get_url_info(self):
        """
        Gets url information from configs and
        sets class variables.
        """
        config = self.get_config()
        self.url = self.check_str_return_none_for_empty(config.get(self.URL_KEY, None))
        self.url_description = self.check_str_return_none_for_empty(config.get(self.URL_DESCRIPTION_KEY, None))
        self.url_operation = self.check_str_return_none_for_empty(config.get(self.URL_OPERATION_KEY, None))

        temp = self.check_str_return_none_for_empty(config.get(self.URL_KWARGS_KEY, None))
        if temp is not None:
            try:
                self.kwargs = json.loads(temp)
            except Exception as e:
                self.logger.error('Invalid kwargs provided for creating url. Exception: %s', e)
                sys.exit(1)

    def upsert_url(self, episode_ids):
        """
        Updates/creates url for single or multiple episodes
        using NotableEventReferenceURL module.

        @param episode_ids: list of episode ids
        """
        session_key = self.get_session_key()
        ref_url = NotableEventReferenceURL(
            session_key,
            action_dispatch_config=self.action_dispatch_config,
            current_user_name=self.settings.get('owner', None)
        )
        if len(episode_ids) == 1:
            ref_url.upsert(episode_ids[0], self.url, self.url_description, **self.kwargs)
        elif len(episode_ids) > 1:
            ref_url.bulk_upsert(episode_ids, self.url, self.url_description, **self.kwargs)
        else:
            self.logger.info("No associated episodes to upsert url.")

    def delete_url(self, episode_ids):
        """
        Deletes url for single or multiple episode using NotableEventReferenceURL module.
        @param episode_ids: list of episode ids
        """
        session_key = self.get_session_key()
        ref_url = NotableEventReferenceURL(
            session_key,
            action_dispatch_config=self.action_dispatch_config,
            current_user_name=self.settings.get('owner', None)
        )
        if len(episode_ids) == 1:
            ref_url.delete(episode_ids[0], description=self.url_description)
        elif len(episode_ids) > 1:
            ref_url.delete_bulk(episode_ids, description=self.url_description)
        else:
            self.logger.info("No associated episode to delete url.")

    def execute(self):
        """
        Performs two types of action, create/update and delete.
        1. create/update url: fetches episodes from result file and perform
        create/update url for each group.
        2. delete url: fetches episode from result file and performs delete
        url for single episode.
        """
        self.get_url_info()
        self.logger.debug('Received settings from splunkd=`%s`', json.dumps(self.settings))
        try:
            if self.url_operation == 'upsert':
                if self.url is None:
                    self.logger.error('URL must be defined to create url.')
                    sys.exit(1)
                if self.url_description is None:
                    self.logger.error('URL description must be defined to create URL.')
                    sys.exit(1)

                groups = []
                for data in self.get_group():
                    group_id = self.extract_group_or_event_id(data)
                    groups.append(group_id)
                self.upsert_url(groups)

            elif self.url_operation == 'delete':
                # Both single and bulk deletion are supported.
                # For bulk deletion:
                # If user doesn't specify description, all links in the same episode(s) will be deleted.
                # If description is specified, all links for the episode(s) with the same description will be deleted.
                groups = []
                for data in self.get_group():
                    group_id = self.extract_group_or_event_id(data)
                    groups.append(group_id)
                self.delete_url(groups)

        except ValueError:
            pass  # best case, try every event.

        except Exception as e:
            self.logger.error('Failed to execute link url action.')
            self.logger.exception(e)
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        input_params = sys.stdin.read()
        link_url = LinkURL(input_params)
        link_url.execute()
