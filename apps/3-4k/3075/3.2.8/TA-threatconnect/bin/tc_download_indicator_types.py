#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ThreatConnect Indicator Types Command"""
import sys
import os

# must be imported before packages in bin/lib
from base_generating_command import BaseGeneratingCommand

from splunklib.searchcommands import dispatch, Configuration, Option


@Configuration()
class DownloadIndicatorTypesCommand(BaseGeneratingCommand):
    """Command to get Indicator Types.

    This command is used by the Event triage to populate the Indicator Type input field, Owner
    Config to populate the input field there, as well as in several other locations to populate the
    Indicator Type input fields..

    Usage:
    | tcioctypes fields=<True|False>

    e.g.,
    | tcioctypes fields=true
    """

    # args
    fields = Option(default=False, doc='Return indicator types with field data.', require=False)

    # properties
    filename = os.path.basename(__file__)

    def generate(self):
        """Implement generate command for retrieving indicator types."""
        if self.fields:
            type_fields = {}
            for indicator_type, itd in self.tcs.request.indicator_types_data.items():
                self.logger.debug(f'indicator_type: {indicator_type}, itd: {itd}')
                if self.tcs.utils.to_bool(itd.get('custom')) or indicator_type.lower() == 'file':
                    if itd.get('value1Label') is not None:
                        type_fields[f'''{indicator_type}.{itd.get('value1Label')}'''] = 0
                    if itd.get('value2Label') is not None:
                        type_fields[f'''{indicator_type}.{itd.get('value2Label')}'''] = 1
                    if itd.get('value3Label') is not None:
                        type_fields[f'''{indicator_type}.{itd.get('value3Label')}'''] = 2
                else:
                    type_fields['{}'.format(indicator_type)] = 0
            for it in type_fields:
                self.results.append({'indicatorType': it})
        else:
            for it in self.tcs.request.indicator_types:
                self.results.append({'indicatorType': it})

        for result in self.results:
            yield result

    def prepare(self):
        """Implement prepare method to perform setup required for generate."""
        if not super().prepare():
            return

        # update options
        self.fields = self.tcs.utils.to_bool(self.fields)


if __name__ == '__main__':
    dispatch(DownloadIndicatorTypesCommand, sys.argv, sys.stdin, sys.stdout, __name__)
