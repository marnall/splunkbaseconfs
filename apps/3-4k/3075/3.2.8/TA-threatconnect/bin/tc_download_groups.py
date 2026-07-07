#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Download Groups Command"""
import json
import os
import sys
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class DownloadGroupsCommand(BaseGeneratingCommand):
    """Command to download Groups

    This command is used by the saved searches configure on the Indicator Download
    page.

    Usage:
    | tcgroupdownload owner_key=<owner kv store key>

    e.g.,
    | tcgroupdownload owner_key=abc123
    """

    # args
    owner_key = Option(doc='The **owner key** from the KV Store.', require=True)

    # properties
    filename = os.path.basename(__file__)

    def add_result(self, action, type_, name, id_):
        """Add result entry for Splunk search output"""
        result_data = OrderedDict()
        result_data['action'] = action
        result_data['type'] = type_
        result_data['name'] = name
        result_data['id'] = id_

        self.results.append(result_data)

    @property
    def association_type_details(self):
        """Return association type details."""
        return {
            'Group': {'apiBranch': 'groups', 'apiEntity': 'group'},
            # 'Indicator': {'apiBranch': 'indicators', 'apiEntity': 'indicator'},
            # 'Victim': {'apiBranch': 'victims', 'apiEntity': 'victim'},
        }

    def associations(self, group_data, group_type):
        """Retrieve associations."""
        associations = []
        group_api_branch = self.tcs.request.group_types_data.get(group_type, {}).get(
            'apiBranch', group_type
        )
        for association_type in self.association_type_details:
            association_type_details = self.association_type_details.get(association_type)
            group_id = group_data.get('id')
            association_api_branch = association_type_details.get('apiBranch')
            url = f'/v2/groups/{group_api_branch}/{group_id}/{association_api_branch}'
            if group_type == 'Task':
                url = f'/v2/{group_api_branch}/{group_id}/{association_api_branch}'
            r = self.tcs.session.request('GET', url)
            if not r.ok:
                self.logger.warning(
                    f'Associations for {group_type}:{group_data.get("id")} could not be retrieved'
                )
                return associations
            associations_json = json.loads(r.content)
            associations_data = associations_json.get('data', {}).get(
                association_type_details.get('apiEntity')
            )
            for association in associations_data:
                associations.append(
                    {'name': association.get('name'), 'type': association.get('type')}
                )
        return associations

    @staticmethod
    def attributes(group_data):
        """Return attributes."""
        attributes = []
        for attribute in group_data.get('attribute', []):
            attributes.append(
                {
                    'type': attribute.get('type'),
                    'value': attribute.get('value'),
                    'dateAdded': attribute.get('dateAdded'),
                    'lastModified': attribute.get('lastModified'),
                    'displayed': attribute.get('displayed'),
                }
            )
        return attributes

    @staticmethod
    def tags(group_data):
        """Return tags."""
        tags = []
        for tag in group_data.get('tag', []):
            tags.append({'name': tag.get('name'), 'webLink': tag.get('webLink')})
        return tags

    @staticmethod
    def security_labels(group_data):
        """Return security labels."""
        security_labels = []
        for security_label in group_data.get('securityLabel', []):
            security_labels.append(
                {
                    'name': security_label.get('name'),
                    'description': security_label.get('description'),
                }
            )
        return security_labels

    def groups(self, group_types, owner, result_limit=500):
        """Return groups."""
        if not isinstance(group_types, list):
            group_types = group_types.split(',')

        for group_type in group_types:
            group_details = self.tcs.request.group_types_data.get(group_type)
            if not group_details:
                self.logger.warning(f'Invalid group type: {group_type}')
                continue

            result_start = 0
            has_next = True
            params = {
                'includes': ['additional', 'attributes', 'labels', 'tags'],
                'owner': owner,
                'resultStart': result_start,
                'resultLimit': result_limit,
            }

            result_count = 0
            while has_next:
                url = f'''/v2/groups/{group_details.get('apiBranch')}'''
                if group_type == 'Task':
                    url = f'''/v2/{group_details.get('apiBranch')}/'''
                r = self.tcs.session.request('GET', url, params=params)
                if not r.ok:
                    raise RuntimeError(
                        group_type, f'Failed retrieving group: {group_type} during pagination.',
                    )
                params['resultStart'] += result_limit
                groups_data = json.loads(r.text)
                if groups_data.get('data', {}).get('resultCount'):
                    result_count = groups_data.get('data', {}).get('resultCount', result_count)
                if params['resultStart'] > result_count:
                    has_next = False
                groups = groups_data.get('data', {}).get(group_details.get('apiEntity', []))
                if not isinstance(groups, list):
                    groups = [groups]
                for group in groups:
                    group.update(
                        {
                            # 'securityLabels': self.security_labels(group),
                            'associations': self.associations(group, group_type),
                            'attribute': self.attributes(group),
                            # 'ownerName': owner,
                            'type': group_type,
                            'tag': self.tags(group),
                        }
                    )
                    yield group

    def generate(self):
        """Implement generate command for group download."""
        owner = self.tcs.collections.owners.query_by_id(self.owner_key)
        owner_name = owner.get('name')
        group_types = owner.get('groupTypes', [])

        # remove any groups that have a null ownerName value
        self.tcs.collections.groups.delete(query={'ownerName': None})

        if not owner or not owner_name or not group_types:
            self.logger.warning('Owner incorrectly configured')
            return

        if not group_types:
            self.logger.warning(f'No Group Types Configured for Owner: {owner_name}')
            return

        group_tracker = {}
        for group_data in self.tcs.collections.groups.paginate(
            fields='_key,id,name,type', query={'ownerName': owner_name}
        ):
            group_id = str(group_data.get('id'))
            if group_id in group_tracker:
                # remove duplicates
                self.tcs.collections.groups.delete_by_id(group_data.get('_key'))
            else:
                group_tracker[group_id] = group_data

        try:
            for group_data in self.groups(group_types, owner_name):
                action = 'add'
                if str(group_data.get('id')) in group_tracker:
                    action = 'update'
                    group_data['_key'] = group_tracker[str(group_data.get('id'))]['_key']
                    del group_tracker[str(group_data.get('id'))]

                # add data to batch list
                self.tcs.collections.groups.batch_data(group_data)

                # add output results
                self.add_result(
                    action, group_data.get('type'), group_data.get('name'), group_data.get('id')
                )
                self.logger.debug(
                    f'''action={action}, group={group_data.get('name')}:{group_data.get('id')}'''
                )
        except RuntimeError as e:
            for group_data in self.tcs.collections.groups.paginate(
                fields='_key,id,name,type', query={'ownerName': owner_name}
            ):
                if group_data.get('type', '??') is e.args[0]:
                    del group_tracker[str(group_data.get('id'))]
            self.logger.error(e.args[1])

        # remove "deleted" groups from collection
        for data in group_tracker.values():
            self.tcs.collections.groups.delete_by_id(data.get('_key'))
            self.add_result('delete', data.get('type', '??'), data.get('name'), data.get('id'))

        # save any remaining data
        self.tcs.collections.groups.batch_save()

        # display results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return


if __name__ == '__main__':
    dispatch(DownloadGroupsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
