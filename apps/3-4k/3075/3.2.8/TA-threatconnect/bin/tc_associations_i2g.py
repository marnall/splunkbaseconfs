#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Indicator to Group Associations"""
import sys
import os
from collections import OrderedDict

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class AssociationsI2GCommand(BaseGeneratingCommand):
    """Command to get Group associations from a Indicator.

    This command is not actively used in the App.

    Usage:
    | tcasci2g indicator=<Indiator Value> owner=<Organization Name> recursive_level=<0|1|Default=0>

    e.g.,
    | tcasci2g indicator=example.com owner=TCI recursive_level=0
    """

    # args
    indicator = Option(
        doc='The Indicator **value** used to retrieve group associations.', require=True
    )
    owner = Option(doc='The Owner **name** that the Indicator resides in.', require=True)
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
        """Implement generate command for Indicator to Group Associations."""
        indicator_data = self.tcs.collections.indicators.query(
            fields='_key,indicator,ownerName,type',
            query={'indicator': self.indicator, 'ownerName': self.owner},
        )

        # need at least one result returned
        if not indicator_data:
            return

        indicator_data = indicator_data[0]
        indicator_association_results = [
            {'indicator': indicator_data.get('indicator'), 'type': indicator_data.get('type')}
        ]

        # support for 1 level or recursion currently (per requirements)
        if self.recursive_level != 0:
            indicator_association_results.append(
                self.tcs.request.get_indicator_associations(indicator_data)
            )

        group_association_results = []
        for iar in indicator_association_results:
            try:
                group_association_results = self.tcs.request.get_group_associations(iar)
            except Exception:  # nosec
                # best effort on getting group associations
                group_association_results = []

        for group in group_association_results:
            self.results.append(group)

        # display the results
        for result in self.results:
            yield result

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update options
        self.recursive_level = int(self.recursive_level)


if __name__ == '__main__':
    dispatch(AssociationsI2GCommand, sys.argv, sys.stdin, sys.stdout, __name__)
