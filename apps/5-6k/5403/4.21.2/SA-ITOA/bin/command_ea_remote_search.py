# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
import time
import hashlib
from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
import itsi_path
from ITOA.setup_logging import logger

from SA_ITOA_app_common.splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from ITOA.event_management.notable_event_utils import ActionDispatchConfiguration
from SA_ITOA_app_common.solnlib.splunk_rest_client import SplunkRestClient
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from SA_ITOA_app_common.splunklib import results


@Configuration(distributed=False, generates_timeorder=True, local=True)
class EARemoteSearch(GeneratingCommand):
    """
    Executes a search against a remote splunk environment and returns the results.
    This only executes searches against the configured remote host for ITSI EA.

    Command Usage in SPL:
        | earemotesearch remote_spl="search `itsi_grouped_alerts_index` itsi_group_id=\"12345\"" | <local spl>

    Note there are implications to this command owing to the settings in commands.conf for it. For example,
    it must output events in timeorder with latest times first. Please see commands.conf.spec and the earemotesearch
    stanza for more details before editing the code.
    """

    remote_spl = Option(
        doc="""
        **Syntax:** **remote_spl=***<escaped spl string>*
        **Description:** The SPL to run on a remote search node""",
        require=True
    )

    def get_conf_remote_search_timeout(self):
        """
        Fetches the remote_ea_search_timeout from itsi_settings.conf
        """
        try:
            cfm = ConfManager(self.service.token, 'SA-ITOA')
            conf = cfm.get_conf('itsi_settings')
            remote_dispatch_settings = conf.get('episode_action_dispatch')
            return int(remote_dispatch_settings['remote_ea_search_timeout'])
        except Exception as e:
            logger.exception(e)
            logger.error('Failed to fetch remote_ea_search_timeout, using default value 120 secs')
            return 120

    @staticmethod
    def wait_for_job(search_job, maxtime=-1):
        """
        Wait up to maxtime seconds for searchjob to finish.  If maxtime is
        negative (default), waits forever.  Returns true, if job finished.
        """
        pause = 0.5
        lapsed = 0.0
        while not search_job.is_done():
            time.sleep(pause)
            lapsed += pause
            if lapsed > maxtime >= 0:
                break
        return search_job.is_done()

    @property
    def search_earliest(self):
        try:
            return self.search_results_info.startTime
        except AttributeError:
            # If you do all time, than the startTime will not exist, so you have to fake it
            return ''

    @property
    def search_latest(self):
        try:
            return self.search_results_info.endTime
        except AttributeError:
            # If you do all time, than the endTime will not exist, so you have to fake it
            return ''

    def get_search_job(self):
        """
        Creates search job based on the remote spl if it does not appear to exist.
        Otherwise fetches existing search job.
        """
        action_dispatch_config = ActionDispatchConfiguration(local_session_key=self.service.token, logger=self.logger)
        remote_client = SplunkRestClient(action_dispatch_config.get_master_host_session_key(), 'SA-ITOA',
                                         scheme=action_dispatch_config.remote_ea_scheme,
                                         host=action_dispatch_config.remote_ea_host,
                                         port=action_dispatch_config.remote_ea_port)

        hash_time = int(time.time())
        hash_time = hash_time - (hash_time % 20)  # within the last twenty seconds
        hash_string = str(hash_time) + str(self.remote_spl) + str(self.search_earliest) + str(
            self.search_latest)
        search_id = hashlib.sha256(hash_string.encode()).hexdigest()
        remote_search = None
        try:
            remote_search = remote_client.job(search_id)
        except Exception:
            pass  # search job doesn't exist or is deleted

        if not remote_search:
            remote_search = remote_client.jobs.create(
                self.remote_spl,
                id=search_id,
                earliest_time=self.search_earliest,
                latest_time=self.search_latest
            )
            logger.info('Remote search dispatched on %s with earliest %s, latest %s, got sid=%s',
                        action_dispatch_config.remote_ea_mgmt_uri, self.search_earliest, self.search_latest,
                        remote_search.sid)
        return remote_search

    def generate(self):
        search_timeout = self.get_conf_remote_search_timeout()
        remote_search = self.get_search_job()
        is_search_completed = self.wait_for_job(remote_search, search_timeout)
        # Count 0 overrides the default count of 100, allowing all results to be returned and streamed, ideally
        # we would paginate this in pages of a 100 or so, but for our use case this is probably okay
        if is_search_completed:
            for result in results.ResultsReader(remote_search.results(count=0)):
                yield result


dispatch(EARemoteSearch, sys.argv, sys.stdin, sys.stdout, __name__)
