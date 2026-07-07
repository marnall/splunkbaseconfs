#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals
from logging import exception
from delta import deltas

import os
import sys

#import of splunklib must follow these first 2 lines to ensure the app uses the local splunklib python library
splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'cc_deltavalues_app', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class deltavalues(StreamingCommand):

    def stream(self, records):
        self.logger.debug('deltavalues: %s', self)  # logs command line

        #Verify correct command syntax
        if len(self.fieldnames) != 1:
            raise Exception('Usage: deltavalues <list-value>')

        #Verify given field has the right syntax (contains valid characters)
        validate = validators.Fieldname()
        try:
            delta_field = validate(self.fieldnames[0])
            
        except ValueError:
            raise Exception(f'{self.fieldnames[0]} is not a valid field name')

        #Initialize
        previous_field=[]
        count = 0

        for record in records:

            #Verify field exists in SPL search
            try:
                current_field = record[delta_field]
            except KeyError:
                raise Exception(f'{self.fieldnames[0]} is not a valid field name.')
            
            #Verify field is the correct field-type
            if isinstance(current_field, str):
                if current_field:
                    current_field = [current_field]
                else:
                    current_field = []
            
            #Ignore first record - this output / syntax matches that of Splunk native "delta" command
            if count == 0:
                count+=1
                
                record['delta_count'] = 0
                record['delta_values'] = ""
            else:
                delta = deltas(current_field, previous_field)
                record['delta_count'] = delta.get_delta_count()
                record['delta_values'] = delta.get_delta_values()

            previous_field = current_field
            yield record

dispatch(deltavalues, sys.argv, sys.stdin, sys.stdout, __name__)