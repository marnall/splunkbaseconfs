import os
import sys
import time
import splunklib.client as client
import splunklib.results as results
from splunklib.searchcommands import (Configuration, GeneratingCommand, 
    Option, validators, dispatch)




@Configuration(type='reporting')
class RebuildVulnLookup(GeneratingCommand):
    """ Rebuilds the io_vuln_data_lookup and sc_vuln_data_lookup kv stores
    
    ##Syntax
    
    .. code-block::
        rebuildvulnlookup delete=<bool>
    
    ##Description
    Rebuild the vuln lookup tables for all time. You can force it to delete the current data first to ensure everything is up to date. 
    
    
    ##Example
    Count the number of words in the `text` of each tweet in tweets.csv and store the result in `word_count`.
    .. code-block::
        | rebuildvulnlookup delete=true
    """

    delete = Option(
        doc='''
        **Syntax:** **delete=****
        **Description:** If set we will not empty the lookups before updating them.''',
        require=False,
        default=True,
        validate=validators.Boolean()
    )

    def generate(self):
        self.logger.error('delete: {}'.format(self.delete))
        lookups = [
            'io_vuln_data_lookup',
            'sc_vuln_data_lookup'
        ]
        searches = [
            'Tenable IO Vuln Data - All Time',
            'Tenable SC Vuln Data - All Time'
        ]
        if self.delete:
            for lookup in lookups:
                self.delete_lookup(lookup)

        for search in searches:
            yield self.rebuild_saved_search(search)

    def run_search(self, search):
        self.logger.info('Executing search: {}'.format(search))
        job = self.service.jobs.create(search, exec_mode="normal")
        while job.is_done() == False:
            if not job.is_ready():
                time.sleep(2)
                continue
            self.logger.debug('Search: {} is {:.3f}% complete'.format(search, float(job["doneProgress"])*100))
        self.logger.info("Search Complete: {} ".format(search))
        result_count = job['resultCount']
        job.cancel()
        return result_count

    def delete_lookup(self, lookup_name):
        search = '| outputlookup {}'.format(lookup_name)    
        self.logger.info('Truncating lookup table: {}'.format(lookup_name))
        result_count = self.run_search(search)
            
    def rebuild_saved_search(self, savedsearch_name):
        search = '| savedsearch "{}"'.format(savedsearch_name)
        self.logger.info('Running saved search: {}'.format(savedsearch_name))
        result_count = self.run_search(search)
        return { "Name":savedsearch_name, "No of events Written": result_count}

dispatch(RebuildVulnLookup, sys.argv, sys.stdin, sys.stdout, __name__)
