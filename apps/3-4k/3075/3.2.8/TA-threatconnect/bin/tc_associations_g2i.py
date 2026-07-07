#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Group to Indicator Association"""
import sys
import os
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class AssociationsG2ICommand(BaseGeneratingCommand):
    """Command to get Indicator associations from a Group.

    This command is used by the diamond dashboard to retrieve Indicator associations
    for the provided group.

    Usage:
    | tcascg2i group_key=<Group Key> recursive_level=<0|1|Default=0>

    e.g.,
    | tcascg2i group_key=5ebc545cbbbbbf66eb45bc17 recursive_level=0
    """

    # args
    group_key = Option(
        doc='The Group **key** used to retrieve indicator associations.', require=True
    )
    recursive_level = Option(
        default=0, doc='How many levels deep to fetch for associations. Defaults to 0.'
    )

    # properties
    filename = os.path.basename(__file__)

    def add_result(self, indicator, type_):
        """Add result entry for Splunk search output"""
        result_data = OrderedDict()
        result_data['indicator'] = indicator
        result_data['type'] = type_
        self.results.append(result_data)

    def generate(self):
        """Implement generate command for Group to Indicator Associations."""
        group_data = self.tcs.collections.groups.query_by_id(
            key=self.group_key, fields='id,name,type'
        )

        # get associations
        group_association_results = [
            {
                'id': group_data.get('id'),
                'name': group_data.get('name'),
                'type': group_data.get('type'),
            }
        ]

        # support for 1 level or recursion currently (per requirements)
        if self.recursive_level != 0:
            group_association_results.append(self.tcs.request.get_group_associations(group_data))

        for gar in group_association_results:
            self.add_result(indicator=gar.get('indicator'), type_=gar.get('type'))

        # display the results
        for r in self.results:
            yield r

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update options
        self.recursive_level = int(self.recursive_level)


if __name__ == '__main__':
    dispatch(AssociationsG2ICommand, sys.argv, sys.stdin, sys.stdout, __name__)
