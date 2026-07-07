import os
import sys

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

from sync import AnalyticProcessor


@Configuration()
class SyncAnalyticsCommand(GeneratingCommand):
    def generate(self):
        self.logger.debug('Syncing analytics with SnapAttack API')
        token = self._metadata.searchinfo.session_key
        processor = AnalyticProcessor(splunk_session_key=token)
        results = processor.update_deployed_analytics()
        yield results


dispatch(SyncAnalyticsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
