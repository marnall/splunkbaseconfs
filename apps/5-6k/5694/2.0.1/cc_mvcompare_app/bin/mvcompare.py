#!/usr/bin/env python

from __future__ import absolute_import, division, print_function, unicode_literals
from compare import intersection

import os
import sys

#import of splunklib must follow these 2 lines to ensure the app uses the local splunklib python library
splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'cc_mvcompare_app', 'lib'))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class mvcompare(StreamingCommand):

    #First of 2 compared fields.
    mv_left = Option(
        doc='''
        **Syntax:** **mvfield1=***<fieldname>***
        **Description:** Name of the first multivalue field''',
        require=True, validate=validators.Fieldname())

    #Second of 2 compared fields.
    mv_right = Option(
        doc='''
        **Syntax:** **mvfield2=***<fieldname>***
        **Description:** Name of the second multivalue field''',
        require=True, validate=validators.Fieldname())

    #Case controller. Not required and by default case is ignored.
    case_sensitive = Option(
        doc='''
        **Syntax:** **case_sensitive=***true|false***
        **Description:** Enable (true) or disable (false) case senitivity. Default is false''',
        require=False, default=False, validate=validators.Boolean())

    #Delimit Option. Not required and by default do not delimit.
    delim = Option(
        doc='''
        **Syntax:** **delim=***none|space|comma***
        **Description:** Control string delimiter. Default is None''',
        require=False, default=None)

    def stream(self, records):
        self.logger.debug('mvcompare: %s', self)  # logs command line

        #set variables to pull from splunk stream function
        mv_left = self.mv_left
        mv_right = self.mv_right
        case_sensitive = self.case_sensitive
        delim = self.delim


        for record in records:

            #verify fields exist and are accurate
            if mv_left not in record:
                raise ValueError("Missing field: %s" % mv_left)
            if mv_right not in record:
                raise ValueError("Missing field: %s" % mv_right)
            if delim == '':
                raise ValueError("By default mvcompare does not set a delimiter. Remove the delim option if empty.")

            #set required fields by pulling them from the splunk record/event
            left = record[mv_left]
            right = record[mv_right]

            #output data to record
            record['intersecting_values'], record['intersecting_count'], record['left_values'], record['left_count'], record['right_values'], record['right_count'], record['relationship'], record['relationship_status'] = intersection(left, right, case_sensitive, delim)

            yield record
            

dispatch(mvcompare, sys.argv, sys.stdin, sys.stdout, __name__)
