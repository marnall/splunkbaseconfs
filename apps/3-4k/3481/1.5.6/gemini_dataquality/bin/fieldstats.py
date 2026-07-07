#!/usr/bin/env python

import sys
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators


@Configuration()
class FieldCountCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """
    showfields = Option(
        doc='''
        **Syntax:** **showfields=***<true/false>*
        **Description:** Wheter to list non-empty fields''',
        require=False, validate=validators.Boolean())

    internal_fields = [ 'eventtype', 'product', 'tag', 'vendor', 'ids_type', 'tag::eventtype', 'timestamp', "_raw", "_bkt", "splunk_server_group", "_cd", "_sourcetype", "_kv", "_si", "_eventtype_color", "_indextime", "_time", "_serial", "date_hour", "date_mday", "date_minute", "date_month", "date_second", "date_wday", "date_year", "date_zone", "host","source","sourcetype","index","linecount","splunk_server","timeendpos","timestartpos","punct"]
    def stream(self, records):
        self.logger.debug('CountMatchesCommand: %s', self)  # logs command line
        
        for record in records:
            fields = set(record.keys()) - set(self.internal_fields)
            no_empty_fields = []

            length = 0
            field_count = 0
            for field in fields:
                length = length + len(record[field])
                if len(record[field]) > 0:
                    field_count = field_count + 1
                    no_empty_fields.append(field)

            record["fieldlength"] = length
            
            record["fieldcount"] = field_count
            if self.showfields:
                record["fields"]     = ", ".join(no_empty_fields)
            yield record

dispatch(FieldCountCommand, sys.argv, sys.stdin, sys.stdout, __name__)
