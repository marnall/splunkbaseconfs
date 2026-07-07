"""
This function will take one argument, the name of another saved search
and execute that search.  Result set passed to the trigger should be
returned unaltered
"""

from __future__ import print_function
import sys,re
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, Boolean
import base64
import json
import time
import collections

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def is_sequence(obj):
    if isinstance(obj, collections.Sequence) and not \
       isinstance(obj, basestring):
        return True
    return False

@Configuration()
class SearchTrigger(ReportingCommand):
    search_name = Option(require=True)
    use_all_values = Option(validate=Boolean())
    mvdelim = Option(default=" ")

    def log(self, message):
        self.logger.error("SearchTriggerLog: " + repr(message))

    def prepare(self):
        self.log("Initializing command and finding search to run")
        self.saved_search = None
        self.count = 0
        if self.service is None:
            return
        for search in self.service.saved_searches.list():
            self.log(search.name)
            if search.name == self.search_name:
                self.saved_search = search
        if self.saved_search is None:
            raise Exception("Saved search could not be found: " + self.search_name)

    @Configuration()
    def map(self, records):
        yield records


    def reduce(self, records):
        self.log(self.fieldnames)
        token_overrides = {}
        for override in self.fieldnames:
            key, value = override.split(":")
            token_overrides["args."+key] = {
                    'field': value,
                    'value': ''
                    }
            if self.use_all_values:
                token_overrides["args."+key]['value'] = []
        self.log(token_overrides)
        self.log(self.phase)
        self.log("Running search: " + self.saved_search.name)
        results = []
        first = True
        overrides = {}
        for record in records:
            for key, override in token_overrides.iteritems():
                value = override['value']
                field = override['field']
                self.log(record)
                self.log(value)
                if field in record:
                    if self.use_all_values:
                        if key not in overrides:
                            overrides[key] = []
                        overrides[key].append(record[field])
                    elif first:
                        overrides[key] = record[field]
            results.append(record)
            first = False
        if self.saved_search is None:
            return results
        for key, override in overrides.iteritems():
            if is_sequence(override):
                overrides[key] = self.mvdelim.join(override)
                
        job = self.saved_search.dispatch(**overrides)
        return results

if __name__ == '__main__':
   dispatch(SearchTrigger, sys.argv, sys.stdin, sys.stdout, __name__)
