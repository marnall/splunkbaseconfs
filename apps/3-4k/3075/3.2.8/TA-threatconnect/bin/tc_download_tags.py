#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Download Tags"""
import sys
import os
import json

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class DownloadTags(BaseGeneratingCommand):
    """Download Tag Data from ThreatConnect.

    Usage:
    | tctags - Returns a unique list of tags for all *enabled* Owners.
    | tctags owner_key=<owner key> - Return a unique list tags for the specified Owner key.
    | tctags owner_name=<owner name> - Return a unique list tags for the specified Owner name.
    """

    # args
    owner_key = Option(doc='The **owner key** from the KV Store.', require=False)
    owner_name = Option(doc='The **owner name**.', require=False)
    tag_limit = Option(doc='The maximum number of tags to download.', require=False)

    # properties
    filename = os.path.basename(__file__)
    owner_names = []

    def generate(self):
        """Implement the generate method it download group data."""
        owner_names = []
        if self.owner_key is not None:
            self.logger.debug(f'owner_key={self.owner_key}')
            owner_data = self.tcs.collections.owners.query_by_id(self.owner_key)
            owner_names.append(owner_data.get('name'))
        elif self.owner_name is not None:
            self.logger.debug(f'owner_name={self.owner_name}')
            owner_names.append(self.owner_name)
        else:
            # retrieve all enabled owners
            config_stanza_prefix = 'TC-Indicator-Download'
            for owner_data in self.tcs.collections.owners.paginate():
                saved_search_name = f"{config_stanza_prefix}-{owner_data.get('id')}"
                try:
                    # retrieve saved search configuration for this owner
                    ss_data = self.service.saved_searches[saved_search_name]
                    if int(ss_data.disabled) == 0:
                        # only retrieve tags if search is not disabled
                        owner_names.append(owner_data.get('name'))
                except KeyError:
                    self.logger.error(f'Saved search {saved_search_name} could not be found.')

        # iterate owners and tags
        self.logger.debug(f'''owner_names={','.join(owner_names)}''')
        limit_hit = False
        for owner_name in owner_names:
            if limit_hit is True:
                break

            self.logger.info(f'action=retrieve-tags, owner={owner_name}')
            for tag_count, t in enumerate(self.retrieve_tags(owner_name), start=1):
                if self.tag_limit is not None and tag_count >= int(self.tag_limit):
                    # check for tag limit
                    self.logger.warning(
                        f'action=limit-hit, tag-limit={self.tag_limit}, tag-count={tag_count}'
                    )
                    limit_hit = True
                    break
                yield {'_raw': json.dumps(t)}

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

    def retrieve_tags(self, owner=None):
        """Retrieve tags for specified owner.

        Args:
            owner (str, optional): The TC owner name. Defaults to None.

        Returns:
            list: A list of tag names
        """
        params = {
            'resultLimit': 10000,
            'resultStart': 0,
        }
        if owner is not None:
            params['owner'] = owner

        tag_count = 0
        while True:
            r = self.tcs.session.get('/v2/tags', params=params)
            if not r.ok:
                self.error_exit(None, 'Failed to retrieve tags from ThreatConnect API.')

            # load tag data from API response
            tag_data = r.json().get('data', {}).get('tag', [])
            self.logger.debug(f'action=api-downloaded, tag-count={len(tag_data)}')

            # yield individual tags
            for tag in tag_data:
                tag_count += 1
                yield tag

            if not tag_data or len(tag_data) < params.get('resultLimit'):
                # check for end of data
                break

            # increment start position for pagination
            params['resultStart'] += params.get('resultLimit')


if __name__ == '__main__':
    dispatch(DownloadTags, sys.argv, sys.stdin, sys.stdout, __name__)
