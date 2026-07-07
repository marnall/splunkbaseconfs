import os
import sys

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

from submit import ResultsProcessor


@Configuration()
class SubmitAnalyticHitsCommand(GeneratingCommand):
    def generate(self):
        self.logger.debug('Uploading analytic hits to SnapAttack API')
        token = self._metadata.searchinfo.session_key
        processor = ResultsProcessor(splunk_session_key=token)
        results = processor.submit_analytic_hits()
        yield results


dispatch(SubmitAnalyticHitsCommand, sys.argv, sys.stdin, sys.stdout, __name__)
